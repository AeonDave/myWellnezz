"""App bootstrap: config load/migration, engine wiring and the Textual entry point."""

from mywellnezz.api.client import close_client
from mywellnezz.api.dto import User
from mywellnezz.app import services
from mywellnezz.booking.engine import MyWellnezz, Relogin
from mywellnezz.config import paths, secrets
from mywellnezz.config.migration import try_migrate
from mywellnezz.config.models import AppConfig, UserProfile
from mywellnezz.config.storage import load_config
from mywellnezz.ui.app import MyWellnezzApp


def _load_or_migrate() -> AppConfig:
    if paths.config_file().exists():
        return load_config()
    migrated = try_migrate()
    if migrated is not None:
        return migrated
    return AppConfig()


def _make_relogin(config: AppConfig) -> Relogin:
    async def relogin(user: User) -> User | None:
        try:
            fresh = await services.login_profile(UserProfile(usr=user.usr))
        except (services.CredentialsRejected, services.NetworkProblem):
            return None
        user.token = fresh.token
        user.token_expire = fresh.token_expire
        if user.usr and fresh.token:
            secrets.save_token(user.usr, fresh.token)
        return fresh

    return relogin


async def run_app() -> None:
    engine = MyWellnezz()
    try:
        config = _load_or_migrate()
        engine.relogin = _make_relogin(config)
        app = MyWellnezzApp(config, engine)
        await app.run_async()
    finally:
        try:
            await engine.shutdown()
        finally:
            await close_client()
