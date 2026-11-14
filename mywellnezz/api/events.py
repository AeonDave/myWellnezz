"""Event search and booking/unbooking."""

import logging
from datetime import datetime

from mywellnezz.api.client import ApiError, post_json
from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.api.endpoints import booking_url, search_events_url

logger = logging.getLogger(__name__)


async def search_events(user: User, facility: Facility, start: int) -> dict[str, Event] | None:
    """Return the events of ``facility`` from ``start`` (YYYYMMDD) keyed by uid.

    ``None`` on failure — callers keep their previous state, like v1 did.
    """
    payload = {
        'dateLimit': 1,
        'dateStart': start,
        'eventType': 'Class',
        'timeScope': 'Custom',
        'token': user.token,
    }
    try:
        response = await post_json(search_events_url(str(facility.id)), payload)
    except ApiError as ex:
        logger.debug('Connection Error: %s', ex)
        return None
    if 'errors' in response:
        errors = response.get('errors') or []
        message = errors[0].get('errorMessage', '?') if errors else '?'
        logger.debug('Error: %s', message)
        return None
    data = response.get('data') or {}
    events: dict[str, Event] = {}
    for payload in (data.get('eventItems') or []):
        try:
            event = Event.from_payload(payload)
        except Exception as ex:  # noqa: BLE001 — one malformed event must not kill the list
            logger.debug('Skipping malformed event: %s', ex)
            continue
        if event is not None:
            events[event.uid] = event
    return events


async def book_unbook(user: User, event: Event) -> bool:
    """Book or unbook according to ``event.is_participant``; ``True`` on success."""
    url = booking_url(str(event.id), unbook=event.is_participant)
    payload = {
        'partitionDate': event.partition_date,
        'userId': user.id,
        'token': user.token,
    }
    try:
        response = await post_json(url, payload)
    except ApiError as ex:
        logger.debug('Connection Error: %s', ex)
        return False
    if not response:
        logger.debug('Empty booking response')
        return False
    return bool(response.get('data'))


def today_partition() -> int:
    return int(datetime.now().strftime('%Y%m%d'))
