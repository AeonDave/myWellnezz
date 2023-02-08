import json
import threading
import time
from datetime import datetime, timedelta
from random import randint
from typing import List

import requests
from inputimeout import TimeoutOccurred, inputimeout
from wakepy import set_keepawake

from constants import schema, base_url, api_book
from models.config import read_config, add_user, Config, remove_user
from models.lesson import Lesson, get_lessons, print_lessons
from models.user import print_users, create_user, User
from modules.console_util import clear, print_logo, print_progress_bar
from modules.math_util import percentage_of
from modules.useragent import fake_ua

# noinspection PyUnresolvedReferences
requests.packages.urllib3.disable_warnings()


class MyWellnezz:
    def __init__(self, **kwargs):
        self.p_thread: threading.Thread = None
        self.threads: dict = {}
        self.lessons: list[Lesson] = []
        self.lock = threading.Lock()
        self.timeout = 30
        self.long_cycle = 20
        self.small_cycle = 1
        self.cycle_timeout = self.long_cycle * 60
        self.cycle_iteration = 1
        self.run = True

    def update_timeout(self):
        if len(self.threads) == 0:
            x = percentage_of(self.long_cycle * 60, 15)
            self.cycle_timeout = self.long_cycle * 60 + randint(-x, x)
            self.cycle_iteration = 1
        else:
            x = percentage_of(self.small_cycle * 60, 15)
            self.cycle_timeout = self.small_cycle * 60 + randint(-x, x)
            self.cycle_iteration = 1

    def clean_threads(self):
        for t in self.threads.copy():
            if not self.threads[t].is_alive():
                self.threads[t].join()
                self.threads.pop(t)
            else:
                with self.lock:
                    for ll in self.lessons:
                        if ll.id == t and not ll.is_participant:
                            ll.status = "Booking"
                            break

    def book_lesson(self, user: User, lesson: Lesson):
        sub_url = 'calendar.'
        r = schema + sub_url + base_url + api_book
        booked = False
        while not booked:
            with self.lock:
                cb = [x for x in self.lessons if x.id == lesson.id]
            if len(cb) != 1:
                print('Class not found!')
                break
            lesson = cb[0]
            if lesson.ended:
                print('Class ended')
                break
            if lesson.booking_info.can_book and not lesson.is_participant:
                if user.token is None or not user.token:
                    user.refresh()
                headers = {"User-Agent": fake_ua(), "Content-type": "application/json; charset=utf-8",
                           "Authorization": f'Bearer {user.token}'}
                payload = {"ClassId": f"{lesson.id}", "PartitionDate": lesson.partition_date,
                           "UserId": f"{user.user_id}"}
                try:
                    with requests.Session() as s:
                        p = s.post(r, data=json.dumps(payload), headers=headers, verify=False)
                    if p.status_code != 200:
                        print(f'Something bad happened: {p.status_code}')
                        user.token = None
                    else:
                        r = p.json()
                        if r['result']:
                            booked = r['result'] and r['result'].lower() == 'booked'
                        else:
                            raise SystemError(f'What is this? {r}')
                except Exception:
                    print('Connection Error')
                    time.sleep(60)
            elif (not lesson.is_participant
                  and (lesson.booking_info.start - timedelta(minutes=30)) < datetime.now() < lesson.booking_info.end
                  and self.cycle_timeout > 5 * 60 + 50):
                self.update_timeout()
            time.sleep(5)

    @staticmethod
    def set_option(config: Config):
        opt = 0
        while True:
            len_users = len(config.users)
            try:
                opt = abs(int(input('Select option: ').strip()))
                if opt > len_users + 1:
                    print('Invalid value, retry')
                    continue
            except Exception:
                print('Invalid value, retry')
                continue
            if opt - len_users == 0:
                config = add_user(create_user())
            elif opt - len_users == 1:
                if len_users == 0:
                    print('No user to delete')
                    continue
                u_opt = int(input('Delete user: ').strip())
                config = remove_user(u_opt)
            else:
                break
            clear()
            print_logo()
            print_users(config)
        config.set_user(opt)

    def manage_config(self) -> Config:
        while True:
            config = read_config()
            if len(config.users) == 0:
                clear()
                print_logo()
                print('No users found: Add user')
                config = add_user(create_user())
            clear()
            print_logo()
            print_users(config)
            self.set_option(config)
            if not config.get_user().refresh():
                print('User with invalid credentials')
            else:
                break
        return config

    def manage_print_thread(self, config: Config) -> List[Lesson]:
        d1 = int((datetime.now()).strftime("%Y%m%d"))
        d2 = int((datetime.now() + timedelta(days=1)).strftime("%Y%m%d"))
        with self.lock:
            lessons = get_lessons(config, d1, d2)
            lessons = [x for x in lessons if not x.ended]
        if self.p_thread is None or not self.p_thread.is_alive():
            self.p_thread = threading.Thread(target=self.print_thread)
            self.p_thread.start()
        return lessons

    def manage_threaded_input(self) -> str:
        try:
            print(self.cycle_timeout)
            return inputimeout(timeout=self.cycle_timeout)
        except TimeoutOccurred:
            return None

    def print_thread(self):
        while self.run:
            clear()
            if len(self.lessons) > 0 or self.cycle_timeout > 0:
                self.clean_threads()
                print_logo()
                with self.lock:
                    print_lessons(self.lessons)
                print_progress_bar(self.cycle_iteration, self.cycle_timeout, prefix='Next check in:',
                                   suffix=f'{str(self.cycle_timeout - self.cycle_iteration)} '
                                          f'seconds of {self.cycle_timeout}',
                                   length=50)
                self.cycle_iteration += 1
                print('\nWanna Workout? Choose class!')
            time.sleep(1)

    def main(self):
        config = self.manage_config()
        self.timeout = 30
        self.update_timeout()
        set_keepawake(keep_screen_awake=False)
        while self.run:
            self.lessons = self.manage_print_thread(config)
            index = self.manage_threaded_input()
            self.update_timeout()
            if index is not None and index.strip() != '':
                try:
                    index = int(index.strip())
                    with self.lock:
                        if len(self.lessons) - 1 >= index <= len(self.lessons) - 1:
                            lx = self.lessons[index]
                            if lx.status.lower() == 'open' or lx.status.lower() == 'full' \
                                    or lx.status.lower() == 'planned':
                                tr = threading.Thread(target=self.book_lesson, args=(config.get_user(), lx,))
                                tr.start()
                                self.threads[lx.id] = tr
                            else:
                                print('You cannot book that! are you blind?')
                        else:
                            print('Wrong value')
                    time.sleep(2)
                except Exception:
                    print('Goodbye')
                    self.run = False
