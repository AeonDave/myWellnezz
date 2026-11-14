"""MyWellness API endpoint URLs."""

from mywellnezz.app.constants import app_id, base_url, schema

_SERVICES = f'{schema}services.{base_url}'


def login_url() -> str:
    return f'{_SERVICES}/Application/{app_id}/Login'


def my_facilities_url(user_id: str) -> str:
    return f'{_SERVICES}/Core/User/{user_id}/MyFacilities'


def search_events_url(facility_id: str) -> str:
    return f'{_SERVICES}/Core/Facility/{facility_id}/SearchCalendarEvents'


def booking_url(event_id: str, unbook: bool) -> str:
    action = 'unbook' if unbook else 'book'
    return f'{_SERVICES}/Core/CalendarEvent/{event_id}/{action}'
