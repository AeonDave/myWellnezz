from app import constants
from app.main_loop import main


def start():
    print(f'[Starting myWellnezz v{constants.version}]')
    main()
    print('[Goodbye]')


if __name__ == '__main__':
    start()
