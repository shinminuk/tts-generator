# -*- coding: utf-8 -*-
"""
ElevenLabs API로 음성(TTS)을 만드는 모듈.
"""
import json
import os
import sys
import urllib.error
import urllib.request

from paths import app_dir

ENV_PATH = os.path.join(app_dir(), ".env")
API_BASE = "https://api.elevenlabs.io/v1"

DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_FORMAT = "mp3"


def load_api_key():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith("ELEVENLABS_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return ""


def save_api_key(new_key):
    lines = []
    found = False
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith("ELEVENLABS_API_KEY="):
                    lines.append(f"ELEVENLABS_API_KEY={new_key}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"ELEVENLABS_API_KEY={new_key}\n")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def list_voices(api_key):
    req = urllib.request.Request(f"{API_BASE}/voices", headers={"xi-api-key": api_key})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs API 오류 ({e.code}): {detail}")
    return data.get("voices", [])


def synthesize(api_key, text, voice_id, model, tempo, audio_format, out_path):
    body = {"text": text, "model_id": model}
    if tempo and abs(tempo - 1.0) > 1e-6:
        body["voice_settings"] = {"speed": tempo}
    req = urllib.request.Request(
        f"{API_BASE}/text-to-speech/{voice_id}",
        data=json.dumps(body).encode("utf-8"),
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(f"ElevenLabs API 오류 ({e.code}): {detail}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path
