import hashlib
from datetime import datetime
from time import sleep
from typing import Dict, Optional, Set

import colorama
from dateutil import parser
from loguru import logger
from prettytable import PrettyTable

from app.constants import base_url, schema, api_book_app, api_search_app
from models.facility import Facility
from models.usercontext import UserContext
from modules.http_calls import post
from modules.useragent import fake_ua_android


class Event:
    def __init__(self, **kwargs):
        try:
            self.id: str = kwargs.get('id')
            self.name: str = kwargs.get('name')
            self.room: str = kwargs.get('room')
            self.start_hour: int = kwargs.get('startHour')
            self.start_minutes: int = kwargs.get('startMinutes')
            self.end_hour: int = kwargs.get('endHour')
            self.end_minutes: int = kwargs.get('endMinutes')
            self.partition_date: int = kwargs.get('partitionDate')
            self.start_date: int = kwargs.get('startDate')
            self.end_date: int = kwargs.get('endDate')
            self.assigned_to: str = kwargs.get('assignedTo')
            self.picture_url: str = kwargs.get('pictureUrl')
            self.max_participants: int = kwargs.get('maxParticipants')
            self.actual_participants: int = kwargs.get('actualParticipants')
            self.booking_days_in_advance: int = kwargs.get('bookingDaysInAdvance')
            self.cancellation_minutes_in_advance: int = kwargs.get('cancellationMinutesInAdvance')
            self.mets: float = kwargs.get('mets')
            self.estimated_calories: int = kwargs.get('estimatedCalories')
            self.estimated_move: int = kwargs.get('estimatedMove')
            self.waiting_list_counter: int = kwargs.get('waitingListCounter')
            self.day_in_advance_start_hour: int = kwargs.get('dayInAdvanceStartHour')
            self.day_in_advance_start_minutes: int = kwargs.get('dayInAdvanceStartMinutes')
            self.booking_opens_on: datetime = datetime.now() if kwargs.get('bookingOpensOn') is None \
                else parser.parse(kwargs.get('bookingOpensOn')).replace(tzinfo=None)
            self.available_places: int = kwargs.get('availablePlaces')
            self.booking_user_status: str = kwargs.get('bookingUserStatus')
            self.booking_available: bool = kwargs.get('bookingAvailable')
            self.is_participant: bool = kwargs.get('isParticipant')
            self.is_in_waiting_list: bool = kwargs.get('isInWaitingList')
            self.booking_has_waiting_list: bool = kwargs.get('bookingHasWaitingList')
            self.has_penalties_on: bool = kwargs.get('hasPenaltiesOn')
            self.live_event: bool = kwargs.get('liveEvent')
            # self.cannot_track: str = kwargs.get('cannotTrack')
            # self.room_id: str = kwargs.get('roomId')
            # self.calendar_event_type: str = kwargs.get('calendarEventType')
            # self.event_type_id: str = kwargs.get('eventTypeId')
            # self.assigned_to_user_id: str = kwargs.get('assignedToUserId')
            # self.staff_id: str = kwargs.get('staffId')
            # self.facility_name: str = kwargs.get('facility_name')
            # self.facility_id: str = kwargs.get('facilityId')
            # self.has_layout: bool = kwargs.get('hasLayout')
            # self.has_done_item: bool = kwargs.get('hasDoneItem')
            # self.is_single_occurrence: bool = kwargs.get('isSingleOccurrence')
            # self.auto_login: bool = kwargs.get('autoLogin')
            # self.tags: [] = kwargs.get('tags')
            # self.auto_start_event: bool = kwargs.get('autoStartEvent')
            # self.ext_data: {} = kwargs.get('tags')
            # self.participants: [] = kwargs.get('extData')
            # self.skus: [] = kwargs.get('skus')
            self.uid: str = hashlib.sha256(f"{self.id}/{self.partition_date}".encode()).hexdigest()
            self.start: datetime = None if self.partition_date is None else parser.parse(
                f'{self.partition_date}T{str(self.start_hour).zfill(2)}:{str(self.start_minutes).zfill(2)}:00')
            self.end: datetime = None if self.partition_date is None else parser.parse(
                f'{self.partition_date}T{str(self.end_hour).zfill(2)}:{str(self.end_minutes).zfill(2)}:00')
            self.can_book: bool = self.booking_user_status == 'CanBook'
            self.status: str = self.get_status()
        except Exception as ex:
            logger.error(f'Error creating event: {ex}')

    def is_ended(self):
        return datetime.now() >= self.end

    def is_started(self):
        return datetime.now() >= self.start

    def is_bookable(self):
        return self.can_book and self.start > datetime.now() >= self.booking_opens_on

    def get_status(self):
        if not self.booking_available:
            return 'Unshedulable'
        if self.is_in_waiting_list:
            return 'WaitingList'
        if self.is_participant:
            return 'Booked'
        if self.is_bookable():
            return 'Full' if self.available_places == 0 else 'Open'
        if self.is_started() and not self.is_ended():
            return 'Progress'
        return 'Ended' if self.is_ended() else 'Planned'

    def add_table_row(self, index: int, table: PrettyTable):
        color_status = self.status
        if self.status == 'Planned':
            color_status = colorama.Fore.BLUE + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Unshedulable':
            color_status = colorama.Fore.RED + self.status + colorama.Style.RESET_ALL
        elif self.status == 'WaitingList':
            color_status = colorama.Fore.LIGHTYELLOW_EX + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Booked':
            color_status = colorama.Fore.GREEN + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Booking':
            color_status = colorama.Fore.YELLOW + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Open':
            color_status = colorama.Fore.CYAN + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Full':
            color_status = colorama.Fore.LIGHTRED_EX + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Progress':
            color_status = colorama.Fore.LIGHTGREEN_EX + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Ended':
            color_status = colorama.Fore.RED + self.status + colorama.Style.RESET_ALL
        table.add_row(
            [index, self.name, self.assigned_to, self.room, self.start.strftime('%A %d %m  %H:%M').capitalize(),
             self.end.strftime('%H:%M'),
             color_status, self.available_places])


def check_event_diff(events: Dict[str, Event], new_events: Dict[str, Event]) -> Set[str]:
    owl = {x for x in events if events[x].is_in_waiting_list}
    npl = {z for z in new_events if new_events[z].is_participant}
    owl = owl - npl
    nwl = {y for y in new_events if new_events[y].is_in_waiting_list}
    return owl - nwl if len(owl) > len(nwl) else nwl - owl


def action_event(user: UserContext, event: Event) -> bool:
    url = f'{schema}services.{base_url}{api_book_app}/{event.id}/{"unbook" if event.is_participant else "book"}'
    headers = {
        "User-Agent": fake_ua_android(),
        "Content-Type": "application/json; charset=utf-8",
        "X-MWAPPS-CLIENT": "MywellnessAppAndroid40"
    }
    payload = {
        "partitionDate": event.partition_date,
        "userId": user.id,
        "token": user.token
    }
    try:
        response = post(url, headers, payload)
        if not response:
            print('Something bad happened')
        else:
            return bool(response['data'])
    except Exception as ex:
        print(f'Connection Error {ex}')
    return False


def update_events(user: UserContext, facility: Facility, start: int) -> Optional[Dict[str, Event]]:
    url = f'{schema}services.{base_url}{api_search_app}/{facility.id}/SearchCalendarEvents'
    while True:
        if user.token is None or not user.token:
            user.refresh()
        try:
            headers = {
                "User-Agent": fake_ua_android(),
                "Content-Type": "application/json; charset=utf-8",
                "X-MWAPPS-CLIENT": "MywellnessAppAndroid40"
            }
            payload = {
                "dateLimit": 1,
                "dateStart": start,
                "eventType": "Class",
                "timeScope": "Custom",
                "token": user.token
            }
            response = post(url, headers, payload)
            if response and 'errors' in response:
                print(f'Error: {response["errors"][0]["errorMessage"]}')
                return None
            if response and 'data' in response:
                evs = [Event(**e) for e in response['data']['eventItems']]
                return {e.uid: e for e in evs}
        except Exception as ex:
            print(f'Connection Error {ex}')
            sleep(20)
        return None
