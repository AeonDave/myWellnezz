"""Shared fakes for tests: an in-memory keyring store."""

from keyring.errors import PasswordDeleteError


class FakeKeyring:
    """Minimal stand-in for the ``keyring`` module used by config.secrets."""

    def __init__(self):
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str):
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str):
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str):
        if (service, username) not in self.store:
            raise PasswordDeleteError(username)
        del self.store[(service, username)]
