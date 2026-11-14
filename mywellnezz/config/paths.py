"""Locations of the application configuration files.

The config lives in the OS user-config directory (e.g. ``%APPDATA%\\myWellnezz``
on Windows) instead of the current working directory, so launching the binary
from anywhere always finds the same configuration.
"""

from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = 'myWellnezz'
CONFIG_FILENAME = 'config.json'


def config_dir() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False))


def config_file() -> Path:
    return config_dir() / CONFIG_FILENAME
