from typing import Any, Dict, Optional

import httpx
from httpx import HTTPStatusError


class AuthException(Exception):
    pass


# async def async_request(
#         method: str,
#         url: str,
#         headers: Optional[Dict[str, str]] = None,
#         payload: Optional[Dict[str, Any]] = None,
#         return_type: str = 'json'
# ) -> Any:
#     if not url or not url.strip():
#         raise ValueError('URL non valida')
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.request(method, url, json=payload, headers=headers) as response:
#                 response.raise_for_status()
#                 if return_type == 'json':
#                     return await response.json()
#                 elif return_type == 'text':
#                     return await response.text()
#                 elif return_type == 'bytes':
#                     return await response.read()
#                 else:
#                     raise ValueError(f"Type not supported: {return_type}")
#     except ClientResponseError as e:
#         print(f"Error HTTP {e.status}: {e.message}")
#         raise
#     except Exception as ex:
#         print(f'Connection error: {ex}')
#         raise
#
#
# async def async_post(
#         url: str,
#         headers: Optional[Dict[str, str]] = None,
#         payload: Optional[Dict[str, Any]] = None
# ) -> Any:
#     return await async_request('POST', url, headers=headers, payload=payload, return_type='json')
#
#
# async def async_get(
#         url: str,
#         headers: Optional[Dict[str, str]] = None
# ) -> Any:
#     return await async_request('GET', url, headers=headers, return_type='json')
#
#
# async def async_raw_get(
#         url: str,
#         headers: Optional[Dict[str, str]] = None
# ) -> bytes:
#     return await async_request('GET', url, headers=headers, return_type='bytes')


def request(
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
        return_type: str = 'json'
) -> Any:
    if not url or not url.strip():
        raise ValueError('URL non valida')

    try:
        with httpx.Client() as client:
            response = client.request(method, url, json=payload, headers=headers)
            response.raise_for_status()
            if return_type == 'json':
                return response.json()
            elif return_type == 'text':
                return response.text
            elif return_type == 'bytes':
                return response.content
            else:
                raise ValueError(f"Tipo non supportato: {return_type}")
    except HTTPStatusError as e:
        print(f"Error HTTP {e.response.status_code}: {e.response.text}")
        raise
    except Exception as ex:
        print(f'Connection error: {ex}')
        raise


def post(
        url: str,
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None
) -> Any:
    return request('POST', url, headers=headers, payload=payload, return_type='json')


def get(
        url: str,
        headers: Optional[Dict[str, str]] = None
) -> Any:
    return request('GET', url, headers=headers, return_type='json')


def raw_get(
        url: str,
        headers: Optional[Dict[str, str]] = None
) -> bytes:
    return request('GET', url, headers=headers, return_type='bytes')
