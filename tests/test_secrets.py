"""Tests for the OS-vault wrapper (with a fake keyring backend)."""

import pytest

from mywellnezz.config import secrets
from tests.fakes import FakeKeyring


@pytest.fixture()
def vault(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(secrets, 'keyring', fake)
    return fake


def test_password_roundtrip(vault):
    secrets.save_password('a@b.c', 'secret')
    assert secrets.get_password('a@b.c') == 'secret'


def test_token_lives_under_its_own_account(vault):
    secrets.save_password('a@b.c', 'secret')
    secrets.save_token('a@b.c', 'tok123')
    assert secrets.get_token('a@b.c') == 'tok123'
    assert secrets.get_password('a@b.c') == 'secret'
    assert ('myWellnezz', 'a@b.c#token') in vault.store


def test_delete_secrets_is_idempotent(vault):
    secrets.save_password('a@b.c', 'secret')
    secrets.save_token('a@b.c', 'tok')
    secrets.delete_secrets('a@b.c')
    assert secrets.get_password('a@b.c') is None
    assert secrets.get_token('a@b.c') is None
    secrets.delete_secrets('a@b.c')  # no raise
    secrets.delete_secrets(None)  # no raise


def test_vault_failure_raises_clear_error(monkeypatch):
    from keyring.errors import KeyringError

    class Broken:
        def get_password(self, service, username):
            raise KeyringError('no backend')

    monkeypatch.setattr(secrets, 'keyring', Broken())
    with pytest.raises(secrets.SecretStoreError):
        secrets.get_password('a@b.c')
