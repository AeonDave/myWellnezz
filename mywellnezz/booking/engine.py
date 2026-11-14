"""Booking engine: keeps the event list fresh and runs per-event booking tasks.

Ported from the v1 ``models/mywellnezz.py`` with the same refresh cycles and
auto-book policy, now fully async, UI-free (rendering belongs to the session
dashboard) and with an injected ``relogin`` callback so the engine never
touches stored secrets itself.
"""

import asyncio
from asyncio import Lock, Task
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from random import randint
from typing import Literal

from mywellnezz.api import events as api_events
from mywellnezz.api.client import ApiError
from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.config.models import AppConfig

Relogin = Callable[[User], Awaitable[User | None]]


def _percentage_of(a: int, b: int) -> int:
    return int((a / 100) * b)


def check_event_diff(old_events: dict[str, Event], new_events: dict[str, Event]) -> set[str]:
    """Detect events that changed waiting-list/participation state between refreshes."""
    old_wl = {x for x in old_events if old_events[x].is_in_waiting_list}
    new_pl = {z for z in new_events if new_events[z].is_participant}
    old_wl = old_wl - new_pl
    new_wl = {y for y in new_events if new_events[y].is_in_waiting_list}
    return old_wl - new_wl if len(old_wl) > len(new_wl) else new_wl - old_wl


class MyWellnezz:
    def __init__(self):
        self.book_tasks: dict[str, Task] = {}
        self.events: dict[str, Event] = {}
        self.lock_events: Lock = asyncio.Lock()
        self.lock_tasks: Lock = asyncio.Lock()
        self.long_cycle: int = 60 * 5
        self.small_cycle: int = 5
        self.cycle_timeout: int = self.long_cycle
        self.cycle_iteration: int = 1
        self.run: bool = True
        self.test: bool = False
        self.relogin: Relogin | None = None

    async def get_events(self) -> dict[str, Event]:
        async with self.lock_events:
            return dict(self.events)

    async def get_event(self, idx: str) -> Event:
        async with self.lock_events:
            return self.events[idx]

    async def set_events(self, user: User, facility: Facility) -> dict[str, Event]:
        fetched = await api_events.search_events(user, facility, api_events.today_partition())
        if fetched is None:
            raise ApiError('Could not refresh classes. Previous results have been kept.')
        async with self.lock_events:
            self.events = {k: v for k, v in fetched.items() if not v.is_ended()}
            return dict(self.events)

    async def get_event_id_by_index(self, index: int) -> str | None:
        events = await self.get_events()
        return next((key for i, key in enumerate(events.keys()) if i == abs(index)), None)

    async def set_event_status(self, idx: str, status: str) -> None:
        (await self.get_event(idx)).status = status

    async def get_book_tasks(self) -> dict[str, Task]:
        async with self.lock_tasks:
            return dict(self.book_tasks)

    async def get_book_task(self, idx: str) -> Task | None:
        async with self.lock_tasks:
            return self.book_tasks.get(idx)

    async def pop_book_task(self, idx: str) -> None:
        async with self.lock_tasks:
            self.book_tasks.pop(idx, None)

    async def shutdown(self) -> None:
        """Stop and join every booking job before closing or switching context."""
        self.run = False
        async with self.lock_tasks:
            tasks = list(self.book_tasks.values())
            self.book_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def reset(self) -> None:
        """Begin an empty context; callers must first stop their refresh workers."""
        await self.shutdown()
        async with self.lock_events:
            self.events.clear()
        self.cycle_timeout = self.long_cycle
        self.cycle_iteration = 1
        self.run = True

    async def set_book_task(
        self, user: User, facility: Facility, event: Event
    ) -> Literal['queued', 'cancelled', 'unavailable']:
        existing = await self.get_book_task(event.uid)
        if existing is not None and not existing.done():
            existing.cancel()
            await asyncio.gather(existing, return_exceptions=True)
            await self.pop_book_task(event.uid)
            if event.uid in self.events:
                await self.set_event_status(event.uid, event.get_status())
            await self.set_loops_timeout(await self.get_events())
            return 'cancelled'
        if (
            not self.run
            or event.start is None
            or event.is_started()
            or (not event.booking_available and not event.is_participant)
        ):
            return 'unavailable'
        if existing is not None:
            # Do not lose an unobserved failure when replacing a completed job.
            await self.pop_book_task(event.uid)
            if not existing.cancelled():
                existing.result()
        async with self.lock_tasks:
            self.book_tasks[event.uid] = asyncio.create_task(
                self._book_event_loop(user, facility, event)
            )
        # A full class can open between periodic checks. Enter the fast cycle as
        # soon as its job is queued, not up to five minutes later at the next refresh.
        await self.set_loops_timeout(await self.get_events())
        return 'queued'

    def refresh_due(self, events: dict[str, Event]) -> bool:
        """Advance the countdown; ``True`` when a data refresh is due now."""
        due = len(events) == 0 or self.cycle_iteration >= self.cycle_timeout
        self.cycle_iteration += 1
        return due

    async def _book_event_loop(self, user: User, facility: Facility, event: Event) -> None:
        unbooking = event.is_participant
        while self.run:
            events = await self.get_events()
            event = events.get(event.uid)
            if event is None:
                return
            if event.is_ended() or event.is_started():
                break
            # A refresh may show that the requested state was reached elsewhere.
            # Never turn a queued booking into an accidental cancellation (or vice versa).
            if event.is_participant != unbooking:
                break
            if unbooking or (event.is_bookable() and (event.available_places or 0) > 0):
                if not user.token and self.relogin is not None:
                    await self.relogin(user)
                if await api_events.book_unbook(user, event):
                    break
            await asyncio.sleep(1)
        await asyncio.sleep(2)
        n_events = await self.set_events(user, facility)
        await self.set_loops_timeout(n_events)

    async def update_events_event(
        self, user: User, facility: Facility, config: AppConfig, old_events: dict[str, Event]
    ) -> dict[str, Event]:
        new_events = await self.set_events(user, facility)
        if config.auto_book:
            events_diff = check_event_diff(old_events, new_events)
            for e in events_diff:
                # Removed events are not actionable; refreshes must not toggle an
                # already queued job off just because waiting-list state changed.
                task = await self.get_book_task(e)
                if e in new_events and (task is None or task.done()):
                    await self.set_book_task(user, facility, new_events[e])
        await self.set_loops_timeout(new_events)
        return new_events

    async def set_loops_timeout(self, events: dict[str, Event]) -> None:
        tasks = await self.get_book_tasks()
        cycle = self.long_cycle
        if len(tasks) > 0:
            task_events = {x: events[x] for x in events if x in tasks}
            for event in task_events.values():
                if (
                    event.booking_opens_on is None
                    or event.booking_opens_on - timedelta(minutes=30) < datetime.now()
                ):
                    cycle = self.small_cycle
                    break
        x = _percentage_of(cycle, 20)
        self.cycle_timeout = cycle + randint(-x, x)
        self.cycle_iteration = 1

    async def clean_tasks(self) -> None:
        failures: list[Exception] = []
        events = await self.get_events()
        for uid, task in (await self.get_book_tasks()).items():
            if task.done():
                await self.pop_book_task(uid)
                if not task.cancelled():
                    error = task.exception()
                    if error is not None:
                        failures.append(error)
            elif uid not in events:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await self.pop_book_task(uid)
            elif not events[uid].is_participant:
                await self.set_event_status(uid, 'Booking')
        if failures:
            # Surface through the UI's error boundary, not stdout under the TUI.
            raise failures[0]
