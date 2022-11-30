import requests


def update_github(user: str, project: str, local_version: str):
    response = requests.get(f"https://api.github.com/repos/{user}/{project}/releases/latest")
