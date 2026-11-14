"""myWellnezz entry point."""

import asyncio
import sys

from mywellnezz.app import constants
from mywellnezz.app.keep_awake import start_keep_awake
from mywellnezz.app.session import run_app
from mywellnezz.config.secrets import SecretStoreError


def start():
    print(f'[Starting myWellnezz v{constants.version}]')
    if not sys.stdout.isatty():
        print('[!] No terminal detected: the interface needs a real console window.')
    start_keep_awake()
    try:
        asyncio.run(run_app())
    except (KeyboardInterrupt, EOFError):
        print()
    except SecretStoreError as ex:
        print(f'[Fatal] {ex}')
    print('[Goodbye]')


if __name__ == '__main__':
    start()
