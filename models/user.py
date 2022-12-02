import base64
import json
import msvcrt
import re
import sys
import uuid

import requests
from prettytable import PrettyTable

from constants import schema, base_url
from modules.useragent import fake_ua

email_re = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'


class User:
    def __init__(self, **kwargs):
        self.usr: str = kwargs.get('usr')
        self.pwd: str = kwargs.get('pwd')
        self.facility: str = kwargs.get('facility')
        self.user_id: str = None
        self.token: str = None

    def login(self):
        sub_url = 'account.'
        api = '/v2/admin/authentication/Login'
        r = schema + sub_url + base_url + api
        headers = {"User-Agent": fake_ua(), "Content-type": "application/json; charset=utf-8"}
        payload = {"username": f"{self.usr}", "password": f"{self.pwd}"}
        with requests.Session() as s:
            p = s.post(r, data=json.dumps(payload), headers=headers, verify=False)
        if p.status_code != 200:
            return False, None, None
        else:
            r = p.json()
            if r['token']:
                b64d = base64.b64decode(r['token'].split('.')[0][:-1]).decode('utf-8').split('|')[6]
                return True, r['token'], uuid.UUID(str(b64d))
            else:
                return False, None, None

    def refresh(self):
        logged, self.token, self.user_id = self.login()
        return logged


def create_user() -> User:
    user = User()
    while True:
        user.usr = input('Insert username:\n').replace(" ", "").strip()
        if re.fullmatch(email_re, user.usr):
            break

    print('Insert password:')
    user.pwd = ''
    while True:
        x = msvcrt.getch()
        if x.decode() == '\r':
            break
        sys.stdout.write('*')
        user.pwd += x.decode()
    print('\n')
    user.facility = input('Insert Gym ID:\n').replace(" ", "").strip()
    return user


def print_users(conf):
    ptc = PrettyTable(['I', 'User'])
    iu = -1
    for iu, u in enumerate(conf.users):
        ptc.add_row([iu, u.usr])
    ptc.add_row([iu + 1, 'Add user'])
    ptc.add_row([iu + 2, 'Delete user'])
    print(ptc)
