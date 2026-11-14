"""Smoke test: the whole package imports without side effects."""

def test_package_imports():
    import mywellnezz.api.auth
    import mywellnezz.api.client
    import mywellnezz.api.dto
    import mywellnezz.api.endpoints
    import mywellnezz.api.events
    import mywellnezz.api.facilities
    import mywellnezz.app.constants
    import mywellnezz.app.keep_awake
    import mywellnezz.app.session
    import mywellnezz.booking.engine
    import mywellnezz.config.migration
    import mywellnezz.config.models
    import mywellnezz.config.paths
    import mywellnezz.config.secrets
    import mywellnezz.config.storage
    import mywellnezz.main
    import mywellnezz.ui.app
    import mywellnezz.ui.ascii_art

    assert mywellnezz.app.constants.version
