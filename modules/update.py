import os
import sys
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


def unzip(source: str, destination: str):
    with ZipFile(source, 'r') as z:
        z.extractall(destination)


def update_github(user: str, project: str, local_version: str):
    response = requests.get(f"https://api.github.com/repos/{user}/{project}/releases/latest")
    if response.status_code != 200:
        return
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
        maindir = os.path.dirname(self_path())
        save_to = Path(os.path.join(maindir, asset_name))
        save_to.write_bytes(response.content)
        if save_to.exists():
            unzip(str(save_to), maindir)
            os.remove(str(save_to))
            sys.exit(0)
        else:
            return
