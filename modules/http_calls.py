import json

import aiohttp


class AuthException(Exception):
    pass


async def async_post(url: str, headers: dict[str, str], payload: dict[str, str]) -> []:
    if url is None or not url.strip():
        print(f'Url is invalid')
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, data=json.dumps(payload), headers=headers) as p:
                if p.status == 200:
                    return await p.json()
    except Exception as ex:
        print(f'Connection Error: {ex}')
    return None


async def async_get(url: str, headers: dict[str, str]) -> []:
    if url is None or not url.strip():
        print(f'Url is invalid')
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


async def async_image_get(url: str, headers: dict[str, str]) -> bytes | None:
    if url is None or not url.strip():
        print(f'Url is invalid')
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers) as p:
                if p.status == 200:
                    return await p.read()
    except Exception as ex:
        print(f'Connection Error: {ex}')
