import os

import constants


def clear():
    os.system('cls') if os.name == 'nt' else os.system('clear')


def print_logo():
    print(constants.logo)


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='X', print_end="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if iteration == total:
        print()
