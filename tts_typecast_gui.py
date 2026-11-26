# -*- coding: utf-8 -*-
"""
TTS생성기 - 다중 TTS 서비스 통합 GUI (다크 + 그린, 둥근 카드 레이아웃 / customtkinter).
타입캐스트 / 일레븐랩스 / 피쉬오디오 탭을 지원합니다.
실행: python tts_typecast_gui.py
"""
import json
import os
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

import tts_typecast as core_typecast
import tts_elevenlabs as core_eleven
import tts_fishaudio as core_fish
import updater
from version import APP_VERSION
from paths import app_dir

INVALID_FILENAME_CHARS = '\\/:*?"<>|'


def safe_filename(text, maxlen=20):
    cleaned = "".join(c for c in text.strip() if c not in INVALID_FILENAME_CHARS)
    cleaned = cleaned.strip()
    return cleaned[:maxlen] or "tts"


FAVORITES_PATH = os.path.join(app_dir(), "favorites.json")


def load_favorites():
    if not os.path.exists(FAVORITES_PATH):
        return {}
    try:
        with open(FAVORITES_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def save_favorites(data):
    with open(FAVORITES_PATH, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


FAVORITES = load_favorites()

MANUAL_VOICES_PATH = os.path.join(app_dir(), "manual_voices.json")


def load_manual_voices():
    if not os.path.exists(MANUAL_VOICES_PATH):
        return {}
    try:
        with open(MANUAL_VOICES_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def save_manual_voices(data):
    with open(MANUAL_VOICES_PATH, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


MANUAL_VOICES = load_manual_voices()

# ---- 색상 (다크 + 그린) ----
PAGE = "#07080a"
CARD = "#1b2023"
CARD_SOFT = "#262d30"
FIELD = "#272e31"
ACCENT = "#00e676"
ACCENT_HOVER = "#33ff9c"
ACCENT_SOFT = "#123627"
TEXT = "#f1fff5"
MUTED = "#90a89c"
BORDER = "#343c3f"

ctk.set_appearance_mode("dark")

FONT_FAMILY = "Pretendard"
FONT_FAMILY_BOLD = "Pretendard ExtraBold"


def f(size, bold=False):
    scaled = round(size * 1.5)
    fam = FONT_FAMILY_BOLD if bold else FONT_FAMILY
    return ctk.CTkFont(family=fam, size=scaled, weight="bold" if bold else "normal")


EMOTION_KO = {
    "normal": "보통", "happy": "기쁨", "sad": "슬픔", "angry": "분노",
    "whisper": "속삭임", "toneup": "톤 업", "tonedown": "톤 다운", "tonemid": "톤 중간",
    "casual": "캐주얼", "cheer": "응원", "cold": "차가움", "cute": "귀여움",
    "inspire": "영감", "regret": "후회", "sarcasm": "비꼼", "scream": "비명",
    "shout": "외침", "soft": "부드러움", "trustful": "신뢰감", "urgent": "긴급",
}
EMOTION_KO_REV = {v: k for k, v in EMOTION_KO.items()}

TEMPO_CHOICES = [f"{x/10:.1f}" for x in range(5, 21)]  # 0.5 ~ 2.0

CATEGORIES = [
    ("child", "male", "아이(남)"), ("child", "female", "아이(여)"),
    ("teenager", "male", "학생(남)"), ("teenager", "female", "학생(여)"),
    ("young_adult", "male", "청년(남)"), ("young_adult", "female", "청년(여)"),
    ("middle_age", "male", "중년(남)"), ("middle_age", "female", "중년(여)"),
    ("elder", "male", "장년(남)"), ("elder", "female", "장년(여)"),
]

MAX_LIST_ROWS = 150
VOICE_ROW_HEIGHT = 28
VOICE_LIST_VISIBLE_ROWS = 6


def _safe_load(loader):
    try:
        return loader()
    except SystemExit:
        return ""


def typecast_voice_label(v):
    name = v.get("voice_name", {})
    label = name.get("kor") or name.get("eng") or v.get("voice_id")
    age = core_typecast.AGE_LABELS.get(v.get("age"), v.get("age"))
    gender = core_typecast.GENDER_LABELS.get(v.get("gender"), v.get("gender"))
    return f"{label} · {age}/{gender}"


class Provider:
    """서비스(타입캐스트/일레븐랩스/피쉬오디오)별 차이를 추상화하는 설정 객체."""

    def __init__(self, key, has_categories, has_emotion, network_voices, formats,
                 default_format, default_tempo, load_api_key, save_api_key,
                 fetch_voices, synthesize, voice_emotions=None, default_voice_id=None):
        self.key = key
        self.has_categories = has_categories
        self.has_emotion = has_emotion
        self.network_voices = network_voices
        self.formats = formats  # {code: label}
        self.default_format = default_format
        self.default_tempo = default_tempo
        self.load_api_key = load_api_key
        self.save_api_key = save_api_key
        self.fetch_voices = fetch_voices       # (api_key) -> list[dict(id,label,age,gender)]
        self.synthesize = synthesize           # (api_key, text, voice_id, tempo, fmt, out_path, prompt)
        self.voice_emotions = voice_emotions or (lambda v: [])
        self.default_voice_id = default_voice_id


def _typecast_fetch_voices(api_key):
    voices = core_typecast.load_voices()
    out = []
    for v in voices:
        out.append({
            "id": v.get("voice_id"), "label": typecast_voice_label(v),
            "age": v.get("age"), "gender": v.get("gender"), "raw": v,
        })
    return out


def _typecast_synthesize(api_key, text, voice_id, tempo, audio_format, out_path, prompt):
    core_typecast.synthesize(api_key, text, voice_id, core_typecast.DEFAULT_MODEL,
                              core_typecast.DEFAULT_LANGUAGE, tempo, audio_format, out_path, prompt=prompt)


def _typecast_voice_emotions(voice):
    return core_typecast.voice_emotions(voice.get("raw", {}))


def _eleven_fetch_voices(api_key):
    voices = core_eleven.list_voices(api_key)
    out = []
    for v in voices:
        out.append({"id": v.get("voice_id"), "label": v.get("name", v.get("voice_id")), "raw": v})
    return out


def _eleven_synthesize(api_key, text, voice_id, tempo, audio_format, out_path, prompt):
    core_eleven.synthesize(api_key, text, voice_id, core_eleven.DEFAULT_MODEL, tempo, audio_format, out_path)


def _fish_fetch_voices(api_key):
    voices = core_fish.list_voices(api_key)
    out = []
    for v in voices:
        out.append({
            "id": v.get("_id") or v.get("id"),
            "label": v.get("title") or v.get("name") or "(이름 없음)", "raw": v,
        })
    return out


def _fish_synthesize(api_key, text, voice_id, tempo, audio_format, out_path, prompt):
    core_fish.synthesize(api_key, text, voice_id, audio_format, out_path)


PROVIDERS = {
    "typecast": Provider(
        key="typecast", has_categories=True, has_emotion=True, network_voices=False,
        formats={"wav": "WAV 음성", "mp3": "MP3 음성"}, default_format=core_typecast.DEFAULT_FORMAT,
        default_tempo=core_typecast.DEFAULT_TEMPO,
        load_api_key=lambda: _safe_load(core_typecast.load_api_key), save_api_key=core_typecast.save_api_key,
        fetch_voices=_typecast_fetch_voices, synthesize=_typecast_synthesize,
        voice_emotions=_typecast_voice_emotions, default_voice_id=core_typecast.DEFAULT_VOICE_ID,
    ),
    "elevenlabs": Provider(
        key="elevenlabs", has_categories=False, has_emotion=False, network_voices=True,
        formats={"mp3": "MP3 음성"}, default_format=core_eleven.DEFAULT_FORMAT,
        default_tempo=1.0,
        load_api_key=core_eleven.load_api_key, save_api_key=core_eleven.save_api_key,
        fetch_voices=_eleven_fetch_voices, synthesize=_eleven_synthesize,
    ),
    "fishaudio": Provider(
        key="fishaudio", has_categories=False, has_emotion=False, network_voices=True,
        formats={"mp3": "MP3 음성"}, default_format=core_fish.DEFAULT_FORMAT,
        default_tempo=1.0,
        load_api_key=core_fish.load_api_key, save_api_key=core_fish.save_api_key,
        fetch_voices=_fish_fetch_voices, synthesize=_fish_synthesize,
    ),
}


class BigTabview(ctk.CTkTabview):
    """탭 버튼을 기본 크기의 2.5배 정도로 키운 CTkTabview."""
    _button_height = round(26 * 2.5)


class Card(ctk.CTkFrame):
    """둥근 모서리 카드 + 점 표시가 있는 제목 헤더 (단계 숫자 없음)."""

    def __init__(self, parent, title, subtitle=None):
        super().__init__(parent, fg_color=CARD, corner_radius=18, border_width=1,
                          border_color=BORDER)
        self.pack(fill="x", padx=18, pady=(0, 14))

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 8))

        dot = ctk.CTkFrame(head, fg_color=ACCENT, width=7, height=7, corner_radius=4)
        dot.pack(side="left", padx=(0, 10), pady=3)

        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(title_box, text=title, text_color=TEXT, font=f(11, bold=True)
                     ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(title_box, text=subtitle, text_color=MUTED, font=f(7)
                         ).pack(anchor="w", pady=(2, 0))

        sep = ctk.CTkFrame(self, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=18, pady=(0, 2))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=18, pady=(10, 16))


class ApiKeyBar(ctk.CTkFrame):
    """기본은 접힌 상태로 미리보기만 보여주고, '수정'을 눌러야 편집창이 열리는 API 키 입력란."""

    def __init__(self, parent, get_key, set_key, on_saved=None):
        super().__init__(parent, fg_color="transparent")
        self.get_key = get_key
        self.set_key = set_key
        self.on_saved = on_saved
        self.editing = False
        self.edit_frame = None

        self.collapsed = ctk.CTkFrame(self, fg_color="transparent")
        self.collapsed.pack(fill="x")
        self.preview_label = ctk.CTkLabel(self.collapsed, text="", text_color=MUTED, font=f(8))
        self.preview_label.pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            self.collapsed, text="수정", command=self.start_edit, width=52, height=24,
            fg_color=FIELD, hover_color=CARD_SOFT, text_color=TEXT, corner_radius=10, font=f(8),
        ).pack(side="left")
        self.refresh_preview()

    def refresh_preview(self):
        key = self.get_key() or ""
        if key:
            masked = key[:4] + "••••" + key[-4:] if len(key) > 8 else "••••"
            text = f"API 키 : {masked}"
        else:
            text = "API 키 : 설정 안됨"
        self.preview_label.configure(text=text)

    def start_edit(self):
        if self.editing:
            return
        self.editing = True
        self.collapsed.pack_forget()
        self.edit_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.edit_frame.pack(fill="x")

        self.key_var = ctk.StringVar(value=self.get_key() or "")
        entry = ctk.CTkEntry(
            self.edit_frame, textvariable=self.key_var, width=220, show="*",
            fg_color=FIELD, text_color=TEXT, border_width=0, corner_radius=10, font=f(8),
        )
        entry.pack(side="left", padx=(0, 8))

        self.show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.edit_frame, text="표시", variable=self.show_var, text_color=MUTED,
            fg_color=ACCENT, checkmark_color="#06130a", border_color=BORDER, font=f(7), width=16,
            command=lambda: entry.configure(show="" if self.show_var.get() else "*"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            self.edit_frame, text="저장", command=self.save, width=46, height=24,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#06130a",
            corner_radius=10, font=f(7, bold=True),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            self.edit_frame, text="취소", command=self.cancel, width=46, height=24,
            fg_color=FIELD, hover_color=CARD_SOFT, text_color=TEXT, corner_radius=10, font=f(7),
        ).pack(side="left")

    def save(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showwarning("입력 필요", "API 키를 입력하세요.")
            return
        self.set_key(key)
        self.cancel()
        self.refresh_preview()
        if self.on_saved:
            self.on_saved()

    def cancel(self):
        self.editing = False
        if self.edit_frame:
            self.edit_frame.destroy()
            self.edit_frame = None
        self.collapsed.pack(fill="x")


class VoiceRow(ctk.CTkFrame):
    def __init__(self, parent, voice, is_favorite, on_click, on_toggle_favorite, on_remove_manual=None):
        super().__init__(parent, fg_color=FIELD, corner_radius=10, height=VOICE_ROW_HEIGHT)
        self.voice = voice
        self.on_click = on_click
        self.pack_propagate(False)
        self.star_btn = ctk.CTkButton(
            self, text="★" if is_favorite else "☆", width=24, height=VOICE_ROW_HEIGHT - 6,
            fg_color="transparent", hover_color=CARD_SOFT,
            text_color=ACCENT if is_favorite else MUTED, font=f(9), corner_radius=8,
            command=lambda: on_toggle_favorite(voice),
        )
        self.star_btn.pack(side="left", padx=(2, 0))
        if voice.get("manual") and on_remove_manual:
            ctk.CTkButton(
                self, text="✕", width=20, height=VOICE_ROW_HEIGHT - 6,
                fg_color="transparent", hover_color=CARD_SOFT, text_color=MUTED,
                font=f(8), corner_radius=8, command=lambda: on_remove_manual(voice),
            ).pack(side="right", padx=(0, 4))
        self.label = ctk.CTkLabel(self, text=voice["label"], text_color=TEXT, font=f(8), anchor="w")
        self.label.pack(side="left", fill="both", expand=True, padx=(4, 10), pady=2)
        for widget in (self, self.label):
            widget.bind("<Button-1>", lambda e: self.on_click(self.voice))

    def set_selected(self, selected):
        color = ACCENT_SOFT if selected else FIELD
        text_color = ACCENT if selected else TEXT
        self.configure(fg_color=color)
        self.label.configure(text_color=text_color)

    def set_favorite(self, is_favorite):
        self.star_btn.configure(text="★" if is_favorite else "☆",
                                 text_color=ACCENT if is_favorite else MUTED)


class ProviderPanel:
    """한 탭(타입캐스트/일레븐랩스/피쉬오디오) 안의 전체 UI와 동작을 담당."""

    def __init__(self, parent, provider):
        self.parent = parent
        self.provider = provider
        self.voices = []
        self.filtered_voices = []
        self.selected_voice = None
        self.active_category = None
        self.voice_rows = []
        self.cat_buttons = {}
        self.favorite_ids = set(FAVORITES.get(provider.key, []))
        self.favorites_only = False
        self.fav_filter_btn = None
        self.manual_voices = [dict(v, manual=True) for v in MANUAL_VOICES.get(provider.key, [])]

        self.page = ctk.CTkScrollableFrame(
            parent, fg_color=PAGE, corner_radius=0,
            scrollbar_button_color=FIELD, scrollbar_button_hover_color=ACCENT_SOFT,
        )
        self.page.pack(fill="both", expand=True)

        self._build_api_key_bar()

        voice_card = Card(self.page, "보이스 선택")
        self._build_filter_bar(voice_card.body)
        self._build_voice_and_settings(voice_card.body)
        self._build_text_input(voice_card.body)

        run_wrap = ctk.CTkFrame(self.page, fg_color="transparent")
        run_wrap.pack(fill="x", padx=18, pady=(2, 14))
        self.run_button = ctk.CTkButton(
            run_wrap, text="▶  음성 생성", command=self.start_generate,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#06130a",
            font=f(11, bold=True), corner_radius=20, height=40, width=170,
        )
        self.run_button.pack()

        if not provider.network_voices:
            self.voices = provider.fetch_voices(None)
        else:
            self.voices = list(self.manual_voices)
        if provider.has_categories:
            self.select_category(None)
        else:
            self.refresh_voice_list()
            if provider.network_voices and provider.load_api_key():
                self.start_fetch_voices()

    # --------------------------------------------------------------- layout
    def _build_api_key_bar(self):
        bar = ctk.CTkFrame(self.page, fg_color="transparent")
        bar.pack(fill="x", padx=18, pady=(14, 8))
        on_saved = self.start_fetch_voices if self.provider.network_voices else None
        ApiKeyBar(bar, self.provider.load_api_key, self.provider.save_api_key, on_saved).pack(fill="x")

    def _build_filter_bar(self, parent):
        if self.provider.has_categories:
            chip_scroll = ctk.CTkScrollableFrame(
                parent, fg_color="transparent", height=32, orientation="horizontal",
                scrollbar_button_color=FIELD, scrollbar_button_hover_color=ACCENT_SOFT,
            )
            chip_scroll.pack(fill="x", pady=(0, 6))
            all_btn = self._make_chip(chip_scroll, "전체", None)
            all_btn.pack(side="left", padx=(0, 4))
            self.cat_buttons[None] = all_btn
            for age, gender, label in CATEGORIES:
                chip = self._make_chip(chip_scroll, label, (age, gender))
                chip.pack(side="left", padx=4)
                self.cat_buttons[(age, gender)] = chip

        search_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        search_wrap.pack(fill="x", pady=(0, 6))
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            search_wrap, textvariable=self.search_var, width=160,
            placeholder_text="이름으로 검색", fg_color=FIELD, text_color=TEXT,
            border_width=0, corner_radius=10, font=f(8),
        )
        search_entry.pack(side="left")
        search_entry.bind("<Return>", lambda e: self.refresh_voice_list())
        ctk.CTkButton(
            search_wrap, text="🔍", command=self.refresh_voice_list, width=30, height=26,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#06130a",
            font=f(8, bold=True), corner_radius=10,
        ).pack(side="left", padx=(6, 0))
        self.fav_filter_btn = ctk.CTkButton(
            search_wrap, text="⭐ 즐겨찾기", command=self.toggle_favorites_filter,
            width=90, height=26, fg_color=FIELD, hover_color=CARD_SOFT, text_color=MUTED,
            corner_radius=10, font=f(7), border_width=1, border_color=BORDER,
        )
        self.fav_filter_btn.pack(side="left", padx=(8, 0))
        if self.provider.network_voices:
            ctk.CTkButton(
                search_wrap, text="보이스 새로고침", command=self.start_fetch_voices,
                width=96, height=26, fg_color=FIELD, hover_color=CARD_SOFT, text_color=TEXT,
                corner_radius=10, font=f(7),
            ).pack(side="left", padx=(8, 0))
            ctk.CTkButton(
                search_wrap, text="ID로 추가", command=self.open_add_manual_voice,
                width=80, height=26, fg_color=FIELD, hover_color=CARD_SOFT, text_color=TEXT,
                corner_radius=10, font=f(7),
            ).pack(side="left", padx=(8, 0))

    def _make_chip(self, parent, label, key):
        return ctk.CTkButton(
            parent, text=label, width=10, height=26, corner_radius=13,
            fg_color=FIELD, hover_color=CARD_SOFT, text_color=MUTED, font=f(7),
            border_width=1, border_color=BORDER,
            command=lambda: self.select_category(key),
        )

    def _build_voice_and_settings(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="both", expand=True)

        list_height = (VOICE_ROW_HEIGHT + 4) * VOICE_LIST_VISIBLE_ROWS + 10

        left = ctk.CTkFrame(row, fg_color="transparent", width=375, height=list_height + 22)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        list_box = ctk.CTkFrame(left, fg_color="transparent", width=375, height=list_height)
        list_box.pack(fill="x")
        list_box.pack_propagate(False)
        self.list_scroll = ctk.CTkScrollableFrame(
            list_box, fg_color=PAGE, corner_radius=10,
            scrollbar_button_color=FIELD, scrollbar_button_hover_color=ACCENT_SOFT,
        )
        self.list_scroll.pack(fill="both", expand=True)
        self.list_note = ctk.CTkLabel(left, text="", text_color=MUTED, font=f(6))
        self.list_note.pack(anchor="w", pady=(4, 0))

        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(right, text="출력 설정", text_color=TEXT, font=f(8, bold=True)
                     ).pack(anchor="w", pady=(0, 6))
        self._build_settings(right)

    def _build_text_input(self, parent):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True, pady=(14, 0))
        ctk.CTkLabel(wrap, text="텍스트 입력", text_color=TEXT, font=f(8, bold=True)
                     ).pack(anchor="w", pady=(0, 4))
        self.text_box = ctk.CTkTextbox(
            wrap, height=260, wrap="word", fg_color=FIELD, text_color=TEXT,
            corner_radius=10, border_width=0, font=f(9),
        )
        self.text_box.pack(fill="both", expand=True)

    def _build_settings(self, parent):
        self.smart_emotion_var = None
        self.emotion_var = None
        self.emotion_menu = None

        if self.provider.has_emotion:
            emo_row = ctk.CTkFrame(parent, fg_color="transparent")
            emo_row.pack(fill="x", pady=(0, 8))
            self.smart_emotion_var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(
                emo_row, text="스마트 이모션", variable=self.smart_emotion_var,
                text_color=TEXT, fg_color=ACCENT, checkmark_color="#06130a",
                border_color=BORDER, font=f(8),
            ).pack(side="left", padx=(0, 12))
            ctk.CTkLabel(emo_row, text="감정", text_color=TEXT, font=f(8)
                         ).pack(side="left", padx=(0, 8))
            self.emotion_var = ctk.StringVar(value=EMOTION_KO["normal"])
            self.emotion_menu = ctk.CTkOptionMenu(
                emo_row, variable=self.emotion_var, values=[EMOTION_KO["normal"]], width=100,
                fg_color=FIELD, button_color=FIELD, button_hover_color=CARD_SOFT,
                text_color=TEXT, dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                dropdown_hover_color=ACCENT_SOFT, corner_radius=10, font=f(8),
            )
            self.emotion_menu.pack(side="left")

        tempo_row = ctk.CTkFrame(parent, fg_color="transparent")
        tempo_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(tempo_row, text="속도", text_color=TEXT, font=f(8)
                     ).pack(side="left", padx=(0, 8))
        tempo_default = f"{self.provider.default_tempo:.1f}"
        self.tempo_var = ctk.StringVar(value=tempo_default)
        self.tempo_menu = ctk.CTkOptionMenu(
            tempo_row, variable=self.tempo_var, values=TEMPO_CHOICES, width=70,
            fg_color=FIELD, button_color=FIELD, button_hover_color=CARD_SOFT,
            text_color=TEXT, dropdown_fg_color=CARD, dropdown_text_color=TEXT,
            dropdown_hover_color=ACCENT_SOFT, corner_radius=10, font=f(8),
        )
        self.tempo_menu.pack(side="left", padx=(0, 4))

        arrow_box = ctk.CTkFrame(tempo_row, fg_color="transparent")
        arrow_box.pack(side="left")
        ctk.CTkButton(arrow_box, text="▲", command=lambda: self.step_tempo(0.1),
                      width=20, height=12, corner_radius=6, fg_color=FIELD,
                      hover_color=CARD_SOFT, text_color=ACCENT, font=f(6)).pack(side="top", pady=(0, 1))
        ctk.CTkButton(arrow_box, text="▼", command=lambda: self.step_tempo(-0.1),
                      width=20, height=12, corner_radius=6, fg_color=FIELD,
                      hover_color=CARD_SOFT, text_color=ACCENT, font=f(6)).pack(side="top")

        format_row = ctk.CTkFrame(parent, fg_color="transparent")
        format_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(format_row, text="포맷", text_color=TEXT, font=f(8)
                     ).pack(side="left", padx=(0, 8))
        self.format_rev = {v: k for k, v in self.provider.formats.items()}
        self.format_var = ctk.StringVar(value=self.provider.formats[self.provider.default_format])
        ctk.CTkOptionMenu(
            format_row, variable=self.format_var, values=list(self.provider.formats.values()), width=90,
            fg_color=FIELD, button_color=FIELD, button_hover_color=CARD_SOFT,
            text_color=TEXT, dropdown_fg_color=CARD, dropdown_text_color=TEXT,
            dropdown_hover_color=ACCENT_SOFT, corner_radius=10, font=f(8),
        ).pack(side="left")

        outdir_row = ctk.CTkFrame(parent, fg_color="transparent")
        outdir_row.pack(fill="x")
        ctk.CTkLabel(outdir_row, text="출력 폴더", text_color=TEXT, font=f(8)
                     ).pack(side="left", padx=(0, 8))
        self.outdir_var = ctk.StringVar(value="tts_output")
        ctk.CTkEntry(outdir_row, textvariable=self.outdir_var, width=150, fg_color=FIELD,
                     text_color=TEXT, border_width=0, corner_radius=10,
                     font=f(8)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(outdir_row, text="폴더 선택", command=self.pick_outdir, width=70, height=26,
                      fg_color=FIELD, hover_color=CARD_SOFT, text_color=TEXT,
                      corner_radius=10, font=f(7)).pack(side="left")

    def step_tempo(self, delta):
        try:
            value = round(float(self.tempo_var.get()) + delta, 1)
        except ValueError:
            value = self.provider.default_tempo
        value = min(2.0, max(0.5, value))
        self.tempo_var.set(f"{value:.1f}")

    # -------------------------------------------------------------- actions
    def select_category(self, key):
        self.active_category = key
        for k, btn in self.cat_buttons.items():
            if k == key:
                btn.configure(fg_color=ACCENT, text_color="#06130a", hover_color=ACCENT_HOVER,
                              border_color=ACCENT)
            else:
                btn.configure(fg_color=FIELD, text_color=MUTED, hover_color=CARD_SOFT,
                              border_color=BORDER)
        self.refresh_voice_list()

    def start_fetch_voices(self):
        api_key = self.provider.load_api_key()
        if not api_key:
            messagebox.showwarning("API 키 필요", "먼저 API 키를 입력하고 저장하세요.")
            return
        threading.Thread(target=self._fetch_voices_worker, args=(api_key,), daemon=True).start()

    def _fetch_voices_worker(self, api_key):
        try:
            voices = self.provider.fetch_voices(api_key)
        except Exception as e:
            self.page.after(0, lambda: messagebox.showerror("오류", f"보이스 목록을 가져오지 못했습니다: {e}"))
            return

        def apply():
            self.voices = voices + self.manual_voices
            self.refresh_voice_list()

        self.page.after(0, apply)

    def toggle_favorites_filter(self):
        self.favorites_only = not self.favorites_only
        if self.favorites_only:
            self.fav_filter_btn.configure(fg_color=ACCENT, text_color="#06130a",
                                           hover_color=ACCENT_HOVER, border_color=ACCENT)
        else:
            self.fav_filter_btn.configure(fg_color=FIELD, text_color=MUTED,
                                           hover_color=CARD_SOFT, border_color=BORDER)
        self.refresh_voice_list()

    def toggle_favorite(self, voice):
        vid = voice["id"]
        if vid in self.favorite_ids:
            self.favorite_ids.discard(vid)
        else:
            self.favorite_ids.add(vid)
        FAVORITES[self.provider.key] = sorted(self.favorite_ids)
        save_favorites(FAVORITES)
        if self.favorites_only:
            self.refresh_voice_list()
        else:
            for row in self.voice_rows:
                if row.voice["id"] == vid:
                    row.set_favorite(vid in self.favorite_ids)
                    break

    def open_add_manual_voice(self):
        dialog = ctk.CTkInputDialog(text="보이스 ID를 입력하세요:", title="ID로 보이스 추가")
        voice_id = dialog.get_input()
        if not voice_id:
            return
        voice_id = voice_id.strip()
        if not voice_id:
            return
        dialog2 = ctk.CTkInputDialog(text="표시할 이름을 입력하세요 (비워두면 ID 사용):", title="ID로 보이스 추가")
        label = dialog2.get_input()
        label = (label or "").strip() or voice_id
        self.add_manual_voice(voice_id, label)

    def add_manual_voice(self, voice_id, label):
        if any(v["id"] == voice_id for v in self.voices):
            messagebox.showwarning("중복", "이미 목록에 있는 보이스 ID입니다.")
            return
        voice = {"id": voice_id, "label": label, "manual": True}
        self.manual_voices.append(voice)
        MANUAL_VOICES[self.provider.key] = [
            {"id": v["id"], "label": v["label"]} for v in self.manual_voices
        ]
        save_manual_voices(MANUAL_VOICES)
        self.voices.append(voice)
        self.refresh_voice_list()

    def remove_manual_voice(self, voice):
        self.manual_voices = [v for v in self.manual_voices if v["id"] != voice["id"]]
        self.voices = [v for v in self.voices if v["id"] != voice["id"]]
        MANUAL_VOICES[self.provider.key] = [
            {"id": v["id"], "label": v["label"]} for v in self.manual_voices
        ]
        save_manual_voices(MANUAL_VOICES)
        self.refresh_voice_list()

    def refresh_voice_list(self):
        search = self.search_var.get().strip().lower()
        result = []
        for v in self.voices:
            if self.provider.has_categories and self.active_category:
                age, gender = self.active_category
                if v.get("age") != age or v.get("gender") != gender:
                    continue
            if search and search not in v["label"].lower():
                continue
            if self.favorites_only and v["id"] not in self.favorite_ids:
                continue
            result.append(v)
        self.filtered_voices = result

        for row in self.voice_rows:
            row.destroy()
        self.voice_rows = []

        shown = result[:MAX_LIST_ROWS]
        for v in shown:
            row = VoiceRow(self.list_scroll, v, v["id"] in self.favorite_ids,
                            self.set_selected_voice, self.toggle_favorite, self.remove_manual_voice)
            row.pack(fill="x", pady=2)
            self.voice_rows.append(row)

        if len(result) > MAX_LIST_ROWS:
            self.list_note.configure(text=f"{len(result)}개 중 {MAX_LIST_ROWS}개 표시 중")
        else:
            self.list_note.configure(text=f"{len(result)}개")

        default_voice = None
        if self.provider.default_voice_id:
            default_voice = next((v for v in shown if v["id"] == self.provider.default_voice_id), None)
        if default_voice:
            self.set_selected_voice(default_voice)
        elif shown:
            self.set_selected_voice(shown[0])
        else:
            self.selected_voice = None

    def set_selected_voice(self, voice):
        self.selected_voice = voice
        for row in self.voice_rows:
            row.set_selected(row.voice["id"] == voice["id"])

        if self.provider.has_emotion:
            emotions = self.provider.voice_emotions(voice) or ["normal"]
            if "normal" not in emotions:
                emotions = ["normal"] + emotions
            emotion_labels = [EMOTION_KO.get(e, e) for e in emotions]
            self.emotion_menu.configure(values=emotion_labels)
            if self.emotion_var.get() not in emotion_labels:
                self.emotion_var.set(EMOTION_KO["normal"])

    def pick_outdir(self):
        path = filedialog.askdirectory()
        if path:
            self.outdir_var.set(path)

    def start_generate(self):
        text = self.text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("입력 필요", "텍스트를 입력하세요.")
            return
        if not self.selected_voice:
            messagebox.showwarning("보이스 필요", "보이스를 선택하세요.")
            return
        try:
            tempo = float(self.tempo_var.get())
        except ValueError:
            messagebox.showerror("오류", "속도는 숫자로 입력하세요.")
            return

        voice_id = self.selected_voice["id"]
        voice_label = self.selected_voice.get("label", "voice")
        tempo_str = self.tempo_var.get().strip()
        audio_format = self.format_rev.get(self.format_var.get(), self.provider.default_format)
        outdir = self.outdir_var.get().strip() or "tts_output"
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        prompt = None
        if self.provider.has_emotion:
            if self.smart_emotion_var.get():
                prompt = {"emotion_type": "smart"}
            else:
                emotion_key = EMOTION_KO_REV.get(self.emotion_var.get(), "normal")
                prompt = {"emotion_type": "preset", "emotion_preset": emotion_key, "emotion_intensity": 1}

        self.run_button.configure(state="disabled", fg_color=MUTED)
        threading.Thread(
            target=self.generate_worker,
            args=(lines, voice_id, voice_label, tempo, tempo_str, audio_format, outdir, prompt),
            daemon=True,
        ).start()

    def generate_worker(self, lines, voice_id, voice_label, tempo, tempo_str, audio_format, outdir, prompt):
        try:
            api_key = self.provider.load_api_key()
            if not api_key:
                raise RuntimeError("API 키가 설정되지 않았습니다.")
            os.makedirs(outdir, exist_ok=True)
            voice_name = safe_filename(voice_label, maxlen=20)
            used_names = set()
            for line in lines:
                base = f"{voice_name}_{tempo_str}_{safe_filename(line)}"
                name = base
                n = 2
                while name in used_names:
                    name = f"{base}_{n}"
                    n += 1
                used_names.add(name)
                out_path = os.path.join(outdir, f"{name}.{audio_format}")
                self.provider.synthesize(api_key, line, voice_id, tempo, audio_format, out_path, prompt)
            self.page.after(0, lambda: messagebox.showinfo(
                "완료", f"총 {len(lines)}개 완료.\n폴더: {outdir}"))
        except SystemExit as e:
            self.page.after(0, lambda e=e: messagebox.showerror("오류", str(e)))
        except Exception as e:
            self.page.after(0, lambda e=e: messagebox.showerror("오류", str(e)))
        finally:
            self.page.after(0, lambda: self.run_button.configure(state="normal", fg_color=ACCENT))


class TtsApp:
    def __init__(self, root):
        self.root = root
        root.title(f"TTS생성기 v{APP_VERSION}")
        root.geometry("1000x900")
        root.configure(fg_color=PAGE)
        root.after(0, lambda: root.state("zoomed"))

        title_bar = ctk.CTkFrame(root, fg_color=PAGE)
        title_bar.pack(fill="x", padx=18, pady=(16, 6))
        ctk.CTkLabel(title_bar, text="TTS생성기", text_color=TEXT, font=f(15, bold=True)
                     ).pack(anchor="w")
        ctk.CTkLabel(title_bar, text="텍스트를 음성으로 변환합니다", text_color=MUTED, font=f(8)
                     ).pack(anchor="w", pady=(2, 0))

        self.tabview = BigTabview(
            root, fg_color=PAGE, segmented_button_fg_color=CARD,
            segmented_button_selected_color=ACCENT, segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=CARD, segmented_button_unselected_hover_color=CARD_SOFT,
            segmented_button_font=ctk.CTkFont(family=FONT_FAMILY_BOLD, size=32, weight="bold"),
            text_color=TEXT, text_color_disabled=MUTED, corner_radius=16,
        )
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        tab_specs = [("Typecast", "typecast"), ("ElevenLabs", "elevenlabs"), ("Fish Audio", "fishaudio")]
        self.panels = {}
        for label, key in tab_specs:
            tab = self.tabview.add(label)
            self.panels[key] = ProviderPanel(tab, PROVIDERS[key])

        self._style_tab_selection_text(self.tabview, "#06130a", TEXT)

        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self):
        if not updater.is_frozen():
            return
        has_update, latest_tag, download_url = updater.check_for_update()
        if has_update:
            self.root.after(0, lambda: self._prompt_update(latest_tag, download_url))

    def _prompt_update(self, latest_tag, download_url):
        if not messagebox.askyesno(
            "업데이트 알림",
            f"새 버전 {latest_tag}이 있습니다 (현재 v{APP_VERSION}).\n지금 업데이트하고 다시 시작할까요?",
        ):
            return
        threading.Thread(target=self._apply_update_worker, args=(download_url,), daemon=True).start()

    def _apply_update_worker(self, download_url):
        try:
            updater.download_and_apply_update(download_url)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("업데이트 실패", str(e)))

    @staticmethod
    def _style_tab_selection_text(tabview, selected_color, unselected_color):
        seg = tabview._segmented_button
        original_callback = seg._command

        def recolor():
            current = seg.get()
            for name, btn in seg._buttons_dict.items():
                btn.configure(text_color=selected_color if name == current else unselected_color)

        def on_change(value):
            if original_callback is not None:
                original_callback(value)
            recolor()

        seg._command = on_change
        recolor()


if __name__ == "__main__":
    root = ctk.CTk()
    app = TtsApp(root)
    root.mainloop()
