import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional

import pwinput
from dateutil import parser, tz

from app.constants import schema, base_url, app_id
from modules.http_calls import async_post
from modules.math_util import read_obfuscation, write_obfuscation
from modules.useragent import fake_ua_android

email_re = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'


class UserContext:
    def __init__(self, **kwargs):
        from models.facility import Facility
        self.id: str = kwargs.get('id')
        self.usr: str = kwargs.get('accountUsername') or kwargs.get('usr')
        self.pwd: str = kwargs.get('pwd')
        self.first_name: str = kwargs.get('firstName') or kwargs.get('first_name')
        self.last_name: str = kwargs.get('lastName') or kwargs.get('last_name')
        self.inclusive_gender: str = kwargs.get('inclusiveGender') or kwargs.get('inclusive_gender')
        self.gender: str = kwargs.get('gender')
        self.address1: str = kwargs.get('address1')
        self.zip_code: str = kwargs.get('zipCode') or kwargs.get('zip_code')
        self.city: str = kwargs.get('city')
        self.state_province: str = kwargs.get('stateProvince') or kwargs.get('state_province')
        self.email: str = kwargs.get('email')
        self.phone_number: str = kwargs.get('phoneNumber') or kwargs.get('phone_number')
        self.mobile_phoneNumber: str = kwargs.get('mobilePhoneNumber') or kwargs.get('mobile_phoneNumber')
        self.display_weight: str = kwargs.get('displayWeight') or kwargs.get('display_weight')
        self.display_birth_date: str = kwargs.get('displayBirthDate') or kwargs.get('display_birth_date')
        self.display_height: str = kwargs.get('displayHeight') or kwargs.get('display_height')
        self.age: int = kwargs.get('age')
        self.picture_url: str = kwargs.get('pictureUrl') or kwargs.get('picture_url')
        if kwargs.get('modifiedOn'):
            self.modified_on: datetime = parser.parse(kwargs.get('modifiedOn')).replace(tzinfo=tz.gettz('UTC'))
        elif kwargs.get('modified_on'):
            self.modified_on: datetime = datetime.fromisoformat(kwargs.get('modified_on'))
        else:
            self.modified_on: None = None
        self.token: str = kwargs.get('token')
        self.token_expire: datetime = (
            datetime.fromisoformat(kwargs.get('token_expire'))
            if kwargs.get('token_expire')
            else None
        )
        self.token_gen: datetime = (
            datetime.fromisoformat(kwargs.get('token_gen'))
            if kwargs.get('token_gen')
            else datetime.now()
        )
        self.facilities: List[Facility] = []

        # self.credential_id: str = kwargs.get('credentialId') or kwargs.get('credential_id')
        # self.nick_name: str = kwargs.get('nickName')
        # self.birth_date: str = kwargs.get('birthDate')
        # self.country_id: int = kwargs.get('countryId')
        # self.language_id: int = kwargs.get('languageId')
        # self.time_zone_id: int = kwargs.get('timeZoneId')
        # self.measurement_system: str = kwargs.get('measurementSystem')
        # self.expenditure_unit_of_measure: str = kwargs.get('expenditureUnitOfMeasure')
        # self.default_culture: str = kwargs.get('defaultCulture')
        # self.time_zone_windows_id: str = kwargs.get('timeZoneWindowsId')
        # self.weight: float = kwargs.get('weight')
        # self.height: float = kwargs.get('height')
        # self.thumb_picture_url: str = kwargs.get('thumbPictureUrl')
        # self.user_culture_info: str = kwargs.get('userCultureInfo')
        # self.is_email_valid: bool = kwargs.get('isEmailValid')
        # self.created_from_app: str = kwargs.get('createdFromApp')
        # self.can_be_multiple_user: bool = kwargs.get('canBeMultipleUser')
        # self.created_on: str = kwargs.get('createdOn') or kwargs.get('created_on')
        # self.cloud_creation_date: str = kwargs.get('cloudCreationDate')
        # self.has_tgs_data: bool = kwargs.get('hasTgsData')

    def set_token(self, token: str, token_expire: int):
        self.token = token.strip()
        self.token_expire = datetime.now() + timedelta(seconds=token_expire)

    async def login_app(self):
        url = f'{schema}services.{base_url}/Application/{app_id}/Login'
        headers = {
            "User-Agent": fake_ua_android(),
            "Content-Type": "application/json; charset=utf-8",
            "X-MWAPPS-CLIENT": "MywellnessAppAndroid40"
        }
        pwd = read_obfuscation(self.usr, self.pwd)
        payload = {
            "domain": "com.mywellness",
            "keepMeLoggedIn": True,
            "username": f"{self.usr}",
            "password": f"{pwd}"
        }
        try:
            response = await async_post(url, headers, payload)
            if response and 'errors' in response:
                print(f'Error: {response["errors"][0]["errorMessage"]}')
                return False, None
            if response and ('data' and 'token') in response:
                response['data']['userContext']['facilities'] = response['data']['facilities']
                user = UserContext(**response['data']['userContext'])
                user.set_token(response['token'], response['expireIn'])
                user.pwd = self.pwd
                return True, user
        except Exception as ex:
            print(f'Connection Error: {ex}')
            await asyncio.sleep(30)
        return False, None

    async def refresh(self):
        return await self.login_app()


def _get_usr() -> Optional[str]:
    usr = input('Insert username:\n').replace(" ", "").strip()
    if re.fullmatch(email_re, usr):
        return usr
    print('Invalid email')
    return None


def _get_pwd() -> Optional[str]:
    return pwinput.pwinput(prompt='Insert password: ', mask='*')


async def create_user() -> UserContext:
    while True:
        user = UserContext()
        while not user.usr:
            user.usr = _get_usr()
        user.pwd = write_obfuscation(user.usr, _get_pwd())
        logged, usr = await user.login_app()
        if logged:
            usr.pwd = user.pwd
            return usr
        print('Username or password are invalid')
