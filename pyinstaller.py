import os
import shutil
from pathlib import Path

import PyInstaller.__main__

main_file = 'main.py'
entry_d = os.path.join(Path(__file__).parent.absolute(), 'mywellnezz')
entry = os.path.join(entry_d, main_file)
build_d = os.path.join(Path(__file__).parent.absolute(), 'build')
# build = os.path.join(build_d, main_file)
# build_m_d = os.path.join(Path(__file__).parent.absolute(), 'build_m')
# build_m = os.path.join(build_m_d, main_file)
ico = '../app.ico'


# def flatten(src, out):
#     directory = os.path.dirname(out)
#     os.makedirs(directory, exist_ok=True)
#     s = stickytape.script(src)
#     with open(out, 'w') as f:
#         f.write(s)
#
#
# def minify(src_dir, out_dir):
#     os.makedirs(out_dir, exist_ok=True)
#     python_project_minify.directory(src_dir, out_dir)


def install(entry_point=entry):
    PyInstaller.__main__.run([
        entry_point,
        '--noconfirm',
        '--name=myWellnezz',
        '--onefile',
        f'--icon={ico}',
        '--clean',
        '--optimize=1',
        '--noupx',
        '--specpath=build'
    ])


if __name__ == '__main__':
    # minify(entry_d, build_m_d)
    # flatten(build_m, build)
    # shutil.rmtree(build_m_d)
    install(entry)
    shutil.rmtree('build')
