import asyncio
from typing import List, Optional

from my_wellnezz.constants import schema, base_url
from my_wellnezz.models.usercontext import UserContext
from my_wellnezz.modules.http_calls import async_post
from my_wellnezz.modules.useragent import fake_ua_android


class Facility:
    def __init__(self, **kwargs):
        self.id: str = kwargs.get('id')
        self.url: str = kwargs.get('url')
        self.name: str = kwargs.get('name')
        self.address: str = kwargs.get('address')
        self.website: str = kwargs.get('website')
        self.phone_number: str = kwargs.get('phoneNumber') or kwargs.get('phone_number')
        self.logo_url: str = kwargs.get('logoUrl') or kwargs.get('logo_url')
        # self.languageId: int = kwargs.get('languageId')
        # self.is_chain: bool = kwargs.get('isChain')
        # self.customerLogicalId: int = kwargs.get('customerLogicalId')
        # self.doNotJoinUsers: bool = kwargs.get('doNotJoinUsers')
        # self.virtual: bool = kwargs.get('virtual')
        # self.has_wellness_system: bool = kwargs.get('hasWellnessSystem')
        # self.is_my_trainer: bool = kwargs.get('isMyTrainer')
        # self.is_demo: bool = kwargs.get('isDemo')


async def my_facilities(user: UserContext) -> Optional[List[Facility]]:
    url = f'{schema}services.{base_url}/Core/User/{user.id}/MyFacilities'
    headers = {
        "User-Agent": fake_ua_android(),
        "Content-Type": "application/json; charset=utf-8",
        "X-MWAPPS-CLIENT": "MywellnessAppAndroid40"
    }
    payload = {
        "token": f"{user.token}"
    }
    try:
        response = await async_post(url, headers, payload)
        if response and 'errors' in response:
            print(f'Error: {response["errors"][0]["errorMessage"]}')
            return None
        if response and 'data' in response:
            return [] if response['data']['facilities'] is None else [Facility(**f) for f in
                                                                      response['data']['facilities']]
    except Exception as ex:
        print(f'Connection Error: {ex}')
        await asyncio.sleep(30)
    return None
