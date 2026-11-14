"""Pilot integration with the real booking engine and offline service boundaries."""

import asyncio
from datetime import datetime, timedelta

import pytest

from mywellnezz.api import events as api_events
from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.app import services
from mywellnezz.booking.engine import MyWellnezz
from mywellnezz.config import storage
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.ui.app import DashboardScreen, MenuScreen, MyWellnezzApp


@pytest.fixture()
def offline_account(monkeypatch):
    gym = Facility(id='g1', name='Offline Gym')
    user = User(id='u1', usr='offline@example.test', token='test-token')
    profile = UserProfile(id=user.id, usr=user.usr, facilities=[gym])
    config = AppConfig(users=[profile], user_choice=0, facility_choice=0)

    async def facilities(config, profile, ask_password=None):
        return [gym]

    async def session(config, profile, ask_password=None):
        return user

    monkeypatch.setattr(services, 'ensure_facilities', facilities)
    monkeypatch.setattr(services, 'ensure_session', session)
    monkeypatch.setattr(storage, 'save_config', lambda config: None)
    return config


async def test_real_engine_booking_and_awaited_cancel_from_keyboard(monkeypatch, offline_account):
    starts = datetime.now() + timedelta(days=1)
    event = Event(
        id='e1', uid='e1', name='Offline Cycling', start=starts,
        end=starts + timedelta(hours=1), booking_opens_on=datetime.now() - timedelta(days=1),
        booking_available=True, available_places=1, can_book=True, status='Open',
    )
    called = asyncio.Event()
    requests = []

    async def search(user, facility, start):
        return {event.uid: event}

    async def book(user, selected):
        requests.append((user.id, selected.uid, selected.is_participant))
        called.set()
        # Simulate a request still in flight until the user cancels the job.
        await asyncio.Event().wait()

    monkeypatch.setattr(api_events, 'search_events', search)
    monkeypatch.setattr(api_events, 'book_unbook', book)
    engine = MyWellnezz()
    app = MyWellnezzApp(offline_account, engine)
    try:
        async with app.run_test(size=(100, 32)) as pilot:
            await pilot.press('enter')
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
            await pilot.press('b')
            await asyncio.wait_for(called.wait(), timeout=5)
            await pilot.pause()
            assert requests == [('u1', 'e1', False)]
            task = await engine.get_book_task('e1')
            assert task is not None and not task.done()
            await pilot.press('b')
            await pilot.pause()
            assert task.cancelled()
            assert await engine.get_book_tasks() == {}
            assert 'Cancelled' in app.screen.query_one('#dashboard-status').render().plain
            await pilot.press('escape')
            await pilot.pause()
            assert isinstance(app.screen, MenuScreen)
            assert await engine.get_events() == {}
    finally:
        await engine.shutdown()
