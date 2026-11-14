"""Application constants: metadata, branding and MyWellness API endpoints.

The package metadata is available when installed (pip/poetry or the PyInstaller
build with ``--copy-metadata``); the fallback keeps the CLI working from source.
"""

try:
    from importlib.metadata import metadata
    from importlib.metadata import version as _pkg_version

    _meta = metadata('mywellnezz')
    author = _meta.get('Author') or 'AeonDave'
    version = _pkg_version('mywellnezz')
except Exception:  # noqa: BLE001 — defensive: log and keep going
    # Keep in sync with pyproject.toml when bumping.
    author = 'AeonDave'
    version = '2.2.0'

name = 'myWellnezz'
app_id = 'EC1D38D7-D359-48D0-A60C-D8C0B8FB9DF9'

schema = 'https://'
base_url = 'mywellness.com'

logo = '''                   M""MMM""MMM""M          dP dP                                     
                   M  MMM  MMM  M          88 88                                     
88d8b.d8b. dP    dP M  MMP  MMP  M .d8888b. 88 88 88d888b. .d8888b. d888888b d888888b 
88\'`88\'`88 88    88 M  MM\'  MM\' .M 88ooood8 88 88 88\'  `88 88ooood8    .d8P\'    .d8P\' 
88  88  88 88.  .88 M  `\' . \'\' .MM 88.  ... 88 88 88    88 88.  ...  .Y8P     .Y8P    
dP  dP  dP `8888P88 M    .d  .dMMM `88888P\' dP dP dP    dP `88888P\' d888888P d888888P 
                .88 MMMMMMMMMMMMMM                                                    
            d8888P                                                                   
'''
