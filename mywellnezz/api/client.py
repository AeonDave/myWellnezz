"""Shared async HTTP client for the MyWellness API.

One ``httpx.AsyncClient`` for the whole app, with timeouts (the v1 client had
none and could hang forever) and a randomized Android user-agent per request.
"""

import random
from typing import Any

import httpx

TIMEOUT = httpx.Timeout(15.0, connect=10.0)

_CLIENT: httpx.AsyncClient | None = None

_USER_AGENTS = [
    'Dalvik/2.1.0 (Linux; U; Android 8.0.0; FIG-LX1 Build/HUAWEIFIG-LX1)',
    'Dalvik/2.1.0 (Linux; U; Android 8.0.0; SM-G930VL Build/R16NW)',
    'Dalvik/2.1.0 (Linux; U; Android 8.0.0; SM-G950F Build/R16NW)',
    'Dalvik/2.1.0 (Linux; U; Android 8.1.0; SM-N960N Build/M1AJQ)',
    'Dalvik/2.1.0 (Linux; U; Android 12; T676J Build/SP1A.210812.016)',
    'Dalvik/2.1.0 (Linux; U; Android 12; moto g71 5G Build/S2RUBS32.51-15-9-3)',
    'Dalvik/2.1.0 (Linux; U; Android 11; S7-SH Build/S1022)',
    'Dalvik/2.1.0 (Linux; U; Android 10; Box Q Build/QTT8.201201.002)',
    'Dalvik/2.1.0 (Linux; U; Android 13; XQ-CT72 Build/64.1.A.0.860)',
    'Dalvik/2.1.0 (Linux; U; Android 13; Pixel 7 Pro Build/T2B3.230109.002)',
    'Dalvik/2.1.0 (Linux; U; Android 13; SM-S918B Build/TP1A.220624.014)',
    'Dalvik/2.1.0 (Linux; U; Android 12; FP4 Build/SKQ1.220201.001)',
    'Dalvik/2.1.0 (Linux; U; Android 11; moto g play (2021) Build/RZAS31.Q2-146-14-6-9)',
    'Dalvik/2.1.0 (Linux; U; Android 13; SM-P610 Build/TP1A.220624.014)',
    'Dalvik/2.1.0 (Linux; U; Android 12; Tab 7 Pro Build/SP1A.210812.016)',
    'Dalvik/2.1.0 (Linux; U; Android 13; SM-A515W Build/TP1A.220624.014)',
    'Dalvik/2.1.0 (Linux; U; Android 11; Luck L130 Build/RP1A.201005.001)',
    'Dalvik/2.1.0 (Linux; U; Android 10; moto e(7) power Build/QOLS30.288-52-18)',
    'Dalvik/2.1.0 (Linux; U; Android 9; KFTRWI Build/PS7327.3326N)',
    'Dalvik/2.1.0 (Linux; U; Android 13; LE2121 Build/TP1A.220905.001)',
]


class ApiError(Exception):
    """Network or transport failure (timeout, DNS, HTTP status...)."""


class ApiAuthError(ApiError):
    """The server explicitly rejected the credentials or the session."""


def _headers() -> dict[str, str]:
    return {
        'User-Agent': random.choice(_USER_AGENTS),
        'Content-Type': 'application/json; charset=utf-8',
        'X-MWAPPS-CLIENT': 'MywellnessAppAndroid40',
    }


async def get_client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
    return _CLIENT


async def close_client() -> None:
    global _CLIENT
    if _CLIENT is not None and not _CLIENT.is_closed:
        await _CLIENT.aclose()
    _CLIENT = None


async def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON and return the decoded body. Raises ``ApiError`` on any transport failure."""
    if not url or not url.strip():
        raise ValueError('Invalid URL')
    client = await get_client()
    try:
        response = await client.post(url, json=payload, headers=_headers())
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as ex:
        raise ApiError(f'HTTP {ex.response.status_code}: {ex.response.text[:200]}') from ex
    except httpx.HTTPError as ex:
        raise ApiError(f'Connection error: {ex}') from ex
    except ValueError as ex:
        # Includes json.JSONDecodeError: proxies and captive portals answer
        # with HTML — it must surface as a transport error, never escape.
        raise ApiError(f'Invalid server response: {ex}') from ex
