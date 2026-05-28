import asyncio
import os
from functools import wraps
from typing import Tuple

from noble_tls.utils.asset import generate_asset_name
from noble_tls.utils.asset import root_dir
from noble_tls.exceptions.exceptions import TLSClientException
import httpx

owner = 'bogdanfinn'
repo = 'tls-client'
url = f'https://api.github.com/repos/{owner}/{repo}/releases/latest'
root_directory = root_dir()
GITHUB_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
_deps_dir = os.path.join(root_directory, 'dependencies')
_version_file = os.path.join(_deps_dir, '.version')


def _asset_path(asset_name: str) -> str:
    return os.path.join(_deps_dir, asset_name)


def _github_headers(accept: str = 'application/vnd.github.v3+json') -> dict:
    headers = {'Accept': accept, 'User-Agent': 'noble-tls'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers


def auto_retry(retries: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while attempt <= retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt > retries:
                        print(f">> Failed after {attempt} attempts with error: {e}")
                        raise e
                    await asyncio.sleep(0.1)

        return wrapper

    return decorator


@auto_retry(retries=3)
async def get_latest_release() -> Tuple[str, list]:
    """
    Fetches the latest release from the GitHub API.

    :return: Latest release tag name, and a list of assets
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_github_headers())

    if response.status_code == 200:
        data = response.json()
        version_num = data['tag_name'].replace('v', '')
        if 'assets' not in data:
            raise TLSClientException(f"Version {version_num} does not have any assets.")

        return version_num, data['assets']
    else:
        raise TLSClientException(f"Failed to fetch the latest release. Status code: {response.status_code}")


async def download_and_save_asset(
        asset_url: str,
        asset_name: str,
        version: str
) -> None:
    headers = _github_headers(accept='application/octet-stream')
    headers['Connection'] = 'keep-alive'
    if GITHUB_TOKEN:
        print(">> Using GitHub token for authentication.")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(asset_url, headers=headers)
        if response.status_code != 200:
            raise TLSClientException(f"Failed to download asset {asset_name}. Status code: {response.status_code}")

        os.makedirs(_deps_dir, exist_ok=True)
        with open(_asset_path(asset_name), 'wb') as f:
            f.write(response.content)

        await save_version_info(asset_name, version)


async def save_version_info(asset_name: str, version: str):
    """Save version info to a hidden .version file in dependencies/."""
    with open(_version_file, 'w') as f:
        f.write(f"{asset_name} {version}")


def delete_version_info():
    """Delete everything inside dependencies/."""
    try:
        for file in os.listdir(_deps_dir):
            os.remove(os.path.join(_deps_dir, file))
    except FileNotFoundError:
        pass


def read_version_info():
    """Read version info from .version file in dependencies/."""
    try:
        with open(_version_file, 'r') as f:
            data = f.read().split(' ')
            return data[0], data[1]
    except FileNotFoundError:
        return None, None


async def download_if_necessary():
    version_num, asset_url = await get_latest_release()
    if not asset_url or not version_num:
        raise TLSClientException(f"Version {version_num} does not have any assets.")

    asset_name = generate_asset_name(custom_part=repo, version=version_num)
    if os.path.exists(_asset_path(asset_name)):
        return

    download_url = [asset['browser_download_url'] for asset in asset_url if asset['name'] == asset_name]
    if len(download_url) == 0:
        raise TLSClientException(f"Unable to find asset {asset_name} for version {version_num}.")

    await download_and_save_asset(download_url[0], asset_name, version_num)


async def update_if_necessary():
    current_asset, current_version = read_version_info()
    if not current_asset or not current_version:
        raise TLSClientException("Unable to read version info, no TLS libs found, use download_if_necessary()")

    version_num, asset_url = await get_latest_release()
    if not asset_url or not version_num:
        raise TLSClientException(f"Version {version_num} does not have any assets.")

    if version_num != current_version:
        print(f">> Current version {current_version} is outdated, downloading the latest TLS release...")
        await download_if_necessary()


if __name__ == "__main__":
    asyncio.run(update_if_necessary())
