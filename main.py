import json
import threading
import time
from datetime import datetime, timedelta
from os.path import exists
from random import randint
from threading import Thread
from typing import List, Dict

import requests
from inputimeout import inputimeout, TimeoutOccurred
from prettytable import PrettyTable
from wakepy import set_keepawake

from constants import schema, base_url, api_book, api_search
from models.config import Config, User
from models.lesson import Lesson
from util import clear, fake_ua, percentage_of

# noinspection PyUnresolvedReferences
requests.packages.urllib3.disable_warnings()

threads: Dict = {}
lessons: List[Lesson] = []
lock = threading.Lock()

long_cycle = 20
small_cycle = 1

cycle_value_timeout = long_cycle
cycle_timeout = cycle_value_timeout * 60
cycle_iteration = 1


def print_users(conf: Config):
    ptc = PrettyTable(['I', 'User'])
    for iu, u in enumerate(conf.users):
        ptc.add_row([iu, u.usr])
    print(ptc)


def print_lessons():
    with lock:
        ptc = PrettyTable(['I', 'Name', 'Teacher', 'Start', 'End', 'Status', 'Free'])
        for ic, e in enumerate(lessons):
            e.add_table_row(ic, ptc)
        print(ptc)


def clean_threads():
    for t in threads.copy():
        if not threads[t].is_alive():
            threads[t].join()
            threads.pop(t)
        else:
            with lock:
                for ll in lessons:
                    if ll.id == t and not ll.is_participant:
                        ll.status = "Booking"
                        break


def get_classes(conf: Config, fr: int, to: int) -> List[Lesson]:
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


def book_lesson(user: User, lesson: Lesson):
    global cycle_value_timeout, lessons, lock
    sub_url = 'calendar.'
    r = schema + sub_url + base_url + api_book
    booked = False
    while not booked:
        with lock:
            cb = [x for x in lessons if x.id == lesson.id]
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
            payload = {"ClassId": f"{lesson.id}", "PartitionDate": lesson.partition_date, "UserId": f"{user.user_id}"}
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
              and cycle_timeout > 5 * 60 + 50):
            update_timeout()
        time.sleep(5)


def update_timeout():
    global cycle_value_timeout, cycle_timeout, cycle_iteration
    if len(threads) == 0:
        cycle_value_timeout = long_cycle
        x = percentage_of(cycle_value_timeout * 60, 10)
        cycle_timeout = cycle_value_timeout * 60 + randint(-x, x)
        cycle_iteration = 1
    else:
        cycle_value_timeout = small_cycle
        x = percentage_of(cycle_value_timeout * 60, 10)
        cycle_timeout = cycle_value_timeout * 60 + randint(-x, x)
        cycle_iteration = 1


def print_logo():
    logo = '''                    M""MMM""MMM""M          dP dP                                     
                    M  MMM  MMM  M          88 88                                     
88d8b.d8b. dP    dP M  MMP  MMP  M .d8888b. 88 88 88d888b. .d8888b. d888888b d888888b 
88'`88'`88 88    88 M  MM'  MM' .M 88ooood8 88 88 88'  `88 88ooood8    .d8P'    .d8P' 
88  88  88 88.  .88 M  `' . '' .MM 88.  ... 88 88 88    88 88.  ...  .Y8P     .Y8P    
dP  dP  dP `8888P88 M    .d  .dMMM `88888P' dP dP dP    dP `88888P' d888888P d888888P  v1.2 by 430n
                .88 MMMMMMMMMMMMMM                                                    
            d8888P                                                                    
'''
    print(logo)


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='X', print_end="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if iteration == total:
        print()


def print_thread():
    global lessons, cycle_timeout, cycle_iteration
    while run:
        clear()
        if len(lessons) > 0 or cycle_timeout > 0:
            clean_threads()
            print_logo()
            print_lessons()
            print_progress_bar(cycle_iteration, cycle_timeout, prefix='Next check in:',
                               suffix=f'{str(cycle_timeout - cycle_iteration)} seconds of {cycle_timeout}', length=50)
            cycle_iteration += 1
            print('\nWanna Workout? Choose class!')
        time.sleep(1)


if __name__ == '__main__':
    if exists('conf.json'):
        with open('conf.json', encoding='utf-8') as f:
            data = json.loads(f.read())
            config = Config(**data)
            print_users(config)
            config.set_user(input('Select user: '))
            config.get_user().refresh()
    else:
        raise SystemError('Missing config')

    timeout = 30
    p_thread: Thread = None
    update_timeout()
    set_keepawake(keep_screen_awake=False)
    run = True
    while run:
        d1 = int((datetime.now()).strftime("%Y%m%d"))
        d2 = int((datetime.now() + timedelta(days=1)).strftime("%Y%m%d"))
        with lock:
            lessons = get_classes(config, d1, d2)
            lessons = [x for x in lessons if not x.ended]
        if p_thread is None or not p_thread.is_alive():
            p_thread = Thread(target=print_thread)
            p_thread.start()

        index = None
        try:
            print(cycle_timeout)
            index = inputimeout(timeout=cycle_timeout)
        except TimeoutOccurred:
            pass

        update_timeout()

        if index is not None and index.strip() != '':
            try:
                index = int(index.strip())
                with lock:
                    if len(lessons) - 1 >= index <= len(lessons) - 1:
                        lx = lessons[index]
                        if lx.status.lower() == 'open' or lx.status.lower() == 'full' \
                                or lx.status.lower() == 'planned':
                            tr = Thread(target=book_lesson, args=(config.get_user(), lx,))
                            tr.start()
                            threads[lx.id] = tr
                        else:
                            print('You cannot book that! are you blind?')
                    else:
                        print('Wrong value')
                time.sleep(2)
            except Exception:
                print('Goodbye')
                run = False
