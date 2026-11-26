# -*- coding: utf-8 -*-
"""
TTS생성기 설치/제거 프로그램.

이 스크립트 자체를 PyInstaller로 묶어서 "TTS생성기_Setup.exe" 를 만든다.
그 안에는 실제 프로그램(TTS생성기.exe)과 아이콘(icon.ico)이 함께 들어있다.
(API 키 파일(.env)은 절대 포함하지 않는다 — 설치 파일에는 프로그램만 들어간다.)

동작:
  설치 모드 (기본, 더블클릭): %LOCALAPPDATA%\\Programs\\TTS생성기 에 프로그램을 복사하고,
    바탕화면/시작메뉴 바로가기와 "프로그램 제거" 등록 정보를 만든다.
  제거 모드 (--uninstall): 설치된 파일, 바로가기, 레지스트리 등록을 모두 지운다.
    (사용자가 직접 만든 .env, favorites.json, manual_voices.json 은 그대로 둔다.)
"""
import argparse
import os
import shutil
import subprocess
import sys
import winreg

APP_NAME = "TTS생성기"
PUBLISHER = "shinminuk"

INSTALL_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Programs", APP_NAME)
MAIN_EXE = os.path.join(INSTALL_DIR, f"{APP_NAME}.exe")
ICON_PATH = os.path.join(INSTALL_DIR, "icon.ico")
SETUP_EXE_COPY = os.path.join(INSTALL_DIR, "Setup.exe")

UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"

DESKTOP_DIR = os.path.join(os.environ["USERPROFILE"], "Desktop")
START_MENU_DIR = os.path.join(
    os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
)


def _bundled_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _run_powershell(script):
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _create_shortcut(lnk_path, target, icon):
    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{lnk_path}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.WorkingDirectory = '{os.path.dirname(target)}'; "
        f"$s.IconLocation = '{icon}'; "
        f"$s.Description = '{APP_NAME}'; "
        "$s.Save()"
    )
    _run_powershell(script)


def install():
    os.makedirs(INSTALL_DIR, exist_ok=True)

    shutil.copy2(_bundled_path(f"{APP_NAME}.exe"), MAIN_EXE)
    shutil.copy2(_bundled_path("icon.ico"), ICON_PATH)

    try:
        setup_source = sys.executable if getattr(sys, "frozen", False) else None
        if setup_source and os.path.abspath(setup_source) != os.path.abspath(SETUP_EXE_COPY):
            shutil.copy2(setup_source, SETUP_EXE_COPY)
    except OSError:
        pass

    _create_shortcut(os.path.join(DESKTOP_DIR, f"{APP_NAME}.lnk"), MAIN_EXE, ICON_PATH)
    os.makedirs(START_MENU_DIR, exist_ok=True)
    _create_shortcut(os.path.join(START_MENU_DIR, f"{APP_NAME}.lnk"), MAIN_EXE, ICON_PATH)

    uninstall_cmd = f'"{SETUP_EXE_COPY if os.path.exists(SETUP_EXE_COPY) else MAIN_EXE}" --uninstall'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, ICON_PATH)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_cmd)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

    _show_message(f"{APP_NAME} 설치가 완료되었습니다.\n바탕화면 바로가기로 실행할 수 있습니다.")
    subprocess.Popen([MAIN_EXE], creationflags=subprocess.CREATE_NO_WINDOW)


def uninstall():
    for path in (
        os.path.join(DESKTOP_DIR, f"{APP_NAME}.lnk"),
        os.path.join(START_MENU_DIR, f"{APP_NAME}.lnk"),
    ):
        if os.path.exists(path):
            os.remove(path)

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass

    for name in (f"{APP_NAME}.exe", "icon.ico"):
        path = os.path.join(INSTALL_DIR, name)
        if os.path.exists(path):
            os.remove(path)

    _show_message(
        f"{APP_NAME}가 제거되었습니다.\n"
        "저장했던 API 키, 즐겨찾기 등의 설정 파일은 남아 있으니 필요 없다면 직접 지워도 됩니다."
    )

    self_path = sys.executable if getattr(sys, "frozen", False) else None
    if self_path and os.path.abspath(self_path) == os.path.abspath(SETUP_EXE_COPY):
        bat = os.path.join(os.environ["TEMP"], f"{APP_NAME}_uninstall_cleanup.bat")
        with open(bat, "w", encoding="utf-8") as f:
            f.write(
                "@echo off\r\n"
                "timeout /t 1 /nobreak >nul\r\n"
                f'del "{self_path}" >nul 2>nul\r\n'
                f'rmdir "{INSTALL_DIR}" >nul 2>nul\r\n'
                'del "%~f0"\r\n'
            )
        subprocess.Popen(
            ["cmd.exe", "/c", bat],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )


def _show_message(text):
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(APP_NAME, text)
    root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
