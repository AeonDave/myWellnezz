import asyncio
import random
from datetime import timedelta, datetime
from typing import Any, Union, Optional

import aioconsole as aioconsole
import mouse

from models.config import Config, read_config, add_user, remove_user, update_user
from models.facility import Facility, my_facilities
from models.mywellnezz import MyWellnezz
from models.usercontext import create_user, UserContext
from modules.console_util import print_missing_facility, print_facilities, print_users


def get_config(mw: MyWellnezz) -> Optional[Config]:
    config = read_config()
    while True:
        print_users(config)
        opt = get_input(mw, 'Select option: ')
        if opt > len(config.users) + 1:
            print('Invalid value, retry')
            continue
        if opt - len(config.users) == 0:
            config = add_user(create_user())
            continue
        elif opt - len(config.users) == 1:
            if len(config.users) == 0:
                print('No user to delete')
                continue
            u_opt = int(input('Delete user: ').strip())
            config = remove_user(u_opt)
        else:
            config.set_user_choice(opt)
        user = config.get_user()
        if not set_user_facilities(mw, user, config):
            print_missing_facility()
            return None
        if user.token_expire is not None and user.token_expire - timedelta(weeks=8) >= datetime.now():
            break
        logged, user = config.get_user().refresh()
        if not logged:
            print('User with invalid credentials')
            remove_user(config.user_choice)
        else:
            config.set_user(user, config.user_choice, True)
            break
    return config


def get_input(mw: MyWellnezz, inp: str):
    opt = None
    while True:
        if not mw.test:
            opt = input(inp).strip()
        if not mw.test and (not opt or not opt.isnumeric()):
            print('Invalid value, retry')
            continue
        return 0 if mw.test else abs(int(opt))


def set_user_facilities(mw: MyWellnezz, user: UserContext, config: Config):
    user.facilities = my_facilities(user)
    while user.facilities is None:
        logged, user = user.login_app()
        config = update_user(user)
    if len(user.facilities) == 0:
        return False
    print_facilities(config)
    len_facilities = len(config.get_user().facilities)
    if len_facilities > 1:
        opt = get_input(mw, 'Select gym: ')
    elif len_facilities == 1:
        opt = 0
    else:
        raise ValueError('no facilities found')
    config.set_facility_choice(opt)
    return True


async def set_user_facility(mw: MyWellnezz, config: Config):
    print_facilities(config)
    len_facilities = len(config.get_user().facilities)
    if len_facilities > 1:
        opt = get_input(mw, 'Select gym: ')
    elif len_facilities == 1:
        opt = 0
    else:
        raise ValueError('no facilities found')
    config.set_facility_choice(opt)


async def book_event(mw: MyWellnezz, user: UserContext, facility: Facility, key: str):
    try:
        await mw.set_book_task(user, facility, await mw.get_event(key))
    except Exception as ex:
        print(f'Goodbye: {ex}')
        mw.run = False


async def numeric_action(mw: MyWellnezz, user: UserContext, facility: Facility, index: int, events: dict):
    if index < len(events):
        await book_event(mw, user, facility, await mw.get_event_id_by_index(index))
    else:
        print('Invalid input')


async def main_loop(mw: MyWellnezz, config: Union[Config, Any]):
    if config is None or config.user_choice is None or config.facility_choice is None:
        print('You are missing some mandatory information')
    else:
        while mw.run:
            try:
                user = config.get_user()
                facility = config.get_facility()
                mw.set_event_task(user, facility, config)
                events = await mw.get_events()
                if len(events) == 0:
                    print('[Looking for lessons...]')
                    await asyncio.sleep(2)
                else:
                    index = (await aioconsole.ainput()).strip()
                    if index != '':
                        if index.isnumeric():
                            await numeric_action(mw, user, facility, abs(int(index)), events)
                        elif index.lower() == 'r':
                            events = await mw.set_events(user, facility)
                        else:
                            print('[Closing...]')
                            mw.run = False
                            await asyncio.gather(mw.print_task)
                            await asyncio.gather(*mw.book_tasks.values())
                            break
                    await mw.set_loops_timeout(events)
                await asyncio.sleep(1)
            except Exception as ex:
                print(f'Error: {ex}')
        await asyncio.sleep(0)


async def awake():
    movement = 30
    wait_for = 60 * 5
    current_position = mouse.get_position()
    expected_position = current_position

    while True:
        await asyncio.sleep(wait_for)
        current_position = mouse.get_position()
        if current_position != expected_position:
            expected_position = current_position
            continue

        for i in range(3):
            x_move = random.randint(-movement, movement)
            y_move = random.randint(-movement, movement)
            mouse.move(x_move, y_move, absolute=False)
            await asyncio.sleep(0.5)


def main():
    asyncio.get_event_loop().create_task(awake())
    mw = MyWellnezz()
    c = get_config(mw)
    asyncio.run(main_loop(mw, c), debug=mw.test)
