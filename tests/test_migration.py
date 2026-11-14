"""Tests for the v1 -> v2 config migration."""

import base64
import json
import uuid

import pytest

from mywellnezz.config import migration, secrets
from tests.fakes import FakeKeyring

NODE = 0x00155D8C2B10  # a plausible stable MAC


def _legacy_encrypt(key: str, plaintext: str) -> str:
    data = plaintext.encode('utf-8')
    xor_key = migration._LegacyCrypto._key(key)
    return base64.b64encode(
        bytes(c ^ xor_key[i % len(xor_key)] for i, c in enumerate(data))
    ).decode('utf-8')


@pytest.fixture()
def legacy_env(tmp_path, monkeypatch):
    """A legacy conf.json in an isolated folder with a deterministic MAC."""
    monkeypatch.setattr(uuid, 'getnode', lambda: NODE)
    monkeypatch.chdir(tmp_path)
    vault = FakeKeyring()
    monkeypatch.setattr(secrets, 'keyring', vault)
    return tmp_path, vault


def _write_legacy_conf(path, *, with_pwd=True):
    payload = {
        'user_choice': 0,
        'facility_choice': 0,
        'auto_book': True,
        'users': [
            {
                'id': 'u1',
                'usr': 'mario@example.com',
                'pwd': _legacy_encrypt('mario@example.com', 'hunter2') if with_pwd else None,
                'first_name': 'Mario',
                'mobile_phoneNumber': '+39 333',
                'token': 'tok-abc',
                'token_expire': '2027-01-01T00:00:00',
                'facilities': [{'id': 'g1', 'name': 'Gym', 'address': 'Via Roma 1'}],
            }
        ],
    }
    blob = json.dumps(payload)
    path.write_text(_legacy_encrypt(str(NODE), blob), encoding='utf-8')
    return payload


def test_migration_imports_users_and_secrets(legacy_env, monkeypatch):
    tmp_path, vault = legacy_env
    _write_legacy_conf(tmp_path / 'conf.json')
    monkeypatch.setattr(migration, '_legacy_locations', lambda: iter([tmp_path / 'conf.json']))
    config = migration.try_migrate(save_path=tmp_path / 'config.json')
    assert config is not None
    assert (tmp_path / 'config.json').exists()
    assert [u.usr for u in config.users] == ['mario@example.com']
    assert config.users[0].mobile_phone_number == '+39 333'
    assert config.users[0].token_expire is not None
    assert vault.store[('myWellnezz', 'mario@example.com')] == 'hunter2'
    assert vault.store[('myWellnezz', 'mario@example.com#token')] == 'tok-abc'
    # The legacy file is preserved under a new name.
    assert (tmp_path / 'conf.json.migrated.bak').exists()
    assert not (tmp_path / 'conf.json').exists()


def test_migration_failure_keeps_file(legacy_env, monkeypatch, capsys):
    tmp_path, _ = legacy_env
    (tmp_path / 'conf.json').write_text('garbage-not-base64!!', encoding='utf-8')
    monkeypatch.setattr(migration, '_legacy_locations', lambda: iter([tmp_path / 'conf.json']))
    config = migration.try_migrate()
    assert config is None
    assert (tmp_path / 'conf.json').exists()
    assert 'cannot be decrypted' in capsys.readouterr().out


def test_migration_skipped_when_no_legacy_file(tmp_path, monkeypatch):
    monkeypatch.setattr(migration, '_legacy_locations', lambda: iter([]))
    assert migration.try_migrate() is None
