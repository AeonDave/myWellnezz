import asyncio
import inspect
from asyncio import Task, Lock
from datetime import datetime, timedelta
from random import randint
from typing import Optional, Dict

from models.config import Config
from models.event import Event, update_events, action_event, check_event_diff
from models.facility import Facility
from models.usercontext import UserContext
from modules.console_util import print_events
from modules.math_util import percentage_of


class MyWellnezz:
    def __init__(self):
        self.print_task: Optional[Task] = None
        self.book_tasks: Dict[str, Task] = {}
        self.events: Dict[str, Event] = {}
        self.lock_events: Lock = asyncio.Lock()
        self.lock_tasks: Lock = asyncio.Lock()
        self.long_cycle: int = 60 * 5
        self.small_cycle: int = 5
        self.cycle_timeout: int = self.long_cycle
        self.cycle_iteration: int = 1
        self.run: bool = True
        self.test: bool = False

    async def get_events(self) -> Dict[str, Event]:
        async with self.lock_events:
            return self.events

    async def get_event(self, idx: str) -> Event:
        async with self.lock_events:
            return self.events[idx]

    async def set_events(self, user: UserContext, facility: Facility) -> Dict[str, Event]:
        d = int((datetime.now()).strftime("%Y%m%d"))
        async with self.lock_events:
            self.events = {k: v for k, v in (update_events(user, facility, d)).items() if not v.is_ended()}
            return self.events

    async def get_event_id_by_index(self, index: int) -> Optional[str]:
        ev = await self.get_events()
        return next((key for i, key in enumerate(ev.keys()) if i == abs(index)), None)

    async def set_event_status(self, idx: str, status: str) -> None:
        (await self.get_event(idx)).status = status

    async def get_book_tasks(self) -> Dict[str, Task]:
        async with self.lock_tasks:
            return self.book_tasks

    async def get_book_task(self, idx: str) -> Optional[Task]:
        async with self.lock_tasks:
            return self.book_tasks[idx] if idx in self.book_tasks else None

    async def pop_book_task(self, idx: str) -> None:
        async with self.lock_tasks:
            self.book_tasks.pop(idx)

    async def set_book_task(self, user: UserContext, facility: Facility, event: Event):
        if event.is_started():
            print(f'{event.name} is already started')
            return
        if event.uid in self.book_tasks and not (await self.get_book_task(event.uid)).done():
            (await self.get_book_task(event.uid)).cancel()
            await self.pop_book_task(event.uid)
            await self.set_event_status(event.uid, event.get_status())
            return
        self.book_tasks[event.uid] = asyncio.create_task(self._book_event_loop(user, facility, event))

    def set_event_task(self, user: UserContext, facility: Facility, config: Config):
        if self.print_task is None or self.print_task.done():
            self.print_task = asyncio.create_task(self._events_loop(user, facility, config))

    async def _book_event_loop(self, user: UserContext, facility: Facility, event: Event):
        while self.run:
            try:
                event = await self.get_event(event.uid)
            except Exception as ex:
                print(f'Event not found: {ex}')
            if not event or event.is_ended() or event.is_started():
                break
            elif event.available_places > 0 or event.is_participant:
                if user.token is None or not user.token:
                    user.refresh()
                try:
                    if action_event(user, event):
                        break
                except Exception as ex:
                    print(f'Error calling api: {ex}')
            await asyncio.sleep(1)
        await asyncio.sleep(2)
        n_events = await self.set_events(user, facility)
        await self.set_loops_timeout(n_events)

    async def update_events_event(self, user: UserContext, facility: Facility, config: Config, old_events: []):
        new_events = await self.set_events(user, facility)
        if config.auto_book:
            events_diff = check_event_diff(old_events, new_events)
            for e in events_diff:
                await self.set_book_task(user, facility, await self.get_event(e))
        await self.set_loops_timeout(new_events)
        return new_events

    async def _events_loop(self, user: UserContext, facility: Facility, config: Config):
        events = []
        while self.run:
            try:
                await self.clean_tasks()
                if len(events) == 0 or \
                        print_events(facility, user, await self.get_events(), self.cycle_iteration,
                                           self.cycle_timeout):
                    events = await self.update_events_event(user, facility, config, events)
                self.cycle_iteration += 1
                await asyncio.sleep(1)
            except Exception as e:
                print(f'Error in {inspect.currentframe().f_code.co_name}: {e}')

    async def set_loops_timeout(self, events: Dict[str, Event]):
        tasks = await self.get_book_tasks()
        cycle = self.long_cycle
        if len(tasks) > 0:
            task_events = {x: events[x] for x in events if x in tasks}
            for event in task_events.values():
                if (event.booking_opens_on - timedelta(minutes=30)) < datetime.now():
                    cycle = self.small_cycle
                    break
        x = percentage_of(cycle, 20)
        self.cycle_timeout = cycle + randint(-x, x)
        self.cycle_iteration = 1

    async def clean_tasks(self):
        try:
            tasks = (await self.get_book_tasks()).copy()
            for t in tasks:
                bt = await self.get_book_task(t)
                if bt and bt.done():
                    await self.pop_book_task(t)
                else:
                    event = await self.get_event(t)
                    if not event.is_participant and event.status != 'Booking':
                        await self.set_event_status(event.uid, 'Booking')
        except Exception as e:
            print(f'Error in {inspect.currentframe().f_code.co_name}: {e}')
