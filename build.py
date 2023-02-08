import os
import shutil
import subprocess
from zipfile import ZipFile

import venv

import constants
from modules.version import SemVersion


def create_env(path: str, remove: bool = False):
    if os.path.exists(path) and remove:
        shutil.rmtree(path)
    if not os.path.exists(path):
        venv.create(path, clear=True, with_pip=True)
    # subprocess.run([python + ext, '-m', 'venv', path])


def pip_install_requirements(env_path: str):
    subprocess.check_call([os.path.join(env_path, python + ext), "-m", "pip", "install", "-r", "requirements.txt"])


def pyarmor(e: str, script_path: str, name: str):
    pyarm = 'pyarmor'
    subprocess.run(
        f'{os.path.join(script_path, python + ext)} {os.path.join(script_path, pyarm)} pack --clean --name={name} '
        f'-e " --onefile --icon=app.ico --noupx" '
        f'-x " --exclude venv '
        f'--exclude __pycache__,modules,build.py '
        f'--mix-str '
        f'--advanced 1" {os.path.join(e, f"{working_dir}/main.py")}')


def get_all_file_paths(directory):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
    return file_paths


def zip_build(s: str, f: str, zip_name: str):
    with ZipFile(f'{zip_name}.zip', 'w') as z:
        z.write(os.path.join(s, f), arcname=file)


def cleanup(d: str):
    shutil.rmtree(d)


ext = '.exe' if os.name == 'nt' else ''
python = 'python'
working_dir = os.getcwd()
env = os.path.join(working_dir, "venv")
if os.name == 'nt':
    scripts = os.path.join(env, "Scripts")
else:
    scripts = os.path.join(env, "bin")
if os.path.exists(os.path.join(working_dir, 'dist')):
    cleanup(os.path.join(working_dir, 'dist'))
create_env(env)
pip_install_requirements(scripts)
pyarmor(working_dir, scripts, f'{constants.name}-{SemVersion(constants.version)}')
if os.path.exists(os.path.join(working_dir, 'build')):
    cleanup(os.path.join(working_dir, 'build'))
source = os.path.join(working_dir, 'dist')
dest = os.path.join(working_dir, 'dist', f'{constants.name}-{constants.version}-{constants.os}')
file = os.listdir(source)
if len(file) > 0:
    zip_build(source, file[0], dest)
