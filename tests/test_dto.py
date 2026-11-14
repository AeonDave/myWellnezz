"""Tests for DTO parsing and booking diff logic."""

from datetime import datetime, timedelta

from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.booking.engine import check_event_diff


def _event_payload(**overrides):
    # Tomorrow, so the event is neither started nor ended when the test runs.
    day = datetime.now() + timedelta(days=1)
    payload = {
        'id': 'e1',
        'name': 'Spinning',
        'partitionDate': int(day.strftime('%Y%m%d')),
        'startHour': 10,
        'startMinutes': 30,
        'endHour': 11,
        'endMinutes': 30,
        'bookingAvailable': True,
        'availablePlaces': 5,
        'bookingUserStatus': 'CanBook',
    }
    payload.update(overrides)
    return payload


def test_event_parses_dates_and_uid():
    event = Event.from_payload(_event_payload())
    assert event is not None
    assert event.uid
    day = datetime.now() + timedelta(days=1)
    assert event.start == datetime(day.year, day.month, day.day, 10, 30)
    assert event.end == datetime(day.year, day.month, day.day, 11, 30)
    assert event.can_book is True
    assert event.get_status() in {'Open', 'Full', 'Planned'}


def test_event_without_partition_date_is_dropped():
    assert Event.from_payload(_event_payload(partitionDate=None)) is None


def test_event_statuses():
    assert Event.from_payload(_event_payload(bookingAvailable=False)).get_status() == \
        'Unshedulable'
    assert Event.from_payload(_event_payload(isParticipant=True)).get_status() == 'Booked'
    assert Event.from_payload(_event_payload(availablePlaces=0)).get_status() == 'Full'
    assert Event.from_payload(_event_payload(availablePlaces=3)).get_status() == 'Open'


def test_user_accepts_camel_and_snake_case():
    user = User.from_payload({'id': 'u1', 'accountUsername': 'a@b.c', 'firstName': 'Mario'})
    assert user.usr == 'a@b.c'
    assert user.first_name == 'Mario'
    snake = User.from_payload({'usr': 'x@y.z', 'first_name': 'Luigi'})
    assert snake.usr == 'x@y.z'
    assert snake.first_name == 'Luigi'


def test_facility_from_payload_defaults():
    facility = Facility.from_payload({'id': 'g1', 'name': 'Gym'})
    assert facility.id == 'g1'
    assert facility.phone_number is None


def test_check_event_diff_detects_waiting_list_changes():
    def event(uid, *, wl=False, participant=False):
        e = Event(id=uid, uid=uid)
        e.is_in_waiting_list = wl
        e.is_participant = participant
        return e

    old = {'a': event('a', wl=True), 'b': event('b', wl=True)}
    new = {'a': event('a', wl=True), 'b': event('b', participant=True), 'c': event('c', wl=True)}
    diff = check_event_diff(old, new)
    assert diff == {'c'}
