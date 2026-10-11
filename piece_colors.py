"""Перекраска свечения фигур Соломона (chessmaster) по способностям.

Идея: все цвета в партиклах способности (m_Color, m_ColorMin/Max, m_ColorFade, m_ConstantColor,
m_LiteralColor, стопы градиентов) переводятся в HSV и получают новый оттенок (hue); серые/белые/чёрные
не трогаются, чтобы блики и дым остались как были. Так золото оригинала становится, например, синим,
а вся анимация и форма эффекта сохраняются.

Партиклы берутся из игры (Source 2 Viewer CLI декомпилирует vpcf_c в текст), правятся и компилируются
обратно resourcecompiler'ом из CSDK 12. Компилятор знает формат vpcf63, игра пишет vpcf66 - разница
только в заголовке, круговая проверка (compile -> decompile) даёт тот же текст байт в байт.

  python piece_colors.py stage   - декомпилировать нужные партиклы, перекрасить, положить в аддон CSDK
  python piece_colors.py collect - (используется solomon_reminder.pack) партиклы + материалы, готовые в VPK

Настройка - словарь HUES ниже: оттенок 0..360 или None (оставить родной цвет).
"""
import colorsys
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
GAME_DIR = Path(os.environ.get("DEADLOCK", r"D:\SteamLibrary\steamapps\common\Deadlock")) / "game" / "citadel"
CSDK = Path(os.environ.get("CSDK", r"C:\Users\Alexd\Downloads\Reduced_CSDK_12\Reduced_CSDK_12"))
CLI = Path(os.environ.get("S2V_CLI", r"C:\Users\Alexd\Documents\DeadlockNeonCrate\tools\cli\Source2Viewer-CLI.exe"))
ADDON = "solomonreminder"
CONTENT = CSDK / "content" / "citadel_addons" / ADDON
GAME = CSDK / "game" / "citadel_addons" / ADDON
EXTRACT = ROOT / "extract"
PARTICLES = "particles/abilities/chessmaster"

# Оттенок (hue, градусы) свечения по способностям. None = не трогать (родное золото).
#   1 - слон (throwbishop)   3 - ладья (forkpiece)     -> по просьбе одного цвета: родное золото
#   2 - конь = щит на союзнике, его же можно таскать (knightbuff, move_ally)
#   4 - ферзь (queen)
HUES = {
    "bishop": None,
    "knight": None,
    "rook": None,
    "queen": None,   # партиклы ферзя тоже родные: пользователь попросил красить саму модель, см. MATERIAL_OVERRIDES
}

# Прямая перекраска материалов моделей: путь в VPK -> {параметр: новое значение (r, g, b, a)}.
# Все параметры с тем же старым значением в этом материале меняются вместе (ограничение бинарного патча:
# ищется число, а не имя; обычно это одинаковые белые (1,1,1) тинты, которым фиолетовый не вредит).
# Ферзь: модель models/particle/blend/chessmaster_queen.vmdl, материал chessmaster_queen.vmat (pbr.vfx):
#   g_vColorTint1 - умножает альбедо (текстура серо-кремовая, так что цвет ложится ровно, тени остаются);
#   g_vSelfIllumTint1 - цвет свечения (включается игрой в «тёмном» состоянии фигуры);
#   g_vSolidOutlineTint - цвет контура NPR.
MATERIAL_OVERRIDES = {}   # золото/серебро фигур переехало в Solomon Neon Squares (neon_pieces.py), чтобы pak03 не перебивал неон
# Как находим параметр в бинарнике: все векторные параметры материала (g_v* и Texture*-умолчания) лежат в
# буфере 1 блока DATA подряд, по 4 double (32 байта), в алфавитном порядке имён - проверено на queen/knight/rook.
# Якорь - любой параметр с уникальным значением; от него считаем смещение нужного имени.
VEC_RE = re.compile(r'"((?:g_v|Texture)\w+)"\s+"\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]"')
MIN_SAT = 0.45      # насыщенность, ниже которой цветные (не серые) цвета подтягиваются, чтобы оттенок читался
GRAY_SAT = 0.08     # ниже - считаем серым/белым и не трогаем

# Какие партиклы принадлежат какой способности (префиксы имён файлов в particles/abilities/chessmaster).
# knight_projectile* общий для ладьи и ферзя - не трогаем, чтобы не красить чужое.
GROUPS = {
    "bishop": ["chessmaster_bishop_", "chessmaster_place_piece", "chessmaster_pawnshield", "chessmaster_move_bishop",
               "chessmaster_move_preview_bishop", "chessmaster_move_available_bishop", "chessmaster_move_ground_path_bishop"],
    "knight": ["chessmaster_knight_buff", "chessmaster_move_ally", "chessmaster_move_preview_knight"],
    "rook": ["chessmaster_rook_", "chessmaster_knight_fork", "chessmaster_knight_aura_ground"],
    "queen": ["chessmaster_queen_", "chessmaster_move_preview_queen"],
}

# Материалы (скомпилированные vmat_c), где цвет задан параметрами g_v*Tint*. Правятся бинарно (tools/kv3patch.py):
# в KV3-блоке DATA подменяются числа вектора, остальное байт в байт как у Valve.
MATERIALS = {
    "bishop": ["models/heroes_wip/chessmaster/materials/chessmaster_bishop.vmat_c",
               "materials/particle/abilities/chessmaster/chessmaster_bishop_cast_projectile_model.vmat_c",
               "materials/particle/abilities/chessmaster/chessmaster_bishop_weapon_explode_ground_projected.vmat_c",
               "materials/particle/abilities/chessmaster/chessmaster_bishop_weapon_explode_sphere.vmat_c",
               "materials/particle/projected/chessmaster_bishop_aura_ground_square_dark_projected.vmat_c",
               "materials/particle/projected/chessmaster_bishop_aura_ground_square_projected.vmat_c"],
    "knight": ["models/heroes_wip/chessmaster/materials/chessmaster_knight.vmat_c",
               "models/heroes_wip/chessmaster/materials/chessmaster_knightshield.vmat_c",
               "materials/particle/abilities/chessmaster/chessmaster_knight_buff_shield.vmat_c"],
    "rook": ["models/heroes_wip/chessmaster/materials/chessmaster_rook.vmat_c",
             "models/heroes_wip/chessmaster/materials/chessmaster_rookglow.vmat_c",
             "materials/particle/projected/chessmaster_knight_aura_ground_square_projected.vmat_c"],
    "queen": ["models/heroes_wip/chessmaster/materials/chessmaster_queen.vmat_c",
              "materials/particle/abilities/chessmaster/chessmaster_queen_warning_cast_ground_projected.vmat_c",
              "materials/particle/projected/chessmaster_queen_stomp_ground_bright_projected.vmat_c",
              "materials/particle/projected/chessmaster_queen_stomp_ground_projected.vmat_c",
              "materials/particle/projected/chessmaster_queen_stomp_post_ground_projected.vmat_c",
              "models/particle/materials/chessmaster_queen_stomp_impact_sphere.vmat_c"],
}
MAT_ANY_RE = re.compile(r'"(g_v\w+)"\s+"\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]"')
MAT_PARAM_RE = re.compile(r'"(g_v\w*Tint\w*)"\s+"\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]"')

COLOR_KEYS = r"m_(?:Color|ColorMin|ColorMax|ColorFade|ConstantColor|LiteralColor|vInterpOutput0|vInterpOutput1)"
COLOR_RE = re.compile(r"(?P<key>\b" + COLOR_KEYS + r"\b\s*=\s*\[\s*)(?P<r>-?\d+(?:\.\d+)?)\s*,\s*(?P<g>-?\d+(?:\.\d+)?)\s*,\s*(?P<b>-?\d+(?:\.\d+)?)(?P<rest>\s*(?:,\s*-?\d+(?:\.\d+)?)?\s*\])")
VPCF66 = "format:vpcf66:version{dd571be4-586e-4f41-8b2d-5bbc969e1c53}"
VPCF63 = "format:vpcf63:version{a6e6a69e-52d3-4527-8b9c-ff3bb91aca3e}"


def shift(r, g, b, hue, scale=255.0):
    """Один цвет -> тот же цвет с новым оттенком. Серые не трогаем."""
    h, s, v = colorsys.rgb_to_hsv(r / scale, g / scale, b / scale)
    if s < GRAY_SAT or v <= 0:
        return r, g, b
    s = max(s, MIN_SAT)
    rr, gg, bb = colorsys.hsv_to_rgb(hue / 360.0, s, v)
    return rr * scale, gg * scale, bb * scale


def recolor_text(text, hue):
    n = 0

    def rep(m):
        nonlocal n
        vals = [m.group("r"), m.group("g"), m.group("b")]
        is_float = any("." in x for x in vals)
        r, g, b = (float(x) for x in vals)
        scale = 1.0 if is_float and max(r, g, b) <= 1.0 else 255.0
        nr, ng, nb = shift(r, g, b, hue, scale)
        if (nr, ng, nb) == (r, g, b):
            return m.group(0)
        n += 1
        fmt = (lambda x: f"{x:.6f}") if is_float else (lambda x: str(int(round(x))))
        return f"{m.group('key')}{fmt(nr)}, {fmt(ng)}, {fmt(nb)}{m.group('rest')}"

    out = COLOR_RE.sub(rep, text)
    return out, n


def wanted(group):
    return [p for p in sorted((EXTRACT / PARTICLES).glob("*.vpcf")) if any(p.name.startswith(pre) for pre in GROUPS[group])]


def ensure_extracted():
    if not (EXTRACT / PARTICLES).exists() or not any((EXTRACT / PARTICLES).glob("*.vpcf")):
        pak = GAME_DIR / "pak01_dir.vpk"
        print("декомпилирую партиклы из", pak)
        subprocess.run([str(CLI), "-i", str(pak), "-d", "-o", str(EXTRACT), "-f", PARTICLES + "/"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stage():
    ensure_extracted()
    dst_dir = CONTENT / PARTICLES
    dst_dir.mkdir(parents=True, exist_ok=True)
    for old in dst_dir.glob("*.vpcf"):
        old.unlink()
    total = 0
    for group, hue in HUES.items():
        if hue is None:
            continue
        for src in wanted(group):
            text = src.read_text(encoding="utf-8")
            if VPCF66 not in text.splitlines()[0]:
                sys.exit(f"{src.name}: неожиданный формат заголовка, посмотри первую строку")
            text = text.replace(VPCF66, VPCF63, 1)
            text, n = recolor_text(text, hue)
            (dst_dir / src.name).write_text(text, encoding="utf-8")
            total += 1
            print(f"  [{group} hue={hue}] {src.name}: {n} цветов")
    print(f"stage ok: {total} партиклов ->", dst_dir)


def material_text(v, rel, raw_dir):
    """(байты vmat_c из игры, декомпилированный текст)."""
    data = v.read(rel)
    raw = raw_dir / rel
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(data)
    txt = raw.with_suffix("")          # .vmat
    if not txt.exists() or txt.stat().st_mtime < raw.stat().st_mtime:
        subprocess.run([str(CLI), "-i", str(raw), "-d", "-o", str(txt)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return data, txt.read_text(encoding="utf-8")


def material_entries():
    """[(путь в VPK, байты)] перекрашенных материалов. Оригиналы достаём из pak01 игры, текст - через CLI."""
    sys.path.insert(0, str(ROOT / "tools"))
    from vpk import VPK
    from kv3patch import patch_vector, patch_at, blocks as res_blocks, kv3_split, find_numbers
    pak = GAME_DIR / "pak01_dir.vpk"
    v = VPK(str(pak))
    raw_dir = EXTRACT / "raw"
    out = []
    for rel, params in MATERIAL_OVERRIDES.items():
        data, text = material_text(v, rel, raw_dir)
        vecs = sorted(((name, (float(r), float(g), float(b))) for name, r, g, b, a in VEC_RE.findall(text)),
                      key=lambda x: x[0].lower())      # порядок как у компилятора: без учёта регистра
        names = [n for n, _ in vecs]
        for typ, off, size in res_blocks(data):
            if typ == "DATA":
                _, bufs, _ = kv3_split(data[off:off + size])
        # якорь: параметр, значение которого встречается в буфере ровно один раз
        base = None
        for i, (n, val) in enumerate(vecs):
            hits = find_numbers(bufs[0], list(val), 8)
            if len(hits) == 1:
                base = hits[0] - 32 * i
                break
        if base is None:
            sys.exit(f"{rel}: не нашёл якорь среди векторных параметров")
        for i, (n, val) in enumerate(vecs):        # контроль: по вычисленным смещениям лежат ожидаемые числа
            cur = [struct.unpack_from("<d", bufs[0], base + 32 * i + 8 * k)[0] for k in range(3)]
            if any(abs(x - y) > 2e-5 for x, y in zip(cur, val)):
                sys.exit(f"{rel}: порядок параметров не алфавитный ({n}: {cur} != {val})")
        for name, new in params.items():
            if name not in names:
                sys.exit(f"{rel}: параметра {name} нет в материале ({names})")
            i = names.index(name)
            data = patch_at(data, 0, base + 32 * i, list(vecs[i][1]), list(new[:3]))
            print(f"  [{Path(rel).name}] {name} {vecs[i][1]} -> {new[:3]}")
        out.append((rel, data))
    for group, hue in HUES.items():
        if hue is None:
            continue
        for rel in MATERIALS[group]:
            if rel not in v.entries:
                print(f"  [{group}] {rel}: нет в pak01 - пропускаю")
                continue
            data = v.read(rel)
            raw = raw_dir / rel
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(data)
            txt = raw.with_suffix("")          # .vmat
            if not txt.exists() or txt.stat().st_mtime < raw.stat().st_mtime:
                subprocess.run([str(CLI), "-i", str(raw), "-d", "-o", str(txt)], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            text = txt.read_text(encoding="utf-8")
            changes = {}
            for name, r, g, b, a in MAT_PARAM_RE.findall(text):
                old = (float(r), float(g), float(b))
                new = shift(*old, hue, scale=1.0)
                if tuple(round(x, 6) for x in new) != tuple(round(x, 6) for x in old):
                    changes.setdefault(old, (new, []))[1].append(name)
            if not changes:
                print(f"  [{group}] {Path(rel).name}: цветных параметров нет")
                continue
            for old, (new, names) in changes.items():
                data = patch_vector(data, list(old), list(new), expect=len(names))
            out.append((rel, data))
            print(f"  [{group} hue={hue}] {Path(rel).name}: " + ", ".join(n for _, (_, ns) in changes.items() for n in ns))
    return out


def collect():
    """[(путь в VPK, байты)] скомпилированных партиклов и перекрашенных материалов; падает, если что-то не собралось."""
    out = material_entries()
    for src in sorted((CONTENT / PARTICLES).glob("*.vpcf")):
        compiled = GAME / PARTICLES / (src.name + "_c")
        if not compiled.exists() or compiled.stat().st_mtime < src.stat().st_mtime:
            sys.exit(f"не скомпилировался партикл {compiled} - смотри build/compile_log.txt")
        out.append((f"{PARTICLES}/{src.name}_c", compiled.read_bytes()))
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
