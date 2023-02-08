import contextlib
import glob
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import constants
from modules.process_util import kill_process_bypid
from modules.useragent import fake_ua_android
from modules.version import SemVersion
from modules.http_calls import async_get, async_raw_get


def self_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return os.path.abspath(__file__)


def unzip(source: str, destination: str, delete: bool = False):
    with ZipFile(source, 'r') as z:
        z.extractall(destination)
    if delete:
        os.remove(source)


def find_files(directory, pattern):
    return glob.glob(os.path.join(directory, f'{pattern}*'))


def write(destination: str, content: str):
    with open(destination, "w") as f:
        f.write(content)


def check_new_versions(directory: str, pattern: str, current_version: str):
    files = find_files(directory, pattern)
    c_version = SemVersion(current_version)
    for d in files:
        with contextlib.suppress(Exception):
            version = SemVersion(os.path.splitext(d)[0].split('-')[-1])
            if version > c_version:
                print('[New version found]')
                sys.exit(0)


def delete_old_versions(directory: str, pattern: str, current_version: str):
    files = find_files(directory, pattern)
    c_version = SemVersion(current_version)
    for d in files:
        try:
            version = SemVersion(os.path.basename(d).split('-')[-1])
            if version < c_version:
                os.remove(d)
        except Exception as e:
            print('[Error]', e)
            os.remove(d)


def open_process(path: str):
    subprocess.Popen(path, shell=True)


async def update_github(user: str, project: str, local_version: str):
    headers = {
        "User-Agent": fake_ua_android(),
        "Content-Type": "application/json; charset=utf-8"
    }
    response = await async_get(f"https://api.github.com/repos/{user}/{project}/releases/latest", headers)
    if not response:
        print('[GoodBye]')
        kill_process_bypid(os.getpid())
        return
    sem_remote = SemVersion(response['tag_name'])
    sem_local = SemVersion(local_version)
    if sem_local >= sem_remote:
        return
    print('[Updating]')
    asset_url = None
    asset_name = None
    for asset in response["assets"]:
        asset_name = asset["name"]
        asset_split = asset_name.split('-')
        for e in asset_split:
            if constants.os.lower() in e.lower():
                asset_url = asset['browser_download_url']
                break

    if asset_url and asset_name:
        response = await async_raw_get(asset_url, headers)
        destination = os.path.dirname(self_path())
        source = Path(os.path.join(destination, asset_name))
        source.write_bytes(response)
        if source.exists():
            unzip(str(source), destination, True)
            if _ := find_files(destination, constants.name):
                print('[New version found]')
                sys.exit(0)
