import contextlib
import io
import json
import os
import tempfile
import unittest

import recipelint as rl

SHAPED = {
    "type": "minecraft:crafting_shaped",
    "pattern": ["###", " | ", " | "],
    "key": {"#": {"item": "minecraft:iron_ingot"}, "|": {"item": "minecraft:stick"}},
    "result": {"item": "minecraft:iron_pickaxe", "count": 1},
}
SHAPELESS = {
    "type": "minecraft:crafting_shapeless",
    "ingredients": [{"item": "minecraft:bone_meal"}],
    "result": {"item": "minecraft:white_dye", "count": 1},
}
COOKING = {
    "type": "minecraft:smelting",
    "ingredient": {"item": "minecraft:iron_ore"},
    "result": "minecraft:iron_ingot",
    "experience": 0.7,
    "cookingtime": 200,
}
STONECUT = {
    "type": "minecraft:stonecutting",
    "ingredient": {"item": "minecraft:stone"},
    "result": "minecraft:stone_bricks",
    "count": 1,
}
SMITHING = {
    "type": "minecraft:smithing_transform",
    "template": {"item": "minecraft:netherite_upgrade_smithing_template"},
    "base": {"item": "minecraft:diamond_pickaxe"},
    "addition": {"item": "minecraft:netherite_ingot"},
    "result": {"item": "minecraft:netherite_pickaxe"},
}


def write(root, name, data):
    path = os.path.join(root, "data", "demo", "recipes", name + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def codes(issues):
    return sorted(i.code for i in issues)


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def run_src(self, data, name="r"):
        write(self.root, name, data)
        return rl.audit(self.root)

    def test_clean_shaped(self):
        _, issues = self.run_src(SHAPED)
        self.assertEqual(issues, [])

    def test_clean_shapeless(self):
        _, issues = self.run_src(SHAPELESS)
        self.assertEqual(issues, [])

    def test_clean_cooking(self):
        _, issues = self.run_src(COOKING)
        self.assertEqual(issues, [])

    def test_clean_stonecutting(self):
        _, issues = self.run_src(STONECUT)
        self.assertEqual(issues, [])

    def test_clean_smithing(self):
        _, issues = self.run_src(SMITHING)
        self.assertEqual(issues, [])

    def test_clean_special(self):
        _, issues = self.run_src({"type": "minecraft:crafting_special_armordye"})
        self.assertEqual(issues, [])

    def test_tag_ingredient(self):
        d = json.loads(json.dumps(SHAPED))
        d["key"]["#"] = {"tag": "minecraft:planks"}
        _, issues = self.run_src(d)
        self.assertEqual(issues, [])

    def test_result_id_key(self):
        d = json.loads(json.dumps(SHAPED))
        d["result"] = {"id": "minecraft:iron_pickaxe", "count": 2}
        _, issues = self.run_src(d)
        self.assertEqual(issues, [])

    def test_r000_not_object(self):
        path = os.path.join(self.root, "data", "demo", "recipes", "r.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("[]")
        _, issues = rl.audit(self.root)
        self.assertIn("R000", codes(issues))

    def test_r001_missing_type(self):
        _, issues = self.run_src({})
        self.assertIn("R001", codes(issues))

    def test_r002_unknown_type(self):
        _, issues = self.run_src({"type": "minecraft:bogus"})
        self.assertIn("R002", codes(issues))

    def test_r003_missing_pattern(self):
        d = {k: v for k, v in SHAPED.items() if k != "pattern"}
        _, issues = self.run_src(d)
        self.assertIn("R003", codes(issues))

    def test_r004_too_many_rows(self):
        d = json.loads(json.dumps(SHAPED))
        d["pattern"] = ["#", "#", "#", "#"]
        _, issues = self.run_src(d)
        self.assertIn("R004", codes(issues))

    def test_r004_uneven_width(self):
        d = json.loads(json.dumps(SHAPED))
        d["pattern"] = ["##", "#"]
        d["key"] = {"#": {"item": "minecraft:stone"}}
        _, issues = self.run_src(d)
        self.assertIn("R004", codes(issues))

    def test_r005_undefined_symbol(self):
        d = json.loads(json.dumps(SHAPED))
        d["pattern"] = ["#"]
        d["key"] = {}
        _, issues = self.run_src(d)
        self.assertIn("R005", codes(issues))

    def test_r006_bad_ingredient(self):
        d = json.loads(json.dumps(SHAPED))
        d["key"]["#"] = {"foo": "bar"}
        _, issues = self.run_src(d)
        self.assertIn("R006", codes(issues))

    def test_r007_unused_key(self):
        d = json.loads(json.dumps(SHAPED))
        d["pattern"] = ["#"]
        d["key"]["X"] = {"item": "minecraft:stone"}
        _, issues = self.run_src(d)
        self.assertIn("R007", codes(issues))

    def test_r008_missing_result(self):
        d = {k: v for k, v in SHAPED.items() if k != "result"}
        _, issues = self.run_src(d)
        self.assertIn("R008", codes(issues))

    def test_r009_bad_result_id(self):
        d = json.loads(json.dumps(SHAPED))
        d["result"] = {"item": "Bad_Item"}
        _, issues = self.run_src(d)
        self.assertIn("R009", codes(issues))

    def test_r010_bad_count(self):
        d = json.loads(json.dumps(SHAPED))
        d["result"]["count"] = 0
        _, issues = self.run_src(d)
        self.assertIn("R010", codes(issues))

    def test_r011_shapeless_missing(self):
        d = {k: v for k, v in SHAPELESS.items() if k != "ingredients"}
        _, issues = self.run_src(d)
        self.assertIn("R011", codes(issues))

    def test_r011_shapeless_bad_ing(self):
        d = json.loads(json.dumps(SHAPELESS))
        d["ingredients"] = [{"foo": 1}]
        _, issues = self.run_src(d)
        self.assertIn("R011", codes(issues))

    def test_r012_too_many(self):
        d = json.loads(json.dumps(SHAPELESS))
        d["ingredients"] = [{"item": "minecraft:stone"}] * 10
        _, issues = self.run_src(d)
        self.assertIn("R012", codes(issues))

    def test_r013_cooking_missing_ing(self):
        d = {k: v for k, v in COOKING.items() if k != "ingredient"}
        _, issues = self.run_src(d)
        self.assertIn("R013", codes(issues))

    def test_r014_bad_experience(self):
        d = json.loads(json.dumps(COOKING))
        d["experience"] = -1
        _, issues = self.run_src(d)
        self.assertIn("R014", codes(issues))

    def test_r015_bad_cookingtime(self):
        d = json.loads(json.dumps(COOKING))
        d["cookingtime"] = 0
        _, issues = self.run_src(d)
        self.assertIn("R015", codes(issues))

    def test_r016_stonecutting_count(self):
        d = {k: v for k, v in STONECUT.items() if k != "count"}
        _, issues = self.run_src(d)
        self.assertIn("R016", codes(issues))

    def test_r017_smithing_missing(self):
        d = {k: v for k, v in SMITHING.items() if k != "template"}
        _, issues = self.run_src(d)
        self.assertIn("R017", codes(issues))

    def test_bad_json(self):
        path = os.path.join(self.root, "data", "demo", "recipes", "r.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("{ nope")
        _, issues = rl.audit(self.root)
        self.assertIn("R000", codes(issues))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return rl.main(args)

    def test_exit_clean(self):
        write(self.root, "r", SHAPED)
        self.assertEqual(self._run([self.root, "--no-color"]), 0)

    def test_exit_error(self):
        write(self.root, "r", {})
        self.assertEqual(self._run([self.root, "--no-color"]), 1)

    def test_exit_bad_path(self):
        self.assertEqual(self._run([os.path.join(self.root, "nope")]), 2)

    def test_strict_warning(self):
        d = json.loads(json.dumps(SHAPED))
        d["pattern"] = ["#"]
        d["key"]["X"] = {"item": "minecraft:stone"}
        write(self.root, "r", d)
        self.assertEqual(self._run([self.root, "--no-color"]), 0)
        self.assertEqual(self._run([self.root, "--no-color", "--strict"]), 1)

    def test_json(self):
        write(self.root, "r", {})
        stats, issues = rl.audit(self.root)
        out = json.loads(rl.report(stats, issues, False, True))
        self.assertGreaterEqual(out["errors"], 1)
        self.assertEqual(out["summary"]["recipes"], 1)


if __name__ == "__main__":
    unittest.main()