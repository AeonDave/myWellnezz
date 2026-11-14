"""Session services: login, facilities and user registration.

Pure async logic with typed exceptions — no printing. The TUI catches these
and shows notifications; storage mutations happen here on success only.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from mywellnezz.api import auth
from mywellnezz.api.client import ApiAuthError, ApiError
from mywellnezz.api.dto import Facility, User
from mywellnezz.api.facilities import my_facilities
from mywellnezz.config import secrets
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.config.storage import replace_user

FACILITY_RETRIES = 3
# Fast path: skip login while the token outlives the grace window (v1 semantics).
TOKEN_GRACE = timedelta(weeks=8)

AskPassword = Callable[[str], Awaitable[str | None]]


class CredentialsRejected(Exception):
    """The server explicitly rejected the credentials."""


class NetworkProblem(Exception):
    """Transport failure (timeout, DNS, unreachable)."""


class NoGyms(Exception):
    """The user is not registered in any facility."""


class Cancelled(Exception):
    """The user cancelled an interactive prompt."""


async def login_profile(
    profile: UserProfile, ask_password: AskPassword | None = None
) -> User:
    """Login with the vault password; ask via ``ask_password`` when the vault has none."""
    pwd = secrets.get_password(profile.usr) if profile.usr else None
    prompted = False
    if not pwd:
        if ask_password is None:
            raise CredentialsRejected('No stored password for this user')
        pwd = await ask_password(profile.usr)
        if not pwd:
            raise Cancelled()
        prompted = True
    try:
        user = await auth.login(profile.usr, pwd)
    except ApiAuthError as ex:
        raise CredentialsRejected(str(ex)) from ex
    except ApiError as ex:
        raise NetworkProblem(str(ex)) from ex
    if prompted and profile.usr:
        secrets.save_password(profile.usr, pwd)
    return user


def _profile_index(config: AppConfig, usr: str | None) -> int | None:
    """Resolve the originating account again after I/O, never the selected row."""
    if not usr:
        return None
    return next((i for i, profile in enumerate(config.users) if profile.usr == usr), None)


def _preserve_facility_choice(
    config: AppConfig, index: int, facilities: list[Facility]
) -> None:
    """Keep a selected gym by identity when its membership list changes order."""
    if config.user_choice != index:
        return
    previous = config.users[index].facilities
    choice = config.facility_choice
    selected_id = previous[choice].id if choice is not None and 0 <= choice < len(previous) else None
    config.facility_choice = next(
        (i for i, facility in enumerate(facilities) if selected_id and facility.id == selected_id),
        None,
    )


def persist_user(config: AppConfig, user: User) -> None:
    """Commit fresh data to its originating account, even if selection changed."""
    index = _profile_index(config, user.usr)
    if index is None:
        # The account may have been removed while the request was pending.
        return
    if user.usr and user.token:
        secrets.save_token(user.usr, user.token)
    previous = config.users[index]
    # Login can omit memberships. Keep the known gyms until an explicit lookup.
    if not user.facilities:
        user.facilities = list(previous.facilities)
    _preserve_facility_choice(config, index, user.facilities)
    replace_user(config, index, UserProfile.from_user(user))


async def ensure_session(
    config: AppConfig, profile: UserProfile, ask_password: AskPassword | None = None
) -> User:
    """Return a logged-in runtime user (vault token fast path, else login)."""
    if profile.token_expire is not None and profile.token_expire >= datetime.now() + TOKEN_GRACE:
        token = secrets.get_token(profile.usr)
        if token:
            return profile.as_user(token)
    user = await login_profile(profile, ask_password)
    persist_user(config, user)
    return user


async def ensure_facilities(
    config: AppConfig, profile: UserProfile, ask_password: AskPassword | None = None
) -> list[Facility]:
    """Fetch the user's facilities, retrying with a fresh login. Raises typed errors."""
    runtime = profile.as_user(secrets.get_token(profile.usr) if profile.usr else None)
    for attempt in range(FACILITY_RETRIES):
        facilities = await my_facilities(runtime)
        if facilities is not None:
            if len(facilities) == 0:
                raise NoGyms()
            index = _profile_index(config, profile.usr)
            if index is not None:
                # A request must not update another account selected during I/O.
                _preserve_facility_choice(config, index, facilities)
                config.users[index].facilities = list(facilities)
            return facilities
        if attempt + 1 < FACILITY_RETRIES:
            runtime = await login_profile(profile, ask_password)
            persist_user(config, runtime)
    raise NetworkProblem('Could not fetch gyms')


async def register_user(usr: str, pwd: str) -> User:
    """Verify new credentials, store the password in the vault, return the user."""
    try:
        user = await auth.login(usr, pwd)
    except ApiAuthError as ex:
        raise CredentialsRejected(str(ex)) from ex
    except ApiError as ex:
        raise NetworkProblem(str(ex)) from ex
    secrets.save_password(usr, pwd)
    if user.token:
        secrets.save_token(usr, user.token)
    return user
