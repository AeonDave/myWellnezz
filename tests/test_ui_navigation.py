"""Late network responses must not replace a newer account/navigation context."""

import asyncio

import pytest

from mywellnezz.api.dto import Facility, User
from mywellnezz.app import services
from mywellnezz.config import storage
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.ui.app import AddUserModal, DashboardScreen, GymScreen, MenuScreen, MyWellnezzApp
from tests.test_ui_workflows import FakeEngine


@pytest.mark.parametrize('switch_account', [False, True])
async def test_leaving_gym_picker_invalidates_pending_login(monkeypatch, switch_account):
    gyms = [Facility(id='shared', name='Shared Gym'), Facility(id='other', name='Other Gym')]
    first = UserProfile(id='a', usr='first@example.test', facilities=list(gyms))
    second = UserProfile(id='b', usr='second@example.test', facilities=list(gyms))
    config = AppConfig(users=[first, second], user_choice=0)
    entered, release = asyncio.Event(), asyncio.Event()

    async def facilities(config, profile, ask_password=None):
        return profile.facilities

    async def session(config, profile, ask_password=None):
        entered.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            # Simulate an external operation that completes despite cancellation.
            await release.wait()
        return User(id=profile.id, usr=profile.usr, token='offline-token')

    monkeypatch.setattr(services, 'ensure_facilities', facilities)
    monkeypatch.setattr(services, 'ensure_session', session)
    monkeypatch.setattr(storage, 'save_config', lambda config: None)
    app = MyWellnezzApp(config, FakeEngine())
    async with app.run_test(size=(100, 32)) as pilot:
        try:
            await pilot.press('enter')
            await pilot.pause()
            assert isinstance(app.screen, GymScreen)
            await pilot.click('#gym-open')
            await asyncio.wait_for(entered.wait(), timeout=5)
            await pilot.press('escape')
            await pilot.pause()
            assert isinstance(app.screen, MenuScreen)
            if switch_account:
                app.screen.query_one('#users').move_cursor(row=1)
                await pilot.press('enter')
                await pilot.pause()
                assert isinstance(app.screen, GymScreen)
                assert config.current_user() is second
            release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, GymScreen if switch_account else MenuScreen)
            assert app.user is None
            assert app.facility is None
            if switch_account:
                await pilot.click('#gym-open')
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert isinstance(app.screen, DashboardScreen)
                assert app.user.id == 'b'
        finally:
            release.set()


@pytest.mark.parametrize('old_request_fails', [False, True])
async def test_add_account_during_gym_loading_does_not_receive_old_gyms(monkeypatch, old_request_fails):
    first_gym = Facility(id='first-gym', name='First Gym')
    own_gym = Facility(id='new-gym', name='New Gym')
    first = UserProfile(id='a', usr='first@example.test', facilities=[first_gym])
    config = AppConfig(users=[first], user_choice=0)
    entered, release = asyncio.Event(), asyncio.Event()

    async def facilities(config, profile, ask_password=None):
        entered.set()
        await release.wait()
        if old_request_fails:
            raise services.NetworkProblem('Old account request failed')
        return [first_gym]

    async def register(usr, password):
        return User(id='b', usr=usr, facilities=[own_gym])

    async def session(config, profile, ask_password=None):
        return User(id=profile.id, usr=profile.usr, token='offline-token')

    def add(config, profile):
        config.users.append(profile)
        config.user_choice = len(config.users) - 1
        return config

    monkeypatch.setattr(services, 'ensure_facilities', facilities)
    monkeypatch.setattr(services, 'ensure_session', session)
    monkeypatch.setattr(services, 'register_user', register)
    monkeypatch.setattr(storage, 'save_config', lambda config: None)
    monkeypatch.setattr(storage, 'add_user', add)
    app = MyWellnezzApp(config, FakeEngine())
    async with app.run_test(size=(100, 32)) as pilot:
        try:
            await pilot.click('#menu-open')
            await asyncio.wait_for(entered.wait(), timeout=5)
            await pilot.click('#menu-add')
            await pilot.pause()
            assert isinstance(app.screen, AddUserModal)
            app.screen.query_one('#email').value = 'new@example.test'
            app.screen.query_one('#password').value = 'test-password'
            await pilot.click('#login')
            await pilot.pause()
            assert config.current_user().usr == 'new@example.test'
            release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert config.current_user().facilities == [own_gym]
            assert config.users[0].facilities == [first_gym]
            assert isinstance(app.screen, MenuScreen)
            assert app.user is None
            assert 'Added new@example.test' in app.screen.query_one('#menu-status').render().plain
        finally:
            release.set()


async def test_failed_gym_login_reenables_open_button_for_retry(monkeypatch):
    gyms = [Facility(id='a', name='Gym A'), Facility(id='b', name='Gym B')]
    profile = UserProfile(id='u', usr='user@example.test', facilities=gyms)
    config = AppConfig(users=[profile], user_choice=0)
    attempts = []

    async def facilities(config, profile, ask_password=None):
        return profile.facilities

    async def session(config, profile, ask_password=None):
        attempts.append(profile.usr)
        if len(attempts) == 1:
            raise services.NetworkProblem('Offline: try again')
        return User(id=profile.id, usr=profile.usr, token='offline-token')

    monkeypatch.setattr(services, 'ensure_facilities', facilities)
    monkeypatch.setattr(services, 'ensure_session', session)
    monkeypatch.setattr(storage, 'save_config', lambda config: None)
    app = MyWellnezzApp(config, FakeEngine())
    async with app.run_test() as pilot:
        await pilot.press('enter')
        await pilot.pause()
        await pilot.click('#gym-open')
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, GymScreen)
        assert 'Offline: try again' in app.screen.query_one('#gym-status').render().plain
        assert not app.screen.query_one('#gym-open').disabled
        # Retry by keyboard, independent of Textual's mouse click animation timer.
        app.screen.query_one('#gyms').focus()
        await pilot.press('enter')
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        assert attempts == [profile.usr, profile.usr]
