"""Fish pipeline, step 1b: the level and star rating of every fish from the game's own data (the FishParameter and
SpearfishingItem sheets, read through the xivapi data mirror), keyed by item id. The wiki's "Recommended Fishing
Level" is often just the fishing hole's level, so the game value wins in fish_build.py. Caches into
fish/fish_levels.json (gitignored); pass --refresh to fetch again."""
import json, os, sys, time, urllib.parse, urllib.request
API = 'https://beta.xivapi.com/api/1/sheet/'
FIELDS = 'Item.Name,GatheringItemLevel.GatheringItemLevel,GatheringItemLevel.Stars'
OUT = 'fish/fish_levels.json'

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def rows(sheet):
    out, after = [], None
    while True:
        q = {'fields': FIELDS, 'limit': 500}
        if after is not None: q['after'] = after
        batch = get(API + sheet + '?' + urllib.parse.urlencode(q)).get('rows', [])
        out += batch
        if len(batch) < 500: return out
        after = batch[-1]['row_id']; time.sleep(0.3)

def main():
    if os.path.exists(OUT) and '--refresh' not in sys.argv:
        print('cached', OUT, '(pass --refresh to fetch again)'); return
    levels = {}
    for sheet in ('FishParameter', 'SpearfishingItem'):
        for r in rows(sheet):
            f = r['fields']; item = f.get('Item') or {}; iid = item.get('value')
            name = ((item.get('fields') or {}).get('Name') or '').strip()
            g = (f.get('GatheringItemLevel') or {}).get('fields') or {}
            if iid and name and g.get('GatheringItemLevel'):
                levels.setdefault(str(iid), {'name': name, 'lv': g['GatheringItemLevel'], 'stars': g.get('Stars') or 0})
        print(sheet, 'read;', len(levels), 'fish so far', flush=True)
    os.makedirs('fish', exist_ok=True)
    json.dump(levels, open(OUT, 'w'), ensure_ascii=False)
    print('DONE', len(levels), 'fish levels cached')

if __name__ == '__main__':
    main()
