"""One-shot import of the legacy v1 ``conf.json``.

The v1 config was obfuscated with XOR + ROT13 keyed by the machine MAC address
(``uuid.getnode()``). That key is unstable (MAC randomization, VPN adapters,
or a random node when no MAC is found), which is why v1 kept losing the
configuration. This module makes a single best-effort attempt with the
current node value; the legacy file is never deleted — on success it is
renamed ``conf.json.migrated.bak``, on failure it is left untouched and the
user re-enters credentials once, this time into the OS vault.
"""

import base64
import codecs
import json
import sys
import uuid
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path

from mywellnezz.config import secrets
from mywellnezz.config.models import AppConfig
from mywellnezz.config.storage import save_config

LEGACY_FILENAME = 'conf.json'


class _LegacyCrypto:
    """Re-implementation of the v1 ``modules/math_util.py`` obfuscation."""

    @staticmethod
    def _xor(data: bytes, key: bytes) -> bytes:
        return bytes(c ^ key[i % len(key)] for i, c in enumerate(data))

    @classmethod
    def _key(cls, seed: str) -> bytes:
        node_digest = sha256(uuid.UUID(int=uuid.getnode()).bytes).digest()
        mixed = cls._xor(codecs.encode(seed, 'rot13').encode('utf-8'), node_digest)
        return sha256(mixed).digest()

    @classmethod
    def decrypt(cls, key: str, payload: str) -> str:
        return cls._xor(base64.b64decode(payload), cls._key(key)).decode('utf-8')


def _legacy_locations() -> Iterator[Path]:
    seen: set[Path] = set()
    candidates = [
        Path.cwd() / LEGACY_FILENAME,
        Path(sys.executable).parent / LEGACY_FILENAME if getattr(sys, 'frozen', False) else None,
        Path(__file__).resolve().parents[2] / LEGACY_FILENAME,
    ]
    for candidate in candidates:
        if candidate is not None and candidate in seen:
            continue
        if candidate is not None:
            seen.add(candidate)
            if candidate.exists():
                yield candidate


def try_migrate(save_path: Path | None = None) -> AppConfig | None:
    """Import the legacy config if readable; returns the imported config or ``None``.

    On success the passwords and tokens move into the OS vault and the legacy
    file is renamed; on failure nothing is modified and the user is asked to
    re-enter credentials. ``save_path`` overrides the destination config file
    (tests pass a temp path).
    """
    for legacy_file in _legacy_locations():
        config = _import_file(legacy_file, save_path)
        if config is not None:
            return config
    return None


def _import_file(legacy_file: Path, save_path: Path | None = None) -> AppConfig | None:
    try:
        raw = legacy_file.read_text(encoding='utf-8')
        data = json.loads(_LegacyCrypto.decrypt(str(uuid.getnode()), raw))
        config = AppConfig.from_dict(data)
    except Exception:  # noqa: BLE001 — defensive: log and keep going
        _report_failure(legacy_file)
        return None
    if not config.users:
        _report_failure(legacy_file)
        return None
    for user in config.users:
        legacy_user = next((u for u in data.get('users', []) if u.get('usr') == user.usr), {})
        if user.usr:
            token = legacy_user.get('token')
            if token:
                secrets.save_token(user.usr, token)
            encrypted_pwd = legacy_user.get('pwd')
            if encrypted_pwd:
                try:
                    secrets.save_password(user.usr, _LegacyCrypto.decrypt(user.usr, encrypted_pwd))
                except Exception:  # noqa: BLE001 — defensive: log and keep going
                    print(f'Could not recover the password for {user.usr}: log in again once.')
    save_config(config, save_path)
    try:
        legacy_file.rename(legacy_file.with_name(f'{LEGACY_FILENAME}.migrated.bak'))
    except OSError:
        pass  # the import already succeeded; the rename is only cosmetic
    print(f'Migrated {len(config.users)} user(s) from {legacy_file.name} to the new config.')
    return config


def _report_failure(legacy_file: Path) -> None:
    print(
        f'Found a legacy {legacy_file} but it cannot be decrypted anymore '
        f'(the old MAC-based key changed). Re-enter your credentials once; '
        f'they will be stored in the OS credential vault and never lost again. '
        f'The old file is kept as {legacy_file}.'
    )
