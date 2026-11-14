"""Secret storage on top of the OS credential vault (``keyring``).

On Windows this is Credential Manager (DPAPI-backed); on macOS Keychain and on
Linux the Secret Service. Passwords and session tokens never touch the config
file: nothing is encrypted with keys derived from hardware that can change
between runs — the OS ties them to the current user account.
"""

import keyring
from keyring.errors import KeyringError

SERVICE = 'myWellnezz'


class SecretStoreError(RuntimeError):
    """The OS credential vault is unavailable or refused the operation."""


def _token_account(usr: str) -> str:
    return f'{usr}#token'


def get_password(usr: str) -> str | None:
    try:
        return keyring.get_password(SERVICE, usr)
    except KeyringError as ex:
        raise SecretStoreError(f'Cannot read the password vault: {ex}') from ex


def save_password(usr: str, password: str) -> None:
    try:
        keyring.set_password(SERVICE, usr, password)
    except KeyringError as ex:
        raise SecretStoreError(f'Cannot write to the password vault: {ex}') from ex


def get_token(usr: str) -> str | None:
    try:
        return keyring.get_password(SERVICE, _token_account(usr))
    except KeyringError as ex:
        raise SecretStoreError(f'Cannot read the password vault: {ex}') from ex


def save_token(usr: str, token: str) -> None:
    try:
        keyring.set_password(SERVICE, _token_account(usr), token)
    except KeyringError as ex:
        raise SecretStoreError(f'Cannot write to the password vault: {ex}') from ex


def delete_secrets(usr: str | None) -> None:
    """Delete password and token; missing entries are ignored."""
    if not usr:
        return
    for account in (usr, _token_account(usr)):
        try:
            keyring.delete_password(SERVICE, account)
        except KeyringError:
            pass
