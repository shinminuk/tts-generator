# -*- coding: utf-8 -*-
"""TTS 생성기용 아이콘(icon.ico)을 만든다."""
import math
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
SIZE = 256

CARD = (27, 32, 35)
ACCENT = (0, 230, 118)
ACCENT_HOVER = (51, 255, 156)
TEXT = (241, 255, 245)


def rounded_rect(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def make_base():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 배경: 둥근 사각형 그라데이션(어두운 카드 색 -> 살짝 밝은 톤)
    grad = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    for y in range(SIZE):
        t = y / SIZE
        r = int(CARD[0] + (CARD[0] * 0.3) * t)
        g = int(CARD[1] + (CARD[1] * 0.3) * t)
        b = int(CARD[2] + (CARD[2] * 0.3) * t)
        gdraw.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (SIZE, SIZE), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=56, fill=255)
    img.paste(grad, (0, 0), mask)

    # 말풍선 (음성 느낌)
    bubble_box = (36, 64, SIZE - 36, 196)
    draw.rounded_rectangle(bubble_box, radius=36, fill=ACCENT)
    tail = [(92, 190), (92, 228), (134, 190)]
    draw.polygon(tail, fill=ACCENT)

    # 말풍선 안 사운드웨이브 바 (TTS 느낌)
    bar_w = 16
    gap = 12
    heights = [28, 52, 76, 52, 28]
    n = len(heights)
    total_w = n * bar_w + (n - 1) * gap
    start_x = (SIZE - total_w) // 2
    mid_y = (bubble_box[1] + bubble_box[3]) // 2
    for i, h in enumerate(heights):
        x0 = start_x + i * (bar_w + gap)
        x1 = x0 + bar_w
        y0 = mid_y - h // 2
        y1 = mid_y + h // 2
        draw.rounded_rectangle((x0, y0, x1, y1), radius=bar_w // 2, fill=CARD)

    return img


def main():
    img = make_base()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    out_path = os.path.join(BASE, "icon.ico")
    imgs = [img.resize((s, s), Image.LANCZOS) for s in sizes]
    imgs[-1].save(out_path, format="ICO", sizes=[(s, s) for s in sizes])
    png_path = os.path.join(BASE, "icon_preview.png")
    img.save(png_path)
    print("saved", out_path)
    print("saved", png_path)


if __name__ == "__main__":
    main()
