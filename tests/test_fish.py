"""Invariants of the generated fish.json: every fish from the Fish Guide is present, with a stable id,
a level in range (or none), and every spot tagged with a known category."""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATS = {"world", "ocean", "diadem", "island", "moon", "unknown"}


class FishDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "fish.json"), encoding="utf-8") as f:
            cls.fish = json.load(f)

    def test_nothing_is_lost(self):
        self.assertGreaterEqual(len(self.fish), 1700, "the Fish Guide lists about 1,700 fish; a refresh must keep them all")
        ids = [e["id"] for e in self.fish]
        self.assertEqual(len(ids), len(set(ids)), "ids must be unique: saved checks are keyed by them")
        names = [e["name"] for e in self.fish]
        self.assertEqual(len(names), len(set(names)), "names must be unique: the name is what gets copied")

    def test_every_fish_is_well_formed(self):
        for e in self.fish:
            self.assertTrue(e["name"], e)
            self.assertIn(e["kind"], ("fish", "spear"), e["name"])
            self.assertTrue(e["lv"] is None or 1 <= e["lv"] <= 100, (e["name"], e["lv"]))
            self.assertTrue(0 <= e["stars"] <= 5, (e["name"], e["stars"]))
            self.assertTrue(e["sources"], e["name"] + " has no spot at all")
            for s in e["sources"]:
                self.assertIn(s["k"], CATS, (e["name"], s))
                self.assertTrue(s["name"] and s.get("loc"), (e["name"], s))
                if s["k"] == "world":
                    self.assertNotIn(s["loc"], ("Unknown", "The Endeavor", "The Diadem"), (e["name"], s))

    def test_fish_guide_page_and_number(self):
        """The Fish Guide numbers fish 1-100 within each page, separately for fishing and spearfishing."""
        seen = set()
        for e in self.fish:
            self.assertTrue(1 <= e["no"] <= 100, (e["name"], e["no"]))
            self.assertGreaterEqual(e["page"], 1, e["name"])
            key = (e["kind"], e["page"], e["no"])
            self.assertNotIn(key, seen, e["name"])
            seen.add(key)
        first = next(e for e in self.fish if e["kind"] == "fish" and e["page"] == 1 and e["no"] == 1)
        self.assertEqual(first["name"], "Malm Kelp")

    def test_sorted_by_level_then_name(self):
        keys = [((e["lv"] if e["lv"] is not None else 999), e["name"]) for e in self.fish]
        self.assertEqual(keys, sorted(keys))

    def test_well_known_fish(self):
        by = {e["name"]: e for e in self.fish}
        self.assertEqual(by["Crayfish"]["lv"], 2)
        # these two have no level line on the wiki; the hole level (15) is wrong, the game data says 20
        self.assertEqual(by["Bluebell Salmon"]["lv"], 20)
        self.assertEqual(by["Razor Clam"]["lv"], 20)
        self.assertTrue(any(s["k"] == "world" and s["loc"] == "Central Shroud" for s in by["Crayfish"]["sources"]))
        self.assertTrue(all(s["k"] == "ocean" for s in by["Merlthor Goby"]["sources"]) or any(s["k"] == "world" for s in by["Merlthor Goby"]["sources"]))
        ocean_only = [e["name"] for e in self.fish if all(s["k"] == "ocean" for s in e["sources"])]
        self.assertGreater(len(ocean_only), 100, "ocean-fishing-only fish are kept, just tagged")


if __name__ == "__main__":
    unittest.main()
