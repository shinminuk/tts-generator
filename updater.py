# -*- coding: utf-8 -*-
"""
GitHub Releases를 이용한 자동 업데이트.

- check_for_update(): GitHub의 "최신 릴리즈" 정보를 읽어와 지금 버전보다 새 버전이
  있는지, 있다면 받아야 할 실행파일(.exe) 주소가 무엇인지 알려준다.
- download_and_apply_update(): 새 실행파일을 내려받은 뒤, 지금 실행 중인 프로그램을
  교체하는 작은 배치 스크립트를 만들어 실행하고 앱을 종료한다.
  (윈도우에서는 실행 중인 exe 자신을 직접 덮어쓸 수 없기 때문에, 이렇게
  "현재 프로그램 종료 -> 새 파일로 교체 -> 재실행"을 대신해줄 배치 파일이 필요하다.)
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from version import APP_VERSION, GITHUB_REPO

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
# GitHub 릴리즈 자산 이름은 한글이 들어가면 업로드 중 깨질 수 있어 영문으로 고정한다.
ASSET_NAME = "TTS_Generator.exe"


def _version_tuple(v):
    v = v.lstrip("v")
    parts = []
    for p in v.split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_frozen():
    return getattr(sys, "frozen", False)


def check_for_update():
    """(새버전 있음, 최신버전, 다운로드주소) 를 돌려준다. 실패하면 (False, None, None)."""
    try:
        req = urllib.request.Request(
            API_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "tts-generator-updater"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
        return False, None, None

    latest_tag = data.get("tag_name", "")
    if not latest_tag:
        return False, None, None

    download_url = None
    for asset in data.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            download_url = asset.get("browser_download_url")
            break
    if not download_url:
        return False, None, None

    if _version_tuple(latest_tag) > _version_tuple(APP_VERSION):
        return True, latest_tag, download_url
    return False, None, None


def download_and_apply_update(download_url, on_progress=None):
    """새 exe를 받아서 지금 프로그램을 교체하고 재시작한다."""
    if not is_frozen():
        raise RuntimeError("개발 모드(.py 직접 실행)에서는 자동 업데이트를 적용할 수 없습니다.")

    current_exe = sys.executable
    app_dir = os.path.dirname(current_exe)
    new_exe = os.path.join(app_dir, "_update_new.exe")

    req = urllib.request.Request(download_url, headers={"User-Agent": "tts-generator-updater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(new_exe, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress and total:
                    on_progress(downloaded, total)

    bat_path = os.path.join(tempfile.gettempdir(), "tts_generator_update.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "timeout /t 1 /nobreak >nul\r\n"
            f'move /y "{new_exe}" "{current_exe}" >nul\r\n'
            f'start "" "{current_exe}"\r\n'
            'del "%~f0"\r\n'
        )

    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    os._exit(0)
