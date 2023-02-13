import asyncio
import datetime
import json
import os
import uuid
from os.path import exists
from typing import List, Optional

from models.facility import Facility, my_facilities
from models.usercontext import UserContext
from modules.math_util import write_obfuscation, read_obfuscation

config_filename = 'conf.json'


class Config:
    def __init__(self, **kwargs):
        self.user_choice: Optional[int] = None
        self.facility_choice: Optional[int] = None
        self.auto_book: bool = True
        if kwargs:
            self.users: List[UserContext] = [UserContext(**us) for us in kwargs.get('users')]
        else:
            self.users: List[UserContext] = []

    def set_facility_choice(self, c):
        if c < len(self.get_user().facilities):
            self.facility_choice = c

    def set_user_choice(self, c):
        if c < len(self.users):
            self.user_choice = c

    def set_user(self, user: UserContext, choice: int, save: bool = False):
        if choice < len(self.users):
            self.users[choice] = user
            if save:
                write_config(self)

    def get_user(self) -> UserContext:
        return self.users[self.user_choice]

    async def get_facility(self) -> Facility:
        if len(self.get_user().facilities) > self.facility_choice:
            return self.get_user().facilities[self.facility_choice]
        while True:
            f = await my_facilities(self.get_user())
            if not f or len(f) == 0:
                print('No gym found')
                await asyncio.sleep(2)
                continue
            self.get_user().facilities = f
            return self.get_user().facilities[self.facility_choice]


def read_config() -> Config:
    if exists(config_filename):
        with open(config_filename, encoding='utf-8') as f:
            try:
                txt = read_obfuscation(str(uuid.getnode()), f.read())
                return Config(**json.loads(txt))
            except Exception as ex:
                print(f'Error reading config {ex}')
                os.remove(config_filename)
    return Config()


def write_config(config: Config):
    with open(config_filename, 'w') as out:
        txt = write_obfuscation(str(uuid.getnode()),
                                json.dumps(remove_none_values(config.__dict__), default=json_default, indent=2))
        out.write(txt)


def json_default(value):
    if isinstance(value, datetime.date):
        return value.isoformat()
    else:
        return value.__dict__


def remove_none_values(d):
    for key, value in list(d.items()):
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            remove_none_values(value)
        elif isinstance(value, list):
            for lt in value:
                if hasattr(lt, '__class__'):
                    if isinstance(value, dict):
                        remove_none_values(lt)
                    else:
                        remove_none_values(lt.__dict__)
    return d


def add_user(user: UserContext) -> Config:
    config = read_config()
    config.users.append(user)
    write_config(config)
    return read_config()


def remove_user(ui: int) -> Config:
    config = read_config()
    if len(config.users) > ui:
        config.users.pop(ui)
    write_config(config)
    return read_config()
