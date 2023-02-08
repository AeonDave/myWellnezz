import os
from typing import Dict

from prettytable import PrettyTable

import constants
from models.config import Config
from models.event import Event
from models.facility import Facility
from models.usercontext import UserContext
from modules.ascii_art import AsciiArt

current_art = None


def clear():
    os.system('cls') if os.name == 'nt' else os.system('clear')


def print_logo():
    print(constants.logo)


def print_progress_bar(i, total, prefix='', suffix='', decimals=1, length=100, fill='█', print_end="\r") -> bool:
    percent = ("{0:." + str(decimals) + "f}").format(100 * (i / float(total)))
    filled_length = int(length * i // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    return i >= total


def print_clear_logo():
    clear()
    print_logo()


def print_missing_facility():
    clear()
    print_logo()
    print('Sorry but you are not registered in any gym!')


def print_users(config: Config):
    clear()
    print_logo()
    _print_users(config)


def print_facilities(config: Config):
    clear()
    print_logo()
    _print_facilities(config)


def _print_users(config: Config):
    ptc = PrettyTable(['I', 'User'])
    iu = -1
    for iu, u in enumerate(config.users):
        ptc.add_row([iu, u.usr])
    ptc.add_row([iu + 1, 'Add user'])
    ptc.add_row([iu + 2, 'Delete user'])
    print(ptc)


def _print_facilities(config: Config):
    ptc = PrettyTable(['I', 'Gym', 'Address'])
    for iu, u in enumerate(config.get_user().facilities):
        ptc.add_row([iu, u.name, u.address])
    print(ptc)


async def print_events(facility: Facility, user: UserContext, events: Dict[str, Event], iteration: int,
                       timeout: int) -> bool:
    clear()
    print_logo()
    await _print_facility_logo(facility)
    _print_user(user)
    _print_events(events)
    end = print_progress_bar(iteration, timeout, prefix='Next check in:',
                             suffix=f'{str(timeout - iteration)} '
                                    f'seconds of {timeout}',
                             length=50)
    print('\nChoose class!')
    return end


async def _print_facility_logo(facility: Facility):
    global current_art
    if current_art is None:
        current_art = AsciiArt()
        await current_art.generate_ascii(facility.logo_url)
    current_art.print_art()


def _print_events(events: Dict[str, Event]):
    ptc = PrettyTable(['I', 'Name', 'Teacher', 'Room', 'Start', 'End', 'Status', 'Free'])
    for ic, e in enumerate(list(events.values())):
        e.add_table_row(ic, ptc)
    print(ptc)


def _print_user(user: UserContext):
    print(f'{user.first_name} {user.last_name}: {user.display_height}/{user.display_weight}')
