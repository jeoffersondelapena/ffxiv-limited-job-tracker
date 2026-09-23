"""Writes tracker.test.html: the built page plus the fake cloud database from tests/fake_db.js
(deep-frozen snapshots, set() echoing a snapshot, one seeded check). Open it in a browser and toggle
entries; window.__writes lists the saves and window.__errors any thrown errors."""
import os
here = os.path.dirname(os.path.abspath(__file__))
fake = open(os.path.join(here, "tests", "fake_db.js"), encoding="utf-8").read()
page = open(os.path.join(here, "tracker.html"), encoding="utf-8").read()
open(os.path.join(here, "tracker.test.html"), "w", encoding="utf-8").write("<script>\n" + fake + "\n</script>\n" + page)
print("tracker.test.html written")
