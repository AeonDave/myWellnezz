"""Tests for config persistence: roundtrip, backup and corrupt-file handling."""

import json

from mywellnezz.api.dto import Facility
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.config.storage import load_config, remove_user, save_config


def _sample_config() -> AppConfig:
    facility = Facility(id='g1', name='Gym', address='Via Roma 1', logo_url='http://logo')
    profile = UserProfile(
        id='u1',
        usr='mario@example.com',
        first_name='Mario',
        facilities=[facility],
    )
    return AppConfig(user_choice=0, facility_choice=0, users=[profile])


def test_roundtrip(tmp_path):
    path = tmp_path / 'config.json'
    config = _sample_config()
    save_config(config, path)
    loaded = load_config(path)
    assert loaded.user_choice == 0
    assert loaded.facility_choice == 0
    assert loaded.users[0].usr == 'mario@example.com'
    assert loaded.users[0].facilities[0].name == 'Gym'
    assert loaded.users[0].facilities[0].logo_url == 'http://logo'


def test_save_keeps_backup_and_is_atomic(tmp_path):
    path = tmp_path / 'config.json'
    save_config(_sample_config(), path)
    first = path.read_text(encoding='utf-8')
    other = AppConfig(users=[UserProfile(usr='second@example.com')])
    save_config(other, path)
    backup = path.with_suffix('.json.bak')
    assert backup.exists()
    assert json.loads(backup.read_text(encoding='utf-8')) == json.loads(first)
    assert not path.with_suffix('.json.tmp').exists()


def test_missing_file_returns_fresh_config(tmp_path):
    loaded = load_config(tmp_path / 'nope.json')
    assert loaded.users == []
    assert loaded.auto_book is True


def test_corrupt_file_is_quarantined_not_deleted(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text('{not json', encoding='utf-8')
    loaded = load_config(path)
    assert loaded.users == []
    quarantined = list(tmp_path.glob('config.json.corrupt-*'))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding='utf-8') == '{not json'


def test_remove_user_deletes_and_resets_selection(tmp_path):
    path = tmp_path / 'config.json'
    config = _sample_config()
    config.users.append(UserProfile(usr='luigi@example.com'))
    save_config(config, path)
    updated = remove_user(load_config(path), 0, path)
    assert [u.usr for u in updated.users] == ['luigi@example.com']
    assert updated.user_choice is None
    assert updated.facility_choice is None
