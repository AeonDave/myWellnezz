"""Load and save the application configuration.

Never deletes user data: on a corrupt file the original is renamed with a
timestamp and the app starts fresh; every save keeps a ``.bak`` of the
previous version and is atomic (temp file + rename).
"""

import json
import os
from datetime import datetime
from pathlib import Path

from mywellnezz.config import paths, secrets
from mywellnezz.config.models import AppConfig


def load_config(path: Path | None = None) -> AppConfig:
    file = path or paths.config_file()
    if not file.exists():
        return AppConfig()
    try:
        data = json.loads(file.read_text(encoding='utf-8'))
        return AppConfig.from_dict(data)
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as ex:
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        quarantine = file.with_name(f'{file.name}.corrupt-{stamp}')
        try:
            file.rename(quarantine)
            print(f'Config unreadable ({ex}); kept as {quarantine.name}, starting fresh.')
        except OSError:
            print(f'Config unreadable ({ex}); starting fresh.')
        return AppConfig()


def save_config(config: AppConfig, path: Path | None = None) -> None:
    file = path or paths.config_file()
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix('.json.tmp')
    backup = file.with_suffix('.json.bak')
    tmp.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding='utf-8')
    if file.exists():
        os.replace(file, backup)
    os.replace(tmp, file)


def add_user(config: AppConfig, profile, path: Path | None = None) -> AppConfig:
    """Append a user profile, persist and return the updated config."""
    config.users.append(profile)
    config.user_choice = len(config.users) - 1
    save_config(config, path)
    return config


def remove_user(config: AppConfig, index: int, path: Path | None = None) -> AppConfig:
    """Remove the user at ``index`` (and their vault entries), persist and return the config."""
    if 0 <= index < len(config.users):
        secrets.delete_secrets(config.users[index].usr)
        config.users.pop(index)
        config.user_choice = None
        config.facility_choice = None
        save_config(config, path)
    return config


def replace_user(config: AppConfig, index: int, profile, path: Path | None = None) -> AppConfig:
    """Replace the profile at ``index`` with fresh data from the API, persist and return."""
    if 0 <= index < len(config.users):
        config.users[index] = profile
        save_config(config, path)
    return config
