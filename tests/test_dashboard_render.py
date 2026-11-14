"""Dashboard rendering with hostile real-world data (brackets in API strings)."""

from datetime import datetime, timedelta

from mywellnezz.api import events as api_events
from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.app import services
from mywellnezz.booking.engine import MyWellnezz
from mywellnezz.config import storage
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.ui.app import DashboardScreen, MyWellnezzApp


def _config() -> AppConfig:
    facility = Facility(id='g1', name='Gym [Center]', address='Via Roma 1')
    profile = UserProfile(id='u1', usr='mario@example.com', facilities=[facility])
    return AppConfig(user_choice=0, facility_choice=0, users=[profile])


def _hostile_event(day) -> Event:
    event = Event(
        id='e1',
        name="[SPIN] 50' [LIVE]",
        assigned_to="Mario 'Rossi' [pro]",
        room='[Sala 1]',
        partition_date=int(day.strftime('%Y%m%d')),
        start_hour=10,
        start_minutes=0,
        end_hour=11,
        end_minutes=0,
        booking_available=True,
        available_places=5,
        booking_opens_on=datetime.now() - timedelta(days=1),
        booking_user_status='CanBook',
    )
    event.uid = 'uid1'
    event.start = datetime(day.year, day.month, day.day, 10, 0)
    event.end = datetime(day.year, day.month, day.day, 11, 0)
    event.can_book = True
    event.status = event.get_status()
    return event


async def test_dashboard_renders_hostile_and_missing_api_fields(monkeypatch):
    day = datetime.now() + timedelta(days=1)
    event = _hostile_event(day)
    partial = Event(id='partial', name='Partial class', partition_date=int(day.strftime('%Y%m%d')))
    partial.uid = 'partial-uid'
    partial.start = None
    partial.end = None
    partial.status = ''

    async def fake_search(user, facility, start):
        return {event.uid: event, partial.uid: partial}

    async def fake_facilities(config, profile, ask_password=None):
        return profile.facilities

    async def fake_session(config, profile, ask_password=None):
        return User(id='u1', usr=profile.usr, token='tok')

    monkeypatch.setattr(api_events, 'search_events', fake_search)
    monkeypatch.setattr(services, 'ensure_facilities', fake_facilities)
    monkeypatch.setattr(services, 'ensure_session', fake_session)
    monkeypatch.setattr(storage, 'save_config', lambda config: None)

    app = MyWellnezzApp(_config(), MyWellnezz())
    async with app.run_test(size=(110, 34)) as pilot:
        await pilot.press('enter')  # select the user row
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        for _ in range(3):
            await pilot.pause()
        table = app.screen.query_one('#events')
        assert table.row_count == 2
        detail = app.screen.query_one('#event-details').render().plain
        assert "[SPIN] 50' [LIVE]" in detail
        assert "Mario 'Rossi' [pro]" in detail
        assert '[Sala 1]' in detail
        assert 'Booking opens' in detail
        table.move_cursor(row=1)
        await pilot.pause()
        partial_detail = app.screen.query_one('#event-details').render().plain
        assert 'Partial class' in partial_detail
        assert 'Teacher: —' in partial_detail
        assert 'Room: —' in partial_detail
        assert 'Booking opens: —' in partial_detail
