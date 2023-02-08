import json
from typing import Dict, Optional

import aiohttp


class AuthException(Exception):
    pass


async def async_post(url: str, headers: Dict[str, str], payload: Dict[str, str]) -> Optional[dict]:
    if url is None or not url.strip():
        print('Url is invalid')
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, data=json.dumps(payload), headers=headers) as p:
                if p.status == 200:
                    return await p.json()
    except Exception as ex:
        print(f'Connection Error: {ex}')
    return None


async def async_get(url: str, headers: Dict[str, str]) -> []:
    if url is None or not url.strip():
        print('Url is invalid')
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers) as p:
                if p.status != 200:
                    raise AuthException(f'Something bad happened: {p.status}')
                else:
                    return await p.json()
    except Exception as ex:
        print(f'Connection Error: {ex}')


async def async_image_get(url: str, headers: Dict[str, str]) -> Optional[bytes]:
    if url is None or not url.strip():
        print('Url is invalid')
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers) as p:
                if p.status == 200:
                    return await p.read()
    except Exception as ex:
        print(f'Connection Error: {ex}')
