"""Local file helpers, not a native Protel parser or a circuit verifier."""

import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import sys

KINDS = {"Sch": ".sch", "PCB": ".pcb", "SchLib": ".lib", "PCBLib": ".lib"}
PORTABLE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
MAX_JSON_BYTES = 16 * 1024 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_name(name):
    if not isinstance(name, str) or not PORTABLE_NAME.fullmatch(name):
        raise ValueError("Use a plain ASCII filename, not a path: " + repr(name))
    if name.endswith("."):
        raise ValueError("Trailing dots are not portable")
    base = name.split(".")[0].upper()
    if base in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9]", base):
        raise ValueError("Reserved Windows filename: " + name)
    return name


def validate_entries(directory, entries):
    seen = set()
    if not entries:
        raise ValueError("At least one existing document is required")
    for name, kind in entries:
        portable_name(name)
        if kind not in KINDS or Path(name).suffix.lower() != KINDS[kind]:
            raise ValueError("Document kind and extension do not match: " + name)
        if name.casefold() in seen:
            raise ValueError("Duplicate filename: " + name)
        seen.add(name.casefold())
        member = directory / name
        if member.is_symlink() or member.resolve().parent != directory.resolve():
            raise ValueError("Member must stay in the index directory: " + name)
        if not member.is_file() or member.stat().st_size == 0:
            raise ValueError("Member is missing or empty: " + name)


def make_ddb(output, entries):
    output = Path(output)
    portable_name(output.name)
    if output.suffix.lower() != ".ddb":
        raise ValueError("Output must have .ddb extension")
    if not output.parent.is_dir():
        raise ValueError("Create the working directory and documents first")
    validate_entries(output.parent, entries)
    lines = ["[Design Root]", "Version=1.0.0", "[Directory]"]
    lines.extend(f"{name}={kind}" for name, kind in entries)
    for name, kind in entries:
        lines.extend([f"[{name}]", f"Editor Kind={kind}"])
    # Exclusive creation protects both existing indices and database containers.
    with output.open("xb") as stream:
        stream.write(("\r\n".join(lines) + "\r\n").encode("ascii"))
    return {"created": output.name, "members": len(entries), "sha256": sha256(output),
            "native_verified": False, "note": "Index only; open and verify in Protel 99 SE."}


def inspect_file(path):
    path = Path(path)
    with path.open("rb") as stream:
        head = stream.read(512)
    result = {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path),
              "format_hint": "unknown", "native_verified": False}
    if head.startswith(b"\x00\x01\x00\x00Standard Jet DB"):
        result["format_hint"] = "jet-database-candidate"
    elif head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        result["format_hint"] = "ole-container-not-a-format-guarantee"
    elif head.startswith(b"[Design Root]"):
        result["format_hint"] = "windows-file-system-ddb"
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Index exceeds the 1 MiB inspection limit")
        config = configparser.ConfigParser(interpolation=None, strict=True)
        config.optionxform = str
        config.read_string(path.read_text(encoding="ascii"))
        entries = list(config.items("Directory"))
        if config.get("Design Root", "Version") != "1.0.0":
            raise ValueError("Unsupported folder-index version")
        validate_entries(path.parent, entries)
        for name, kind in entries:
            if config.get(name, "Editor Kind", fallback=None) != kind:
                raise ValueError("Editor Kind mismatch: " + name)
        result["members"] = [{"name": name, "kind": kind} for name, kind in entries]
        result["index_members_valid"] = True
    elif b"Protel" in head or b"RECORD=" in head:
        result["format_hint"] = "protel-like-header-requires-parser-and-native-check"
    return result


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("JSON exceeds the 16 MiB input limit")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_nets(document):
    if not isinstance(document, dict) or not isinstance(document.get("nets"), list):
        raise ValueError("Expected an object with a nets list")
    if not document["nets"]:
        raise ValueError("Empty network exports cannot establish equivalence")
    groups, seen_pins, seen_names = {}, set(), set()
    for net in document["nets"]:
        if not isinstance(net, dict) or "name" not in net:
            raise ValueError("Each net needs name (string or null) and pins")
        name, pins = net["name"], net.get("pins")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("Network names must be nonempty strings or null")
        if name is not None:
            if name in seen_names:
                raise ValueError("Repeated network name; normalize scope explicitly: " + name)
            seen_names.add(name)
        if not isinstance(pins, list) or not pins:
            raise ValueError("Every net needs at least one pin")
        group = set()
        for pin in pins:
            if (not isinstance(pin, list) or len(pin) != 2 or
                    any(not isinstance(v, str) or not v.strip() for v in pin)):
                raise ValueError("Pins must be [reference, pin_number] string pairs")
            key = tuple(pin)
            if key in seen_pins:
                raise ValueError("A pin occurs more than once: " + repr(key))
            seen_pins.add(key)
            group.add(key)
        groups[frozenset(group)] = name
    return groups


def describe_group(group, name):
    return {"name": name, "pins": [list(pin) for pin in sorted(group)]}


def compare_nets(expected, actual, ignore_names=False):
    left, right = normalize_nets(expected), normalize_nets(actual)
    order = lambda group: sorted(group)
    missing = [describe_group(g, left[g]) for g in sorted(left.keys() - right.keys(), key=order)]
    extra = [describe_group(g, right[g]) for g in sorted(right.keys() - left.keys(), key=order)]
    mismatches = []
    if not ignore_names:
        for group in sorted(left.keys() & right.keys(), key=order):
            if left[group] is not None and left[group] != right[group]:
                mismatches.append({"pins": [list(p) for p in sorted(group)],
                                   "expected": left[group], "actual": right[group]})
    return {
        "passed": not (missing or extra or mismatches),
        "scope": "Supplied pin partitions only; not native parsing, ERC, DRC or coverage certification.",
        "expected_nets": len(left), "actual_nets": len(right),
        "expected_pins": sum(map(len, left)), "actual_pins": sum(map(len, right)),
        "ignore_names": ignore_names, "missing_groups": missing,
        "extra_groups": extra, "name_mismatches": mismatches,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Inspect one local file without modifying it")
    inspect.add_argument("path", type=Path)
    create = sub.add_parser("make-ddb", help="Create a new folder index, not design contents")
    create.add_argument("output", type=Path)
    create.add_argument("--entry", action="append", required=True, metavar="FILE=KIND")
    compare = sub.add_parser("compare-nets", help="Compare explicit normalized net exports")
    compare.add_argument("expected", type=Path)
    compare.add_argument("actual", type=Path)
    compare.add_argument("--ignore-names", action="store_true")
    compare.add_argument("--output", type=Path, help="New JSON report; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_file(args.path)
        elif args.command == "make-ddb":
            entries = []
            for entry in args.entry:
                if entry.count("=") != 1:
                    raise ValueError("Use --entry FILE=KIND")
                entries.append(tuple(entry.split("=", 1)))
            result = make_ddb(args.output, entries)
        else:
            result = compare_nets(read_json(args.expected), read_json(args.actual), args.ignore_names)
            result.update(expected_sha256=sha256(args.expected), actual_sha256=sha256(args.actual))
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.command == "compare-nets" and args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(rendered + "\n")
        print(rendered)
        return 1 if result.get("passed") is False else 0
    except (OSError, ValueError, configparser.Error) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
