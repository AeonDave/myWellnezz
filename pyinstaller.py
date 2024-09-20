import errno
import shutil
from pathlib import Path

import PyInstaller.__main__

from app.constants import name


def remove_directory(path):
    try:
        shutil.rmtree(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise


main_file = 'main.py'
base_dir = Path(__file__).parent.absolute()
entry_d = base_dir / name
entry = entry_d / main_file
build_d = base_dir / 'build'
dist_d = base_dir / 'dist'
ico = base_dir / '../app.ico'
remove_directory(build_d)
remove_directory(dist_d)


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
        '--specpath=build',
        f'--copy-metadata={name}',
        '--copy-metadata=importlib_metadata'
    ])


if __name__ == '__main__':
    # minify(entry_d, build_m_d)
    # flatten(build_m, build)
    install(entry)
