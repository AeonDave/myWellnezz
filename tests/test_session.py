"""Application resource ownership: close jobs and HTTP client even on UI failure."""

from unittest.mock import AsyncMock

import pytest

from mywellnezz.app import session
from mywellnezz.config.models import AppConfig


@pytest.mark.parametrize('crash', [False, True])
async def test_run_app_always_stops_engine_and_closes_client(monkeypatch, crash):
    order = []

    class Engine:
        async def shutdown(self):
            order.append('shutdown')

    class App:
        def __init__(self, config, engine):
            pass

        async def run_async(self):
            order.append('ui')
            if crash:
                raise RuntimeError('UI failed')

    async def close():
        order.append('close')

    monkeypatch.setattr(session, '_load_or_migrate', lambda: AppConfig())
    monkeypatch.setattr(session, 'MyWellnezz', Engine)
    monkeypatch.setattr(session, 'MyWellnezzApp', App)
    monkeypatch.setattr(session, 'close_client', close)
    if crash:
        with pytest.raises(RuntimeError, match='UI failed'):
            await session.run_app()
    else:
        await session.run_app()
    assert order == ['ui', 'shutdown', 'close']


async def test_run_app_closes_client_if_engine_shutdown_fails(monkeypatch):
    class Engine:
        shutdown = AsyncMock(side_effect=RuntimeError('shutdown failed'))

    class App:
        def __init__(self, config, engine):
            pass

        run_async = AsyncMock()

    close = AsyncMock()
    monkeypatch.setattr(session, '_load_or_migrate', lambda: AppConfig())
    monkeypatch.setattr(session, 'MyWellnezz', Engine)
    monkeypatch.setattr(session, 'MyWellnezzApp', App)
    monkeypatch.setattr(session, 'close_client', close)
    with pytest.raises(RuntimeError, match='shutdown failed'):
        await session.run_app()
    close.assert_awaited_once()
