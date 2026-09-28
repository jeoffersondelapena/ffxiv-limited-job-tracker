"""Fish pipeline, step 2: turn the cached fish pages into fish.json. Every fish from the Fish Guide is
kept; each of its spots is tagged by where it is caught: open world (zones you walk and teleport
through), ocean fishing, the Diadem, the island, the moon, or other/unknown. The page decides what to show."""
import json, os, re, sys, collections, urllib.parse
sys.path.insert(0, './pylib')
import build_data as b

CATEGORY_ZONES = {'The Endeavor': 'ocean', 'The Diadem': 'diadem', 'Unnamed Island': 'island',
                  'Sinus Ardorum': 'moon', 'Phaenna': 'moon', 'The Moon': 'moon'}
CATEGORY_REGIONS = {'Ocean Fishing': 'ocean', 'Ishgardian Restoration': 'diadem', 'Island Sanctuary': 'island', 'Cosmic Exploration': 'moon'}
HOUSING = {'Mist', 'The Lavender Beds', 'Lavender Beds', 'The Goblet', 'Shirogane', 'Empyreum'}

def strip_links(s):
    s = re.sub(r'\{\{(?:item icon|i|action icon)\|([^}|]+)[^}]*\}\}', r'\1', s)
    s = re.sub(r'\{\{[^{}]*\}\}', '', s)                      # any other template (videos, notes)
    s = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)
    s = re.sub(r"'''", '', s)
    return re.sub(r'\s+', ' ', s).strip(' ,;')

def main():
    b.load_places()
    zones = set(b.ZONES) | HOUSING
    idx = json.load(open('fish/index_pages.json'))
    hole_zone, hole_region = {}, {}
    cur = [None, None, None]
    for line in (idx.get('Fishing Log') or '').split('\n'):
        m = re.match(r'^(=+)\s*(.*?)\s*=+\s*$', line)
        if m:
            lvl = len(m.group(1)); t = strip_links(m.group(2))
            cur[lvl - 1:] = [t] + [None] * (3 - lvl)
            continue
        m = re.match(r'^\*\s*\[\[(?:Fishing|Spearfishing) Log: ([^\]|]+)', line)
        if m:
            hole = m.group(1).strip()
            hole_region[hole] = cur[0]
            hole_zone[hole] = cur[2] if cur[2] in zones else ('Ultima Thule' if cur[2] == 'Elysion' else None)

    fish_list = json.load(open('fish/fish_list.json'))
    pages = json.load(open('fish/pages.json'))
    game = json.load(open('fish/fish_levels.json')) if os.path.exists('fish/fish_levels.json') else {}  # from fish_levels.py
    out, stats = [], collections.Counter()
    seen = set()
    for f in fish_list:
        wt = pages.get(f['title']) or ''
        m = re.search(r"Recommended \[\[(?:Fishing|Spearfishing)\]\] Level''':\s*(\d+)", wt)
        lv = int(m.group(1)) if m else None
        if lv is not None and not 1 <= lv <= 100: lv = None      # a wiki typo such as "360"
        ft = re.search(r"\*'''Fish Type''':\s*(.*)", wt)
        ftype = strip_links(ft.group(1)) if ft else ''
        gt = re.search(r'\|\s*id-gt\s*=\s*(\d+)', wt)
        fid = int(gt.group(1)) if gt else None
        g = game.get(str(fid)) if fid is not None else None
        stars = 0
        if g and 1 <= (g.get('lv') or 0) <= 100:      # the game's own level beats the wiki's, which is often the hole level
            lv, stars = g['lv'], g.get('stars') or 0
            stats['level from game data'] += 1
        elif lv is not None:
            stats['level from wiki'] += 1
        spots = []
        for sec in re.finditer(r'^===\s*\[\[(?:Fishing|Spearfishing) Log: ([^\]|]+)(?:\|[^\]]*)?\]\][^\n]*===\s*$(.*?)(?=^==|\Z)', wt, re.M | re.S):
            hole = strip_links(sec.group(1)); body = sec.group(2)
            loc = re.search(r"\*'''\[\[Location\]\]''':[ \t]*(.*)", body)
            zone = xy = None
            if loc:
                z = re.search(r'\[\[([^\]|]+)', loc.group(1))
                zone = urllib.parse.unquote(strip_links(z.group(1))) if z else None
                c = re.search(r'\{\{coords\|([^}]+)\}\}', loc.group(1)); xy = b.norm_xy(c.group(1)) if c else None
            if zone == 'Lavender Beds': zone = 'The Lavender Beds'
            if zone not in zones and zone not in CATEGORY_ZONES: zone = hole_zone.get(hole) or zone
            region = hole_region.get(hole)
            cat = ('world' if zone in zones else CATEGORY_ZONES.get(zone) or CATEGORY_REGIONS.get(region) or 'unknown')
            hl = re.search(r"Hole Level''':[ \t]*(\d+)", body)
            notes = []
            for label, pat in (('bait', r"\[\[Baits?\]\]''':[ \t]*(.*)"), ('mooch', r"\[\[Mooch\]\]ed From''':[ \t]*(.*)"),
                               ('weather', r"\[\[Weather\]\]''':[ \t]*(.*)"), ('time', r"Time''':[ \t]*(.*)"), ('', r"Condition''':[ \t]*(.*)")):
                mm = re.search(pat, body)
                if mm:
                    v = strip_links(mm.group(1))
                    if v and v.lower() not in ('n/a', 'any', 'none', '-', '?'): notes.append((label + ' ' + v).strip())
            spots.append(dict(k=cat, name=hole, loc=zone if (zone in zones or zone in CATEGORY_ZONES) else (region or 'Unknown'),
                              xy=xy if cat == 'world' else None, holeLv=int(hl.group(1)) if hl else None, note='; '.join(notes)[:160]))
        # Older pages list spots in a "Fishing Locations" table: Area | Location | Hole Level | Baits | Mooch | Condition | Weather
        for row in re.finditer(r'^\|\s*\[\[(?:Fishing|Spearfishing) Log: ([^\]|]+)(?:\|[^\]]*)?\]\]\s*\|\|(.*)$', wt, re.M):
            hole = strip_links(row.group(1)); cells = [c.strip() for c in row.group(2).split('||')]
            if any(s['name'] == hole for s in spots) or not cells: continue
            z = re.search(r'\[\[([^\]|]+)', cells[0]); zone = urllib.parse.unquote(strip_links(z.group(1))) if z else None
            if zone == 'Lavender Beds': zone = 'The Lavender Beds'
            c = re.search(r'\{\{coords\|([^}]+)\}\}', cells[0]); xy = b.norm_xy(c.group(1)) if c else None
            if zone not in zones and zone not in CATEGORY_ZONES: zone = hole_zone.get(hole) or zone
            region = hole_region.get(hole)
            cat = ('world' if zone in zones else CATEGORY_ZONES.get(zone) or CATEGORY_REGIONS.get(region) or 'unknown')
            hl = re.search(r'(\d+)', cells[1]) if len(cells) > 1 else None
            notes = []
            for label, i in (('bait', 2), ('mooch', 3), ('', 4), ('weather', 5)):
                if len(cells) > i:
                    v = strip_links(cells[i])
                    if v and v.lower() not in ('n/a', 'any', 'none', '-', '?'): notes.append((label + ' ' + v).strip())
            spots.append(dict(k=cat, name=hole, loc=zone if (zone in zones or zone in CATEGORY_ZONES) else (region or 'Unknown'),
                              xy=xy if cat == 'world' else None, holeLv=int(hl.group(1)) if hl else None, note='; '.join(notes)[:160]))
        if lv is None:
            hl = [s['holeLv'] for s in spots if s['holeLv']]
            lv = min(hl) if hl else None
            stats['level from hole' if hl else 'no level at all'] += 1
        if not spots:
            spots = [dict(k='unknown', name='No fishing spot listed on the wiki', loc='Unknown', xy=None, holeLv=None, note='')]
            stats['no spot on the wiki'] += 1
        if fid is None or fid in seen:
            fid = 900000 + len(out); stats['no stable id'] += 1
        seen.add(fid)
        for s in spots:
            s['lv'] = lv if lv is not None else 101
            s.pop('holeLv', None)
            for k in list(s):
                if s[k] in (None, ''): del s[k]
        cats = sorted({s['k'] for s in spots})
        for c in cats: stats['spots in: ' + c] += 1
        out.append(dict(id=fid, name=f['name'], lv=lv, stars=stars, kind=f['kind'], type=ftype, page=int(f['page']), no=int(f['no']), sources=spots))
    out.sort(key=lambda e: (e['lv'] if e['lv'] is not None else 999, e['name']))
    json.dump(out, open('fish.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(out), 'fish kept of', len(fish_list), 'listed;', sum(e['kind'] == 'spear' for e in out), 'spearfishing')
    print('stats:', dict(stats))
    unknown = [e['name'] for e in out if any(s['k'] == 'unknown' for s in e['sources'])]
    print('fish with an unknown spot:', len(unknown), unknown[:10])
    bands = collections.Counter('unknown' if e['lv'] is None else '1-15' if e['lv'] <= 15 else '16-30' if e['lv'] <= 30 else f"{(e['lv']-1)//10*10+1}-{(e['lv']-1)//10*10+10}" for e in out)
    print('per band:', dict(bands))

if __name__ == '__main__':
    main()
