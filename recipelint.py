#!/usr/bin/env python3
"""recipelint - validator for Minecraft datapack recipe JSON files.

Checks recipe type, shaped patterns and keys, shapeless ingredient lists,
cooking/stonecutting/smithing fields, result item ids and counts. Single file,
standard library only, Python 3.9+.
"""

import argparse
import json
import os
import re
import sys

__version__ = "1.0.0"

ERROR = "error"
WARN = "warning"

ID_RE = re.compile(r"^(?:[a-z0-9_.-]+:)?[a-z0-9_./-]+$")

SHAPED = "minecraft:crafting_shaped"
SHAPELESS = "minecraft:crafting_shapeless"
COOKING = {"minecraft:smelting", "minecraft:blasting",
           "minecraft:smoking", "minecraft:campfire_cooking"}
STONECUTTING = "minecraft:stonecutting"
SMITHING_TRANSFORM = "minecraft:smithing_transform"
SMITHING_TRIM = "minecraft:smithing_trim"
SPECIAL = {
    "minecraft:crafting_special_armordye",
    "minecraft:crafting_special_bookcloning",
    "minecraft:crafting_special_mapcloning",
    "minecraft:crafting_special_mapextending",
    "minecraft:crafting_special_firework_rocket",
    "minecraft:crafting_special_firework_star",
    "minecraft:crafting_special_firework_star_fade",
    "minecraft:crafting_special_repairitem",
    "minecraft:crafting_special_tippedarrow",
    "minecraft:crafting_special_bannerduplicate",
    "minecraft:crafting_special_shielddecoration",
    "minecraft:crafting_special_shulkerboxcoloring",
    "minecraft:crafting_special_suspiciousstew",
    "minecraft:crafting_decorated_pot",
}
KNOWN_TYPES = ({SHAPED, SHAPELESS, STONECUTTING, SMITHING_TRANSFORM, SMITHING_TRIM}
               | COOKING | SPECIAL)


class Issue:
    __slots__ = ("code", "severity", "file", "line", "message")

    def __init__(self, code, severity, file, line, message):
        self.code = code
        self.severity = severity
        self.file = file
        self.line = line
        self.message = message

    def as_dict(self):
        return {"code": self.code, "severity": self.severity, "file": self.file,
                "line": self.line, "message": self.message}


def valid_id(s):
    return isinstance(s, str) and bool(s) and bool(ID_RE.match(s))


def positive_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def ingredient_ok(v):
    if isinstance(v, str):
        return valid_id(v[1:] if v.startswith("#") else v)
    if isinstance(v, dict):
        keys = [k for k in ("item", "tag") if k in v]
        if len(keys) != 1:
            return False
        return valid_id(v[keys[0]])
    if isinstance(v, list):
        return len(v) > 0 and all(isinstance(x, dict) and ingredient_ok(x) for x in v)
    return False


def validate_result(data, add, allow_string=False):
    res = data.get("result")
    if res is None:
        add("R008", ERROR, "missing 'result'")
        return
    if isinstance(res, str):
        if not allow_string:
            add("R009", ERROR, "result must be an object with 'item'")
        elif not valid_id(res):
            add("R009", ERROR, "invalid result item id '%s'" % res)
        return
    if not isinstance(res, dict):
        add("R009", ERROR, "result must be an object with 'item'")
        return
    item = res.get("item", res.get("id"))
    if not valid_id(item):
        add("R009", ERROR, "result missing a valid 'item' id")
    count = res.get("count")
    if count is not None and not positive_int(count):
        add("R010", ERROR, "result count must be a positive integer (got %r)" % count)


def validate_shaped(data, add):
    pattern = data.get("pattern")
    key = data.get("key")
    used = set()
    if pattern is None:
        add("R003", ERROR, "shaped recipe missing 'pattern'")
    elif not isinstance(pattern, list) or not 1 <= len(pattern) <= 3:
        add("R004", ERROR, "pattern must be a list of 1-3 rows")
    else:
        widths = set()
        for row in pattern:
            if not isinstance(row, str) or not 1 <= len(row) <= 3:
                add("R004", ERROR, "each pattern row must be 1-3 characters")
                continue
            widths.add(len(row))
            used.update(ch for ch in row if ch != " ")
        if len(widths) > 1:
            add("R004", ERROR, "pattern rows must all have the same width")
    if not isinstance(key, dict):
        if used:
            add("R006", ERROR, "shaped recipe missing 'key' object")
    else:
        for sym, ing in key.items():
            if not isinstance(sym, str) or len(sym) != 1:
                add("R006", ERROR, "key symbol %r must be a single character" % sym)
            if not ingredient_ok(ing):
                add("R006", ERROR, "key '%s' needs an ingredient {item} or {tag}" % sym)
        for ch in sorted(used):
            if ch not in key:
                add("R005", ERROR, "pattern symbol '%s' is not defined in key" % ch)
        for sym in sorted(key):
            if sym != " " and sym not in used:
                add("R007", WARN, "key symbol '%s' is defined but unused" % sym)
    validate_result(data, add)


def validate_shapeless(data, add):
    ings = data.get("ingredients")
    if ings is None:
        add("R011", ERROR, "shapeless recipe missing 'ingredients'")
    elif not isinstance(ings, list) or not ings:
        add("R011", ERROR, "ingredients must be a non-empty list")
    else:
        if len(ings) > 9:
            add("R012", ERROR, "shapeless recipe has %d ingredients (max 9)" % len(ings))
        for ing in ings:
            if not ingredient_ok(ing):
                add("R011", ERROR, "ingredient needs {item} or {tag} with a valid id")
    validate_result(data, add)


def validate_cooking(data, add):
    ing = data.get("ingredient")
    if ing is None:
        add("R013", ERROR, "cooking recipe missing 'ingredient'")
    elif not ingredient_ok(ing):
        add("R013", ERROR, "ingredient needs {item} or {tag} with a valid id")
    exp = data.get("experience")
    if exp is not None:
        if isinstance(exp, bool) or not isinstance(exp, (int, float)) or exp < 0:
            add("R014", ERROR, "experience must be a number >= 0 (got %r)" % exp)
    ct = data.get("cookingtime")
    if ct is not None and not positive_int(ct):
        add("R015", ERROR, "cookingtime must be a positive integer (got %r)" % ct)
    validate_result(data, add, allow_string=True)


def validate_stonecutting(data, add):
    ing = data.get("ingredient")
    if ing is None:
        add("R013", ERROR, "stonecutting recipe missing 'ingredient'")
    elif not ingredient_ok(ing):
        add("R013", ERROR, "ingredient needs {item} or {tag} with a valid id")
    validate_result(data, add, allow_string=True)
    if isinstance(data.get("result"), str):
        count = data.get("count")
        if count is None:
            add("R016", ERROR, "stonecutting recipe missing 'count'")
        elif not positive_int(count):
            add("R016", ERROR, "count must be a positive integer (got %r)" % count)


def validate_smithing(data, add, rtype):
    for field in ("template", "base", "addition"):
        v = data.get(field)
        if v is None:
            add("R017", ERROR, "smithing recipe missing '%s'" % field)
        elif not ingredient_ok(v):
            add("R017", ERROR, "'%s' needs an ingredient {item} or {tag}" % field)
    if rtype == SMITHING_TRANSFORM:
        validate_result(data, add)


def validate(data, path, issues):
    def add(code, sev, msg, line=1):
        issues.append(Issue(code, sev, path, line, msg))

    if not isinstance(data, dict):
        add("R000", ERROR, "recipe must be a JSON object")
        return None
    rtype = data.get("type")
    if not rtype:
        add("R001", ERROR, "missing 'type'")
        return None
    if not isinstance(rtype, str) or rtype not in KNOWN_TYPES:
        add("R002", ERROR, "unknown recipe type '%s'" % rtype)
        return rtype if isinstance(rtype, str) else None
    if rtype == SHAPED:
        validate_shaped(data, add)
    elif rtype == SHAPELESS:
        validate_shapeless(data, add)
    elif rtype in COOKING:
        validate_cooking(data, add)
    elif rtype == STONECUTTING:
        validate_stonecutting(data, add)
    elif rtype in (SMITHING_TRANSFORM, SMITHING_TRIM):
        validate_smithing(data, add, rtype)
    return rtype


def collect(root):
    if os.path.isfile(root):
        return [root]
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", "node_modules")]
        parts = os.path.normpath(dirpath).replace("\\", "/").split("/")
        if "recipes" in parts or "recipe" in parts:
            for fn in sorted(filenames):
                if fn.endswith(".json"):
                    found.append(os.path.join(dirpath, fn))
    return found


def audit(root):
    issues = []
    types = set()
    stats = {"files": 0, "recipes": 0, "types": 0}
    for path in collect(root):
        rel = os.path.relpath(path, root) if os.path.isdir(root) else os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            issues.append(Issue("R000", ERROR, rel, 1, "cannot read: %s" % exc))
            continue
        stats["files"] += 1
        stats["recipes"] += 1
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            issues.append(Issue("R000", ERROR, rel, exc.lineno, "invalid JSON: %s" % exc.msg))
            continue
        rtype = validate(data, rel, issues)
        if isinstance(rtype, str):
            types.add(rtype)
    stats["types"] = len(types)
    return stats, issues


def colorize(text, color, enabled):
    if not enabled:
        return text
    codes = {"red": "31", "green": "32", "yellow": "33", "bold": "1"}
    return "\x1b[%sm%s\x1b[0m" % (codes[color], text)


def report(stats, issues, color, as_json):
    errors = [i for i in issues if i.severity == ERROR]
    warns = [i for i in issues if i.severity == WARN]
    if as_json:
        return json.dumps({"summary": stats, "errors": len(errors), "warnings": len(warns),
                           "issues": [i.as_dict() for i in issues]}, indent=2)
    lines = [colorize("SUMMARY", "bold", color)]
    lines.append("  recipes  %d" % stats["recipes"])
    lines.append("  types    %d" % stats["types"])
    if not issues:
        lines.append(colorize("clean: no issues found", "green", color))
        return "\n".join(lines)
    if errors:
        lines.append(colorize("ERRORS (%d)" % len(errors), "red", color))
        for i in errors:
            lines.append("  %s:%d: [%s] %s" % (i.file, i.line, i.code, i.message))
    if warns:
        lines.append(colorize("WARNINGS (%d)" % len(warns), "yellow", color))
        for i in warns:
            lines.append("  %s:%d: [%s] %s" % (i.file, i.line, i.code, i.message))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="recipelint", description="Validator for Minecraft datapack recipe JSON files.")
    parser.add_argument("path", help="a recipe .json file, or a datapack directory")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--version", action="version", version="recipelint " + __version__)
    opts = parser.parse_args(argv)
    if not os.path.exists(opts.path):
        sys.stderr.write("recipelint: path not found: %s\n" % opts.path)
        return 2
    color = not opts.no_color and not os.environ.get("NO_COLOR") and sys.stdout.isatty()
    stats, issues = audit(opts.path)
    print(report(stats, issues, color, opts.json))
    errors = sum(1 for i in issues if i.severity == ERROR)
    warns = sum(1 for i in issues if i.severity == WARN)
    return 1 if (errors or (opts.strict and warns)) else 0


if __name__ == "__main__":
    sys.exit(main())