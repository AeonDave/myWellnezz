"""Freeze-command contract without running PyInstaller or deleting user artifacts."""

from pathlib import Path
from unittest.mock import Mock

import PyInstaller.__main__

from mywellnezz import build


def _capture_build(monkeypatch, tmp_path):
    monkeypatch.setattr(build, '__file__', str(tmp_path / 'mywellnezz' / 'build.py'))
    run = Mock()
    monkeypatch.setattr(PyInstaller.__main__, 'run', run)
    return run


def test_build_preserves_other_build_and_dist_artifacts(monkeypatch, tmp_path):
    run = _capture_build(monkeypatch, tmp_path)
    sentinels = [tmp_path / 'build' / 'keep.txt', tmp_path / 'dist' / 'keep.txt']
    for file in sentinels:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('user artifact', encoding='utf-8')
    build.install()
    assert all(file.read_text(encoding='utf-8') == 'user artifact' for file in sentinels)
    run.assert_called_once()


def test_build_includes_dynamic_modules_and_explicit_absolute_output_paths(monkeypatch, tmp_path):
    run = _capture_build(monkeypatch, tmp_path)
    build.install()
    args = run.call_args.args[0]
    assert str(tmp_path / 'mywellnezz' / 'main.py') == args[0]
    for flag in ('--onefile', '--console', '--collect-all=textual', '--collect-all=keyring',
                 '--copy-metadata=mywellnezz', '--copy-metadata=keyring'):
        assert flag in args
    for name, suffix in (
        ('icon', Path('app.ico')),
        ('distpath', Path('dist')),
        ('workpath', Path('build') / 'pyinstaller' / 'work'),
        ('specpath', Path('build') / 'pyinstaller'),
    ):
        assert f'--{name}={tmp_path / suffix}' in args
