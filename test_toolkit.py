"""Synthetic fixtures only; no customer design or Protel software is needed."""

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

import protel99se_toolkit as kit


def example():
    return {"nets": [
        {"name": "SIGNAL", "pins": [["U1", "1"], ["J1", "2"]]},
        {"name": None, "pins": [["U1", "2"]]},
    ]}


class NetTests(unittest.TestCase):
    def test_order_does_not_matter(self):
        actual = example()
        actual["nets"].reverse()
        for net in actual["nets"]:
            net["pins"].reverse()
        self.assertTrue(kit.compare_nets(example(), actual)["passed"])

    def test_split_fails(self):
        actual = {"nets": [{"name": None, "pins": [pin]} for pin in
                           [["U1", "1"], ["J1", "2"], ["U1", "2"]]]}
        self.assertFalse(kit.compare_nets(example(), actual)["passed"])

    def test_merge_fails(self):
        actual = {"nets": [{"name": "SIGNAL", "pins": [["U1", "1"], ["J1", "2"], ["U1", "2"]]}]}
        self.assertFalse(kit.compare_nets(example(), actual)["passed"])

    def test_same_counts_wrong_pins_fails(self):
        actual = example()
        actual["nets"][0]["pins"][0], actual["nets"][1]["pins"][0] = ["U1", "2"], ["U1", "1"]
        self.assertFalse(kit.compare_nets(example(), actual)["passed"])

    def test_name_change_requires_explicit_option(self):
        actual = example()
        actual["nets"][0]["name"] = "OTHER"
        self.assertFalse(kit.compare_nets(example(), actual)["passed"])
        self.assertTrue(kit.compare_nets(example(), actual, ignore_names=True)["passed"])

    def test_null_names_do_not_merge_isolated_pins(self):
        actual = {"nets": [{"name": None, "pins": [["U1", "1"]]},
                           {"name": None, "pins": [["U1", "2"]]}]}
        self.assertEqual(kit.compare_nets(actual, actual)["actual_nets"], 2)

    def test_duplicate_pin_rejected(self):
        actual = example()
        actual["nets"][1]["pins"] = [["U1", "1"]]
        with self.assertRaises(ValueError):
            kit.normalize_nets(actual)

    def test_empty_exports_rejected(self):
        with self.assertRaises(ValueError):
            kit.compare_nets({"nets": []}, {"nets": []})

    def test_invalid_fields_rejected(self):
        for value in [None, {"nets": [None]}, {"nets": [{"pins": []}]},
                      {"nets": [{"name": 1, "pins": [["U1", "1"]]}]},
                      {"nets": [{"name": None, "pins": [["U1", 1]]}]}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                kit.normalize_nets(value)

    def test_duplicate_names_rejected(self):
        actual = example()
        actual["nets"][1]["name"] = "SIGNAL"
        with self.assertRaises(ValueError):
            kit.normalize_nets(actual)

    def test_input_not_modified(self):
        source = example()
        saved = copy.deepcopy(source)
        kit.compare_nets(source, example())
        self.assertEqual(source, saved)


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "Main.SCH").write_bytes(b"SYNTHETIC-NOT-A-REAL-SCHEMATIC")
        (self.root / "Main.PCB").write_bytes(b"SYNTHETIC-NOT-A-REAL-PCB")
        self.entries = [("Main.SCH", "Sch"), ("Main.PCB", "PCB")]

    def test_index_roundtrip_not_native_certification(self):
        target = self.root / "Design.ddb"
        before = kit.sha256(self.root / "Main.SCH")
        created = kit.make_ddb(target, self.entries)
        inspected = kit.inspect_file(target)
        self.assertTrue(inspected["index_members_valid"])
        self.assertEqual(len(inspected["members"]), 2)
        self.assertFalse(created["native_verified"])
        self.assertFalse(inspected["native_verified"])
        self.assertEqual(before, kit.sha256(self.root / "Main.SCH"))
        self.assertIn(b"\r\n", target.read_bytes())

    def test_no_overwrite(self):
        target = self.root / "Design.ddb"
        target.write_bytes(b"ORIGINAL")
        with self.assertRaises(FileExistsError):
            kit.make_ddb(target, self.entries)
        self.assertEqual(target.read_bytes(), b"ORIGINAL")

    def test_missing_member_rejected(self):
        with self.assertRaises(ValueError):
            kit.make_ddb(self.root / "Design.ddb", [("Missing.SCH", "Sch")])
        self.assertFalse((self.root / "Design.ddb").exists())

    def test_empty_member_rejected(self):
        (self.root / "Empty.PCB").touch()
        with self.assertRaises(ValueError):
            kit.make_ddb(self.root / "Design.ddb", [("Empty.PCB", "PCB")])

    def test_unsafe_names_rejected(self):
        for name in ["../Main.SCH", "C:\\Main.SCH", "a/b.SCH", "Bad\nName.SCH", "CON.SCH", "a].SCH"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                kit.make_ddb(self.root / "Design.ddb", [(name, "Sch")])

    def test_wrong_kind_and_duplicate_rejected(self):
        for entries in [[("Main.SCH", "PCB")], self.entries + [("main.sch", "Sch")]]:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                kit.make_ddb(self.root / "Design.ddb", entries)

    def test_unknown_file_is_not_verified(self):
        report = kit.inspect_file(self.root / "Main.SCH")
        self.assertEqual(report["format_hint"], "unknown")
        self.assertFalse(report["native_verified"])

    def test_broken_index_editor_detected(self):
        target = self.root / "Design.ddb"
        kit.make_ddb(target, self.entries)
        target.write_bytes(target.read_bytes().replace(b"Editor Kind=Sch", b"Editor Kind=PCB"))
        with self.assertRaises(ValueError):
            kit.inspect_file(target)

    def test_cli_report_and_mismatch_exit(self):
        expected, actual, output = [self.root / name for name in ["expected.json", "actual.json", "report.json"]]
        expected.write_text(json.dumps(example()), encoding="utf-8")
        changed = example()
        changed["nets"][0]["name"] = "OTHER"
        actual.write_text(json.dumps(changed), encoding="utf-8")
        args = ["compare-nets", str(expected), str(actual), "--output", str(output)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(kit.main(args), 1)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(report["passed"])
            saved = output.read_bytes()
            self.assertEqual(kit.main(args), 2)
        self.assertEqual(output.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
