import json
import os
from os.path import exists
from typing import List

from models.user import User

config_filename = 'conf.json'


class Config:
    def __init__(self, **kwargs):
        self.choice = None
        if len(kwargs) > 0:
            self.users: List[User] = [User(**us) for us in kwargs.get('users')]
        else:
            self.users: List[User] = []

    def set_user(self, c):
        if c < len(self.users):
            self.choice = c

    def get_user(self) -> User:
        return self.users[self.choice]


def read_config() -> Config:
    if exists(config_filename):
        with open(config_filename, encoding='utf-8') as f:
            try:
                return Config(**json.loads(f.read()))
            except Exception:
                print('Error reading config')
                os.remove(config_filename)
    return Config()


def write_config(config: Config):
    with open(config_filename, 'w') as out:
        json.dump(remove_none_values(config.__dict__), out, default=lambda o: o.__dict__, indent=2)


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


def add_user(user: User) -> Config:
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
