import asyncio
from asyncio import Task
from datetime import datetime, timedelta
from random import randint
from typing import Optional, Dict

from models.event import Event, update_events, action_event
from models.facility import Facility
from models.usercontext import UserContext
from modules.console_util import print_events
from modules.math_util import percentage_of


class MyWellnezz:
    def __init__(self):
        self.lesson_update_task: Optional[Task] = None
        self.print_task: Optional[Task] = None
        self.book_tasks: Dict[str, Task] = {}
        self.events: Dict[str, Event] = {}
        self.lock_events = asyncio.Lock()
        self.lock_tasks = asyncio.Lock()
        self.long_cycle = 60 * 10
        self.small_cycle = 30
        self.cycle_timeout = self.long_cycle
        self.cycle_iteration = 1
        self.run = True
        self.test = False

    async def get_events(self) -> Dict[str, Event]:
        async with self.lock_events:
            return self.events

    async def get_event(self, idx: str) -> Event:
        async with self.lock_events:
            return self.events[idx]

    async def set_events(self, user: UserContext, facility: Facility):
        async with self.lock_events:
            d = int((datetime.now()).strftime("%Y%m%d"))
            self.events = {k: v for k, v in (await update_events(user, facility, d)).items() if not v.is_ended()}

    async def get_event_id_by_index(self, index: int) -> Optional[str]:
        ev = await self.get_events()
        return next((key for i, key in enumerate(ev.keys()) if i == abs(index)), None)

    async def get_last_status_event(self, status: str) -> str:
        tasks = await self.get_book_tasks()
        if len(tasks) > 0:
            return ''
        events = await self.get_events()
        event = None
        for i, value in enumerate(events.values()):
            if value.get_status().lower() == status.lower():
                event = str(i)
        return event

    async def set_event_status(self, idx: str, status: str) -> None:
        (await self.get_event(idx)).status = status

    async def set_book_task(self, user: UserContext, facility: Facility, key: str, event: Event):
        if key in self.book_tasks and not self.book_tasks[key].done():
            self.book_tasks[key].cancel()
            self.book_tasks.pop(key)
            await self.set_event_status(key, event.get_status())
            return
        self.book_tasks[key] = asyncio.create_task(self._book_event_loop(user, facility, key))

    async def get_book_tasks(self) -> Dict[str, Task]:
        async with self.lock_tasks:
            return self.book_tasks

    async def get_book_task(self, idx: str) -> Task:
        async with self.lock_tasks:
            return self.book_tasks[idx]

    async def pop_book_task(self, idx: str) -> None:
        async with self.lock_tasks:
            self.book_tasks.pop(idx)

    def set_event_task(self, user: UserContext, facility: Facility):
        if self.print_task is None or self.print_task.done():
            self.print_task = asyncio.create_task(self._events_loop(user, facility))

    async def _book_event_loop(self, user: UserContext, facility: Facility, key: str):
        event = None
        e_count = 0
        while True:
            try:
                event = await self.get_event(key)
                e_count = 0
            except Exception as ex:
                print(f'Class not found: {ex}')
                e_count += 1
            if e_count > 5 or not event or event.is_ended() or event.is_started():
                break
            elif event.get_status().lower() == 'open' or event.is_participant:
                if user.token is None or not user.token:
                    await user.refresh()
                if await action_event(user, event):
                    await self.set_events(user, facility)
                    break
            await asyncio.sleep(3)

    async def _events_loop(self, user: UserContext, facility: Facility):
        while self.run:
            await self.clean_tasks()
            events = await self.get_events()
            if len(events) == 0:
                await self.set_events(user, facility)
            elif await print_events(facility, user, await self.get_events(), self.cycle_iteration,
                                    self.cycle_timeout):
                await self.set_events(user, facility)
                await self.set_loops_timeout()
            self.cycle_iteration += 1
            await asyncio.sleep(1)

    async def set_loops_timeout(self):
        tasks = await self.get_book_tasks()
        cycle = self.long_cycle
        if len(tasks) > 0:
            events = await self.get_events()
            task_events = {x: events[x] for x in events if x in tasks}
            for event in task_events.values():
                if (event.booking_opens_on - timedelta(minutes=30)) < datetime.now():
                    cycle = self.small_cycle
                    break
        x = percentage_of(cycle, 15)
        self.cycle_timeout = cycle + randint(-x, x)
        self.cycle_iteration = 1

    async def clean_tasks(self):
        tasks = await self.get_book_tasks()
        for t in tasks:
            if (await self.get_book_task(t)).done():
                await self.pop_book_task(t)
            else:
                lesson = await self.get_event(t)
                if not lesson.is_participant:
                    await self.set_event_status(t, 'Booking')
