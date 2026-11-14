"""Login flow against the MyWellness application API."""

from typing import Any

from mywellnezz.api.client import ApiAuthError, post_json
from mywellnezz.api.dto import Facility, User
from mywellnezz.api.endpoints import login_url


async def login(usr: str, pwd: str) -> User:
    """Authenticate and return the user with token and facilities.

    Raises:
        ApiAuthError: the server explicitly rejected the credentials.
        ApiError: network/transport failure — must NOT be treated as bad credentials.
    """
    payload = {
        'domain': 'com.mywellness',
        'keepMeLoggedIn': True,
        'username': usr,
        'password': pwd,
    }
    # Network failures propagate as ApiError: only an ``errors`` body from the
    # server is a credential verdict.
    response = await post_json(login_url(), payload)
    if 'errors' in response:
        raise ApiAuthError(_error_message(response))
    data = response.get('data') or {}
    if 'token' not in response or not data:
        raise ApiAuthError('Unexpected login response')
    user = User.from_payload(data.get('userContext') or {})
    user.usr = usr
    user.set_token(response['token'], response.get('expireIn'))
    user.facilities = [Facility.from_payload(f) for f in (data.get('facilities') or [])]
    return user


def _error_message(response: dict[str, Any]) -> str:
    errors = response.get('errors') or []
    if errors and isinstance(errors, list):
        return str(errors[0].get('errorMessage', 'authentication failed'))
    return 'authentication failed'
