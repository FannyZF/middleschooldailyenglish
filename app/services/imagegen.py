from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import settings

W, H = 1080, 1440
MARGIN = 90
CONTENT_RIGHT = W - MARGIN
CONTENT_WIDTH = W - MARGIN * 2

HEADER_H = 120
TOP_PAD = 55
FOOTER_H = 110
AVAILABLE = H - HEADER_H - TOP_PAD - FOOTER_H

BG = "#FDFBF6"
CARD = "#FFFFFF"
ACCENT = "#2563EB"
ACCENT_LIGHT = "#DBEAFE"
GOLD = "#F59E0B"
INK = "#111827"
BODY = "#334155"
MUTED = "#64748B"
LINE = "#E5E7EB"
WHITE = "#FFFFFF"

DEFAULT_FOOTER = "每日英语 · Daily English"
SLANG_FOOTER = "Slang Lab | 每天一个地道Slang"
REGULAR = "NotoSansCJKsc-Regular"
BOLD = "NotoSansCJKsc-Bold"
# 含完整 IPA 音标符号的拉丁字体（Noto Sans CJK 缺少部分音标字符）
NOTO_LATIN = "NotoSans-Var"

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for ext in (".otf", ".ttf"):
        p = settings.font_dir / f"{name}{ext}"
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise FileNotFoundError(f"字体未找到: {name}.otf/.ttf 位于 {settings.font_dir}")


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    size = max(size, 1)
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = _load_font(name, size)
    return _font_cache[key]


def _s(size: int, scale: float) -> int:
    return max(int(round(size * scale)), 1)


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch.isascii():
            if ch.isalnum():
                buf.append(ch)
            else:
                if buf:
                    tokens.append("".join(buf))
                    buf = []
                tokens.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        tokens = _tokenize(para)
        line = ""
        for tok in tokens:
            if line and draw.textlength(line + tok, font=font) > max_width:
                lines.append(line.rstrip())
                line = "" if tok == " " else tok
            else:
                line += tok
        lines.append(line.rstrip())
    return lines


def _line_height(font) -> int:
    asc, desc = font.getmetrics()
    return int((asc + desc) * 1.45)


# ---- header / footer ----

def _draw_header(draw: ImageDraw.ImageDraw, title: str) -> None:
    draw.rectangle([0, 0, W, HEADER_H], fill=ACCENT)
    brand = _font(BOLD, 38)
    draw.text((MARGIN, 40), title, font=brand, fill=WHITE)


def _draw_footer(draw: ImageDraw.ImageDraw, footer: str = DEFAULT_FOOTER) -> None:
    font = _font(REGULAR, 26)
    tw = draw.textlength(footer, font=font)
    draw.text(((W - tw) / 2, H - 62), footer, font=font, fill=MUTED)


# ---- block height / draw ----

def _block_height(b: dict, draw: ImageDraw.ImageDraw, scale: float) -> int:
    kind = b["kind"]
    if kind == "heading":
        return _line_height(_font(BOLD, _s(52, scale))) + 6 + 8 + 30
    if kind == "title":
        f = _font(BOLD, _s(46, scale))
        return len(wrap_text(draw, b["text"], f, CONTENT_WIDTH)) * _line_height(f) + 20
    if kind == "label":
        return _line_height(_font(BOLD, _s(34, scale))) + 12
    if kind == "para":
        size = _s(b.get("size", 40), scale)
        f = _font(BOLD if b.get("bold") else REGULAR, size)
        lines = wrap_text(draw, b["text"], f, CONTENT_WIDTH)
        return len(lines) * _line_height(f) + b.get("gap", 18)
    if kind == "word":
        return _line_height(_font(BOLD, _s(96, scale))) + 8
    if kind == "meta":
        f = _font(NOTO_LATIN, _s(34, scale))
        return len(wrap_text(draw, b["text"], f, CONTENT_WIDTH)) * _line_height(f) + 20
    if kind == "grade":
        f = _font(BOLD, _s(32, scale))
        return _line_height(f) + 16 + 20
    if kind == "divider":
        return 24
    if kind == "space":
        return b["px"]
    if kind == "options":
        f = _font(REGULAR, _s(38, scale))
        letters = ["A", "B", "C", "D"]
        total = 0
        for i, opt in enumerate(b["options"]):
            text = f"{letters[i]}. {opt}"
            total += len(wrap_text(draw, text, f, CONTENT_WIDTH)) * _line_height(f) + 8
        return total + 6
    if kind == "definition":
        return _card_height(b["data"], draw, scale) + 24
    return 0


def _draw_block(draw: ImageDraw.ImageDraw, b: dict, scale: float, y: int) -> int:
    h = _block_height(b, draw, scale)
    kind = b["kind"]

    if kind == "heading":
        font = _font(BOLD, _s(52, scale))
        draw.text((MARGIN, y), b["text"], font=font, fill=INK)
        ul_y = y + _line_height(font) + 6
        draw.rectangle([MARGIN, ul_y, MARGIN + 120, ul_y + 8], fill=GOLD)

    elif kind == "title":
        font = _font(BOLD, _s(46, scale))
        cy = y
        for line in wrap_text(draw, b["text"], font, CONTENT_WIDTH):
            draw.text((MARGIN, cy), line, font=font, fill=INK)
            cy += _line_height(font)

    elif kind == "label":
        font = _font(BOLD, _s(34, scale))
        draw.text((MARGIN, y), b["text"], font=font, fill=ACCENT)

    elif kind == "para":
        size = _s(b.get("size", 40), scale)
        font = _font(BOLD if b.get("bold") else REGULAR, size)
        color = b.get("color", BODY)
        cy = y
        for line in wrap_text(draw, b["text"], font, CONTENT_WIDTH):
            draw.text((MARGIN, cy), line, font=font, fill=color)
            cy += _line_height(font)

    elif kind == "word":
        font = _font(BOLD, _s(96, scale))
        draw.text((MARGIN, y), b["text"], font=font, fill=ACCENT)

    elif kind == "meta":
        font = _font(NOTO_LATIN, _s(34, scale))
        cy = y
        for line in wrap_text(draw, b["text"], font, CONTENT_WIDTH):
            draw.text((MARGIN, cy), line, font=font, fill=MUTED)
            cy += _line_height(font)

    elif kind == "grade":
        font = _font(BOLD, _s(32, scale))
        text = b["text"]
        tw = draw.textlength(text, font=font)
        lh = _line_height(font)
        draw.rounded_rectangle(
            [MARGIN, y, MARGIN + tw + 40, y + lh + 16], radius=(lh + 16) // 2, fill=ACCENT_LIGHT
        )
        draw.text((MARGIN + 20, y + 8), text, font=font, fill=ACCENT)

    elif kind == "divider":
        draw.line([MARGIN, y, CONTENT_RIGHT, y], fill=LINE, width=2)

    elif kind == "space":
        pass

    elif kind == "options":
        font = _font(REGULAR, _s(38, scale))
        letters = ["A", "B", "C", "D"]
        cy = y
        for i, opt in enumerate(b["options"]):
            text = f"{letters[i]}. {opt}"
            for line in wrap_text(draw, text, font, CONTENT_WIDTH):
                draw.text((MARGIN, cy), line, font=font, fill=BODY)
                cy += _line_height(font)
            cy += 8

    elif kind == "definition":
        _draw_card(draw, b["data"], scale, y)

    return y + h


# ---- definition card ----

def _card_fonts(scale: float):
    return {
        "label": _font(BOLD, _s(36, scale)),
        "zh": _font(REGULAR, _s(38, scale)),
        "en": _font(REGULAR, _s(32, scale)),
        "ex": _font(REGULAR, _s(38, scale)),
        "ex_zh": _font(REGULAR, _s(32, scale)),
    }


def _card_height(d: dict, draw: ImageDraw.ImageDraw, scale: float) -> int:
    pad_x, pad_y = 34, 28
    inner_w = CONTENT_WIDTH - pad_x * 2
    f = _card_fonts(scale)

    zh_lines = wrap_text(draw, d.get("meaning_zh", ""), f["zh"], inner_w)
    en_lines = wrap_text(draw, "EN: " + d.get("meaning_en", ""), f["en"], inner_w)
    ex_lines = wrap_text(draw, d.get("example_en", ""), f["ex"], inner_w)
    ex_zh_lines = wrap_text(draw, "译: " + d.get("example_zh", ""), f["ex_zh"], inner_w)

    return (
        pad_y * 2
        + _line_height(f["label"])
        + len(zh_lines) * _line_height(f["zh"])
        + len(en_lines) * _line_height(f["en"])
        + 8
        + len(ex_lines) * _line_height(f["ex"])
        + len(ex_zh_lines) * _line_height(f["ex_zh"])
        + 6
    )


def _draw_card(draw: ImageDraw.ImageDraw, d: dict, scale: float, y: int) -> None:
    pad_x, pad_y = 34, 28
    inner_w = CONTENT_WIDTH - pad_x * 2
    f = _card_fonts(scale)
    h = _card_height(d, draw, scale)

    draw.rounded_rectangle(
        [MARGIN, y, CONTENT_RIGHT, y + h], radius=18, fill=CARD, outline=LINE, width=2
    )

    cy = y + pad_y
    draw.text((MARGIN + pad_x, cy), f"释义 {d.get('index', '')}", font=f["label"], fill=ACCENT)
    cy += _line_height(f["label"])

    for line in wrap_text(draw, d.get("meaning_zh", ""), f["zh"], inner_w):
        draw.text((MARGIN + pad_x, cy), line, font=f["zh"], fill=INK)
        cy += _line_height(f["zh"])
    for line in wrap_text(draw, "EN: " + d.get("meaning_en", ""), f["en"], inner_w):
        draw.text((MARGIN + pad_x, cy), line, font=f["en"], fill=MUTED)
        cy += _line_height(f["en"])

    cy += 8
    for line in wrap_text(draw, d.get("example_en", ""), f["ex"], inner_w):
        draw.text((MARGIN + pad_x, cy), line, font=f["ex"], fill=BODY)
        cy += _line_height(f["ex"])
    for line in wrap_text(draw, "译: " + d.get("example_zh", ""), f["ex_zh"], inner_w):
        draw.text((MARGIN + pad_x, cy), line, font=f["ex_zh"], fill=MUTED)
        cy += _line_height(f["ex_zh"])


# ---- page engine ----

def _render_blocks(blocks: list[dict], path: Path, header_title: str, footer: str = DEFAULT_FOOTER) -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    total = sum(_block_height(b, draw, 1.0) for b in blocks)
    scale = 1.0 if total <= AVAILABLE else max(AVAILABLE / total, 0.3)

    _draw_header(draw, header_title)
    y = HEADER_H + TOP_PAD
    for b in blocks:
        y = _draw_block(draw, b, scale, y)
    _draw_footer(draw, footer)
    img.save(path)


def _choice_answer_text(choice) -> str:
    ans = (choice.answer or "").strip().upper()
    if len(ans) == 1 and "A" <= ans <= "D":
        idx = ord(ans) - ord("A")
        if 0 <= idx < len(choice.options):
            return f"{ans}. {choice.options[idx]}"
    return choice.answer or ""


# ---- page builders ----

def _render_news(content, out_dir: Path) -> None:
    source_parts = [content.source_name or "网络媒体"]
    if content.pub_date:
        source_parts.append(content.pub_date)
    blocks = [
        {"kind": "heading", "text": content.category or "今日热点"},
        {"kind": "title", "text": content.title},
        {"kind": "divider"},
        {"kind": "label", "text": "英文摘要 Summary"},
        {"kind": "para", "text": content.summary_en},
        {"kind": "label", "text": "中文翻译 Translation"},
        {"kind": "para", "text": content.summary_zh},
        {"kind": "divider"},
        {"kind": "para", "text": "来源：" + " · ".join(source_parts), "size": 28, "color": MUTED, "gap": 8},
    ]
    if content.original_title:
        blocks.append(
            {"kind": "para", "text": f"原标题：{content.original_title}", "size": 28, "color": MUTED, "gap": 0}
        )
    _render_blocks(blocks, out_dir / "01.png", "今日新闻 · News")


def _render_word(content, out_dir: Path) -> None:
    blocks = [
        {"kind": "heading", "text": "今日核心词"},
        {"kind": "word", "text": content.word},
    ]
    meta = " ".join(x for x in [content.word_pos, content.word_phonetic] if x)
    if meta:
        blocks.append({"kind": "meta", "text": meta})
    if content.word_grade:
        blocks.append({"kind": "grade", "text": f"课本年级：{content.word_grade}"})
    blocks.append({"kind": "divider"})
    for i, d in enumerate(content.definitions, start=1):
        data = d.model_dump()
        data["index"] = i
        blocks.append({"kind": "definition", "data": data})
    _render_blocks(blocks, out_dir / "02.png", "今日核心词 · Word")


def _render_questions(content, out_dir: Path) -> None:
    blocks = [
        {"kind": "heading", "text": "每日练习"},
    ]
    for i, ch in enumerate(content.choices, start=1):
        blocks.append(
            {"kind": "label", "text": f"{'一二三'[i - 1]}、选词填空 Choose the correct word"}
        )
        blocks.append({"kind": "para", "text": ch.question, "color": INK, "bold": True})
        blocks.append({"kind": "options", "options": ch.options})
        blocks.append({"kind": "divider"})
    blocks.append({"kind": "label", "text": "三、翻译题 Translate into English"})
    blocks.append({"kind": "para", "text": content.translation.question, "color": INK, "bold": True})
    blocks.append({"kind": "space", "px": 12})
    blocks.append({"kind": "para", "text": "提示：答案见第 4 张图片", "size": 32, "color": MUTED})
    _render_blocks(blocks, out_dir / "03.png", "每日练习 · Practice")


def _render_answers(content, out_dir: Path) -> None:
    blocks = [
        {"kind": "heading", "text": "参考答案"},
    ]
    for i, ch in enumerate(content.choices, start=1):
        blocks.append({"kind": "label", "text": f"{'一二三'[i - 1]}、选词填空答案"})
        blocks.append({"kind": "para", "text": _choice_answer_text(ch), "color": INK, "bold": True})
        blocks.append({"kind": "divider"})
    blocks.append({"kind": "label", "text": "三、翻译参考"})
    blocks.append({"kind": "para", "text": content.translation.answer, "color": BODY})
    blocks.append({"kind": "divider"})
    blocks.append({"kind": "label", "text": "核心词回顾"})
    zh_means = "；".join(d.meaning_zh for d in content.definitions if d.meaning_zh)
    blocks.append({"kind": "para", "text": f"{content.word}：{zh_means}", "color": BODY})
    _render_blocks(blocks, out_dir / "04.png", "参考答案 · Answer")


def render_all(content, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _render_news(content, out_dir)
    _render_word(content, out_dir)
    _render_questions(content, out_dir)
    _render_answers(content, out_dir)


# ---- 俚语模块 ----

def _render_slang_main(content, out_dir: Path) -> None:
    blocks = [
        {"kind": "heading", "text": "今日地道俚语"},
        {"kind": "word", "text": content.slang},
    ]
    if content.phonetic:
        blocks.append({"kind": "meta", "text": content.phonetic})
    blocks.append({"kind": "divider"})
    blocks.append({"kind": "label", "text": "释义 Meaning"})
    blocks.append({"kind": "para", "text": content.meaning_en, "color": BODY})
    blocks.append({"kind": "para", "text": content.meaning_zh, "color": INK, "bold": True})
    blocks.append({"kind": "divider"})
    if content.source:
        blocks.append(
            {"kind": "para", "text": f"来源：{content.source}", "size": 28, "color": MUTED, "gap": 0}
        )
    _render_blocks(blocks, out_dir / "01.png", "地道俚语 · Slang", footer=SLANG_FOOTER)


def _render_slang_usage(content, out_dir: Path) -> None:
    blocks = [
        {"kind": "heading", "text": "用法与例句"},
        {"kind": "label", "text": "用法说明 Usage"},
        {"kind": "para", "text": content.usage},
        {"kind": "divider"},
    ]
    for i, ex in enumerate(content.examples, start=1):
        blocks.append({"kind": "label", "text": f"例句 {i}"})
        blocks.append({"kind": "para", "text": ex.en, "color": INK})
        blocks.append({"kind": "para", "text": ex.zh, "color": MUTED})
        if i < len(content.examples):
            blocks.append({"kind": "divider"})
    _render_blocks(blocks, out_dir / "02.png", "用法与例句 · Usage", footer=SLANG_FOOTER)


def _render_slang_scenarios(content, out_dir: Path) -> None:
    blocks = [
        {"kind": "heading", "text": "使用场景"},
    ]
    for i, sc in enumerate(content.scenarios, start=1):
        blocks.append({"kind": "label", "text": f"场景 {i} · {sc.title}"})
        blocks.append({"kind": "para", "text": sc.dialogue_en, "color": INK, "size": 36})
        blocks.append({"kind": "para", "text": sc.dialogue_zh, "color": MUTED, "size": 32})
        if i < len(content.scenarios):
            blocks.append({"kind": "divider"})
    _render_blocks(blocks, out_dir / "03.png", "使用场景 · Scenarios", footer=SLANG_FOOTER)


def render_slang_all(content, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _render_slang_main(content, out_dir)
    _render_slang_usage(content, out_dir)
    _render_slang_scenarios(content, out_dir)
