import time
from datetime import datetime
from typing import List

import colorama
import requests
from prettytable import PrettyTable

from constants import schema, base_url, api_search
from models.booking import Booking
from models.config import Config
from modules.useragent import fake_ua


class Lesson:
    def __init__(self, **kwargs):
        self.id: str = kwargs.get('id')
        self.name: str = kwargs.get('name')
        self.room: str = kwargs.get('room')
        self.teacher: str = kwargs.get('assignedTo')
        self.partition_date: str = kwargs.get('partitionDate')
        self.start: datetime = datetime.fromisoformat(kwargs.get('startDate'))
        self.end: datetime = datetime.fromisoformat(kwargs.get('endDate'))
        self.booking_info: Booking = Booking(self.start, **kwargs.get('bookingInfo'))
        self.max_participants: int = kwargs.get('maxParticipants')
        self.available: int = kwargs.get('availablePlaces')
        self.participants: int = kwargs.get('numberOfParticipants')
        self.is_participant: bool = kwargs.get('isParticipant')
        self.is_in_waiting_list: bool = kwargs.get('isInWaitingList')
        self.started: bool = self.is_started()
        self.ended: bool = self.is_ended()
        self.status: str = self.get_status()

    def is_ended(self):
        return datetime.now() >= self.end

    def is_started(self):
        return datetime.now() >= self.start

    def add_table_row(self, index: int, table: PrettyTable):
        color_status = self.status
        if self.status == 'Planned':
            color_status = colorama.Fore.BLUE + self.status + colorama.Style.RESET_ALL
        elif self.status == 'Unshedulable':
            color_status = colorama.Fore.RED + self.status + colorama.Style.RESET_ALL
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
            [index, self.name, self.teacher, self.start.strftime('%A %d %H:%M'), self.end.strftime('%H:%M'),
             color_status, self.available])

    def get_status(self):
        status = 'Planned'
        if not self.booking_info.available:
            return 'Unshedulable'
        if self.is_participant:
            return 'Booked'
        if self.booking_info.can_book and self.booking_info.start < datetime.now() < self.booking_info.end:
            status = 'Open'
        if self.available == 0 and self.booking_info.start < datetime.now() < self.booking_info.end:
            status = 'Full'
        if self.booking_info.end <= datetime.now():
            status = 'Progress'
        if self.ended:
            status = 'Ended'
        return status


def get_lessons(conf: Config, fr: int, to: int) -> List[Lesson]:
    sub_url = 'calendar.'
    api = f'?eventTypes=Class&facilityId={conf.get_user().facility}&toDate={to}&fromDate={fr}'
    r = schema + sub_url + base_url + api_search + api
    while True:
        if conf.get_user().token is None or not conf.get_user().token:
            conf.get_user().refresh()
        headers = {"User-Agent": fake_ua(), "Authorization": f'Bearer {conf.get_user().token}'}
        try:
            with requests.Session() as s:
                p = s.get(r, headers=headers, verify=False)
            if p.status_code != 200:
                print(f'Something bad happened: {p.status_code}')
                conf.get_user().token = None
                time.sleep(30)
            else:
                return [Lesson(**c) for c in p.json()]
        except Exception:
            print('Connection Error')


def print_lessons(lessons: List[Lesson]):
    ptc = PrettyTable(['I', 'Name', 'Teacher', 'Start', 'End', 'Status', 'Free'])
    for ic, e in enumerate(lessons):
        e.add_table_row(ic, ptc)
    print(ptc)
