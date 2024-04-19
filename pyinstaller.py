import os
from pathlib import Path

import PyInstaller.__main__

main = os.path.join(Path(__file__).parent.absolute(), 'mywellnezz')
entry = os.path.join(main, 'main.py')
ico = 'app.ico'


def install():
    PyInstaller.__main__.run([
        entry,
        '--noconfirm',
        '--name=myWellnezz',
        '--onefile',
        f'--icon={ico}',
        '--clean',
        '--optimize=1',
        '--noupx'
    ])
