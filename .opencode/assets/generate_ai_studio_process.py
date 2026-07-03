#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
PROCESS_IMAGE = ROOT / "ai-studio-process.png"
WORKFLOW_IMAGE = ROOT / "ai-studio-workflow.png"
FONT_PATH = Path("/System/Library/Fonts/AppleSDGothicNeo.ttc")
CANVAS_W = 2400
CANVAS_H = 1350


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size, index=8 if bold else 0)


def centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font_obj, fill: str) -> None:
    draw.multiline_text(xy, text, fill=fill, font=font_obj, anchor="mm", align="center", spacing=6)


def wrapped_lines(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in text.split("\n"):
        current = ""
        for ch in raw_line:
            candidate = current + ch
            if draw.textlength(candidate, font=font_obj) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    top_y: int,
    text: str,
    font_obj,
    fill: str,
    max_width: int,
    spacing: int = 6,
) -> None:
    lines = wrapped_lines(draw, text, font_obj, max_width)
    y = top_y
    for line in lines:
        draw.text((center_x, y), line, fill=fill, font=font_obj, anchor="ma")
        y += font_obj.size + spacing


def arrow(draw: ImageDraw.ImageDraw, x: int, y: int, color: str = "#0b4ea2") -> None:
    draw.line((x, y, x + 42, y), fill=color, width=6)
    draw.polygon([(x + 42, y - 14), (x + 62, y), (x + 42, y + 14)], fill=color)


def icon_model_search(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
    draw.rounded_rectangle((cx - 52, cy - 36, cx + 38, cy + 42), radius=8, outline=color, width=4, fill="#eaf4ff")
    draw.arc((cx - 52, cy - 58, cx - 8, cy - 8), 180, 360, fill=color, width=4)
    draw.ellipse((cx + 12, cy + 18, cx + 78, cy + 84), outline=color, width=5)
    draw.line((cx + 62, cy + 68, cx + 102, cy + 108), fill=color, width=5)


def icon_select(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
    draw.rounded_rectangle((cx - 62, cy - 58, cx + 32, cy + 58), radius=8, outline=color, width=4, fill="#f8fbff")
    for i, label in enumerate(["1", "2", "3"]):
        y = cy - 34 + i * 36
        draw.text((cx - 42, y), label, fill=color, font=font(24, True), anchor="mm")
        draw.line((cx - 16, y, cx + 38, y), fill=color, width=5)
    draw.polygon([(cx + 28, cy + 8), (cx + 96, cy + 42), (cx + 62, cy + 58), (cx + 76, cy + 92)], fill=color)


def icon_template(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
    draw.rectangle((cx - 70, cy - 46, cx - 18, cy + 52), outline="#111827", width=3, fill="#ffffff")
    draw.polygon([(cx - 42, cy - 46), (cx - 18, cy - 22), (cx - 42, cy - 22)], outline="#111827", fill="#eef5ff")
    draw.line((cx - 58, cy + 2, cx - 32, cy + 2), fill="#111827", width=2)
    draw.line((cx - 58, cy + 22, cx - 32, cy + 22), fill="#111827", width=2)
    draw.polygon([(cx - 6, cy - 10), (cx + 24, cy + 12), (cx - 6, cy + 34)], fill=color)
    draw.rectangle((cx + 42, cy - 46, cx + 94, cy + 52), outline="#111827", width=3, fill="#ffffff")
    draw.text((cx + 68, cy + 4), "</>", fill=color, font=font(24, True), anchor="mm")


def icon_requirements(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
    draw.rounded_rectangle((cx - 72, cy - 64, cx + 72, cy + 68), radius=10, outline="#111827", width=4, fill="#f8fbff")
    draw.rounded_rectangle((cx - 26, cy - 82, cx + 26, cy - 54), radius=10, outline="#111827", width=4, fill="#dbeafe")
    for i in range(3):
        y = cy - 28 + i * 38
        draw.line((cx - 42, y, cx - 24, y + 18), fill=color, width=5)
        draw.line((cx - 24, y + 18, cx - 4, y - 12), fill=color, width=5)
        draw.line((cx + 14, y, cx + 52, y), fill="#111827", width=3)
    draw.ellipse((cx + 50, cy + 34, cx + 106, cy + 90), outline=color, width=5, fill="#ffffff")
    draw.line((cx + 78, cy + 44, cx + 78, cy + 80), fill=color, width=4)
    draw.line((cx + 60, cy + 62, cx + 96, cy + 62), fill=color, width=4)


def icon_inference(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
    draw.rounded_rectangle((cx - 82, cy - 54, cx + 82, cy + 52), radius=8, outline=color, width=5, fill="#f8fff8")
    draw.rectangle((cx - 24, cy + 52, cx + 24, cy + 78), fill="#f8fff8", outline=color, width=4)
    draw.line((cx - 48, cy + 82, cx + 48, cy + 82), fill=color, width=5)
    draw.ellipse((cx - 38, cy - 34, cx + 38, cy + 42), outline=color, width=4)
    draw.line((cx - 20, cy + 2, cx - 4, cy + 18), fill=color, width=6)
    draw.line((cx - 4, cy + 18, cx + 26, cy - 16), fill=color, width=6)


def icon_mlflow(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
    draw.ellipse((cx - 74, cy - 28, cx + 22, cy + 54), outline="#111827", width=4, fill="#ffffff")
    draw.ellipse((cx - 30, cy - 52, cx + 70, cy + 34), outline="#111827", width=4, fill="#ffffff")
    draw.rectangle((cx - 58, cy - 16, cx + 88, cy + 54), fill="#ffffff")
    draw.text((cx + 8, cy + 8), "mlflow", fill=color, font=font(34, True), anchor="mm")
    draw.polygon([(cx, cy + 88), (cx + 24, cy + 52), (cx - 24, cy + 52)], fill=color)
    draw.rectangle((cx - 8, cy + 50, cx + 8, cy + 88), fill=color)


def icon_retry(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str) -> None:
    draw.arc((cx - 76, cy - 72, cx + 76, cy + 72), 20, 165, fill=color, width=7)
    draw.arc((cx - 76, cy - 72, cx + 76, cy + 72), 205, 345, fill=color, width=7)
    draw.polygon([(cx + 72, cy - 40), (cx + 82, cy - 92), (cx + 32, cy - 74)], fill=color)
    draw.polygon([(cx - 72, cy + 40), (cx - 82, cy + 92), (cx - 32, cy + 74)], fill=color)
    draw.line((cx - 28, cy + 42, cx + 32, cy - 18), fill="#111827", width=9)
    draw.line((cx + 6, cy - 44, cx + 44, cy - 6), fill="#111827", width=9)
    draw.line((cx - 44, cy + 6, cx - 6, cy + 44), fill="#111827", width=9)


def draw_card(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    number: str,
    title: str,
    icon_name: str,
    footer: str,
    accent: str,
) -> None:
    shadow = "#d8e2f1" if accent != "#258326" else "#d9ecd9"
    draw.rounded_rectangle((x + 10, y + 12, x + w + 10, y + h + 12), radius=22, fill=shadow)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=22, fill="#fbfdff", outline=accent, width=3)
    draw.ellipse((x + w // 2 - 36, y + 28, x + w // 2 + 36, y + 100), fill=accent)
    centered(draw, (x + w // 2, y + 64), number, font(42, True), "#ffffff")
    centered(draw, (x + w // 2, y + 166), title, font(30, True), "#111827")
    dash_y = y + 238
    for dx in range(x + 32, x + w - 32, 16):
        draw.line((dx, dash_y, dx + 7, dash_y), fill=accent, width=3)
    icon_cx, icon_cy = x + w // 2, y + 420
    {
        "search": icon_model_search,
        "select": icon_select,
        "template": icon_template,
        "requirements": icon_requirements,
        "mlflow": icon_mlflow,
        "inference": icon_inference,
        "retry": icon_retry,
    }[icon_name](draw, icon_cx, icon_cy, accent)
    draw_text_block(draw, x + w // 2, y + h - 135, footer, font(28), "#111827", w - 42, spacing=7)


def draw_process(path: Path, bottom_text: str) -> None:
    image = Image.new("RGB", (CANVAS_W, CANVAS_H), "#f7f9fc")
    draw = ImageDraw.Draw(image)

    blue = "#0b4ea2"
    green = "#258326"
    navy = "#06172f"

    centered(draw, (CANVAS_W // 2, 106), "AI Studio 프로세스", font(96, True), navy)
    centered(draw, (CANVAS_W // 2, 190), "모델 선택부터 원격 등록, 추론 테스트까지 7단계 흐름", font(34), "#43536a")
    draw.line((120, 250, 1070, 250), fill=blue, width=4)
    draw.line((1330, 250, CANVAS_W - 120, 250), fill=blue, width=4)
    draw.rounded_rectangle((1085, 239, 1315, 261), radius=10, fill=blue)

    cards = [
        ("1", "모델 목록 확인", "search", "프로젝트 루트\n+ data/** 검색", blue),
        ("2", "모델 선택", "select", "번호 또는\n경로 선택", blue),
        ("3", "환경변수\nrequirements 갱신", "requirements", "MLflow 입력값,\n패키지 갱신", blue),
        ("4", "템플릿 변환", "template", "템플릿 복사,\n연결부 수정", blue),
        ("5", "원격 MLflow\n등록 실행", "mlflow", "runtest_2.py\n실행", blue),
        ("6", "추론 테스트", "inference", "추론 테스트\n실행", green),
        ("7", "오류 재실행", "retry", "실패 단계부터\n다시 실행", green),
    ]

    card_w, card_h = 282, 720
    gap = 28
    total_w = card_w * len(cards) + gap * (len(cards) - 1)
    x = (CANVAS_W - total_w) // 2
    y = 330
    for idx, card in enumerate(cards):
        draw_card(draw, x, y, card_w, card_h, *card)
        if idx < len(cards) - 1:
            arrow(draw, x + card_w + 8, y + card_h // 2)
        x += card_w + gap

    draw.rounded_rectangle((120, 1168, CANVAS_W - 120, 1268), radius=22, fill="#ffffff", outline=blue, width=3)
    centered(draw, (CANVAS_W // 2, 1218), bottom_text, font(42, True), blue)

    image.save(path)


def main() -> None:
    draw_process(PROCESS_IMAGE, "모델 검색  →  선택  →  갱신  →  변환  →  등록  →  테스트  →  재실행")
    draw_process(WORKFLOW_IMAGE, "모델 선택  →  환경 갱신  →  템플릿 변환  →  등록 실행  →  추론 테스트")
    print(PROCESS_IMAGE)
    print(WORKFLOW_IMAGE)


if __name__ == "__main__":
    main()
