"""Step 7: embed data.json (with resolved image URLs) into tracker.template.html -> tracker.html."""
import json
d = json.load(open('data.json')); urls = json.load(open('image_urls.json'))
for l in d.values():
    for e in l:
        for s in e['sources']:
            if s.get('img') and not s['img'].startswith('http'):
                s['img'] = urls.get(s['img'], 'https://ffxiv.consolegameswiki.com/wiki/File:' + s['img'].replace(' ', '_'))
tpl = open('tracker.template.html').read()
assert '/*__DATA__*/null' in tpl
html = tpl.replace('/*__DATA__*/null', json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'), 1)
open('tracker.html', 'w').write(html)
print('tracker.html written:', len(html.encode()), 'bytes;', len(d['blu']), 'spells,', len(d['bst']), 'beasts')
