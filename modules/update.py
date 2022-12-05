import glob
import os
import subprocess
import sys
import time
from pathlib import Path
from zipfile import ZipFile

import requests

import constants
from modules.version import SemVersion


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


def delete_old_versions(directory: str, pattern: str, current_version: str):
    files = find_files(directory, pattern)
    c_version = SemVersion(current_version)
    for d in files:
        try:
            version = SemVersion(os.path.splitext(d)[0].split('-')[-1])
            if version < c_version:
                os.remove(d)
        except Exception:
            os.remove(d)


def update_github(user: str, project: str, local_version: str):
    response = requests.get(f"https://api.github.com/repos/{user}/{project}/releases/latest")
    if response.status_code != 200:
        os.remove(self_path())
        sys.exit(0)
    data = response.json()
    sem_remote = SemVersion(data['tag_name'])
    sem_local = SemVersion(local_version)
    if sem_local >= sem_remote:
        return

    asset_url = None
    asset_name = None
    for asset in data["assets"]:
        asset_name = asset["name"]
        asset_split = asset_name.split('-')
        for e in asset_split:
            if constants.os.lower() in e.lower():
                asset_url = asset['browser_download_url']
                break

    if asset_url and asset_name:
        response = requests.get(asset_url)
        destination = os.path.dirname(self_path())
        source = Path(os.path.join(destination, asset_name))
        source.write_bytes(response.content)
        if source.exists():
            unzip(str(source), destination, True)
            f = find_files(destination, constants.name)
            if f:
                subprocess.Popen(f[0])
            time.sleep(2)
            sys.exit(0)
        else:
            return
