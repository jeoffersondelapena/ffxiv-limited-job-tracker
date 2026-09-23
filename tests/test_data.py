"""Tests for the data rules in build_data.py and invariants of the generated data.json."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pylib"))
os.chdir(ROOT)

import build_data as b  # noqa: E402

KINDS = {"world", "fate", "leve", "hunt", "map", "dungeon", "trial", "raid", "carnivale", "guildhest", "tdungeon", "totem", "questmob", "quest", "default"}
INSTANCE = {"dungeon", "trial", "raid", "carnivale", "guildhest", "tdungeon"}


def fake_enemy(title, fields=None, rows=None, wt="", img=None):
    b.enemies[title] = dict(fields=fields or {}, rows=rows or [], wt=wt, img=img)


class HelperTests(unittest.TestCase):
    def test_lv_parse(self):
        self.assertEqual(b.lv_parse("50"), (50, None))
        self.assertEqual(b.lv_parse("44-50"), (44, 50))
        self.assertEqual(b.lv_parse("12–17"), (12, 17))
        self.assertEqual(b.lv_parse("-"), (None, None))
        self.assertEqual(b.lv_parse(""), (None, None))

    def test_norm_xy(self):
        self.assertEqual(b.norm_xy("16,15"), "16, 15")
        self.assertEqual(b.norm_xy(" 26.5,23.1 "), "26.5, 23.1")
        self.assertIsNone(b.norm_xy(""))
        self.assertIsNone(b.norm_xy("50"))

    def test_base_strips_difficulty(self):
        self.assertEqual(b.base("The Whorleater (Hard)"), "The Whorleater")
        self.assertEqual(b.base("Sastasha"), "Sastasha")


class PlaceTests(unittest.TestCase):
    def setUp(self):
        b.load_places()  # no places/ cache in the repo: only the hard-coded zones and Carnivale stages

    def test_zones_and_stages_are_known(self):
        self.assertEqual(b.resolve_place("Central Shroud")[1]["kind"], "zone")
        self.assertEqual(b.resolve_place("Sea of Clouds")[0], "The Sea of Clouds", "alias is normalised")
        stage = b.resolve_place("Miss Typhon")[1]
        self.assertEqual((stage["kind"], stage["level"], stage["stage"]), ("carnivale", 50, 20))

    def test_savage_unreal_ultimate_are_skipped(self):
        for name in ("Alphascape V3.0 (Savage)", "The Whorleater (Unreal)", "The Epic of Alexander (Ultimate)"):
            self.assertEqual(b.resolve_place(name)[1]["kind"], "skip", name)

    def test_extreme_falls_back_to_the_known_difficulty(self):
        b.place["The Whorleater (Hard)"] = dict(kind="trial", level=50)
        self.assertEqual(b.resolve_place("The Whorleater (Extreme)")[1]["kind"], "trial")

    def test_unknown_place_is_reported_not_guessed(self):
        self.assertIsNone(b.resolve_place("Nowhere In Particular")[1])
        self.assertIn("Nowhere In Particular", b.unknown)


class EnemyClassificationTests(unittest.TestCase):
    def setUp(self):
        b.load_places()
        b.enemies.clear()
        b.place["Haukke Manor"] = dict(kind="dungeon", level=28)
        b.place["The Dragon's Neck"] = dict(kind="trial", level=50)
        b.place["Sigmascape V3.0"] = dict(kind="raid", level=70)

    def kinds(self, sources):
        return [(s["k"], s["loc"], s["lv"]) for s in sources]

    def test_regular_mob_with_spots_in_several_zones(self):
        fake_enemy("Treant Sapling", fields={"name": "Treant Sapling", "level": "12-17"}, rows=[
            ("Central Shroud", "27,15", "12"), ("North Shroud", "30,26", "12"), ("Central Shroud", "21,17", "17")])
        src = b.enemy_sources("Treant Sapling")
        self.assertEqual(self.kinds(src), [("world", "Central Shroud", 12), ("world", "North Shroud", 12)])
        self.assertEqual(src[0]["note"], "several spots")
        self.assertEqual(src[0]["xy"], "27, 15")

    def test_hunt_mark_uses_rank_and_hides_coordinates(self):
        fake_enemy("Cornu", fields={"location": "Outer La Noscea", "rank": "A", "level": "50"}, rows=[("Outer La Noscea", "16,18", "50"), ("Outer La Noscea", "15,18", "50")])
        (s,) = b.enemy_sources("Cornu")
        self.assertEqual((s["k"], s["rank"], s["xy"], s["note"]), ("hunt", "A", None, "A-rank hunt mark"))

    def test_treasure_map_mob_collapses_to_one_source(self):
        fake_enemy("Alpha Zu", fields={"level": "50", "goal": "Unhidden Leather Map"}, rows=[("Upper La Noscea", "26,23", "50"), ("Middle La Noscea", "15,10", "50")])
        (s,) = b.enemy_sources("Alpha Zu")
        self.assertEqual((s["k"], s["loc"], s["note"], s["xy"]), ("map", "Treasure map", "Unhidden Leather Map", None))

    def test_levequest_mob_is_marked(self):
        fake_enemy("Denizen of the Dark", fields={"location": "Mor Dhona", "coordinates": "24,12", "level": "44-48"},
                   rows=[("Mor Dhona", "24,12", "44-48")], wt="It only appears during the levequest after collecting all 5 pages.")
        (s,) = b.enemy_sources("Denizen of the Dark")
        self.assertEqual((s["k"], s["loc"], s["lv"], s["lvMax"]), ("leve", "Mor Dhona", 44, 48))

    def test_coordinate_less_zone_rows_are_dropped_when_better_rows_exist(self):
        fake_enemy("Magitek Vanguard", fields={"level": "44-50"}, rows=[("Lower La Noscea", "", "22"), ("Northern Thanalan", "15.8,14.7", "49")])
        self.assertEqual(self.kinds(b.enemy_sources("Magitek Vanguard")), [("world", "Northern Thanalan", 49)])

    def test_duty_boss_never_becomes_an_open_world_source(self):
        fake_enemy("Zu (Boss)", fields={"name": "Zu", "dungeon": "Pharos Sirius", "objective": "boss", "level": "50"},
                   rows=[("Pharos Sirius", "", "50"), ("Outer La Noscea", "14,14", "50")])
        b.place["Pharos Sirius"] = dict(kind="dungeon", level=50)
        src = b.enemy_sources("Zu (Boss)")
        self.assertEqual(self.kinds(src), [("dungeon", "Pharos Sirius", 50)])
        self.assertEqual(src[0]["name"], "Zu")

    def test_carnivale_stage_gets_stage_level_and_note(self):
        fake_enemy("Ultros", fields={"trial": "The Dragon's Neck", "objective": "boss", "level": "50-70"},
                   rows=[("The Dragon's Neck", "", "50"), ("Central Thanalan", "23.5,34.0", "-"), ("Miss Typhon", "", "50"), ("Sigmascape V3.0 (Savage)", "", "70")])
        src = b.enemy_sources("Ultros")
        self.assertEqual(self.kinds(src), [("trial", "The Dragon's Neck", 50), ("carnivale", "Miss Typhon", 50)])
        self.assertEqual(src[1]["note"], "Stage 20")

    def test_location_image_only_where_it_cannot_mislead(self):
        fake_enemy("Axe Beak", fields={"level": "25-26"}, img="axe-beak-map.jpg",
                   rows=[("Eastern Thanalan", "23.7,18.6", "25-26"), ("Western La Noscea", "23.4,23.6", "13")])
        src = {s["loc"]: s for s in b.enemy_sources("Axe Beak")}
        self.assertIsNone(src["Eastern Thanalan"].get("img"), "ambiguous: two places, file name names neither")
        self.assertIsNone(src["Western La Noscea"].get("img"))
        fake_enemy("Arbor Buzzard", fields={"level": "7"}, img="Arbor_Buzzard_Central_Shroud_Map.jpg",
                   rows=[("Central Shroud", "28,29", "7"), ("East Shroud", "20,20", "9")])
        src = {s["loc"]: s for s in b.enemy_sources("Arbor Buzzard")}
        self.assertEqual(src["Central Shroud"]["img"], "Arbor_Buzzard_Central_Shroud_Map.jpg", "file name names the zone")
        self.assertIsNone(src["East Shroud"].get("img"))
        fake_enemy("Salt Dhruva", fields={"level": "69"}, img="Salt Dhruva Location.png", rows=[("The Lochs", "22,23", "69")])
        self.assertEqual(b.enemy_sources("Salt Dhruva")[0]["img"], "Salt Dhruva Location.png", "single place: unambiguous")

    def test_unknown_enemy_falls_back_to_the_main_table_hint(self):
        src = b.enemy_sources("Mystery Mob", fallback=dict(kind="dungeon", place="Haukke Manor", lv=28))
        self.assertEqual(self.kinds(src), [("dungeon", "Haukke Manor", 28)])
        self.assertEqual(b.enemy_sources("Mystery Mob"), [])


class DataInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
            cls.data = json.load(f)
        with open(os.path.join(ROOT, "image_urls.json"), encoding="utf-8") as f:
            cls.image_urls = json.load(f)  # data.json keeps wiki file names; inject.py swaps in these URLs

    def test_counts_and_ids(self):
        self.assertEqual(len(self.data["blu"]), 124)
        self.assertEqual(len(self.data["bst"]), 50)
        for key in ("blu", "bst"):
            ids = [e["id"] for e in self.data[key]]
            self.assertEqual(ids, list(range(1, len(ids) + 1)), key)

    def test_every_entry_and_source_is_well_formed(self):
        for key, cap in (("blu", 80), ("bst", 100)):
            for e in self.data[key]:
                self.assertTrue(e["name"], e)
                self.assertGreaterEqual(e["minLv"], 1, e["name"])
                self.assertTrue(e["sources"], e["name"] + " has no sources")
                for s in e["sources"]:
                    self.assertIn(s["k"], KINDS, (e["name"], s))
                    self.assertTrue(s["name"], (e["name"], s))
                    self.assertTrue(1 <= s["lv"] <= cap, (e["name"], s))
                    if s.get("lvMax"):
                        self.assertGreater(s["lvMax"], s["lv"], (e["name"], s))
                    if s["k"] in INSTANCE or s["k"] in {"world", "fate", "leve", "hunt", "questmob"}:
                        self.assertTrue(s.get("loc"), (e["name"], s))
                    if s["k"] == "hunt":
                        self.assertIn(s.get("rank"), ("A", "B", "S"), (e["name"], s))
                    if s.get("img"):
                        self.assertTrue(s["img"].startswith("https://") or s["img"] in self.image_urls, (e["name"], s))

    def test_no_savage_unreal_or_ultimate_sources(self):
        for key in ("blu", "bst"):
            for e in self.data[key]:
                for s in e["sources"]:
                    self.assertNotRegex(s.get("loc", ""), r"\((Savage|Unreal|Ultimate)\)", (e["name"], s))

    def test_well_known_facts(self):
        blu = {e["name"]: e for e in self.data["blu"]}
        self.assertEqual(blu["Water Cannon"]["sources"][0]["k"], "default")
        self.assertTrue(any(s["k"] == "totem" for s in blu["Mighty Guard"]["sources"]))
        self.assertTrue(any(s["k"] == "hunt" and s["rank"] == "B" for s in blu["Loom"]["sources"]))
        bst = {e["name"]: e for e in self.data["bst"]}
        self.assertEqual(bst["Cu Sith"]["sources"][0]["k"], "default")
        self.assertTrue(any(s["k"] == "quest" for s in bst["Slime"]["sources"]), "Kornago Gourd alternative")
        self.assertTrue(any(s["k"] == "hunt" and s["rank"] == "B" for s in bst["Damselfly"]["sources"]))


if __name__ == "__main__":
    unittest.main()
