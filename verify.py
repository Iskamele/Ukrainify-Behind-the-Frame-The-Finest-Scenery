# -*- coding: utf-8 -*-
"""Post-install check. Run via:  python apply.py "<...>/Behind the Frame_Data" --verify

Installing opens every cropped textureRect out to the whole texture, so the
original rects are read back from the untouched .orig backup that sits beside
the game files.
"""
import os, sys, csv, io, re, struct
from collections import defaultdict
from PIL import Image
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
ART = os.path.join(HERE, 'private', 'art')
REF = os.path.join(HERE, 'reference')
UK_CHARS = 'ҐЄІЇЦШЩЬЮґєії’…'


def _pristine_rects(orig_path):
    """path_id -> (original textureRect, was_atlas_packed)"""
    env = UnityPy.load(orig_path)
    atlas = {}
    for o in env.objects:
        if o.type.name == 'SpriteAtlas':
            for key, v in o.read_typetree()['m_RenderDataMap']:
                g, l = key
                atlas[(tuple(g.values()), l)] = v
    out = {}
    for o in env.objects:
        if o.type.name != 'Sprite':
            continue
        t = o.read_typetree()
        g, l = t['m_RenderDataKey']
        hit = atlas.get((tuple(g.values()), l))
        out[o.path_id] = (hit['textureRect'] if hit else t['m_RD']['textureRect'], bool(hit))
    return out


def verify(g):
    import apply as A
    fails = []

    def ok(label, cond, detail=''):
        print(f'  {"PASS" if cond else "FAIL"}  {label:34} {detail}')
        if not cond:
            fails.append(label)

    orig = g.assets + '.orig'
    prect = _pristine_rects(orig) if os.path.exists(orig) else {}
    if not prect:
        print('  (no .orig backup found — rect checks will be skipped)')

    def crop_of(sprite_obj, art):
        """The region the art was installed into, read back out of the game."""
        tex, cur, _ = g.texture_of(sprite_obj)
        tt = tex.read_typetree()
        r0 = prect.get(sprite_obj.path_id, (cur, False))[0]
        rx, ry, rw, rh = A.placement(tt, art, r0)
        page = tex.read().image.convert('RGBA')
        TH = tt['m_Height']
        return page.crop((rx, TH - ry - rh, rx + rw, TH - ry))

    # 1 font
    font = next(o for o in g.env.objects if o.type.name == 'Font'
                and o.read_typetree().get('m_Name') == A.FONT_NAME)
    cps = {r['index'] for r in font.read_typetree()['m_CharacterRects']}
    ok('font glyph table', len(cps) == 154, f'{len(cps)} glyphs')
    ok('ukrainian glyphs baked', all(ord(c) in cps for c in UK_CHARS))

    # 2 text
    ta = next(o for o in g.env.objects if o.type.name == 'TextAsset'
              and o.read_typetree().get('m_Name') == A.LANG_SLOT)
    rows = [r for r in csv.reader(io.StringIO(ta.read_typetree()['m_Script'])) if r]
    ok('translation rows', len(rows) == 703, str(len(rows)))
    bad = {c for r in rows if len(r) > 1 for c in r[1] if c not in '\r\n' and ord(c) not in cps}
    ok('every character renderable', not bad, ''.join(sorted(bad)))
    uk = sum(1 for r in rows if len(r) > 1 and any(c in 'іїєґІЇЄҐ' for c in r[1]))
    ok('rows using ukrainian letters', uk > 500, str(uk))

    # 3 language label
    KEY = b'Languages/TypeSettings/Russian'
    mb = next(o for o in g.env.objects
              if o.type.name == 'MonoBehaviour' and KEY in o.get_raw_data())
    raw = mb.get_raw_data()
    i = raw.find(KEY) + len(KEY)
    while i % 4:
        i += 1
    n = struct.unpack('<i', raw[i:i + 4])[0]
    q = i + 4 + n
    while q % 4:
        q += 1
    ln = struct.unpack('<i', raw[q:q + 4])[0]
    ok('language label', raw[q + 4:q + 4 + ln].decode('utf-8') == A.NEW_LABEL)

    # 4-5 title + the two computer images
    for name, path, atlas_expected in (
            ('press_text_ru', os.path.join(ART, 'title', 'press_text.png'), False),
            ('puzzle_computer_ch4_resume_ru', os.path.join(ART, 'computer', 'ch4_resume.png'), True),
            ('puzzle_computer_popup_background_ru', os.path.join(ART, 'computer', 'popup_background.png'), True)):
        sp = g.one(name)
        art = Image.open(path).convert('RGBA')
        score = A.mae(crop_of(sp, art), art)
        quad = sp.read_typetree()['m_RD']['m_VertexData']['m_VertexCount'] == 4
        _, _, hit = g.texture_of(sp)
        good = score < 6 and (bool(hit) if atlas_expected else quad)
        ok(name[:32], good, f'MAE {score:.2f}' + (' (atlas page)' if atlas_expected else f', quad {quad}'))

    # 6 resume
    layout = A._resume_layout(g)
    ua = defaultdict(list)
    for f in sorted(os.listdir(os.path.join(ART, 'resume'))):
        if f.endswith('.png'):
            ua[int(f.split('-')[0])].append(f)
    bad_words, blanked = [], 0
    for i, row in enumerate(layout, 1):
        for j, slot in enumerate(row):
            sp = g.objs[slot['sprite_id']]
            tex, r, _ = g.texture_of(sp)
            rx, ry, rw, rh = A.rect_px(r)
            page = tex.read().image.convert('RGBA')
            crop = page.crop((rx, 2048 - ry - rh, rx + rw, 2048 - ry))
            if j < len(ua[i]):
                src = Image.open(os.path.join(ART, 'resume', ua[i][j])).convert('RGBA')
                if (slot['w'], slot['h']) != (src.width, src.height) or A.mae(crop, src) >= 2:
                    bad_words.append(f'row{i}#{j}')
            else:
                blanked += sum(1 for p in crop.split()[-1].get_flattened_data() if p > 8) == 0
    ok('resume words', not bad_words,
       f'{sum(len(v) for v in ua.values())} placed' + (f', bad: {bad_words}' if bad_words else ''))
    ok('surplus word blanked', blanked == 1)

    # 7-8 own-texture art
    #
    # Each of these names exists in ten language variants. Checking that *some*
    # variant carries the Ukrainian art is not enough — an earlier bug painted
    # five of them onto the German/Spanish sprite and this check still passed.
    # So: find the object that was the Russian one in the untouched backup, and
    # confirm that exact object is the one now carrying the new artwork.
    import hashlib
    porig_sprites = {}
    if os.path.exists(orig):
        env0 = UnityPy.load(orig)
        for o in env0.objects:
            if o.type.name == 'Sprite':
                porig_sprites.setdefault(o.read_typetree().get('m_Name'), []).append(o)

    norm = lambda s: re.sub(r'[\s_]+', '', os.path.splitext(s)[0]).lower()
    for label, folder, mdir in (('journal', 'journal', 'journal_ru'),
                                ('cutscenes', 'cutscenes', 'cutscenes_ru')):
        man = list(csv.DictReader(open(os.path.join(REF, mdir, 'manifest.csv'), encoding='utf-8')))
        files = {norm(f): f for f in os.listdir(os.path.join(ART, folder))}
        worst, worstname, misrouted = 0.0, '', []
        for row in man:
            art = Image.open(os.path.join(ART, folder, files[norm(row['file'])])).convert('RGBA')
            want = row.get('sprite_sha256')
            target = None
            for o in porig_sprites.get(row['sprite'], []):
                if hashlib.sha256(o.read().image.convert('RGBA').tobytes()).hexdigest() == want:
                    target = o.path_id
                    break
            if target is None:
                misrouted.append(f'{row["sprite"]}: not found in backup')
                continue
            sp = g.objs[target]
            if sp.read_typetree()['m_RD']['m_VertexData']['m_VertexCount'] != 4:
                misrouted.append(f'{row["sprite"]}: id {target} was not patched')
                continue
            score = A.mae(crop_of(sp, art), art)
            if score > worst:
                worst, worstname = score, row['sprite']
        ok(f'{label} art', worst < 6 and not misrouted,
           f'{len(man)} images, worst MAE {worst:.2f} ({worstname})'
           + (f'; MISROUTED: {misrouted}' if misrouted else ''))

    print()
    print('RESULT:', 'all checks passed' if not fails else f'{len(fails)} FAILED: {fails}')
    return not fails
