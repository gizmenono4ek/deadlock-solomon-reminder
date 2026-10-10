"""Точечная правка чисел в скомпилированном ресурсе Source 2 с бинарным KV3 (vmat_c и т.п.).

Полный разбор KV3 не нужен: векторные параметры материала (g_vSelfIllumTint1 и др.) лежат в секции
8-байтовых чисел (double) распакованного блока DATA. Ищем тройку значений оригинала и заменяем на новую.
Блок сжат LZ4 (raw block) - распаковываем своим декодером, после правки упаковываем обратно (простой
LZ4-энкодер: только литералы и совпадения с жадным поиском - поток валидный, игра читает его обычным LZ4).
"""
import struct


def lz4_decompress(src, out_size):
    out = bytearray()
    i = 0
    n = len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        out += src[i:i + lit]
        i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        ml = token & 15
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        start = len(out) - off
        for k in range(ml):
            out.append(out[start + k])
    assert len(out) == out_size, (len(out), out_size)
    return bytes(out)


def _len_bytes(v):
    b = bytearray()
    while v >= 255:
        b.append(255)
        v -= 255
    b.append(v)
    return bytes(b)


def lz4_compress(data):
    """Жадный LZ4 block encoder (хэш по 4 байтам). Выход валиден для любого LZ4-декодера."""
    n = len(data)
    out = bytearray()
    table = {}
    anchor = 0
    i = 0
    while i + 4 <= n - 5:          # последние 5 байт - всегда литералы (правило LZ4)
        key = data[i:i + 4]
        cand = table.get(key)
        table[key] = i
        if cand is not None and i - cand <= 0xFFFF and data[cand:cand + 4] == key:
            ml = 4
            limit = n - 5 - i
            while ml < limit and data[cand + ml] == data[i + ml]:
                ml += 1
            lit = data[anchor:i]
            tok_l = min(len(lit), 15)
            tok_m = min(ml - 4, 15)
            out.append((tok_l << 4) | tok_m)
            if tok_l == 15:
                out += _len_bytes(len(lit) - 15)
            out += lit
            out += struct.pack("<H", i - cand)
            if tok_m == 15:
                out += _len_bytes(ml - 4 - 15)
            i += ml
            anchor = i
            continue
        i += 1
    lit = data[anchor:]
    tok_l = min(len(lit), 15)
    out.append(tok_l << 4)
    if tok_l == 15:
        out += _len_bytes(len(lit) - 15)
    out += lit
    return bytes(out)


def blocks(res):
    _, hv, ver, boff, cnt = struct.unpack_from("<IHHII", res, 0)
    out = []
    for i in range(cnt):
        p = 16 + i * 12
        rel, size = struct.unpack_from("<II", res, p + 4)
        out.append((res[p:p + 4].decode(), p + 4 + rel, size))
    return out


KV3_MAGIC = {0x4B563301: 1, 0x4B563302: 2, 0x4B563303: 3, 0x4B563304: 4, 0x4B563305: 5}


def _unpack(method, raw, size):
    if size == 0:
        return bytearray()
    if method == 0:
        return bytearray(raw[:size])
    if method == 1:
        try:
            import lz4.block
            return bytearray(lz4.block.decompress(bytes(raw), uncompressed_size=size))
        except ImportError:
            return bytearray(lz4_decompress(raw, size))
    raise ValueError(f"сжатие {method} (zstd?) не поддерживается")


def _pack(method, data):
    if method == 0 or len(data) == 0:
        return bytes(data)
    try:
        import lz4.block
        return lz4.block.compress(bytes(data), store_size=False, mode="high_compression")
    except ImportError:
        return lz4_compress(bytes(data))


def kv3_split(blk):
    """KV3 v4/v5 (как в VRF BinaryKV3.cs): заголовок + 1 (v4) или 2 (v5) сжатых буфера.
    -> (header bytearray, [буферы распакованные], info)"""
    magic = struct.unpack_from("<I", blk, 0)[0]
    ver = KV3_MAGIC.get(magic)
    if ver not in (4, 5):
        raise ValueError(f"KV3 v{ver} не поддерживается (magic {magic:#x})")
    method = struct.unpack_from("<I", blk, 20)[0]
    # Смещения по VRF BinaryKV3.cs: 0 magic, 4 guid, 20 method, 24 dict+frame, 28 bytes1, 32 bytes4, 36 bytes8,
    # 40 types, 44 objs+arrs, 48 uncmpTotal, 52 cmpTotal, 56 blocks, 60 blobs, 64 bytes2, 68 blockCmpSizes,
    # v5: 72 unc1, 76 cmp1, 80 unc2, 84 cmp2, 88..116 восемь счётчиков, 120 данные
    o_uncmp, o_cmp = 48, 52
    off = 72
    if ver == 4:
        uncmp, cmp = struct.unpack_from("<II", blk, o_uncmp)
        hdr = off
        return bytearray(blk[:hdr]), [_unpack(method, blk[hdr:hdr + cmp], uncmp)], dict(ver=4, method=method, hdr=hdr, o_sizes=[(o_uncmp, o_cmp)], o_total=o_cmp, tail=bytes(blk[hdr + cmp:]))
    o_b1 = off                        # 76: unc1, cmp1, unc2, cmp2
    unc1, cmp1, unc2, cmp2 = struct.unpack_from("<IIII", blk, o_b1)
    hdr = off + 16 + 8 * 4            # 72 + 48 = 120
    bufs = [_unpack(method, blk[hdr:hdr + cmp1], unc1), _unpack(method, blk[hdr + cmp1:hdr + cmp1 + cmp2], unc2)]
    # после буферов могут лежать бинарные блобы (countBlocks > 0, например байткод DynamicParams) - сохраняем как есть
    tail = bytes(blk[hdr + cmp1 + cmp2:])
    return bytearray(blk[:hdr]), bufs, dict(ver=5, method=method, hdr=hdr, o_sizes=[(o_b1, o_b1 + 4), (o_b1 + 8, o_b1 + 12)], o_total=o_cmp, tail=tail)


def kv3_join(header, bufs, info):
    payload = b""
    total = 0
    for data, (o_unc, o_cmp) in zip(bufs, info["o_sizes"]):
        packed = _pack(info["method"], data)
        assert _unpack(info["method"], packed, len(data)) == data
        struct.pack_into("<I", header, o_cmp, len(packed) if info["method"] else 0)
        payload += packed
        total += len(packed)
    if info["method"]:
        struct.pack_into("<I", header, info["o_total"], total)
    return bytes(header) + payload + info["tail"]


def find_numbers(data, values, width=8, tol=2e-5):
    """Смещения (кратные width) всех мест, где подряд лежат числа values (double при width=8, float при 4)."""
    fmt = "<d" if width == 8 else "<f"
    hits = []
    n = len(values)
    for off in range(0, len(data) - width * n + 1, width):
        if all(abs(struct.unpack_from(fmt, data, off + width * k)[0] - v) <= tol for k, v in enumerate(values)):
            hits.append(off)
    return hits


def patch_vector(res, old, new, expect=1):
    """Заменить в блоке DATA ресурса вектор old (список чисел) на new. Возвращает новые байты ресурса."""
    for typ, off, size in blocks(res):
        if typ != "DATA":
            continue
        blk = res[off:off + size]
        header, bufs, info = kv3_split(blk)
        hits = [(bi, h, w) for bi, data in enumerate(bufs) for w in (8, 4) for h in find_numbers(data, old, w)]
        if (expect is None and not hits) or (expect is not None and len(hits) != expect):
            raise ValueError(f"найдено {len(hits)} вхождений {old}, ожидалось {expect}: {hits}")
        for bi, h, w in hits:
            for k, v in enumerate(new):
                struct.pack_into("<d" if w == 8 else "<f", bufs[bi], h + w * k, float(v))
        new_blk = kv3_join(header, bufs, info)
        return replace_block(res, "DATA", new_blk)
    raise ValueError("нет блока DATA")


def patch_at(res, buf_index, offset, old, new):
    """Заменить вектор по точному смещению в распакованном буфере buf_index блока DATA (old проверяется)."""
    for typ, off, size in blocks(res):
        if typ != "DATA":
            continue
        header, bufs, info = kv3_split(res[off:off + size])
        data = bufs[buf_index]
        cur = [struct.unpack_from("<d", data, offset + 8 * k)[0] for k in range(len(old))]
        if any(abs(a - b) > 2e-5 for a, b in zip(cur, old)):
            raise ValueError(f"по смещению {offset} лежит {cur}, а не {old}")
        for k, v in enumerate(new):
            struct.pack_into("<d", data, offset + 8 * k, float(v))
        return replace_block(res, "DATA", kv3_join(header, bufs, info))
    raise ValueError("нет блока DATA")


def replace_block(res, name, new_data):
    """Пересобрать ресурс с заменой одного блока; порядок и выравнивание 16 сохраняются."""
    _, hver, ver, _, count = struct.unpack_from("<IHHII", res, 0)
    items = [(t, new_data if t == name else res[o:o + s]) for t, o, s in blocks(res)]
    table_end = 16 + 12 * count
    offsets, pos = [], table_end
    for _, d in items:
        pos = (pos + 15) & ~15
        offsets.append(pos)
        pos += len(d)
    out = bytearray(pos)
    struct.pack_into("<IHHII", out, 0, pos, hver, ver, 8, count)
    for i, ((t, d), o) in enumerate(zip(items, offsets)):
        p = 16 + 12 * i
        out[p:p + 4] = t.encode()
        struct.pack_into("<II", out, p + 4, o - (p + 4), len(d))
        out[o:o + len(d)] = d
    return bytes(out)
