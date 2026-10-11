"""Deadlock mod: Solomon Piece Reminder.

Если у Соломона (внутреннее имя героя chessmaster) выставлена фигура (1 - слон, 4 - ферзь, конь тоже) и
способность висит в состоянии «нажми ещё раз» дольше DELAY секунд без изменений, иконка способности мигает
красным - напоминание, что фигуру пора убрать/активировать, иначе кулдаун не пойдёт.

Как: подменяем panorama/layout/hud_ability_icon.xml (родная разметка иконки + подключение своего css и js).
Скрипт hud/solomon_reminder.js живёт внутри каждой иконки, раз в полсекунды смотрит на её классы состояния
(.active / .toggled_on / .is_trigger, без .cooling_down) и через DELAY секунд непрерывного состояния вешает
класс solomon_overdue; hud/solomon_reminder.css по нему мигает. Любая смена состояния сбрасывает отсчёт.
(Первая версия была на CSS animation-delay - Panorama в Deadlock его игнорирует, мигало сразу.)

  python solomon_reminder.py stage             - положить исходники в аддон CSDK (solomonreminder)
  python solomon_reminder.py pack              - упаковать скомпилированное в build/<вариант>/pak03_dir.vpk + zip
  python solomon_reminder.py install [variant] - скопировать build/<variant>/pak03_dir.vpk в citadel/addons

Варианты: solomon - только иконки Соломона; universal - любая способность любого героя, висящая активной
дольше DELAY. Компиляция - build.bat.
"""
import hashlib
import os
import re
import shutil
import struct
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))
from vpk import VPK  # noqa: E402
from pano import blocks, text as pano_text  # noqa: E402
from kv3patch import replace_block  # noqa: E402

DELAY = 15            # секунд до начала мигания
BLINK = 0.5           # период мигания, с
PAK_NAME = "pak03_dir.vpk"   # в addons уже заняты pak01 (Neon Crates) и pak02 (Buff Timer)

GAME_DIR = Path(os.environ.get("DEADLOCK", r"D:\SteamLibrary\steamapps\common\Deadlock")) / "game" / "citadel"
CSDK = Path(os.environ.get("CSDK", r"C:\Users\Alexd\Downloads\Reduced_CSDK_12\Reduced_CSDK_12"))
ADDON = "solomonreminder"
CONTENT = CSDK / "content" / "citadel_addons" / ADDON
GAME = CSDK / "game" / "citadel_addons" / ADDON
BUILD = ROOT / "build"

# путь в VPK (скомпилированный) -> (исходник в аддоне CSDK, файл в проекте)
FILES = {
    "panorama/layout/hud_ability_icon.vxml_c": ("panorama/layout/hud_ability_icon.xml", "hud/hud_ability_icon.xml"),
    "panorama/scripts/solomon_reminder.vjs_c": ("panorama/scripts/solomon_reminder.js", "hud/solomon_reminder.js"),
    "panorama/styles/solomon_reminder.vcss_c": ("panorama/styles/solomon_reminder.css", "hud/solomon_reminder.css"),
}
VARIANTS = {"solomon": "true", "universal": "false"}      # значение SOLOMON_ONLY в js
MARKER = "solomon_overdue"


def source_text(project_file, variant="solomon"):
    t = (ROOT / project_file).read_text(encoding="utf-8")
    return (t.replace("__DELAY__", str(int(DELAY)))
             .replace("__SOLOMON_ONLY__", VARIANTS[variant])
             .replace("__BLINK__", f"{BLINK:g}"))


def stage():
    for vpk_rel, (src, project_file) in FILES.items():
        dst = CONTENT / src
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(source_text(project_file), encoding="utf-8")
        print("stage:", dst)
    print(f"stage ok (DELAY={DELAY}s)")


def write_vpk(files, out_path):
    """VPK v2, всё в одном _dir.vpk (archive index 0x7fff), с MD5-секцией как у Source 2 Viewer."""
    tree_map = {}
    for rel, data in files:
        p = Path(rel)
        tree_map.setdefault(p.suffix[1:], {}).setdefault(p.parent.as_posix() or " ", []).append((p.stem, data))
    tree, blob = bytearray(), bytearray()
    for ext in sorted(tree_map):
        tree += ext.encode() + b"\0"
        for folder in sorted(tree_map[ext]):
            tree += folder.encode() + b"\0"
            for name, data in sorted(tree_map[ext][folder]):
                tree += name.encode() + b"\0"
                tree += struct.pack("<IHHIIH", zlib.crc32(data) & 0xFFFFFFFF, 0, 0x7FFF, len(blob), len(data), 0xFFFF)
                blob += data
            tree += b"\0"
        tree += b"\0"
    tree += b"\0"
    header = struct.pack("<7I", 0x55AA1234, 2, len(tree), len(blob), 0, 48, 0)
    body = header + bytes(tree) + bytes(blob)
    md5 = hashlib.md5(bytes(tree)).digest() + hashlib.md5(b"").digest()
    md5 += hashlib.md5(body + md5).digest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(body + md5)


def compiled_bytes(vpk_rel, src):
    staged = CONTENT / src
    compiled = GAME / vpk_rel
    if not compiled.exists() or compiled.stat().st_mtime < staged.stat().st_mtime:
        sys.exit(f"не скомпилировалось: {compiled} - смотри build/compile_log.txt")
    return compiled.read_bytes()


def js_text(data):
    """Текст скрипта из vjs_c: блок DATA - это сам исходник как есть (без заголовка, в отличие от vcss_c)."""
    for typ, off, sz in blocks(data):
        if typ == "DATA":
            return data[off:off + sz].decode("utf-8")
    sys.exit("в vjs_c нет блока DATA")


def patch_js(data, variant):
    """Подменить SOLOMON_ONLY в скомпилированном vjs_c."""
    text = js_text(data)
    new = re.sub(r"SOLOMON_ONLY = (true|false);", f"SOLOMON_ONLY = {VARIANTS[variant]};", text, count=1)
    return data if new == text else replace_block(data, "DATA", new.encode("utf-8"))


def pack():
    for variant in VARIANTS:
        entries = []
        for vpk_rel, (src, project_file) in FILES.items():
            data = compiled_bytes(vpk_rel, src)
            if vpk_rel.endswith(".vjs_c"):
                data = patch_js(data, variant)   # js компилируется для варианта solomon, остальным правим флаг
            entries.append((vpk_rel, data))
        for rel, data in entries:                       # самопроверка
            if rel.endswith((".vjs_c", ".vcss_c")):
                t = js_text(data) if rel.endswith(".vjs_c") else (pano_text(data) or "")
                assert MARKER in t, rel
                if rel.endswith(".vjs_c"):
                    assert f"SOLOMON_ONLY = {VARIANTS[variant]};" in t and f"DELAY_SECONDS = {DELAY};" in t, (rel, variant)
        out = BUILD / variant / PAK_NAME
        write_vpk(entries, out)
        with zipfile.ZipFile(BUILD / f"SolomonReminder_{variant}_{DELAY}s.zip", "w", zipfile.ZIP_DEFLATED) as z:
            z.write(out, PAK_NAME)
        back = VPK(str(out))
        assert set(back.entries) == {rel for rel, _ in entries}
        print(f"pack ok [{variant}]: {out} ({out.stat().st_size} B): " + ", ".join(Path(r).name for r, _ in entries))


def install(variant="solomon"):
    src = BUILD / variant / PAK_NAME
    dst = GAME_DIR / "addons" / PAK_NAME
    if not src.exists():
        sys.exit(f"нет {src} - сначала pack")
    if dst.exists():
        ours = VPK(str(dst))
        if not any(k in FILES or "chessmaster" in k or "solomon" in k for k in ours.entries):
            sys.exit(f"{dst} уже существует и это не наш мод - выбери другой PAK_NAME")
    try:
        shutil.copyfile(src, dst)
    except PermissionError:
        sys.exit(f"{dst} занят игрой - закрой Deadlock и повтори: python solomon_reminder.py install {variant}")
    print("install ok ->", dst)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "stage":
        stage()
    elif cmd == "pack":
        pack()
    elif cmd == "install":
        install(*args[:1])
    else:
        sys.exit(__doc__)
