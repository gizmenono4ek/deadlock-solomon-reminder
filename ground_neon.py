"""Неоновая разметка на полу у фигур Соломона.

Клетки вокруг слона (и предупреждающие клетки ферзя) рисуются партиклами через проецируемые декали
(C_OP_RenderProjected + projected_decals.vfx):
  - светлая клетка: materials/particle/projected/chessmaster_bishop_aura_ground_square_projected.vmat -
    это только тонкий контур квадрата (текстура chessmaster_square_board_edge: линия + мягкое гало),
    цвет даёт партикл (255,233,187), яркость - $SELFILLUM из альфы партикла (<= 1, поэтому тускло);
  - тёмная клетка: ..._dark_projected.vmat - залитый квадрат с рваным краем (chessmaster_square_glow_dark),
    цвет - градиент партикла золото -> почти чёрный.

Что делаем:
  1. Свои текстуры (PIL из родных масок): у светлой - контур толще и ярче, широкое гало, золото;
     у тёмной - тёмная заливка и светло-серая неоновая кромка по краю формы.
  2. Свои материалы с теми же параметрами, но g_flSelfIllumScale - константа (5 / 4) вместо $SELFILLUM,
     и золотой тинт у светлой. Компилирует resourcecompiler (CSDK 12), текстуры - из PNG.
  3. Партиклы: цвет светлой клетки -> насыщенное золото, градиент тёмной -> серый неон.

  python ground_neon.py stage    - текстуры + vmat + vpcf в аддон CSDK
  python ground_neon.py collect  - (из solomon_reminder.pack) скомпилированные vmat_c + vtex_c
"""
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))
CSDK = Path(os.environ.get("CSDK", r"C:\Users\Alexd\Downloads\Reduced_CSDK_12\Reduced_CSDK_12"))
ADDON = "solomonreminder"
CONTENT = CSDK / "content" / "citadel_addons" / ADDON
GAME = CSDK / "game" / "citadel_addons" / ADDON
EXTRACT = ROOT / "extract"
TEX_SRC = EXTRACT / "materials/particle/projected"
PARTICLES = "particles/abilities/chessmaster"
MAT_DIR = "materials/particle/projected"

ENABLED = True
GOLD = (255, 212, 96)          # цвет контура светлой клетки (текстура)
GOLD_TINT = (1.0, 0.86, 0.40)  # тинт материала светлой клетки
LIGHT_ILLUM = 5.0              # яркость свечения светлой клетки (у Valve <= 1)
DARK_FILL = (34, 34, 40)       # заливка тёмной клетки
DARK_EDGE = (222, 228, 240)    # серый неон по краю тёмной клетки
DARK_ILLUM = 4.0
LIGHT_PARTICLE_COLOR = (255, 214, 110)                     # было (255, 233, 187)
DARK_PARTICLE_GRADIENT = ((236, 240, 248), (72, 74, 84))   # было (238,198,118) -> (16,15,13) / (24,23,21)

# родные текстуры (вытащены Source 2 Viewer в extract/)
LIGHT_EDGE_PNG = TEX_SRC / "chessmaster_square_board_edge_psd_17d16921.png"
DARK_SHAPE_PNG = TEX_SRC / "chessmaster_square_glow_dark_projected_psd_c37950d2.png"

LIGHT_VMAT = f"{MAT_DIR}/chessmaster_bishop_aura_ground_square_projected.vmat"
DARK_VMAT = f"{MAT_DIR}/chessmaster_bishop_aura_ground_square_dark_projected.vmat"
# партиклы, где меняем цвета: (файл, список замен (старая строка, новая))
LIGHT_PARTICLES = ["chessmaster_bishop_aura_ground_proj"]
DARK_PARTICLES = ["chessmaster_bishop_aura_ground_dark_proj", "chessmaster_bishop_aura_warning_proj", "chessmaster_queen_aura_warning"]


def need(p):
    if not p.exists():
        sys.exit(f"нет {p}: сначала вытащи текстуры (см. README, Source 2 Viewer -d на materials/particle/projected/)")
    return p


def blur(a, r):
    return a.filter(ImageFilter.GaussianBlur(r))


def dilate(a, size):
    return a.filter(ImageFilter.MaxFilter(size))


def erode(a, size):
    return a.filter(ImageFilter.MinFilter(size))


def mul(a, k):
    return a.point(lambda v: min(255, int(v * k)))


def light_textures(out_dir):
    """Светлая клетка: толстый яркий контур + широкое гало. Возвращает (color.png, illum.png)."""
    edge = Image.open(need(LIGHT_EDGE_PNG)).convert("RGBA").split()[3]          # тонкая линия + слабое гало
    line = dilate(edge.point(lambda v: 255 if v > 200 else 0), 9)              # линия в 9 px вместо ~3
    halo = blur(line, 22)
    alpha = ImageChops.lighter(mul(blur(line, 2), 1.0), mul(halo, 1.4))
    color = Image.new("RGBA", edge.size, GOLD + (0,))
    color.putalpha(alpha)
    # свечение: линия на полную, гало послабее
    illum_a = ImageChops.lighter(mul(blur(line, 1.5), 1.0), mul(halo, 0.9))
    illum = Image.merge("RGB", (illum_a, illum_a, illum_a))
    cp, ip = out_dir / "solomon_neon_light_color.png", out_dir / "solomon_neon_light_illum.png"
    color.save(cp)
    illum.save(ip)
    return cp, ip


def dark_textures(out_dir):
    """Тёмная клетка: тёмная заливка, по краю формы - светлая неоновая кромка с гало."""
    shape = Image.open(need(DARK_SHAPE_PNG)).convert("RGBA").split()[3]
    solid = shape.point(lambda v: 255 if v > 128 else 0)
    ring = ImageChops.subtract(solid, erode(solid, 13))                        # кромка ~6 px
    ring_soft = ImageChops.lighter(blur(ring, 1.2), mul(blur(ring, 10), 0.8))
    ring_soft = ImageChops.multiply(ring_soft, solid)                          # гало только внутри формы
    fill = Image.new("RGBA", shape.size, DARK_FILL + (255,))
    edge = Image.new("RGBA", shape.size, DARK_EDGE + (255,))
    color = Image.composite(edge, fill, ring_soft)
    color.putalpha(shape)
    illum = Image.merge("RGB", (ring_soft, ring_soft, ring_soft))
    cp, ip = out_dir / "solomon_neon_dark_color.png", out_dir / "solomon_neon_dark_illum.png"
    color.save(cp)
    illum.save(ip)
    return cp, ip


def vmat_text(color_png, illum_png, tint, illum_scale, cutoff_width, slope_fade):
    return f"""// Solomon Piece Reminder: neon ground square (generated by ground_neon.py)
Layer0
{{
	shader "projected_decals.vfx"
	g_bCutoff "0"
	g_bMaskFacingCenter "0"
	g_flAlbedoOpacity "1"
	g_flCutoffWidth "{cutoff_width}"
	g_flEdgeWidth "0.05"
	g_flNormalOpacity "0"
	g_flOpacityScale "1"
	g_flRoughMetalEmitOpacity "1"
	g_flSelfIllumScale "{illum_scale:.3f}"
	g_flSlopeFade "{slope_fade}"
	g_flSlopeFadeSharpness "1"
	g_vColorTint "[{tint[0]:.6f} {tint[1]:.6f} {tint[2]:.6f} 0.000000]"
	TextureColor "{MAT_DIR}/{color_png.name}"
	TextureSelfIllumMask "{MAT_DIR}/{illum_png.name}"
}}
"""


def patch_particles():
    """Цвета клеток в партиклах: пишет изменённые vpcf в аддон (заголовок vpcf63, как в piece_colors)."""
    import piece_colors as pc
    pc.ensure_extracted()
    dst_dir = CONTENT / PARTICLES
    dst_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for name in LIGHT_PARTICLES + DARK_PARTICLES:
        src = EXTRACT / PARTICLES / f"{name}.vpcf"
        text = need(src).read_text(encoding="utf-8").replace(pc.VPCF66, pc.VPCF63, 1)
        before = text
        if name in LIGHT_PARTICLES:
            r, g, b = LIGHT_PARTICLE_COLOR
            text = re.sub(r"m_ConstantColor = \[ 255, 233, 187, 255 \]", f"m_ConstantColor = [ {r}, {g}, {b}, 255 ]", text)
        else:
            (r1, g1, b1), (r2, g2, b2) = DARK_PARTICLE_GRADIENT
            text = re.sub(r"m_Color = \[ 238, 198, 118 \]", f"m_Color = [ {r1}, {g1}, {b1} ]", text)
            text = re.sub(r"m_Color = \[ (?:16, 15, 13|24, 23, 21) \]", f"m_Color = [ {r2}, {g2}, {b2} ]", text)
        if text == before:
            sys.exit(f"{name}: не нашёл ожидаемые цвета - Valve поменяла партикл, обнови ground_neon.py")
        (dst_dir / src.name).write_text(text, encoding="utf-8")
        n += 1
    print(f"  партиклов перекрашено: {n}")


def stage():
    if not ENABLED:
        print("ground_neon выключен")
        return
    out = CONTENT / MAT_DIR
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("test_*")) + list(out.glob("solomon_neon_*")) + list(out.glob("chessmaster_*.vmat")):
        old.unlink()
    for old in (GAME / MAT_DIR).glob("*") if (GAME / MAT_DIR).exists() else []:
        old.unlink()
    lc, li = light_textures(out)
    dc, di = dark_textures(out)
    (CONTENT / LIGHT_VMAT).write_text(vmat_text(lc, li, GOLD_TINT, LIGHT_ILLUM, "0.976", "1"), encoding="utf-8")
    (CONTENT / DARK_VMAT).write_text(vmat_text(dc, di, (1.0, 1.0, 1.0), DARK_ILLUM, "0.1", "0.996"), encoding="utf-8")
    patch_particles()
    print("stage ok:", out)


def collect():
    """[(путь в VPK, байты)] - материалы клеток под родными путями + их текстуры."""
    if not ENABLED:
        return []
    out = []
    for vmat in (LIGHT_VMAT, DARK_VMAT):
        src = CONTENT / vmat
        compiled = GAME / (vmat + "_c")
        if not compiled.exists() or compiled.stat().st_mtime < src.stat().st_mtime:
            sys.exit(f"не скомпилировался материал {compiled} - смотри build/compile_log.txt")
        out.append((vmat + "_c", compiled.read_bytes()))
    for tex in sorted((GAME / MAT_DIR).glob("solomon_neon_*.vtex_c")):
        out.append((f"{MAT_DIR}/{tex.name}", tex.read_bytes()))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stage"
    if cmd == "stage":
        stage()
    elif cmd == "collect":
        for rel, data in collect():
            print(rel, len(data))
    else:
        sys.exit(__doc__)
