"""
GitHub Release update checker for Gel Labeler Molecular Biology Suite.
Queries the official GitHub API asynchronously to check for new releases without blocking the UI.
"""
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Tuple, Optional, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("gel_labeler.core.updater")

CURRENT_VERSION = "1.0.0"
GITHUB_OWNER = "vropalcrown"
GITHUB_REPO = "pcr-gel-labbler"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def parse_version_string(ver_str: str) -> Tuple[int, ...]:
    """
    Parses a version string like 'v1.2.3', '1.0.0', 'v2.1-beta' into a comparable tuple of integers.
    e.g. 'v1.2.3' -> (1, 2, 3)
    """
    if not ver_str:
        return (0, 0, 0)
    cleaned = ver_str.strip().lstrip("vV")
    numbers = re.findall(r'\d+', cleaned)
    if not numbers:
        return (0, 0, 0)
    return tuple(int(n) for n in numbers[:4])


def is_version_newer(remote_version: str, local_version: str = CURRENT_VERSION) -> bool:
    """Returns True if remote_version is strictly newer than local_version."""
    v_remote = parse_version_string(remote_version)
    v_local = parse_version_string(local_version)
    return v_remote > v_local


def fetch_latest_release_info(timeout: int = 6) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Synchronously queries the GitHub Releases API with a timeout.
    Returns: (success: bool, info_dict: dict, error_message: str or None)
    """
    headers = {
        "User-Agent": f"GelLabeler-App/{CURRENT_VERSION} (Molecular Biology Suite)",
        "Accept": "application/vnd.github.v3+json"
    }
    req = urllib.request.Request(GITHUB_API_LATEST_RELEASE, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            if status_code == 200:
                raw_data = response.read().decode("utf-8")
                data = json.loads(raw_data)
                return True, data, None
            else:
                return False, {}, f"GitHub returned HTTP status {status_code}."
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # 404 means no official releases have been published yet on the repo
            return True, {
                "tag_name": CURRENT_VERSION,
                "html_url": GITHUB_RELEASES_URL,
                "body": "No releases have been published yet.",
                "assets": []
            }, None
        return False, {}, f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, {}, f"Network connection error: {e.reason}"
    except Exception as e:
        return False, {}, f"Unexpected error checking updates: {str(e)}"


class UpdateCheckWorker(QThread):
    """Asynchronous worker thread for checking updates without freezing the GUI."""
    
    # Signals
    # check_completed(bool is_newer, str latest_version, str release_url, str release_notes, str direct_download_url)
    check_completed = pyqtSignal(bool, str, str, str, str)
    check_failed = pyqtSignal(str)

    def __init__(self, local_version: str = CURRENT_VERSION, parent=None):
        super().__init__(parent)
        self.local_version = local_version

    def run(self):
        success, release_data, error_msg = fetch_latest_release_info(timeout=6)
        if not success:
            self.check_failed.emit(error_msg or "Failed to connect to GitHub.")
            return

        tag_name = release_data.get("tag_name", "").strip() or CURRENT_VERSION
        html_url = release_data.get("html_url", GITHUB_RELEASES_URL)
        body = release_data.get("body", "No release notes provided.").strip()

        # Find direct download asset (e.g. .exe or .zip) if available
        download_url = html_url
        assets = release_data.get("assets", [])
        if isinstance(assets, list):
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".exe") or name.endswith(".zip"):
                    download_url = asset.get("browser_download_url", html_url)
                    break

        newer = is_version_newer(tag_name, self.local_version)
        self.check_completed.emit(newer, tag_name, html_url, body, download_url)
