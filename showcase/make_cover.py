"""Обложки для GameBanana, три стиля на выбор.

python showcase/make_cover.py            -> showcase/cover_A_clean.png, cover_B_plate.png, cover_C_noir.png (1000x1000)
python showcase/make_cover.py B wide     -> showcase/cover.png 1920x1080 в выбранном стиле (A/B/C)

Исходники: showcase/src/screenshot_gold_queen.png (скрин из игры), showcase/src/bar_red.png / bar_normal.png
(панель способностей в момент вспышки и обычная).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = Path(__file__).parent
SRC = HERE / "src"
F = Path(r"C:\Windows\Fonts")

TITLE = "Don't Forget Your Pieces"
KICKER = "SOLOMON  ·  HUD MOD"
SUB = "Icon blinks red after 15 s of an unused piece.  Gold Queen, silver pieces."
CREAM = (246, 236, 214)
GOLD = (222, 180, 92)
RED = (236, 72, 64)
INK = (16, 12, 11)


def font(name, size):
    return ImageFont.truetype(str(F / name), size)


def fit_cover(im, w, h, focus=(0.5, 0.5)):
    """Вписать с обрезкой, точка интереса focus (доли ширины/высоты исходника) по возможности в центре."""
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = min(max(round(im.width * focus[0] - w / 2), 0), im.width - w)
    y = min(max(round(im.height * focus[1] - h / 2), 0), im.height - h)
    return im.crop((x, y, x + w, y + h))


def vignette(im, strength=0.55, bottom=0.0):
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-w * 0.25, -h * 0.25, w * 1.25, h * 1.25), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(w * 0.18))
    dark = Image.new("RGB", (w, h), INK)
    out = Image.composite(im, dark, mask.point(lambda v: 255 - int((255 - v) * strength)))
    if bottom:
        g = Image.new("L", (1, h))
        for y in range(h):
            t = max(0.0, (y / h - (1 - bottom)) / bottom)
            g.putpixel((0, y), int(235 * t ** 1.6))
        out = Image.composite(dark, out, g.resize((w, h)))
    return out


def fit_font(d, text, name, size, max_w):
    """Уменьшать кегль, пока текст не влезет в max_w."""
    while size > 20 and d.textlength(text, font=font(name, size)) > max_w:
        size -= 2
    return font(name, size)


def spaced(d, xy, text, fnt, fill, tracking=0, anchor_center=False, width=None):
    """Текст с разрядкой букв. anchor_center: центрировать по width."""
    total = sum(d.textlength(c, font=fnt) for c in text) + tracking * (len(text) - 1)
    x, y = xy
    if anchor_center and width:
        x = x + (width - total) / 2
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill)
        x += d.textlength(c, font=fnt) + tracking
    return total


def bars_strip(width, gap_label=True):
    """Полоска «обычная панель -> мигающая» для вставки, ширина width."""
    a = Image.open(SRC / "bar_normal.png").convert("RGB")
    b = Image.open(SRC / "bar_red.png").convert("RGB")
    bw = (width - 24) // 2
    bh = round(a.height * bw / a.width)
    strip = Image.new("RGB", (width, bh), INK)
    strip.paste(a.resize((bw, bh), Image.LANCZOS), (0, 0))
    strip.paste(b.resize((bw, bh), Image.LANCZOS), (width - bw, 0))
    d = ImageDraw.Draw(strip)
    d.rectangle((0, 0, bw - 1, bh - 1), outline=(70, 60, 55), width=2)
    d.rectangle((width - bw, 0, width - 1, bh - 1), outline=RED, width=3)
    if gap_label:
        fx = font("segoeuib.ttf", max(14, bh // 7))
        d.text((bw + 12, bh / 2), "›", font=font("georgiab.ttf", bh // 2), fill=GOLD, anchor="lm")
    return strip


# --- стиль A: чисто, скрин во всю обложку, строгая серифная типографика внизу слева -----------------
def style_a(w, h):
    im = fit_cover(Image.open(SRC / "screenshot_gold_queen.png").convert("RGB"), w, h, focus=(0.47, 0.42))
    im = vignette(im, strength=0.35, bottom=0.46)
    d = ImageDraw.Draw(im)
    k = h / 1000
    pad = int(60 * k)
    y = h - pad - int(250 * k)
    spaced(d, (pad, y), KICKER, font("bahnschrift.ttf", int(26 * k)), GOLD, tracking=int(5 * k))
    y += int(48 * k)
    tf = fit_font(d, TITLE, "georgiab.ttf", int(86 * k), w - 2 * pad)
    d.text((pad, y), TITLE, font=tf, fill=CREAM)
    y += int(tf.size * 1.3)
    d.line((pad, y, pad + int(120 * k), y), fill=GOLD, width=max(2, int(3 * k)))
    y += int(22 * k)
    d.text((pad, y), SUB, font=font("segoeui.ttf", int(27 * k)), fill=(214, 206, 192))
    return im


# --- стиль B: скрин сверху, тёмная плашка снизу с заголовком и панелью «до -> после» ----------------
def style_b(w, h):
    k = h / 1000
    plate_h = int(h * 0.36)
    im = Image.new("RGB", (w, h), INK)
    top = fit_cover(Image.open(SRC / "screenshot_gold_queen.png").convert("RGB"), w, h - plate_h, focus=(0.42, 0.52))
    top = vignette(top, strength=0.3)
    im.paste(top, (0, 0))
    d = ImageDraw.Draw(im)
    # тонкая золотая линия-разделитель
    d.rectangle((0, h - plate_h, w, h - plate_h + max(2, int(3 * k))), fill=GOLD)
    pad = int(56 * k)
    y = h - plate_h + int(34 * k)
    spaced(d, (pad, y), KICKER, font("bahnschrift.ttf", int(24 * k)), GOLD, tracking=int(5 * k))
    y += int(40 * k)
    tf = fit_font(d, TITLE, "georgiab.ttf", int(74 * k), w - 2 * pad)
    d.text((pad, y), TITLE, font=tf, fill=CREAM)
    y += int(tf.size * 1.35)
    d.text((pad, y), SUB, font=font("segoeui.ttf", int(25 * k)), fill=(200, 192, 178))
    y += int(50 * k)
    strip = bars_strip(w - 2 * pad)
    room = h - pad // 2 - y
    if strip.height > room:
        strip = strip.resize((round(strip.width * room / strip.height), room), Image.LANCZOS)
    im.paste(strip, (pad, y))
    return im


# --- стиль C: нуар-постер, тёплый приглушённый кадр, заголовок по центру, фигурка ферзя --------------
def style_c(w, h):
    k = h / 1000
    im = fit_cover(Image.open(SRC / "screenshot_gold_queen.png").convert("RGB"), w, h, focus=(0.42, 0.45))
    im = ImageEnhance.Color(im).enhance(0.72)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = vignette(im, strength=0.7, bottom=0.3)
    d = ImageDraw.Draw(im)
    # рамка в один пиксель с отступом - как у афиши
    m = int(28 * k)
    d.rectangle((m, m, w - m - 1, h - m - 1), outline=GOLD + (0,), width=max(1, int(2 * k)))
    # ферзь-символ и заголовок сверху по центру
    glyph_font = font("seguisym.ttf", int(110 * k)) if (F / "seguisym.ttf").exists() else font("georgiab.ttf", int(110 * k))
    d.text((w / 2, int(120 * k)), "\u265B", font=glyph_font, fill=GOLD, anchor="mm")
    spaced(d, (0, int(190 * k)), KICKER, font("bahnschrift.ttf", int(24 * k)), GOLD, tracking=int(6 * k), anchor_center=True, width=w)
    tf = fit_font(d, TITLE, "georgiab.ttf", int(80 * k), w - 2 * int(90 * k))
    d.text((w / 2, int(275 * k)), TITLE, font=tf, fill=CREAM, anchor="mm")
    # снизу - подпись и панель-вспышка
    d.text((w / 2, h - int(205 * k)), SUB, font=font("segoeui.ttf", int(25 * k)), fill=(214, 206, 192), anchor="mm")
    strip = bars_strip(int(w * 0.62))
    im.paste(strip, ((w - strip.width) // 2, h - int(170 * k)))
    return im


# --- стиль D: золото и корона как в C, но весь текст на тёмных плашках с золотой рамкой ---------------
def panel(im, box, alpha=215, radius=18, border=GOLD, bw=2):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius, fill=INK + (alpha,))
    out = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    ImageDraw.Draw(out).rounded_rectangle(box, radius, outline=border, width=bw)
    return out


def style_d(w, h):
    k = h / 1000
    im = fit_cover(Image.open(SRC / "screenshot_gold_queen.png").convert("RGB"), w, h, focus=(0.42, 0.5))
    im = ImageEnhance.Color(im).enhance(0.85)
    im = vignette(im, strength=0.5)
    m = int(36 * k)
    # верхняя плашка: корона + кикер + заголовок
    top_h = int(300 * k)
    im = panel(im, (m, m, w - m - 1, m + top_h), alpha=222, radius=int(16 * k), bw=max(2, int(2 * k)))
    d = ImageDraw.Draw(im)
    glyph_font = font("seguisym.ttf", int(96 * k))
    d.text((w / 2, m + int(72 * k)), "♛", font=glyph_font, fill=GOLD, anchor="mm")
    spaced(d, (0, m + int(128 * k)), KICKER, font("bahnschrift.ttf", int(22 * k)), GOLD, tracking=int(6 * k), anchor_center=True, width=w)
    tf = fit_font(d, TITLE, "georgiab.ttf", int(78 * k), w - 2 * m - int(60 * k))
    d.text((w / 2, m + int(215 * k)), TITLE, font=tf, fill=CREAM, anchor="mm")
    # нижняя плашка: подпись + панель «до -> после»
    strip = bars_strip(min(w - 2 * m - int(60 * k), int(900 * k)))
    bot_h = strip.height + int(118 * k)
    im = panel(im, (m, h - m - bot_h, w - m - 1, h - m - 1), alpha=222, radius=int(16 * k), bw=max(2, int(2 * k)))
    d = ImageDraw.Draw(im)
    d.text((w / 2, h - m - bot_h + int(36 * k)), SUB, font=fit_font(d, SUB, "segoeui.ttf", int(26 * k), w - 2 * m - int(60 * k)), fill=CREAM, anchor="mm")
    im.paste(strip, ((w - strip.width) // 2, h - m - strip.height - int(44 * k)))
    # подписи под панелями
    lf = font("bahnschrift.ttf", int(18 * k))
    half = strip.width // 2
    sx = (w - strip.width) // 2
    sy = h - m - int(36 * k)
    spaced(d, (sx, sy), "JUST PLACED", lf, (170, 160, 148), tracking=int(3 * k), anchor_center=True, width=half - 12)
    spaced(d, (sx + half + 12, sy), "15 SECONDS LATER", lf, RED, tracking=int(3 * k), anchor_center=True, width=half - 12)
    return im


# --- стиль E: как заставка OP Stamina - размытый тёмный фон, плотный заголовок слева, большая пиктограмма справа
def bahn(size, variation="Bold Condensed"):
    f = font("bahnschrift.ttf", size)
    f.set_variation_by_name(variation)
    return f


def big_icon(size, bg, glyph_fill, glow=None, label="4", faded=False, glyph="icon_undoqueen.png"):
    """Иконка способности как в HUD игры: плоский цветной круг, настоящий глиф способности (из pak01,
    panorama/images/hud/abilities/chess/*), окрашенный в чёрный, и бирка с номером снизу."""
    S = size * 2  # рисуем вдвое крупнее и уменьшаем - ровные края
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = int(S * 0.27)                 # круг заметно меньше холста: ореолу есть куда затухать, без обрезки
    cx, cy = S // 2, int(S * 0.46)
    if glow:
        g = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((cx - r * 1.18, cy - r * 1.18, cx + r * 1.18, cy + r * 1.18), fill=glow + (150,))
        im = Image.alpha_composite(im, g.filter(ImageFilter.GaussianBlur(S * 0.05)))
        d = ImageDraw.Draw(im)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg + (255,))
    # глиф: альфа из игрового PNG, цвет - заливка
    src = Image.open(SRC / glyph).convert("RGBA")
    gs = int(r * 1.45)
    alpha = src.split()[3].resize((gs, gs), Image.LANCZOS)
    layer = Image.new("RGBA", (gs, gs), glyph_fill + (255,))
    layer.putalpha(alpha)
    im.alpha_composite(layer, (cx - gs // 2, cy - gs // 2))
    d = ImageDraw.Draw(im)
    # бирка с номером (как в HUD: скруглённый квадрат чуть темнее круга, тёмная цифра)
    tw = th = int(r * 0.46)
    tx, ty = cx - tw // 2, cy + r - int(th * 0.45)
    tag_fill = tuple(max(0, int(c * 0.92)) for c in bg)
    d.rounded_rectangle((tx, ty, tx + tw, ty + th), int(th * 0.22), fill=tag_fill + (255,))
    d.text((cx, ty + th // 2 + 1), label, font=bahn(int(th * 0.78), "Bold"), fill=(28, 20, 18, 255), anchor="mm")
    if faded:
        a = im.split()[3].point(lambda v: int(v * 0.55))
        im.putalpha(a)
    return im.resize((size, size), Image.LANCZOS)


def style_e(w, h):
    k = h / 1080
    square = w / h < 1.3
    bg = fit_cover(Image.open(SRC / "screenshot_gold_queen.png").convert("RGB"), w, h, focus=(0.42, 0.5))
    bg = bg.filter(ImageFilter.GaussianBlur(int(14 * k)))
    bg = ImageEnhance.Brightness(bg).enhance(0.38)
    bg = ImageEnhance.Color(bg).enhance(0.8)
    im = vignette(bg, strength=0.45)
    d = ImageDraw.Draw(im)
    x = int((90 if square else 120) * k)
    ts = int((150 if square else 174) * k)       # кегль заголовка
    # заголовок
    y = int((90 if square else 190) * k)
    d.text((x, y), "SOLOMON", font=bahn(int(ts * 0.5)), fill=GOLD)
    y += int(ts * 0.5)
    tf = bahn(ts)
    for line in ("DON'T FORGET", "YOUR PIECES"):
        d.text((x, y), line, font=tf, fill=(250, 246, 238))
        y += int(ts * 0.9)
    y += int(28 * k)
    sf = bahn(int(42 * k), "Bold SemiCondensed")
    d.text((x, y), "BLINKS AFTER 15 S  ·  RESETS WHEN YOU MOVE IT", font=fit_font_var(d, "BLINKS AFTER 15 S  ·  RESETS WHEN YOU MOVE IT", int(42 * k), w - 2 * x), fill=(236, 232, 224))
    y += int(62 * k)
    d.text((x, y), "GOLD QUEEN  ·  SILVER PIECES", font=sf, fill=GOLD)
    y += int(66 * k)
    d.text((x, y), "HUD only, no gameplay changes", font=bahn(int(30 * k), "SemiLight SemiCondensed"), fill=(150, 142, 132))
    # пиктограммы: обычная (приглушённая) -> мигающая (с красным свечением)
    big = int((440 if square else 540) * k)
    normal = big_icon(int(big * (0.78 if square else 0.7)), (242, 238, 230), (24, 20, 20), label="4", glyph="icon_queen.png")
    red = big_icon(big, (250, 72, 60), (40, 12, 12), glow=(250, 72, 60), label="4", glyph="icon_queen.png")
    gap = int((20 if square else 0) * k)
    arrow_w = int((70 if square else 50) * k)
    group_w = normal.width + gap + arrow_w + gap + big
    if square:
        gx = (w - group_w) // 2
        cy = h - int(40 * k) - big // 2 - int(90 * k)
    else:
        gx = w - int(40 * k) - group_w
        cy = int(h * 0.47)
    nx = gx
    im.paste(normal, (nx, cy - normal.height // 2), normal)
    rx = gx + group_w - big
    im.paste(red, (rx, cy - big // 2), red)
    d = ImageDraw.Draw(im)
    d.text((nx + normal.width + gap + arrow_w // 2, cy), "›", font=font("georgiab.ttf", int(90 * k)), fill=GOLD, anchor="mm")
    # подпись под большой иконкой с красной чертой
    cap = "15 S LATER: STILL OUT"
    cf = bahn(int(44 * k), "Bold SemiCondensed")
    cx = rx + big // 2 if not square else w // 2
    cy2 = cy + int(big * 0.38) + int(40 * k)
    d.text((cx, cy2), cap, font=cf, fill=(250, 246, 238), anchor="mm")
    d.line((cx - int(60 * k), cy2 + int(40 * k), cx + int(60 * k), cy2 + int(40 * k)), fill=RED, width=max(3, int(5 * k)))
    return im


def fit_font_var(d, text, size, max_w, variation="Bold SemiCondensed"):
    while size > 16 and d.textlength(text, font=bahn(size, variation)) > max_w:
        size -= 2
    return bahn(size, variation)


STYLES = {"A": style_a, "B": style_b, "C": style_c, "D": style_d, "E": style_e}

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        style = sys.argv[1].upper()
        if len(sys.argv) >= 3 and sys.argv[2] == "wide":
            STYLES[style](1920, 1080).save(HERE / "cover.png", quality=95)
            print("-> cover.png 1920x1080", style)
        STYLES[style](1000, 1000).save(HERE / "cover_square.png", quality=95)
        print("-> cover_square.png", style)
    else:
        for s, fn in STYLES.items():
            out = HERE / f"cover_{s}_{ {'A': 'clean', 'B': 'plate', 'C': 'noir', 'D': 'gold', 'E': 'poster'}[s] }.png"
            fn(1000, 1000).save(out, quality=95)
            print("->", out.name)
