import os
import shutil
import subprocess
from zipfile import ZipFile

import venv

import constants
from modules.version import SemVersion


def create_env(path: str):
    venv.create(path, clear=True, with_pip=True)


def pip_install_requirements(env_path: str):
    subprocess.check_call([os.path.join(env_path, python + ext), "-m", "pip", "install", "-r", "requirements.txt"])


def pyarmor(script_path: str, entry_script: str, name: str):
    path = os.path.join(script_path, "pyarmor")
    if not os.path.exists(path):
        print(f'Error, missing {path}')
    else:
        subprocess.run(f'{path} pack --clean --name={name} '
                       f'-e " --onefile --icon=app.ico --noupx" '
                       f'-x " --exclude venv '
                       f'--exclude __pycache__,modules,build.py '
                       f'--mix-str '
                       f'--advanced 1" {entry_script}', shell=True)


def get_all_file_paths(directory):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
    return file_paths


def zip_build(source: str, file: str, zip_name: str):
    with ZipFile(f'{zip_name}.zip', 'w') as z:
        z.write(os.path.join(source, file), arcname=file)


def cleanup(d: str):
    shutil.rmtree(d)


if os.name == 'nt':
    ext = '.exe'
    python = 'python'
    dir_lib = 'Scripts'
else:
    ext = ''
    python = 'python3'
    dir_lib = 'bin'

working_dir = os.getcwd()
env = os.path.join(working_dir, "venv")
scripts = os.path.join(env, dir_lib)

if os.path.exists(os.path.join(working_dir, 'dist')):
    cleanup(os.path.join(working_dir, 'dist'))
create_env(env)
pip_install_requirements(scripts)
pyarmor(scripts, os.path.join(working_dir, 'main.py'), f'{constants.name}-{SemVersion(constants.version)}')
if os.path.exists(os.path.join(working_dir, 'build')):
    cleanup(os.path.join(working_dir, 'build'))
source = os.path.join(working_dir, 'dist')
dest = os.path.join(working_dir, 'dist', f'{constants.name}-{constants.version}-{constants.os}')
file = os.listdir(source)
if len(file) > 0:
    zip_build(source, file[0], dest)
