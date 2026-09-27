"""Fish pipeline, step 1: list every fish from the Fish Guide, then fetch each fish's wikitext plus the
Fishing Log / Spearfishing Log index pages (spot -> zone). Caches into fish/ (gitignored)."""
import json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, './pylib')
from bs4 import BeautifulSoup
API = 'https://ffxiv.consolegameswiki.com/mediawiki/api.php'
BASE = 'https://ffxiv.consolegameswiki.com'
os.makedirs('fish', exist_ok=True)
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=60).read()
def title_of(href): return urllib.parse.unquote(href.split('/wiki/', 1)[1]).replace('_', ' ')
def wikitexts(titles):
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        q = urllib.parse.urlencode({'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main', 'format': 'json',
                                    'formatversion': '2', 'redirects': '1', 'titles': '|'.join(batch)})
        r = json.loads(get(API + '?' + q))
        red = {x['from']: x['to'] for x in r['query'].get('redirects', [])}
        norm = {x['from']: x['to'] for x in r['query'].get('normalized', [])}
        pages = {p['title']: p for p in r['query']['pages']}
        for t in batch:
            key = red.get(norm.get(t, t), norm.get(t, t))
            p = pages.get(key)
            out[t] = p['revisions'][0]['slots']['main']['content'] if p and 'revisions' in p else None
        print('  batch', i // 50 + 1, 'of', (len(titles) + 49) // 50, flush=True)
        time.sleep(0.4)
    return out

if not os.path.exists('fish/fish_guide.html'):
    open('fish/fish_guide.html', 'wb').write(get(BASE + '/wiki/Fish_Guide'))
s = BeautifulSoup(open('fish/fish_guide.html').read(), 'html.parser')
tables = s.select('#mw-content-text table')
fish = []
for kind, t in (('fish', tables[0]), ('spear', tables[1])):
    for r in t.select('tr')[1:]:
        td = r.select('td')
        if len(td) < 3: continue
        a = [x for x in td[2].select('a[href^="/wiki/"]') if x.get_text(strip=True)]
        if not a: continue
        fish.append({'kind': kind, 'name': a[-1].get_text(' ', strip=True), 'title': title_of(a[-1]['href']),
                     'page': td[0].get_text(strip=True), 'no': td[1].get_text(strip=True),
                     'bait': td[3].get_text(' ', strip=True) if kind == 'fish' else ''})
json.dump(fish, open('fish/fish_list.json', 'w'), ensure_ascii=False, indent=0)
print(len(fish), 'fish listed:', sum(f['kind'] == 'fish' for f in fish), 'fishing,', sum(f['kind'] == 'spear' for f in fish), 'spearfishing', flush=True)

idx = wikitexts(['Fishing Log', 'Spearfishing Log', 'Fishing Locations'])
json.dump(idx, open('fish/index_pages.json', 'w'), ensure_ascii=False)
have = {}
if os.path.exists('fish/pages.json'): have = json.load(open('fish/pages.json'))
todo = sorted({f['title'] for f in fish} - set(have))
print(len(todo), 'fish pages to fetch', flush=True)
have.update(wikitexts(todo))
json.dump(have, open('fish/pages.json', 'w'), ensure_ascii=False)
print('DONE', len(have), 'pages cached;', sum(1 for v in have.values() if v is None), 'missing', flush=True)
