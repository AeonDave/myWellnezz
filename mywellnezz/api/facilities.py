"""Facility lookup for a logged-in user."""

import logging

from mywellnezz.api.client import ApiError, post_json
from mywellnezz.api.dto import Facility, User
from mywellnezz.api.endpoints import my_facilities_url

logger = logging.getLogger(__name__)


async def my_facilities(user: User) -> list[Facility] | None:
    """Return the user's facilities, ``[]`` when none, ``None`` on failure."""
    payload = {'token': user.token}
    try:
        response = await post_json(my_facilities_url(str(user.id)), payload)
    except ApiError as ex:
        logger.debug('Connection Error: %s', ex)
        return None
    if 'errors' in response:
        errors = response.get('errors') or []
        message = errors[0].get('errorMessage', '?') if errors else '?'
        logger.debug('Error: %s', message)
        return None
    data = response.get('data') or {}
    facilities = data.get('facilities')
    return [] if facilities is None else [Facility.from_payload(f) for f in facilities]
