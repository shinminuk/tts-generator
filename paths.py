# -*- coding: utf-8 -*-
"""
설정/키 파일을 저장할 위치를 정한다.

exe로 빌드(PyInstaller)했을 때는 __file__ 이 실행할 때마다 지워지는 임시 압축 해제
폴더를 가리키므로, 그 대신 실제 exe가 있는 폴더를 기준으로 삼아야
.env, 즐겨찾기, 수동 보이스 같은 사용자 데이터가 재실행해도 남아 있는다.
개발 중(.py로 직접 실행)에는 기존처럼 스크립트 폴더를 그대로 쓴다.
"""
import os
import sys


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
