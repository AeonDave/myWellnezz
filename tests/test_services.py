"""Tests for session services (typed exceptions, vault interactions)."""

import asyncio

import pytest

from mywellnezz.api.client import ApiAuthError, ApiError
from mywellnezz.api.dto import Facility, User
from mywellnezz.app import services
from mywellnezz.config.models import AppConfig, UserProfile
from tests.fakes import FakeKeyring


@pytest.fixture()
def vault(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(services.secrets, 'keyring', fake)
    return fake


def _profile(**kw) -> UserProfile:
    return UserProfile(id='u1', usr='mario@example.com', **kw)


def _patch_auth(monkeypatch, *, login=None, error=None):
    async def fake_login(usr, pwd):
        if error is not None:
            raise error
        return login or User(id='u1', usr=usr, token='tok', token_expire=None)

    monkeypatch.setattr(services.auth, 'login', fake_login)


async def test_login_with_vault_password(vault, monkeypatch):
    vault.store[('myWellnezz', 'mario@example.com')] = 'hunter2'
    _patch_auth(monkeypatch)
    user = await services.login_profile(_profile())
    assert user.usr == 'mario@example.com'
    assert user.token == 'tok'


async def test_login_without_vault_needs_ask(vault, monkeypatch):
    _patch_auth(monkeypatch)
    with pytest.raises(services.CredentialsRejected):
        await services.login_profile(_profile())


async def test_login_prompts_and_stores_password(vault, monkeypatch):
    _patch_auth(monkeypatch)

    async def ask(usr):
        return 'typed-pwd'

    user = await services.login_profile(_profile(), ask_password=ask)
    assert user.token == 'tok'
    assert vault.store[('myWellnezz', 'mario@example.com')] == 'typed-pwd'


async def test_login_cancelled_prompt(vault, monkeypatch):
    _patch_auth(monkeypatch)

    async def ask(usr):
        return None

    with pytest.raises(services.Cancelled):
        await services.login_profile(_profile(), ask_password=ask)


async def test_auth_rejection_raises_credentials_rejected(vault, monkeypatch):
    _patch_auth(monkeypatch, error=ApiAuthError('wrong password'))
    with pytest.raises(services.CredentialsRejected):
        await services.login_profile(_profile(), ask_password=_ask)


async def test_network_error_raises_network_problem(vault, monkeypatch):
    _patch_auth(monkeypatch, error=ApiError('timeout'))
    with pytest.raises(services.NetworkProblem):
        await services.login_profile(_profile(), ask_password=_ask)


async def test_ensure_session_fast_path_uses_vault_token(vault, monkeypatch):
    from datetime import datetime, timedelta

    vault.store[('myWellnezz', 'mario@example.com#token')] = 'saved-token'
    profile = _profile(token_expire=datetime.now() + timedelta(weeks=30))
    called = False

    async def fake_login(usr, pwd):
        nonlocal called
        called = True
        return User(usr=usr)

    monkeypatch.setattr(services.auth, 'login', fake_login)
    user = await services.ensure_session(None, profile)
    assert user.token == 'saved-token'
    assert called is False


async def test_ensure_facilities_no_gyms(vault, monkeypatch):
    async def fake_facilities(user):
        return []

    monkeypatch.setattr(services, 'my_facilities', fake_facilities)
    with pytest.raises(services.NoGyms):
        await services.ensure_facilities(None, _profile())


async def test_ensure_facilities_retries_then_network(vault, monkeypatch):
    calls = []

    async def fake_facilities(user):
        calls.append(user)

    monkeypatch.setattr(services, 'my_facilities', fake_facilities)
    _patch_auth(monkeypatch)
    with pytest.raises(services.NetworkProblem):
        await services.ensure_facilities(AppConfig(), _profile(), ask_password=_ask)
    assert len(calls) == services.FACILITY_RETRIES


async def test_register_user_stores_password(vault, monkeypatch):
    _patch_auth(monkeypatch)
    user = await services.register_user('mario@example.com', 'hunter2')
    assert user.token == 'tok'
    assert vault.store[('myWellnezz', 'mario@example.com')] == 'hunter2'


async def _ask(usr: str = 'mario@example.com') -> str:
    return 'typed-pwd'


async def test_refresh_session_preserves_selected_facility(vault, monkeypatch):
    gym = Facility(id='g1', name='Saved gym')
    profile = _profile(facilities=[gym])
    config = AppConfig(users=[profile], user_choice=0, facility_choice=0)
    _patch_auth(monkeypatch)
    monkeypatch.setattr(services, 'replace_user', _replace_in_memory)
    await services.ensure_session(config, profile, ask_password=_ask)
    assert config.current_facility() == gym


async def test_facility_retry_uses_fresh_user_and_updates_current_profile(vault, monkeypatch):
    profile = _profile()
    config = AppConfig(users=[profile], user_choice=0)
    gym = Facility(id='g1', name='Fresh gym')
    seen = []

    async def facilities(user):
        seen.append((user.id, user.token))
        return None if len(seen) == 1 else [gym]

    _patch_auth(monkeypatch, login=User(id='fresh-id', usr=profile.usr, token='fresh-token'))
    monkeypatch.setattr(services, 'my_facilities', facilities)
    monkeypatch.setattr(services, 'replace_user', _replace_in_memory)
    assert await services.ensure_facilities(config, profile, ask_password=_ask) == [gym]
    assert seen == [('u1', None), ('fresh-id', 'fresh-token')]
    assert config.current_user().facilities == [gym]


def _replace_in_memory(config, index, profile):
    config.users[index] = profile
    return config


async def test_login_completion_updates_originating_account_not_new_selection(vault, monkeypatch):
    first = _profile()
    second = UserProfile(id='u2', usr='second@example.com')
    config = AppConfig(users=[first, second], user_choice=0)
    entered = asyncio.Event()
    resume = asyncio.Event()

    async def login(usr, pwd):
        entered.set()
        await resume.wait()
        return User(id='fresh-id', usr=usr, token='fresh-token')

    monkeypatch.setattr(services.auth, 'login', login)
    monkeypatch.setattr(services, 'replace_user', _replace_in_memory)
    task = asyncio.create_task(services.ensure_session(config, first, ask_password=_ask))
    try:
        await entered.wait()
        config.set_user_choice(1)
        resume.set()
        await task
        assert config.users[1] is second
        assert config.users[0].id == 'fresh-id'
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_facilities_completion_does_not_write_to_another_account(vault, monkeypatch):
    first = _profile()
    second = UserProfile(id='u2', usr='second@example.com')
    config = AppConfig(users=[first, second], user_choice=0)
    gym = Facility(id='g1')

    async def facilities(user):
        config.set_user_choice(1)
        return [gym]

    monkeypatch.setattr(services, 'my_facilities', facilities)
    assert await services.ensure_facilities(config, first) == [gym]
    assert second.facilities == []
    assert first.facilities == [gym]


async def test_login_completion_does_not_restore_removed_account(vault, monkeypatch):
    first = _profile()
    second = UserProfile(id='u2', usr='second@example.com')
    config = AppConfig(users=[first, second], user_choice=0)

    async def login(usr, pwd):
        config.users.pop(0)
        config.set_user_choice(0)
        return User(id='fresh-id', usr=usr, token='fresh-token')

    monkeypatch.setattr(services.auth, 'login', login)
    monkeypatch.setattr(services, 'replace_user', _replace_in_memory)
    await services.ensure_session(config, first, ask_password=_ask)
    assert config.users == [second]


@pytest.mark.parametrize('via_login', [True, False])
@pytest.mark.parametrize('remove_selected', [True, False])
async def test_membership_refresh_preserves_selected_gym_by_id(
    vault, monkeypatch, via_login, remove_selected
):
    first_gym, second_gym = Facility(id='a'), Facility(id='b')
    profile = _profile(facilities=[first_gym, second_gym])
    config = AppConfig(users=[profile], user_choice=0, facility_choice=0)
    refreshed = [second_gym] if remove_selected else [second_gym, first_gym]
    monkeypatch.setattr(services, 'replace_user', _replace_in_memory)
    if via_login:
        _patch_auth(monkeypatch, login=User(usr=profile.usr, token='tok', facilities=refreshed))
        await services.ensure_session(config, profile, ask_password=_ask)
    else:
        async def facilities(user):
            return refreshed
        monkeypatch.setattr(services, 'my_facilities', facilities)
        await services.ensure_facilities(config, profile)
    if remove_selected:
        assert config.facility_choice is None
    else:
        assert config.current_facility().id == 'a'
        assert config.facility_choice == 1
