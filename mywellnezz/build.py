"""PyInstaller packaging, reachable with ``poetry run build``.

PyInstaller is a dev dependency: it is imported lazily so the app itself never
requires it.
"""

from pathlib import Path

from mywellnezz.app.constants import name


def install() -> None:
    import PyInstaller.__main__

    base_dir = Path(__file__).resolve().parents[1]
    build_dir = base_dir / 'build' / 'pyinstaller'
    # Only PyInstaller's own work files and the named EXE are replaced. Other
    # artifacts in build/ and dist/ belong to the user and must survive a rebuild.
    PyInstaller.__main__.run([
        str(base_dir / 'mywellnezz' / 'main.py'),
        '--noconfirm',
        f'--name={name}',
        '--onefile',
        '--console',
        f'--icon={base_dir / "app.ico"}',
        '--clean',
        '--optimize=1',
        '--noupx',
        f'--specpath={build_dir}',
        f'--workpath={build_dir / "work"}',
        f'--distpath={base_dir / "dist"}',
        # Absolute imports, lazy widget/backend imports and package resources all
        # need to remain available in the frozen application.
        f'--paths={base_dir}',
        '--copy-metadata=mywellnezz',
        '--copy-metadata=keyring',
        '--collect-all=textual',
        '--collect-all=keyring',
    ])
