import base64
import json
import uuid
from typing import List

import requests

from constants import schema, base_url
from util import fake_ua


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
            raise SystemError('Unauthorized')
        else:
            r = p.json()
            if r['token']:
                b64d = base64.b64decode(r['token'].split('.')[0][:-1]).decode('utf-8').split('|')[6]
                return r['token'], uuid.UUID(str(b64d))
            else:
                raise SystemError('Unauthorized')

    def refresh(self):
        self.token, self.user_id = self.login()


class Config:

    def __init__(self, **kwargs):
        self.choice = 0
        self.users: List[User] = [User(**us) for us in kwargs.get('users')]

    def set_user(self, c):
        c = abs(int(c.strip()))
        if c < len(self.users):
            self.choice = c

    def get_user(self) -> User:
        return self.users[self.choice]
