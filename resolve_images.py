"""Step 6: turn the map image file names referenced in data.json into direct image URLs (image_urls.json)."""
import json, time, urllib.parse, urllib.request
API = 'https://ffxiv.consolegameswiki.com/mediawiki/api.php'
d = json.load(open('data.json'))
files = sorted({s['img'] for l in d.values() for e in l for s in e['sources'] if s.get('img') and not s['img'].startswith('http')})
urls = {}
for i in range(0, len(files), 50):
    batch = files[i:i + 50]
    q = urllib.parse.urlencode({'action': 'query', 'prop': 'imageinfo', 'iiprop': 'url', 'format': 'json', 'formatversion': '2',
                                'redirects': '1', 'titles': '|'.join('File:' + f for f in batch)})
    req = urllib.request.Request(API + '?' + q, headers={'User-Agent': 'Mozilla/5.0'})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    norm = {n['from']: n['to'] for n in r['query'].get('normalized', [])}
    red = {x['from']: x['to'] for x in r['query'].get('redirects', [])}
    pages = {p['title']: p for p in r['query']['pages']}
    for f in batch:
        t = 'File:' + f; t = norm.get(t, t); t = red.get(t, t)
        p = pages.get(t)
        urls[f] = p['imageinfo'][0]['url'] if p and p.get('imageinfo') else \
            'https://ffxiv.consolegameswiki.com/wiki/' + urllib.parse.quote(('File:' + f).replace(' ', '_'))
    time.sleep(0.3)
json.dump(urls, open('image_urls.json', 'w'), indent=1)
print(len(urls), 'image URLs resolved')
