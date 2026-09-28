# FFXIV log tracker

Data pipeline for the private "Spellbook, Bestiary & Fishing Log" page: a checklist of all Blue Mage spells, Beastmaster beasts and fish for two characters, with level, location, and open-world filters.

- Live page: a private hosted copy of `tracker.html` (the link is deliberately kept out of this repo).
- Source: ffxiv.consolegameswiki.com (Blue Magic Spellbook, Master's Bestiary, Fish Guide, each spell/beast/fish page, every linked enemy and place via the MediaWiki API).

## Refresh after a patch

```bash
python3 run_all.py
```

Then republish `tracker.html` to the same hosted page (republishing keeps saved checks). Skim `report.txt` first: it lists every entry with its classified sources.

## Invariants

- `tracker.html` is generated. Edit `tracker.template.html` (page), `build_data.py` (spell and beast rules) or `fish_build.py` (fish rules), never the output.
- `fish.json` keeps every fish from the Fish Guide with its guide page and number (fishing and spearfishing are numbered separately). Levels and star ratings come from the game's own FishParameter and SpearfishingItem sheets (`fish_levels.py`, via the xivapi data mirror), because the wiki's "Recommended Fishing Level" is often just the fishing hole's level; the wiki value, then the hole level, are the fallbacks. Each spot is tagged open world / ocean / Diadem / island / moon / unknown and the page's toggles decide what is shown. Fish ids are the wiki's Garland Tools item ids, so saved checks survive a refresh.
- Saved checks live in the hosted page's database (`progress/<c1|c2>-<blu|bst>`), not in this repo. Republishing never touches them.
- `build_data.py` drops Savage, Unreal, Ultimate and level > 80 sources for Blue Mage (job cap), and only the hard-coded zone list counts as open world.
- Download caches (`pages/`, `enemies/`, `places/`) are re-fetched when missing; delete them to force a full refresh.

## Testing page changes

`python3 make_harness.py` writes `tracker.test.html`, the page plus a fake cloud database that returns frozen snapshots like the real one. Open it locally, toggle entries, and check `window.__writes` / `window.__errors` in the console. Automated browser clicks do not reach the hosted page's frame, so this harness is the reliable check.

## Tests

```bash
npm install   # once: pulls jsdom for the page tests
npm test
```

`tests/page.test.mjs` drives the built page in jsdom against `tests/fake_db.js` (a stand-in for the cloud database with the same frozen-snapshot behaviour): filters, search, grouping, confirmations, uncheck-all, sync, and per-character isolation. `tests/test_data.py` checks the classification rules in `build_data.py` and invariants of the generated `data.json`; `tests/test_fish.py` checks `fish.json`. Run the tests after any page change and after every data refresh.
