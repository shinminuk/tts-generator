# -*- coding: utf-8 -*-
"""
Typecast API로 음성(TTS)만 만드는 범용 프로그램.

사용법 예시:
  python tts_typecast.py --text "안녕하세요" --out output.wav
  python tts_typecast.py --text-file 대본.txt --outdir 대본_audio/내프로젝트
  python tts_typecast.py --list-voices
  python tts_typecast.py --list-voices --search 이준
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from paths import app_dir

ENV_PATH = os.path.join(app_dir(), ".env")
VOICES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices.json")
API_URL = "https://api.typecast.ai/v1/text-to-speech"

DEFAULT_VOICE_ID = "tc_662a05b17419f60500ac5630"  # 이준
DEFAULT_MODEL = "ssfm-v31"
DEFAULT_LANGUAGE = "kor"
DEFAULT_TEMPO = 1.0  # 기본 속도는 1.0으로 고정
DEFAULT_FORMAT = "wav"


def load_api_key():
    key = os.environ.get("TYPECAST_API_KEY")
    if key:
        return key
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith("TYPECAST_API_KEY="):
                    return line.strip().split("=", 1)[1]
    sys.exit("TYPECAST_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")


def save_api_key(new_key):
    lines = []
    found = False
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith("TYPECAST_API_KEY="):
                    lines.append(f"TYPECAST_API_KEY={new_key}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"TYPECAST_API_KEY={new_key}\n")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def load_voices():
    if not os.path.exists(VOICES_PATH):
        return []
    with open(VOICES_PATH, encoding="utf-8") as f:
        return json.load(f)


AGE_LABELS = {
    "child": "아이",
    "teenager": "학생",
    "young_adult": "청년",
    "middle_age": "중년",
    "elder": "장년",
}
GENDER_LABELS = {"male": "남", "female": "여"}


def voice_emotions(voice, model=DEFAULT_MODEL):
    for m in voice.get("models", []):
        if m.get("version") == model:
            return m.get("emotions", [])
    models = voice.get("models", [])
    return models[0].get("emotions", []) if models else []


def list_voices(search=None):
    voices = load_voices()
    for v in voices:
        name = v.get("voice_name", {})
        eng = name.get("eng", "")
        kor = name.get("kor", "")
        if search and search.lower() not in eng.lower() and search not in kor:
            continue
        print(f"{v.get('voice_id')}\t{eng}/{kor}\t{v.get('gender')}\t{v.get('age')}")


def synthesize(api_key, text, voice_id, model, language, tempo, audio_format, out_path, prompt=None):
    body = {
        "voice_id": voice_id,
        "text": text,
        "model": model,
        "language": language,
        "output": {
            "audio_tempo": tempo,
            "audio_format": audio_format,
        },
    }
    if prompt:
        body["prompt"] = prompt
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-KEY": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(f"Typecast API 오류 ({e.code}): {detail}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def read_lines_from_file(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Typecast API로 음성만 생성하는 프로그램")
    parser.add_argument("--text", help="변환할 텍스트 한 줄")
    parser.add_argument("--text-file", help="한 줄에 한 문장씩 들어있는 텍스트 파일")
    parser.add_argument("--out", help="단일 텍스트일 때 출력 파일 경로 (예: output.wav)")
    parser.add_argument("--outdir", default="tts_output", help="여러 줄일 때 출력 폴더 (기본: tts_output)")
    parser.add_argument("--voice", default=DEFAULT_VOICE_ID, help="voice_id (기본: 이준)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="모델 버전 (기본: ssfm-v31)")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="언어 코드 (기본: kor)")
    parser.add_argument("--tempo", type=float, default=DEFAULT_TEMPO, help="재생 속도 (기본: 1.0)")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="오디오 포맷 (기본: wav)")
    parser.add_argument("--list-voices", action="store_true", help="사용 가능한 voice 목록 출력")
    parser.add_argument("--search", help="--list-voices와 함께 이름으로 검색")
    args = parser.parse_args()

    if args.list_voices:
        list_voices(args.search)
        return

    if not args.text and not args.text_file:
        sys.exit("텍스트를 입력하세요. --text 또는 --text-file 중 하나가 필요합니다.")

    api_key = load_api_key()

    if args.text:
        out_path = args.out or "output.wav"
        synthesize(api_key, args.text, args.voice, args.model, args.language,
                   args.tempo, args.format, out_path)
        print("saved", out_path)
        return

    lines = read_lines_from_file(args.text_file)
    if not lines:
        sys.exit("텍스트 파일에 내용이 없습니다.")
    os.makedirs(args.outdir, exist_ok=True)
    for i, text in enumerate(lines):
        out_path = os.path.join(args.outdir, f"{i:02d}.{args.format}")
        synthesize(api_key, text, args.voice, args.model, args.language,
                   args.tempo, args.format, out_path)
        print("saved", out_path)


if __name__ == "__main__":
    main()
