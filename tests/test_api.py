"""Regression tests: transport errors and malformed payloads must never escape."""

import httpx
import pytest

from mywellnezz.api import client as api_client
from mywellnezz.api import events as api_events
from mywellnezz.api import facilities as api_facilities
from mywellnezz.api.client import ApiError
from mywellnezz.api.dto import Event, Facility, User


async def test_post_json_invalid_json_raises_api_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, text='<html>captive portal</html>')

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def fake_get_client():
        return http

    monkeypatch.setattr(api_client, 'get_client', fake_get_client)
    with pytest.raises(ApiError):
        await api_client.post_json('https://example.test/x', {})
    await http.aclose()


async def test_search_events_skips_malformed_events(monkeypatch, capsys):
    payload = {
        'data': {
            'eventItems': [
                {'id': 'e1', 'partitionDate': 20990101, 'startHour': 10, 'startMinutes': 0,
                 'endHour': 11, 'endMinutes': 0, 'bookingAvailable': True},
                {'id': 'bad', 'partitionDate': 20990101, 'startHour': 'not-a-number',
                 'startMinutes': None, 'endHour': 11, 'endMinutes': 0},
            ]
        }
    }

    async def fake_post(url, body):
        return payload

    monkeypatch.setattr(api_events, 'post_json', fake_post)
    events = await api_events.search_events(User(id='u1'), Facility(id='g1'), 20990101)
    assert len(events) == 1
    assert all(e.uid for e in events.values())
    captured = capsys.readouterr()
    assert captured.out == captured.err == ''


async def test_search_events_error_response_returns_none(monkeypatch, capsys):
    async def fake_post(url, body):
        return {'errors': [{'errorMessage': 'bad token'}]}

    monkeypatch.setattr(api_events, 'post_json', fake_post)
    assert await api_events.search_events(User(id='u1'), Facility(id='g1'), 20990101) is None
    captured = capsys.readouterr()
    assert captured.out == captured.err == ''


async def test_search_events_transport_error_returns_none(monkeypatch, capsys):
    async def fake_post(url, body):
        raise ApiError('boom')

    monkeypatch.setattr(api_events, 'post_json', fake_post)
    assert await api_events.search_events(User(id='u1'), Facility(id='g1'), 20990101) is None
    captured = capsys.readouterr()
    assert captured.out == captured.err == ''


async def test_my_facilities_error_response_returns_none_without_output(monkeypatch, capsys):
    async def fake_post(url, body):
        return {'errors': [{'errorMessage': 'bad token'}]}

    monkeypatch.setattr(api_facilities, 'post_json', fake_post)
    assert await api_facilities.my_facilities(User(id='u1')) is None
    captured = capsys.readouterr()
    assert captured.out == captured.err == ''


async def test_my_facilities_transport_error_returns_none_without_output(monkeypatch, capsys):
    async def fake_post(url, body):
        raise ApiError('boom')

    monkeypatch.setattr(api_facilities, 'post_json', fake_post)
    assert await api_facilities.my_facilities(User(id='u1')) is None
    captured = capsys.readouterr()
    assert captured.out == captured.err == ''


async def test_book_unbook_transport_error_returns_false_without_output(monkeypatch, capsys):
    async def fake_post(url, body):
        raise ApiError('boom')

    monkeypatch.setattr(api_events, 'post_json', fake_post)
    assert await api_events.book_unbook(User(id='u1'), Event(id='e1')) is False
    captured = capsys.readouterr()
    assert captured.out == captured.err == ''


async def test_book_unbook_empty_response_returns_false_without_output(monkeypatch, capsys):
    async def fake_post(url, body):
        return {}

    monkeypatch.setattr(api_events, 'post_json', fake_post)
    assert await api_events.book_unbook(User(id='u1'), Event(id='e1')) is False
    captured = capsys.readouterr()
    assert captured.out == captured.err == ''


@pytest.mark.parametrize(
    ('is_participant', 'is_in_waiting_list', 'action'),
    [
        (False, False, 'book'),
        (True, False, 'unbook'),
        (False, True, 'book'),
        (True, True, 'unbook'),
    ],
)
async def test_book_unbook_endpoint_and_payload(
    monkeypatch, is_participant, is_in_waiting_list, action
):
    request = {}

    async def fake_post(url, body):
        request['url'] = url
        request['body'] = body
        return {'data': {'success': True}}

    monkeypatch.setattr(api_events, 'post_json', fake_post)
    user = User(id='u1', token='token-1')
    event = Event(
        id='e1',
        partition_date=20990101,
        is_participant=is_participant,
        is_in_waiting_list=is_in_waiting_list,
    )

    assert await api_events.book_unbook(user, event) is True
    assert request == {
        'url': f'https://services.mywellness.com/Core/CalendarEvent/e1/{action}',
        'body': {'partitionDate': 20990101, 'userId': 'u1', 'token': 'token-1'},
    }
