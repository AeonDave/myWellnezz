"""Deterministic Pilot coverage for account, gym and course workflows."""

import asyncio
from datetime import datetime, timedelta

import pytest

from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.app import services
from mywellnezz.config import storage
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.ui.app import ConfirmModal, DashboardScreen, GymScreen, MenuScreen, MyWellnezzApp


class CompletedTask:
    def done(self):
        return True


class FakeEngine:
    """Small async engine boundary: no HTTP, booking tasks, or disk access."""

    def __init__(self, events=()):
        self.seed_events = list(events)
        self.events = {}
        self.next_events = list(events) if events else None
        self.tasks = {}
        self.cycle_timeout = 60
        self.cycle_iteration = 1
        self.reset_calls = 0
        self.shutdown_calls = 0
        self.update_calls = 0
        self.book_calls = []
        self.next_book_result = 'queued'
        self.fail_refresh = False
        self.fail_clean = False
        self.block_refresh = False
        self.refresh_started = False
        self.refresh_cancelled = False

    async def reset(self):
        self.reset_calls += 1
        self.events.clear()
        if self.next_events is None and self.seed_events:
            self.next_events = list(self.seed_events)
        self.tasks.clear()
        self.cycle_timeout = 60
        self.cycle_iteration = 1

    async def shutdown(self):
        self.shutdown_calls += 1
        self.tasks.clear()

    async def clean_tasks(self):
        self.tasks = {
            uid: task for uid, task in self.tasks.items()
            if not callable(getattr(task, 'done', None)) or not task.done()
        }
        if self.fail_clean:
            raise RuntimeError('offline booking task failure')

    async def get_events(self):
        return dict(self.events)

    async def get_book_tasks(self):
        return dict(self.tasks)

    def refresh_due(self, events):
        due = self.update_calls == 0 or self.cycle_iteration >= self.cycle_timeout
        self.cycle_iteration += 1
        return due

    async def update_events_event(self, user, facility, config, old_events):
        self.update_calls += 1
        if self.fail_refresh:
            raise RuntimeError('offline test refresh')
        if self.block_refresh:
            self.refresh_started = True
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                self.refresh_cancelled = True
                raise
        if self.next_events is not None:
            self.events = {event.uid: event for event in self.next_events}
            self.next_events = None
        return dict(self.events)

    async def get_event(self, uid):
        return self.events[uid]

    async def set_book_task(self, user, facility, event):
        self.book_calls.append(event.uid)
        result = 'cancelled' if event.uid in self.tasks else self.next_book_result
        if result == 'queued':
            self.tasks[event.uid] = object()
        elif result == 'cancelled':
            self.tasks.pop(event.uid, None)
        return result


def make_event(uid='course-1', *, name='Morning Yoga', **overrides):
    starts = datetime.now() + timedelta(days=1)
    fields = {
        'id': uid,
        'uid': uid,
        'name': name,
        'assigned_to': 'Taylor Coach',
        'room': 'Studio 2',
        'start': starts,
        'end': starts + timedelta(hours=1),
        'booking_opens_on': datetime.now() - timedelta(days=1),
        'available_places': 4,
        'booking_available': True,
        'can_book': True,
        'status': 'Open',
    }
    fields.update(overrides)
    return Event(**fields)


def make_config(facilities=None):
    profile = UserProfile(
        id='user-1', usr='alex@example.test', facilities=list(facilities or [
            Facility(id='gym-1', name='North Gym', address='1 Main Street'),
        ]),
    )
    return AppConfig(user_choice=0, facility_choice=0, users=[profile])


def install_service_fakes(monkeypatch, *, facilities=None, user=None):
    """Patch every account boundary; these tests must never touch a vault/API."""
    facilities = facilities or [Facility(id='gym-1', name='North Gym', address='1 Main Street')]
    user = user or User(
        id='user-1', usr='alex@example.test', first_name='Alex', last_name='Example', token='test-token'
    )
    async def fake_facilities(config, profile, ask_password=None):
        return list(facilities)

    async def fake_session(config, profile, ask_password=None):
        return user

    monkeypatch.setattr(services, 'ensure_facilities', fake_facilities)
    monkeypatch.setattr(services, 'ensure_session', fake_session)
    monkeypatch.setattr(storage, 'save_config', lambda config: None)
    return user


async def enter_dashboard(pilot, app):
    """Open the selected account through the real menu controls."""
    await pilot.click('#menu-open')
    await pilot.pause()
    if isinstance(app.screen, GymScreen):
        await pilot.click('#gym-open')
        await pilot.pause()
    assert isinstance(app.screen, DashboardScreen)


async def test_empty_menu_has_real_empty_state_and_clickable_actions(monkeypatch):
    app = MyWellnezzApp(AppConfig(), FakeEngine())
    async with app.run_test(size=(80, 24)) as pilot:
        assert isinstance(app.screen, MenuScreen)
        assert app.screen.query_one('#menu-empty').display
        assert app.screen.query_one('#menu-open').disabled
        assert app.screen.query_one('#menu-remove').disabled
        for selector in ('#menu-open', '#menu-add', '#menu-remove', '#menu-quit'):
            assert app.screen.query_one(selector).display
        await pilot.click('#menu-add')
        await pilot.pause()
        assert app.screen.query_one('#email')


async def test_menu_remove_confirms_and_keyboard_quit(monkeypatch):
    install_service_fakes(monkeypatch)
    config = make_config()
    removed = []
    def fake_remove(current, index):
        removed.append(index)
        current.users.pop(index)
        return current
    monkeypatch.setattr(storage, 'remove_user', fake_remove)
    app = MyWellnezzApp(config, FakeEngine())
    async with app.run_test() as pilot:
        await pilot.click('#menu-remove')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmModal)
        await pilot.click('#no')
        await pilot.pause()
        assert not removed
        await pilot.click('#menu-remove')
        await pilot.pause()
        await pilot.click('#yes')
        await pilot.pause()
        assert removed == [0]
        assert len(config.users) == 0
        await pilot.press('q')
        assert not app.is_running


async def test_account_and_gym_selection_use_explicit_actions(monkeypatch):
    gyms = [
        Facility(id='gym-1', name='North Gym', address='1 Main Street'),
        Facility(id='gym-2', name='South Gym', address='9 Lake Road'),
    ]
    install_service_fakes(monkeypatch, facilities=gyms)
    app = MyWellnezzApp(make_config(gyms), FakeEngine([make_event()]))
    async with app.run_test(size=(100, 32)) as pilot:
        await pilot.click('#menu-open')
        await pilot.pause()
        assert isinstance(app.screen, GymScreen)
        assert app.screen.query_one('#gyms').row_count == 2
        assert app.screen.query_one('#gym-open').display
        assert app.screen.query_one('#gym-back').display
        await pilot.click('#gym-open')
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        assert app.facility.id == 'gym-1'
        assert app.engine.reset_calls >= 1


async def test_enter_books_selected_course_and_pending_b_cancels(monkeypatch):
    install_service_fakes(monkeypatch)
    event = make_event()
    engine = FakeEngine([event])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        table = app.screen.query_one('#events')
        table.focus()
        await pilot.press('enter')
        await pilot.pause()
        assert engine.book_calls == [event.uid]
        assert 'Queued' in app.screen.query_one('#dashboard-status').render().plain
        await pilot.press('b')
        await pilot.pause()
        assert engine.book_calls == [event.uid, event.uid]
        assert 'Cancelled' in app.screen.query_one('#dashboard-status').render().plain


async def test_participant_unbook_requires_confirmation_but_waitlist_does_not(monkeypatch):
    install_service_fakes(monkeypatch)
    participant = make_event('participant', name='Booked Class', is_participant=True,
                             booking_available=False, can_book=False, status='Booked')
    waitlisted = make_event('waitlist', name='Queue Class', is_in_waiting_list=True,
                            booking_available=True, can_book=True, status='WaitingList')
    engine = FakeEngine([participant, waitlisted])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        table = app.screen.query_one('#events')
        table.move_cursor(row=0)
        await pilot.pause()
        assert app.screen.query_one('#book').label.plain == 'Unbook'
        await pilot.click('#book')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmModal)
        await pilot.click('#no')
        await pilot.pause()
        assert engine.book_calls == []
        table = app.screen.query_one('#events')
        table.move_cursor(row=1)
        await pilot.pause()
        assert app.screen.query_one('#book').label.plain == 'Book when available'
        await pilot.click('#book')
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmModal)
        assert engine.book_calls == ['waitlist']


@pytest.mark.parametrize(
    ('change_state', 'expected_status'),
    [
        ('not_participant', 'no longer booked'),
        ('started', 'has started'),
    ],
)
async def test_unbook_confirmation_never_flips_into_booking(monkeypatch, change_state, expected_status):
    install_service_fakes(monkeypatch)
    participant = make_event('participant', name='Booked Class', is_participant=True,
                             booking_available=False, can_book=False, status='Booked')
    engine = FakeEngine([participant])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        await pilot.click('#book')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmModal)
        current = engine.events['participant']
        if change_state == 'not_participant':
            current.is_participant = False
        else:
            current.start = datetime.now() - timedelta(minutes=1)
            current.end = datetime.now() + timedelta(minutes=30)
        await pilot.click('#yes')
        await pilot.pause()
        assert engine.book_calls == []
        assert expected_status in app.screen.query_one('#dashboard-status').render().plain.lower()


async def test_participant_unbook_acceptance_and_future_full_queue(monkeypatch):
    install_service_fakes(monkeypatch)
    participant = make_event('participant', name='Booked Class', is_participant=True,
                             booking_available=False, can_book=False, status='Booked')
    full_future = make_event('full', name='Full Future Class', available_places=0,
                             booking_opens_on=datetime.now() + timedelta(days=2),
                             can_book=False, status='Full')
    engine = FakeEngine([participant, full_future])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        await pilot.click('#book')
        await pilot.pause()
        await pilot.click('#yes')
        await pilot.pause()
        assert engine.book_calls == ['participant']
        table = app.screen.query_one('#events')
        table.move_cursor(row=1)
        await pilot.pause()
        assert not app.screen.query_one('#book').disabled
        assert app.screen.query_one('#book').label.plain == 'Book when available'
        await pilot.click('#book')
        await pilot.pause()
        assert engine.book_calls == ['participant', 'full']


async def test_completed_booking_job_updates_dashboard_on_tick_without_network(monkeypatch):
    install_service_fakes(monkeypatch)
    event = make_event()
    engine = FakeEngine([event])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        await pilot.press('b')
        await pilot.pause()
        assert app.screen.query_one('#book').label.plain == 'Cancel queued'
        engine.events[event.uid].is_participant = True
        engine.events[event.uid].status = 'Booked'
        engine.tasks[event.uid] = CompletedTask()
        update_calls = engine.update_calls
        app.screen._on_tick()
        await pilot.pause()
        assert engine.update_calls == update_calls
        assert event.uid not in app.screen._pending_uids
        assert app.screen.query_one('#book').label.plain == 'Unbook'
        assert 'Status: Booked' in app.screen.query_one('#event-details').render().plain


async def test_failed_booking_job_is_consumed_and_reported_on_tick(monkeypatch):
    install_service_fakes(monkeypatch)
    event = make_event()
    engine = FakeEngine([event])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        await pilot.press('b')
        await pilot.pause()
        engine.tasks[event.uid] = CompletedTask()
        engine.fail_clean = True
        app.screen._on_tick()
        await pilot.pause()
        assert event.uid not in app.screen._pending_uids
        assert app.screen.query_one('#book').label.plain == 'Book'
        assert 'offline booking task failure' in app.screen.query_one('#dashboard-status').render().plain


async def test_started_participant_cannot_start_unbook_action(monkeypatch):
    install_service_fakes(monkeypatch)
    started = make_event('started-participant', is_participant=True,
                         booking_available=False, can_book=False, status='Progress')
    started.start = datetime.now() - timedelta(minutes=1)
    started.end = datetime.now() + timedelta(minutes=30)
    engine = FakeEngine([started])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        assert app.screen.query_one('#book').disabled
        await pilot.press('b')
        await pilot.pause()
        assert engine.book_calls == []


async def test_nonbookable_class_is_disabled_and_never_queued(monkeypatch):
    install_service_fakes(monkeypatch)
    event = make_event('closed', name='Closed Class', booking_available=False,
                       can_book=False, status='Unshedulable')
    engine = FakeEngine([event])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        assert app.screen.query_one('#book').disabled
        await pilot.press('b')
        await pilot.pause()
        assert engine.book_calls == []
        assert 'cannot be booked' in app.screen.query_one('#dashboard-status').render().plain


async def test_uid_selection_survives_reorder_and_filter(monkeypatch):
    install_service_fakes(monkeypatch)
    first = make_event('one', name='Alpha Pilates')
    selected = make_event('two', name='Beta Spin')
    engine = FakeEngine([first, selected])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test(size=(100, 32)) as pilot:
        await enter_dashboard(pilot, app)
        table = app.screen.query_one('#events')
        await pilot.press('down')
        await pilot.pause()
        assert 'Beta Spin' in app.screen.query_one('#event-details').render().plain
        engine.next_events = [selected, first]
        await pilot.click('#reload')
        await pilot.pause()
        table = app.screen.query_one('#events')
        assert table.get_row_at(table.cursor_row)[0].plain == 'Beta Spin'
        search = app.screen.query_one('#search')
        search.value = 'Beta'
        await pilot.pause()
        assert table.row_count == 1
        assert table.get_row_at(table.cursor_row)[0].plain == 'Beta Spin'
        search.value = 'nothing matches'
        await pilot.pause()
        assert table.row_count == 0
        assert 'No classes match' in app.screen.query_one('#event-details').render().plain


async def test_empty_and_error_course_states_are_visible(monkeypatch):
    install_service_fakes(monkeypatch)
    engine = FakeEngine()
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test(size=(80, 24)) as pilot:
        await enter_dashboard(pilot, app)
        assert 'No classes' in app.screen.query_one('#event-details').render().plain
        engine.fail_refresh = True
        await pilot.click('#reload')
        await pilot.pause()
        assert 'offline test refresh' in app.screen.query_one('#dashboard-status').render().plain


@pytest.mark.parametrize('size', [(80, 24), (120, 40)])
async def test_dashboard_controls_fit_at_supported_terminal_sizes(monkeypatch, size):
    install_service_fakes(monkeypatch)
    app = MyWellnezzApp(make_config(), FakeEngine([make_event()]))
    async with app.run_test(size=size) as pilot:
        await enter_dashboard(pilot, app)
        assert app.screen.query_one('#event-details').region.height >= 5
        for selector in ('#search', '#book', '#reload', '#back'):
            widget = app.screen.query_one(selector)
            assert widget.display, selector
            assert widget.region.width > 0, selector
            assert widget.region.x >= 0 and widget.region.x + widget.region.width <= size[0], selector
            assert widget.region.y >= 0 and widget.region.y + widget.region.height <= size[1], selector
            assert widget.is_on_screen, selector


async def test_back_with_pending_task_confirms_then_returns_to_menu(monkeypatch):
    install_service_fakes(monkeypatch)
    event = make_event()
    engine = FakeEngine([event])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        await pilot.press('b')
        await pilot.pause()
        await pilot.click('#back')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmModal)
        await pilot.click('#yes')
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        # Textual keeps its built-in default screen under the menu; no gym/dashboard remains stacked.
        assert len(app.screen_stack) == 2
        assert engine.reset_calls >= 2


async def test_back_cancels_and_awaits_refresh_before_reset(monkeypatch):
    install_service_fakes(monkeypatch)
    engine = FakeEngine([make_event()])
    app = MyWellnezzApp(make_config(), engine)
    async with app.run_test() as pilot:
        await enter_dashboard(pilot, app)
        screen = app.screen
        engine.block_refresh = True
        await pilot.click('#reload')
        await pilot.pause()
        assert engine.refresh_started
        assert not screen.query_one('#back').disabled
        await pilot.click('#back')
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        assert engine.refresh_cancelled
        assert screen._timer is None
        assert screen._refresh_worker is None
        update_count = engine.update_calls
        screen._on_tick()
        assert engine.update_calls == update_count


async def test_switching_user_clears_previous_facility_index(monkeypatch):
    first = UserProfile(id='u1', usr='first@example.test', facilities=[
        Facility(id='a', name='A'), Facility(id='b', name='B'),
    ])
    second = UserProfile(id='u2', usr='second@example.test', facilities=[
        Facility(id='only', name='Only Gym'),
    ])
    config = AppConfig(user_choice=0, facility_choice=1, users=[first, second])
    seen_facility_choices = []
    async def fake_facilities(current, profile, ask_password=None):
        seen_facility_choices.append(current.facility_choice)
        return list(profile.facilities)
    async def fake_session(current, profile, ask_password=None):
        return User(id=profile.id, usr=profile.usr, token='test-token')
    monkeypatch.setattr(services, 'ensure_facilities', fake_facilities)
    monkeypatch.setattr(services, 'ensure_session', fake_session)
    monkeypatch.setattr(storage, 'save_config', lambda current: None)
    app = MyWellnezzApp(config, FakeEngine())
    async with app.run_test() as pilot:
        table = app.screen.query_one('#users')
        table.move_cursor(row=1)
        await pilot.press('enter')
        await pilot.pause()
        assert seen_facility_choices == [None]
        assert app.config.current_facility().id == 'only'


async def test_missing_selected_gym_aborts_with_visible_error(monkeypatch):
    gyms = [Facility(id='gym-a', name='Gym A'), Facility(id='gym-b', name='Gym B')]
    install_service_fakes(monkeypatch, facilities=gyms)
    async def remove_selected_gym(config, profile, ask_password=None):
        profile.facilities = [gyms[0]]
        return User(id='user-1', usr=profile.usr, token='test-token')
    monkeypatch.setattr(services, 'ensure_session', remove_selected_gym)
    app = MyWellnezzApp(make_config(gyms), FakeEngine())
    async with app.run_test() as pilot:
        await pilot.click('#menu-open')
        await pilot.pause()
        app.screen.query_one('#gyms').move_cursor(row=1)
        await pilot.click('#gym-open')
        await pilot.pause()
        assert isinstance(app.screen, GymScreen)
        assert 'no longer available' in app.screen.query_one('#gym-status').render().plain
        assert app.facility is None


async def test_selected_gym_is_resolved_by_id_after_login_reorders_memberships(monkeypatch):
    gyms = [Facility(id='gym-a', name='Gym A'), Facility(id='gym-b', name='Gym B')]
    install_service_fakes(monkeypatch, facilities=gyms)
    async def reorder_during_login(config, profile, ask_password=None):
        profile.facilities = [gyms[1], gyms[0]]
        return User(id='user-1', usr=profile.usr, token='test-token')
    monkeypatch.setattr(services, 'ensure_session', reorder_during_login)
    app = MyWellnezzApp(make_config(gyms), FakeEngine())
    async with app.run_test() as pilot:
        await pilot.click('#menu-open')
        await pilot.pause()
        app.screen.query_one('#gyms').move_cursor(row=1)
        await pilot.click('#gym-open')
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        assert app.facility.id == 'gym-b'


@pytest.mark.parametrize('size', [(80, 24), (120, 40)])
async def test_menu_is_compact_at_supported_sizes(monkeypatch, size):
    install_service_fakes(monkeypatch)
    app = MyWellnezzApp(make_config(), FakeEngine())
    async with app.run_test(size=size):
        for selector in ('#menu-open', '#menu-add', '#menu-remove', '#menu-quit'):
            widget = app.screen.query_one(selector)
            assert widget.display
            assert widget.region.width > 0
            assert widget.region.x >= 0 and widget.region.x + widget.region.width <= size[0]
            assert widget.region.y >= 0 and widget.region.y + widget.region.height <= size[1]
            assert widget.is_on_screen
