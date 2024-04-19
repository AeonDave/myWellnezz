# import os
# import shutil
# import subprocess
# import venv
# from zipfile import ZipFile
#
# import constants
# from modules.version import SemVersion
#
#
# def create_env(path: str, remove: bool = False):
#     if remove:
#         print(f'        [Cleanup {path}]')
#         shutil.rmtree(path)
#     if not os.path.exists(path):
#         print(f'        [Creating venv {path}]')
#         try:
#             venv.create(path, clear=True, with_pip=True)
#         except Exception as ex:
#             venv.create(path, clear=True)
#             venv_py = os.path.join(path, 'Scripts', python + ext)
#             if os.path.exists(venv_py):
#                 subprocess.Popen([venv_py, "-m", "ensurepip", "--upgrade", "--default-pip"], shell=True).wait()
#                 subprocess.Popen([venv_py, "-m", "pip", "install", "--upgrade", "pip"], shell=True).wait()
#
#
# def pip_install_requirements(env_path: str):
#     print('        [Installing requirements.txt]')
#     subprocess.check_call([os.path.join(env_path, python + ext), "-m", "pip", "install", "-r", "requirements.txt"])
#
#
# def pyarmor(script_path: str, name: str):
#     pyarm = f'pyarmor{ext}'
#     main = '__main__.py'
#     ico = 'app.ico'
#     xec = f'{os.path.join(script_path, pyarm)} pack --clean --name={name} ' \
#           f'-e " --onefile --icon={ico} --noupx" ' \
#           f'-x " --exclude venv,bin,build,dist,include,__pycache__,modules,build.py,config.json --mix-str --advanced 1" ' \
#           f'{main}'
#     print(f'        [Packing with {pyarm}]')
#     subprocess.run(xec)
#
#
# def get_all_file_paths(directory):
#     file_paths = []
#     for root, directories, files in os.walk(directory):
#         for filename in files:
#             filepath = os.path.join(root, filename)
#             file_paths.append(filepath)
#     return file_paths
#
#
# def zip_build(s: str, f: str, zip_name: str):
#     print('        [Zipping output]')
#     with ZipFile(f'{zip_name}.zip', 'w') as z:
#         z.write(os.path.join(s, f), arcname=f)
#
#
# def cleanup(d: str):
#     print(f'        [Cleanup {d}]')
#     if os.path.exists(d):
#         shutil.rmtree(d)
#
#
# ext = '.exe' if os.name == 'nt' else ''
# python = 'python'
# working_dir = os.getcwd()
# env = os.path.join(working_dir, "venv")
# if os.name == 'nt':
#     scripts = os.path.join(env, "Scripts")
# else:
#     scripts = os.path.join(env, "bin")
# print('        [Starting build]')
# if os.path.exists(os.path.join(working_dir, '__pycache__')):
#     cleanup(os.path.join(working_dir, '__pycache__'))
# if os.path.exists(os.path.join(working_dir, 'dist')):
#     cleanup(os.path.join(working_dir, 'dist'))
# create_env(env, True)
# pip_install_requirements(scripts)
# pyarmor(scripts, f'{constants.name}-{SemVersion(constants.version)}')
# if os.path.exists(os.path.join(working_dir, 'build')):
#     cleanup(os.path.join(working_dir, 'build'))
# source = os.path.join(working_dir, 'dist')
# dest = os.path.join(working_dir, 'dist', f'{constants.name}-{constants.version}-{constants.os}')
# file = os.listdir(source)
# if len(file) > 0:
#     zip_build(source, file[0], dest)
