# -*- coding: utf-8 -*-
"""Behind the Frame — Ukrainian localisation. Full installer.

Applies every stage to a clean install in one pass:

  1 font      rebaked MPLUSRounded1c atlas (adds і ї є ґ and friends)
  2 text      703 translated strings into the "Language - Russian" slot
  3 label     the language picker entry -> Українська
  4 title     "Натисніть, щоб почати"
  5 computer  the two full-page images (they live in atlas pages, not their
              own textures — that distinction matters, see open_fullrect)
  6 resume    36 word images, repacked into the atlas + re-laid-out
  7 journal   16 handwritten notes
  8 cutscenes 12 spoken lines

Everything is resolved by asset NAME or by matching stored reference pixels,
never by stored object ids, so a re-downloaded (or slightly patched) game is
still handled correctly.

Usage:
    python apply.py "<...>/Behind the Frame_Data"      install
    python apply.py "<path>" --verify                  check an installed copy
"""
import os, sys, json, csv, io, re, struct, shutil, gc, hashlib
from collections import defaultdict

try:
    import UnityPy
    from UnityPy.enums import TextureFormat
    from PIL import Image
except ImportError as e:
    sys.exit(f'missing dependency: {e}\n  pip install UnityPy pillow')

# when frozen by PyInstaller the data files live in the unpacked bundle, not
# next to the executable
HERE = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
# the translation and artwork are not in the public repository: private/ links
# to them locally and is bundled into the installer (see LICENSE)
PRIVATE = os.path.join(HERE, 'private')
ART = os.path.join(PRIVATE, 'art')
REF = os.path.join(HERE, 'reference')
PPU = 100.0
FONT_NAME = 'MPLUSRounded1c-Medium'
LANG_SLOT = 'Language - Russian'
NEW_LABEL = 'Українська'

log = lambda *a: print(*a, flush=True)


# ---------------------------------------------------------------- helpers ---
def quad_vertex_data(w, h):
    """4-vertex full-rect mesh in the layout these sprites use:
    stream 0 = float3 position, stream 1 = uv0 + blend weights + blend indices."""
    hw, hh = w / 2 / PPU, h / 2 / PPU
    s0 = b''.join(struct.pack('<3f', *v) for v in
                  [(-hw, hh, 0.0), (hw, hh, 0.0), (-hw, -hh, 0.0), (hw, -hh, 0.0)])
    per = (struct.pack('<2f', 0.0, 0.0) + struct.pack('<4f', 1.0, 0.0, 0.0, 0.0)
           + struct.pack('<4I', 0, 0, 0, 0))
    return s0 + b'\x00' * ((-len(s0)) % 16) + per * 4


def open_fullrect(stt, TW, TH):
    """Drop the shipped tight mesh + cropped textureRect so the whole texture
    is drawn. Without this, artwork reaching outside the old lettering is
    silently clipped."""
    rd = stt['m_RD']
    rd['textureRect'] = {'x': 0.0, 'y': 0.0, 'width': float(TW), 'height': float(TH)}
    rd['textureRectOffset'] = {'x': 0.0, 'y': 0.0}
    rd['uvTransform'] = {'x': PPU, 'y': TW / 2, 'z': PPU, 'w': TH / 2}
    if (stt['m_Rect']['width'], stt['m_Rect']['height']) != (float(TW), float(TH)):
        stt['m_Rect'] = {'x': 0.0, 'y': 0.0, 'width': float(TW), 'height': float(TH)}
    rd['m_VertexData']['m_VertexCount'] = 4
    rd['m_VertexData']['m_DataSize'] = quad_vertex_data(TW, TH)
    rd['m_IndexBuffer'] = struct.pack('<6H', 0, 1, 2, 2, 1, 3)
    rd['m_SubMeshes'][0].update({'firstByte': 0, 'indexCount': 6, 'baseVertex': 0,
                                 'firstVertex': 0, 'vertexCount': 4})


def mae(a, b):
    from PIL import ImageChops
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    d = ImageChops.difference(a.convert('RGBA'), b.convert('RGBA')).convert('L')
    return sum(i * c for i, c in enumerate(d.histogram())) / (a.width * a.height)


class Game:
    def __init__(self, data_dir):
        self.dir = data_dir
        self.assets = os.path.join(data_dir, 'resources.assets')
        self.ress = os.path.join(data_dir, 'resources.assets.resS')
        for p in (self.assets, self.ress):
            if not os.path.isfile(p):
                sys.exit(f'not a game data folder: {p} missing')
        self.env = UnityPy.load(self.assets)
        self.objs = {o.path_id: o for o in self.env.objects}
        self._sprites = defaultdict(list)
        self._atlas = {}
        for o in self.env.objects:
            if o.type.name == 'Sprite':
                self._sprites[o.read_typetree().get('m_Name')].append(o)
            elif o.type.name == 'SpriteAtlas':
                t = o.read_typetree()
                for key, v in t['m_RenderDataMap']:
                    g, l = key
                    self._atlas[(tuple(g.values()), l)] = (o, t, v)

    def sprites(self, name):
        return self._sprites.get(name, [])

    def one(self, name):
        s = self.sprites(name)
        assert len(s) == 1, f'{name}: expected 1 sprite, found {len(s)}'
        return s[0]

    def atlas_entry(self, stt):
        g, l = stt['m_RenderDataKey']
        return self._atlas.get((tuple(g.values()), l))

    def texture_of(self, sprite_obj):
        """-> (texture object, rect in that texture). Handles both the
        own-texture and the atlas-packed case."""
        stt = sprite_obj.read_typetree()
        hit = self.atlas_entry(stt)
        if hit:
            _, _, v = hit
            r = v['textureRect']
            return self.objs[v['texture']['m_PathID']], r, hit
        r = stt['m_RD']['textureRect']
        return self.objs[stt['m_RD']['texture']['m_PathID']], r, None

    def save(self):
        data = self.env.file.save()
        with open(self.assets, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        return len(data)


def paint(tex_obj, img, rx, ry, rw, rh, clear_whole=True):
    """Paste into a texture using Unity's bottom-up Y. Returns the new page."""
    tt = tex_obj.read_typetree()
    TW, TH = tt['m_Width'], tt['m_Height']
    if clear_whole:
        page = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    else:
        page = tex_obj.read().image.convert('RGBA')
    if (img.width, img.height) != (rw, rh):
        img = img.resize((rw, rh), Image.LANCZOS)
    page.paste(img, (rx, TH - ry - rh))
    t2 = tex_obj.read()
    t2.set_image(page, target_format=TextureFormat(tt['m_TextureFormat']))
    t2.save()
    return TW, TH


def rect_px(r):
    return round(r['x']), round(r['y']), round(r['width']), round(r['height'])


def placement(tex_tt, art, rect):
    """Where a redrawn image belongs in its texture.

    Some art was redrawn on the full texture canvas (the title screen), the rest
    on just the cropped lettering rect (journal, cutscenes).  Telling them apart
    by size is what keeps the title screen from being squashed into the smaller
    rect, and the journal notes from being stretched across the whole texture."""
    TW, TH = tex_tt['m_Width'], tex_tt['m_Height']
    if (art.width, art.height) == (TW, TH):
        return 0, 0, TW, TH
    return rect_px(rect)


# ------------------------------------------------------------- the stages ---
def stage_font(g):
    font = next(o for o in g.env.objects if o.type.name == 'Font'
                and o.read_typetree().get('m_Name') == FONT_NAME)
    tt = font.read_typetree()
    tex = g.objs[tt['m_Texture']['m_PathID']]
    sd = tex.read_typetree()['m_StreamData']
    blob = open(os.path.join(DATA, 'font', 'uk_atlas.resS.bin'), 'rb').read()
    assert len(blob) == sd['size'], f'atlas {len(blob)} vs expected {sd["size"]}'
    with open(g.ress, 'r+b') as f:                       # 1 MB inside an 827 MB file
        f.seek(sd['offset'])
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    tt['m_CharacterRects'] = json.load(open(os.path.join(DATA, 'font', 'uk_rects.json')))
    font.save_typetree(tt)
    log(f'  font      {len(tt["m_CharacterRects"])} glyphs, atlas -> resS@{sd["offset"]}')


def stage_text(g):
    body = open(os.path.join(PRIVATE, 'translation', 'Ukrainian.csv'),
                encoding='utf-8', newline='').read()
    obj = next(o for o in g.env.objects if o.type.name == 'TextAsset'
               and o.read_typetree().get('m_Name') == LANG_SLOT)
    tt = obj.read_typetree()
    tt['m_Script'] = body
    obj.save_typetree(tt)
    log(f'  text      {len([r for r in csv.reader(io.StringIO(body)) if r])} rows')


def stage_label(g):
    KEY = b'Languages/TypeSettings/Russian'
    obj = next(o for o in g.env.objects
               if o.type.name == 'MonoBehaviour' and KEY in o.get_raw_data())
    raw = obj.get_raw_data()
    i = raw.find(KEY)
    p = i + len(KEY)
    while p % 4:
        p += 1
    n = struct.unpack('<i', raw[p:p + 4])[0]             # the enum name
    q = p + 4 + n
    while q % 4:
        q += 1
    old_len = struct.unpack('<i', raw[q:q + 4])[0]       # the displayed label
    after = q + 4 + old_len + ((-old_len) % 4)
    payload = NEW_LABEL.encode('utf-8')
    block = struct.pack('<i', len(payload)) + payload + b'\x00' * ((-len(payload)) % 4)
    obj.set_raw_data(raw[:q] + block + raw[after:])
    log(f'  label     {raw[q+4:q+4+old_len].decode("utf-8")!r} -> {NEW_LABEL!r}')


def stage_title(g):
    sp = g.one('press_text_ru')
    stt = sp.read_typetree()
    tex, r, _ = g.texture_of(sp)
    img = Image.open(os.path.join(ART, 'title', 'press_text.png')).convert('RGBA')
    rx, ry, rw, rh = placement(tex.read_typetree(), img, r)
    TW, TH = paint(tex, img, rx, ry, rw, rh)
    open_fullrect(stt, TW, TH)
    sp.save_typetree(stt)
    log(f'  title     press_text_ru {rw}x{rh} -> full {TW}x{TH}')


def stage_computer_images(g):
    for name, f in (('puzzle_computer_ch4_resume_ru', 'ch4_resume.png'),
                    ('puzzle_computer_popup_background_ru', 'popup_background.png')):
        sp = g.one(name)
        tex, r, hit = g.texture_of(sp)
        assert hit, f'{name}: expected an atlas-packed sprite'
        rx, ry, rw, rh = rect_px(r)
        img = Image.open(os.path.join(ART, 'computer', f)).convert('RGBA')
        # an atlas page holds other sprites too — never clear the whole thing
        paint(tex, img, rx, ry, rw, rh, clear_whole=False)
        log(f'  computer  {name} -> atlas page {tex.path_id} @({rx},{ry}) {rw}x{rh}')


def _resume_layout(g):
    """Rebuild the row layout from the game itself: renderer -> GameObject ->
    RectTransform, grouped into rows by Y and ordered by X."""
    rus = {}
    for name, lst in g._sprites.items():
        m = re.match(r'^puzzle_computer_resume_text_(\d\d)_a(\d+)$', name or '')
        if m:
            rus[lst[0].path_id] = (int(m.group(1)), name)
    pats = {pid: struct.pack('<iq', 0, pid) for pid in rus}
    recs = []
    for o in g.env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        raw = o.get_raw_data()
        for pid, pt in pats.items():
            if pt not in raw:
                continue
            go = struct.unpack('<q', raw[4:12])[0]
            tr = None
            for c in g.objs[go].read_typetree()['m_Component']:
                cid = list(c.values())[0]
                cid = cid['m_PathID'] if isinstance(cid, dict) else cid
                if cid in g.objs and g.objs[cid].type.name in ('Transform', 'RectTransform'):
                    tr = g.objs[cid]
                    break
            t = tr.read_typetree()
            ap = t.get('m_AnchoredPosition') or t['m_LocalPosition']
            sd = t.get('m_SizeDelta') or {'x': 0, 'y': 0}
            slot, name = rus[pid]
            recs.append({'slot': slot, 'sprite': name, 'sprite_id': pid, 'go': go,
                         'tr': tr.path_id, 'x': ap['x'], 'y': ap['y'],
                         'w': sd['x'], 'h': sd['y']})
            break
    recs.sort(key=lambda r: -r['y'])
    rows, cur = [], []
    for r in recs:
        if cur and abs(r['y'] - cur[-1]['y']) > 15:
            rows.append(cur)
            cur = []
        cur.append(r)
    rows.append(cur)
    for r in rows:
        r.sort(key=lambda a: a['x'])
    return rows


def stage_resume(g):
    LIMIT, PUNCT = -2.0, 6
    rows = _resume_layout(g)
    ua = defaultdict(list)
    for f in sorted(os.listdir(os.path.join(ART, 'resume'))):
        if f.lower().endswith('.png'):
            im = Image.open(os.path.join(ART, 'resume', f)).convert('RGBA')
            ua[int(f.split('-')[0])].append((f, im))
    assert len(rows) == len(ua), f'{len(rows)} rows in game vs {len(ua)} supplied'

    jobs, surplus = [], []
    for i, row in enumerate(rows, 1):
        words = ua[i]
        left = row[0]['x'] - row[0]['w'] / 2
        for gap in (7.0, 6.5, 6.0, 5.5, 5.0, 4.5, 4.0):
            cur, placed = left, []
            for j, (f, im) in enumerate(words):
                if j:
                    cur += 0.0 if im.width <= PUNCT else gap
                placed.append((f, im, cur + im.width / 2))
                cur += im.width
            if cur <= LIMIT:
                break
        for j, slot in enumerate(row):
            if j < len(placed):
                f, im, cx = placed[j]
                jobs.append({**slot, 'img': im, 'cx': cx})
            else:
                surplus.append(slot)

    # pack into the atlas' free band
    atlas_obj, atlas_tt, _ = g.atlas_entry(g.objs[jobs[0]['sprite_id']].read_typetree())
    page_id = None
    occ = defaultdict(lambda: Image.new('L', (2048, 2048), 0))
    from PIL import ImageDraw
    for key, v in atlas_tt['m_RenderDataMap']:
        r = v['textureRect']
        ImageDraw.Draw(occ[v['texture']['m_PathID']]).rectangle(
            [r['x'], r['y'], r['x'] + r['width'] - 1, r['y'] + r['height'] - 1], fill=255)
    page_id = g.texture_of(g.objs[jobs[0]['sprite_id']])[0].path_id
    band = None
    a = occ[page_id]
    free_rows = [y for y in range(2048) if not a.crop((0, y, 2048, y + 1)).getbbox()]
    runs, start = [], None
    for y in range(2048):
        f = y in set(free_rows)
        if f and start is None:
            start = y
        elif not f and start is not None:
            runs.append((start, y - 1))
            start = None
    if start is not None:
        runs.append((start, 2047))
    need_h = max(j['img'].height for j in jobs)
    band = next((r for r in runs if r[1] - r[0] + 1 >= need_h * 4), None)
    assert band, 'no free band in the atlas page'

    x, y, shelf = 0, band[0], 0
    for j in sorted(jobs, key=lambda j: -j['img'].height):
        if x + j['img'].width > 2048:
            x, y, shelf = 0, y + shelf + 1, 0
        assert y + j['img'].height - 1 <= band[1], 'free band exhausted'
        j['ax'], j['ay'] = x, y
        x += j['img'].width + 1
        shelf = max(shelf, j['img'].height)

    tex = g.objs[page_id]
    page = tex.read().image.convert('RGBA')
    for j in jobs:
        page.paste(j['img'], (j['ax'], 2048 - j['ay'] - j['img'].height))
    for s in surplus:                                     # erase the unused word
        _, r, _ = g.texture_of(g.objs[s['sprite_id']])
        rx, ry, rw, rh = rect_px(r)
        page.paste((0, 0, 0, 0), (rx, 2048 - ry - rh, rx + rw, 2048 - ry))
    t2 = tex.read()
    t2.set_image(page, target_format=TextureFormat.DXT5)
    t2.save()

    lut = {}
    for idx, (key, v) in enumerate(atlas_tt['m_RenderDataMap']):
        gg, l = key
        lut[(tuple(gg.values()), l)] = idx
    for j in jobs:
        sp = g.objs[j['sprite_id']]
        stt = sp.read_typetree()
        w, h = float(j['img'].width), float(j['img'].height)
        stt['m_Rect'] = {'x': 0.0, 'y': 0.0, 'width': w, 'height': h}
        rd = stt['m_RD']
        rd['textureRect'] = {'x': 0.0, 'y': 0.0, 'width': w, 'height': h}
        rd['textureRectOffset'] = {'x': 0.0, 'y': 0.0}
        rd['uvTransform'] = {'x': PPU, 'y': w / 2, 'z': PPU, 'w': h / 2}
        rd['m_VertexData']['m_VertexCount'] = 4
        rd['m_VertexData']['m_DataSize'] = quad_vertex_data(w, h)
        rd['m_IndexBuffer'] = struct.pack('<6H', 0, 1, 2, 2, 1, 3)
        rd['m_SubMeshes'][0].update({'firstByte': 0, 'indexCount': 6, 'baseVertex': 0,
                                     'firstVertex': 0, 'vertexCount': 4})
        sp.save_typetree(stt)
        gg, l = stt['m_RenderDataKey']
        e = atlas_tt['m_RenderDataMap'][lut[(tuple(gg.values()), l)]][1]
        e['textureRect'] = {'x': float(j['ax']), 'y': float(j['ay']), 'width': w, 'height': h}
        e['atlasRectOffset'] = {'x': float(j['ax']), 'y': float(j['ay'])}
        e['textureRectOffset'] = {'x': 0.0, 'y': 0.0}
        e['uvTransform'] = {'x': PPU, 'y': j['ax'] + w / 2, 'z': PPU, 'w': j['ay'] + h / 2}
        # these words are UI Images: the RectTransform box is what actually
        # sizes and positions them, the sprite alone is not enough
        tro = g.objs[j['tr']]
        t = tro.read_typetree()
        t['m_SizeDelta'] = {'x': w, 'y': h}
        t['m_AnchoredPosition']['x'] = float(j['cx'])
        t['m_LocalPosition']['x'] = float(j['cx'])
        tro.save_typetree(t)
    atlas_obj.save_typetree(atlas_tt)
    log(f'  resume    {len(jobs)} words repacked into page {page_id} rows {band[0]}..{y+shelf-1}, '
        f'{len(surplus)} blanked')


def _bake_own_texture(g, folder, manifest_dir, label):
    man = list(csv.DictReader(open(os.path.join(manifest_dir, 'manifest.csv'), encoding='utf-8')))
    norm = lambda s: re.sub(r'[\s_]+', '', os.path.splitext(s)[0]).lower()
    files = {norm(f): f for f in os.listdir(folder) if f.lower().endswith('.png')}
    done = 0
    for row in man:
        # Ten language variants share each name; the Russian one is picked by the
        # hash of its pixels. A hash identifies without carrying a copy of the
        # original artwork, which is what makes this package redistributable.
        want = row.get('sprite_sha256')
        best = None
        if want:
            for o in g.sprites(row['sprite']):
                if hashlib.sha256(o.read().image.convert('RGBA').tobytes()).hexdigest() == want:
                    best = o
                    break
            assert best is not None, (f'{row["sprite"]}: no variant matches the recorded hash '
                                      '— the game version is probably different')
        else:                                    # older manifests: fall back to pixels
            ref = Image.open(os.path.join(manifest_dir, row['file'])).convert('RGBA')
            best, score = None, 1e9
            for o in g.sprites(row['sprite']):
                s = mae(ref, o.read().image.convert('RGBA'))
                if s < score:
                    best, score = o, s
            assert best is not None and score < 25, f'{row["sprite"]}: no match ({score:.1f})'
        stt = best.read_typetree()
        tex, r, hit = g.texture_of(best)
        assert not hit, f'{row["sprite"]} unexpectedly atlas-packed'
        img = Image.open(os.path.join(folder, files[norm(row['file'])])).convert('RGBA')
        rx, ry, rw, rh = placement(tex.read_typetree(), img, r)
        TW, TH = paint(tex, img, rx, ry, rw, rh)
        open_fullrect(stt, TW, TH)
        best.save_typetree(stt)
        done += 1
    log(f'  {label:9} {done} images')


def stage_journal(g):
    _bake_own_texture(g, os.path.join(ART, 'journal'),
                      os.path.join(REF, 'journal_ru'), 'journal')


def stage_cutscenes(g):
    _bake_own_texture(g, os.path.join(ART, 'cutscenes'),
                      os.path.join(REF, 'cutscenes_ru'), 'cutscenes')


STAGES = [('font', stage_font), ('text', stage_text), ('label', stage_label),
          ('title', stage_title), ('computer', stage_computer_images),
          ('resume', stage_resume), ('journal', stage_journal),
          ('cutscenes', stage_cutscenes)]


def backup(g):
    made = []
    for p in (g.assets, g.ress):
        b = p + '.orig'
        if not os.path.exists(b):
            shutil.copyfile(p, b)
            made.append(os.path.basename(b))
    return made


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data_dir = sys.argv[1]
    verify_only = '--verify' in sys.argv
    if not os.path.isdir(PRIVATE):
        sys.exit('private/ not found: the translation and artwork are not part of '
                 'this repository. Install from Releases instead (see LICENSE).')
    g = Game(data_dir)
    if not verify_only:
        made = backup(g)
        log('backup:', ', '.join(made) if made else 'already present (kept)')
        log('applying:')
        for name, fn in STAGES:
            fn(g)
        size = g.save()
        log(f'\nresources.assets written ({size/1e6:.1f} MB)')
        log('done — launch the game with language set to Russian')
    else:
        from verify import verify
        verify(g)


if __name__ == '__main__':
    main()
