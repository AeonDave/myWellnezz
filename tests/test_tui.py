"""Focused Pilot coverage for menu controls and modal input."""

from mywellnezz.api.dto import Facility, User
from mywellnezz.app import services
from mywellnezz.booking.engine import MyWellnezz
from mywellnezz.config import storage
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.ui.app import AddUserModal, ConfirmModal, MenuScreen, MyWellnezzApp


def _config() -> AppConfig:
    facility = Facility(id='g1', name='Gym One', address='Via Roma 1')
    profile = UserProfile(id='u1', usr='mario@example.test', facilities=[facility])
    return AppConfig(user_choice=0, users=[profile])


async def test_menu_rows_are_accounts_and_actions_are_buttons():
    app = MyWellnezzApp(_config(), MyWellnezz())
    async with app.run_test():
        assert isinstance(app.screen, MenuScreen)
        assert app.screen.query_one('#users').row_count == 1
        for selector in ('#menu-open', '#menu-add', '#menu-remove', '#menu-quit'):
            assert app.screen.query_one(selector).display


async def test_keyboard_add_opens_and_escape_cancels():
    app = MyWellnezzApp(_config(), MyWellnezz())
    async with app.run_test() as pilot:
        await pilot.press('a')
        await pilot.pause()
        assert isinstance(app.screen, AddUserModal)
        await pilot.press('escape')
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        assert len(app.config.users) == 1


async def test_add_user_uses_fake_registration_and_storage(monkeypatch):
    saved = []
    user = User(id='u2', usr='new@example.test', first_name='New')
    async def fake_register(usr, password):
        assert (usr, password) == ('new@example.test', 'private-test-value')
        return user
    def fake_add(config, profile):
        saved.append(profile.usr)
        config.users.append(profile)
        return config
    monkeypatch.setattr(services, 'register_user', fake_register)
    monkeypatch.setattr(storage, 'add_user', fake_add)
    app = MyWellnezzApp(_config(), MyWellnezz())
    async with app.run_test() as pilot:
        await pilot.click('#menu-add')
        await pilot.pause()
        app.screen.query_one('#email').value = 'new@example.test'
        app.screen.query_one('#password').value = 'private-test-value'
        await pilot.click('#login')
        await pilot.pause()
        assert saved == ['new@example.test']
        assert len(app.config.users) == 2
        assert app.screen.query_one('#users').row_count == 2


async def test_add_user_storage_failure_is_visible(monkeypatch):
    async def fake_register(usr, password):
        return User(id='u2', usr=usr)
    def fail_add(config, profile):
        raise OSError('read-only test config')
    monkeypatch.setattr(services, 'register_user', fake_register)
    monkeypatch.setattr(storage, 'add_user', fail_add)
    app = MyWellnezzApp(_config(), MyWellnezz())
    async with app.run_test() as pilot:
        await pilot.click('#menu-add')
        await pilot.pause()
        app.screen.query_one('#email').value = 'new@example.test'
        app.screen.query_one('#password').value = 'test-only'
        await pilot.click('#login')
        await pilot.pause()
        assert isinstance(app.screen, MenuScreen)
        assert 'Cannot save account' in app.screen.query_one('#menu-status').render().plain
        assert len(app.config.users) == 1


async def test_remove_requires_confirmation_and_quit_shortcut():
    app = MyWellnezzApp(_config(), MyWellnezz())
    async with app.run_test() as pilot:
        await pilot.press('d')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmModal)
        await pilot.press('escape')
        await pilot.pause()
        assert len(app.config.users) == 1
        await pilot.press('q')
        assert not app.is_running
