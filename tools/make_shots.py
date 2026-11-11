#!/usr/bin/env python3
"""Regenerate docs/audit.png and docs/clean.png. Requires Pillow.

Run: python tools/make_demo.py && python tools/make_shots.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import recipelint as rl
import render_terminal as rt

CLEAN = {
    "type": "minecraft:crafting_shaped",
    "pattern": ["###", " | ", " | "],
    "key": {"#": {"item": "minecraft:iron_ingot"}, "|": {"item": "minecraft:stick"}},
    "result": {"item": "minecraft:iron_pickaxe", "count": 1},
}


def render(name, ansi, cmd, title):
    rt.render(rt.parse_ansi(ansi), title, cmd, os.path.join(ROOT, "docs", name + ".png"))


def main():
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    stats, issues = rl.audit(os.path.join(ROOT, "tests", "demo"))
    render("audit", rl.report(stats, issues, True, False),
           "python recipelint.py tests/demo", "recipelint — audit")
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "data", "demo", "recipes")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "pickaxe.json"), "w", encoding="utf-8") as fh:
            json.dump(CLEAN, fh)
        stats, issues = rl.audit(tmp)
        render("clean", rl.report(stats, issues, True, False),
               "python recipelint.py datapacks/mypack", "recipelint — clean")


if __name__ == "__main__":
    main()