#!/usr/bin/env python3
"""Write tests/demo: datapack recipes with one of each issue."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "tests", "demo", "data", "demo", "recipes")

CLEAN = {
    "type": "minecraft:crafting_shaped",
    "pattern": ["###", " | ", " | "],
    "key": {"#": {"item": "minecraft:iron_ingot"}, "|": {"item": "minecraft:stick"}},
    "result": {"item": "minecraft:iron_pickaxe", "count": 1},
}
BROKEN_SHAPED = {
    "type": "minecraft:crafting_shaped",
    "pattern": ["##", "#"],
    "key": {"#": {"item": "minecraft:stone"}, "X": {"item": "minecraft:dirt"}},
    "result": {"item": "minecraft:stone", "count": 0},
}
MYSTERY = {"type": "minecraft:crafting_magic"}
SALAD = {
    "type": "minecraft:crafting_shapeless",
    "ingredients": [{"item": "minecraft:stone"}] * 10,
}
SMELT = {
    "type": "minecraft:smelting",
    "result": "minecraft:iron_ingot",
    "experience": -1,
    "cookingtime": 0,
}
TRIM = {
    "type": "minecraft:smithing_transform",
    "base": {"item": "minecraft:diamond_pickaxe"},
    "addition": {"item": "minecraft:netherite_ingot"},
    "result": {"item": "minecraft:netherite_pickaxe"},
}


def main():
    os.makedirs(DEMO, exist_ok=True)
    for name, data in (("pickaxe", CLEAN), ("broken_shaped", BROKEN_SHAPED),
                       ("mystery", MYSTERY), ("salad", SALAD),
                       ("smelt", SMELT), ("trim", TRIM)):
        with open(os.path.join(DEMO, name + ".json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    print("wrote", DEMO)


if __name__ == "__main__":
    main()