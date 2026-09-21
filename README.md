# FFXIV limited-job tracker

Data pipeline for the private "Spellbook & Bestiary" page: a checklist of all Blue Mage spells and Beastmaster beasts for two characters, with level, location, and open-world filters.

- Live page: a private hosted copy of `tracker.html` (the link is deliberately kept out of this repo).
- Source: ffxiv.consolegameswiki.com (Blue Magic Spellbook, Master's Bestiary, each spell/beast page, every linked enemy and place via the MediaWiki API).

## Refresh after a patch

```bash
python3 run_all.py
```

Then republish `tracker.html` to the same hosted page (republishing keeps saved checks). Skim `report.txt` first: it lists every entry with its classified sources.

## Invariants

- `tracker.html` is generated. Edit `tracker.template.html` (page) or `build_data.py` (data rules), never the output.
- Saved checks live in the hosted page's database (`progress/<c1|c2>-<blu|bst>`), not in this repo. Republishing never touches them.
- `build_data.py` drops Savage, Unreal, Ultimate and level > 80 sources for Blue Mage (job cap), and only the hard-coded zone list counts as open world.
- Download caches (`pages/`, `enemies/`, `places/`) are re-fetched when missing; delete them to force a full refresh.
