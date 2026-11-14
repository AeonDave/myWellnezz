"""Tests for the booking engine's refresh scheduling."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from mywellnezz.api.client import ApiError
from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.booking.engine import MyWellnezz
from mywellnezz.config.models import AppConfig


def test_refresh_due_when_no_events():
    engine = MyWellnezz()
    assert engine.refresh_due({}) is True


def test_refresh_due_after_countdown():
    engine = MyWellnezz()
    engine.cycle_timeout = 3
    engine.cycle_iteration = 1
    events = {'a': Event(id='a', uid='a')}
    assert engine.refresh_due(events) is False
    assert engine.refresh_due(events) is False
    assert engine.refresh_due(events) is True


def test_cycle_jitter_bounds():
    engine = MyWellnezz()
    assert engine.long_cycle == 300
    assert engine.small_cycle == 5


def _event(**changes):
    values = {
        'id': 'e1',
        'uid': 'e1',
        'name': 'Cycling',
        'booking_available': True,
        'can_book': True,
        'start': datetime.now() + timedelta(days=1),
        'end': datetime.now() + timedelta(days=1, hours=1),
        'booking_opens_on': datetime.now() - timedelta(hours=1),
        'available_places': 2,
    }
    values.update(changes)
    return Event(**values)


async def test_reset_awaits_cancellation_and_clears_previous_context():
    engine = MyWellnezz()
    entered = asyncio.Event()
    finished = asyncio.Event()

    async def pending():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()

    task = asyncio.create_task(pending())
    engine.book_tasks['old'] = task
    engine.events['old'] = _event(uid='old')
    engine.cycle_iteration = 42
    await entered.wait()
    try:
        await engine.reset()
        assert finished.is_set()
        assert task.cancelled()
        assert await engine.get_book_tasks() == {}
        assert await engine.get_events() == {}
        assert engine.cycle_iteration == 1
        assert engine.cycle_timeout == engine.long_cycle
        assert engine.run
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_shutdown_cancels_and_joins_tasks():
    engine = MyWellnezz()
    task = asyncio.create_task(asyncio.Event().wait())
    engine.book_tasks['old'] = task
    try:
        await engine.shutdown()
        assert task.cancelled()
        assert not engine.run
        assert await engine.get_book_tasks() == {}
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_book_task_reports_queue_and_awaited_cancellation(monkeypatch):
    engine = MyWellnezz()
    event = _event()
    engine.events[event.uid] = event
    entered = asyncio.Event()
    finished = asyncio.Event()

    async def booking(*args):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()

    monkeypatch.setattr(engine, '_book_event_loop', booking)
    task = None
    try:
        assert await engine.set_book_task(User(), Facility(), event) == 'queued'
        task = await engine.get_book_task(event.uid)
        await entered.wait()
        # Cancelling a queued job must remain possible after the class starts.
        event.start = datetime.now() - timedelta(seconds=1)
        assert await engine.set_book_task(User(), Facility(), event) == 'cancelled'
        assert finished.is_set()
        assert task.cancelled()
        assert await engine.get_book_task(event.uid) is None
    finally:
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        for task in (await engine.get_book_tasks()).values():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize(
    'changes',
    [
        {'booking_available': False},
        {'start': None},
        {'start': datetime(2000, 1, 1)},
    ],
)
async def test_unavailable_events_never_create_jobs(changes):
    engine = MyWellnezz()
    event = _event(**changes)
    try:
        assert await engine.set_book_task(User(), Facility(), event) == 'unavailable'
        assert await engine.get_book_tasks() == {}
    finally:
        for task in (await engine.get_book_tasks()).values():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_refresh_failure_is_visible_without_erasing_previous_events(monkeypatch):
    engine = MyWellnezz()
    event = _event()
    engine.events[event.uid] = event
    monkeypatch.setattr(
        'mywellnezz.booking.engine.api_events.search_events', AsyncMock(return_value=None)
    )
    with pytest.raises(ApiError, match='refresh'):
        await engine.set_events(User(), Facility())
    assert await engine.get_events() == {event.uid: event}


async def test_cleanup_surfaces_worker_failure_and_removes_missing_event():
    engine = MyWellnezz()

    async def fail():
        raise ApiError('Booking failed')

    task = asyncio.create_task(fail())
    await asyncio.gather(task, return_exceptions=True)
    engine.book_tasks['gone'] = task
    with pytest.raises(ApiError, match='Booking failed'):
        await engine.clean_tasks()
    assert await engine.get_book_tasks() == {}


async def test_missing_booking_open_time_does_not_crash_countdown():
    engine = MyWellnezz()
    event = _event(booking_opens_on=None)
    task = asyncio.create_task(asyncio.Event().wait())
    engine.book_tasks[event.uid] = task
    try:
        await engine.set_loops_timeout({event.uid: event})
        assert 4 <= engine.cycle_timeout <= 6
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize(
    'changes',
    [
        {'booking_opens_on': datetime.now() + timedelta(hours=1)},
        {'available_places': None},
        {'available_places': 0},
    ],
)
async def test_booking_waits_for_opening_and_known_available_places(monkeypatch, changes):
    engine = MyWellnezz()
    event = _event(**changes)
    engine.events[event.uid] = event
    book = AsyncMock()

    async def one_iteration(seconds):
        engine.run = False

    monkeypatch.setattr('mywellnezz.booking.engine.api_events.book_unbook', book)
    monkeypatch.setattr('mywellnezz.booking.engine.asyncio.sleep', one_iteration)
    monkeypatch.setattr(engine, 'set_events', AsyncMock(return_value=engine.events))
    monkeypatch.setattr(engine, 'set_loops_timeout', AsyncMock())
    await engine._book_event_loop(User(token='test-token'), Facility(), event)
    book.assert_not_awaited()


@pytest.mark.parametrize('unbooking', [False, True])
async def test_booking_job_never_reverses_intent_after_refresh(monkeypatch, unbooking):
    engine = MyWellnezz()
    queued = _event(is_participant=unbooking)
    refreshed = _event(is_participant=not unbooking)
    engine.events[queued.uid] = refreshed
    book = AsyncMock()
    monkeypatch.setattr('mywellnezz.booking.engine.api_events.book_unbook', book)
    monkeypatch.setattr('mywellnezz.booking.engine.asyncio.sleep', AsyncMock())
    monkeypatch.setattr(engine, 'set_events', AsyncMock(return_value=engine.events))
    monkeypatch.setattr(engine, 'set_loops_timeout', AsyncMock())
    await engine._book_event_loop(User(token='test-token'), Facility(), queued)
    book.assert_not_awaited()


async def test_booking_job_drops_removed_event_instead_of_using_stale_data(monkeypatch):
    engine = MyWellnezz()
    book = AsyncMock()
    monkeypatch.setattr('mywellnezz.booking.engine.api_events.book_unbook', book)
    await engine._book_event_loop(User(token='test-token'), Facility(), _event())
    book.assert_not_awaited()


async def test_auto_booking_skips_removed_waitlist_entries(monkeypatch):
    engine = MyWellnezz()
    old = _event(is_in_waiting_list=True)
    monkeypatch.setattr(engine, 'set_events', AsyncMock(return_value={}))
    queue = AsyncMock()
    monkeypatch.setattr(engine, 'set_book_task', queue)
    assert await engine.update_events_event(User(), Facility(), AppConfig(), {old.uid: old}) == {}
    queue.assert_not_awaited()


async def test_queued_job_immediately_switches_refresh_to_fast_cycle(monkeypatch):
    engine = MyWellnezz()
    event = _event(available_places=0)
    engine.events[event.uid] = event

    async def pending(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr(engine, '_book_event_loop', pending)
    try:
        assert await engine.set_book_task(User(), Facility(), event) == 'queued'
        assert 4 <= engine.cycle_timeout <= 6
        assert await engine.set_book_task(User(), Facility(), event) == 'cancelled'
        assert 240 <= engine.cycle_timeout <= 360
    finally:
        await engine.shutdown()


async def test_auto_booking_does_not_toggle_off_existing_job(monkeypatch):
    engine = MyWellnezz()
    old = _event(is_in_waiting_list=False)
    new = _event(is_in_waiting_list=True)
    task = asyncio.create_task(asyncio.Event().wait())
    engine.book_tasks[new.uid] = task
    monkeypatch.setattr(engine, 'set_events', AsyncMock(return_value={new.uid: new}))
    queue = AsyncMock()
    monkeypatch.setattr(engine, 'set_book_task', queue)
    try:
        await engine.update_events_event(User(), Facility(), AppConfig(), {old.uid: old})
        queue.assert_not_awaited()
        assert not task.cancelled()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
