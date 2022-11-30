import os
import shutil
import subprocess
import venv


def create_env(path: str):
    venv.create(path, clear=True, with_pip=True)


def pip_install_requirements(env_path: str):
    subprocess.check_call([os.path.join(env_path, python + ext), "-m", "pip", "install", "-r", "requirements.txt"])


def pyarmor(script_path: str, name: str):
    subprocess.run(f'{os.path.join(script_path, "pyarmor")} pack --clean --name={name} '
                   f'-e " --onefile --icon=app.ico --noupx" '
                   f'-x " --exclude venv --exclude build.py --advanced 1" main.py')


def cleanup(d: str):
    shutil.rmtree(d)


if os.name == 'nt':
    ext = '.exe'
    python = 'python'
else:
    ext = ''
    python = 'python3'

working_dir = os.getcwd()
env = os.path.join(working_dir, "venv")
scripts = os.path.join(env, "Scripts")

create_env(env)
pip_install_requirements(scripts)
pyarmor(scripts, 'myWellnezz')
cleanup(os.path.join(working_dir, 'build'))
