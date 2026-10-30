"""Isolated behavior tests for dependency planning and scoped usage accounting."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import audit_model_usage as usage
import check_input_snapshot as snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="game-skill-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        (self.project / "a.js").write_text("a", encoding="utf-8")
        (self.project / "b.js").write_text("b", encoding="utf-8")
        (self.project / "evidence.json").write_text('{"observed":true}', encoding="utf-8")
        self.tool = self.root / "tool.py"
        self.tool.write_text("tool-v1", encoding="utf-8")
        self.definition = {"schema_version": 1, "checks": [
            {"id": name, "scope": "Web", "context": {"viewport": [390, 844], "dpr": 2},
             "dependencies": [name.lower() + ".js"], "tool_files": [str(self.tool)],
             "evidence": ["evidence.json"]} for name in ("A", "B")]}

    def capture(self, definition=None):
        return snapshot.capture(self.project, definition or self.definition)

    def test_unchanged_only_requests_evidence_review(self):
        before = self.capture()
        result = snapshot.compare(before, self.capture())
        self.assertEqual(result["review_existing_evidence"], ["A", "B"])
        self.assertFalse(result["is_acceptance_result"])
        self.assertNotIn("passed", result)

    def test_changed_source_selects_only_affected_check(self):
        before = self.capture()
        (self.project / "a.js").write_text("changed", encoding="utf-8")
        result = snapshot.compare(before, self.capture())
        self.assertEqual(result["needs_run"], ["A"])
        self.assertEqual(result["review_existing_evidence"], ["B"])

    def test_added_resource_in_declared_directory_changes_fingerprint(self):
        art = self.project / "art"
        art.mkdir()
        (art / "one.png").write_bytes(b"one")
        self.definition["checks"][0]["dependencies"] = ["art"]
        before = self.capture()
        (art / "two.png").write_bytes(b"two")
        self.assertEqual(snapshot.compare(before, self.capture())["needs_run"], ["A"])

    def test_tool_environment_and_scope_changes_need_run(self):
        before = self.capture()
        self.tool.write_text("tool-v2", encoding="utf-8")
        self.assertEqual(snapshot.compare(before, self.capture())["needs_run"], ["A", "B"])
        self.tool.write_text("tool-v1", encoding="utf-8")
        for field, value in [("context", {"dpr": 3}), ("scope", "physical-device")]:
            changed = copy.deepcopy(self.definition)
            changed["checks"][0][field] = value
            self.assertEqual(snapshot.compare(before, self.capture(changed))["needs_run"], ["A"])

    def test_missing_dependency_cannot_reuse(self):
        before = self.capture()
        (self.project / "a.js").unlink()
        result = snapshot.compare(before, self.capture())
        self.assertEqual(result["cannot_reuse"], ["A"])

    def test_changed_or_missing_evidence_cannot_reuse(self):
        before = self.capture()
        (self.project / "evidence.json").write_text("different evidence", encoding="utf-8")
        self.assertEqual(snapshot.compare(before, self.capture())["cannot_reuse"], ["A", "B"])
        (self.project / "evidence.json").unlink()
        self.assertEqual(snapshot.compare(before, self.capture())["cannot_reuse"], ["A", "B"])

    def test_new_removed_and_unbound_checks(self):
        before = self.capture()
        changed = copy.deepcopy(self.definition)
        changed["checks"].pop()
        changed["checks"][0]["evidence"] = []
        added = copy.deepcopy(changed["checks"][0])
        added["id"] = "NEW"
        changed["checks"].append(added)
        result = snapshot.compare(before, self.capture(changed))
        self.assertEqual(result["removed_checks"], ["B"])
        self.assertEqual(result["needs_run"], ["NEW"])
        self.assertEqual(result["cannot_reuse"], ["A"])

    def test_escape_duplicate_ids_and_tampering_rejected(self):
        for dependencies in [["../tool.py"], []]:
            changed = copy.deepcopy(self.definition)
            changed["checks"][0]["dependencies"] = dependencies
            with self.assertRaises(ValueError):
                self.capture(changed)
        changed = copy.deepcopy(self.definition)
        changed["checks"][1]["id"] = "A"
        with self.assertRaises(ValueError):
            self.capture(changed)
        before = self.capture()
        before["checks"]["A"]["fingerprint"] = "incorrect"
        with self.assertRaises(ValueError):
            snapshot.compare(before, self.capture())

    def test_cli_preserves_input_and_writes_json_to_space_path(self):
        definition = self.root / "check list.json"
        definition.write_text(json.dumps(self.definition), encoding="utf-8")
        command = [sys.executable, "-B", str(Path(snapshot.__file__)), "snapshot", "--project", str(self.project), "--checks", str(definition)]
        original = definition.read_bytes()
        failed = subprocess.run(command + ["--out", str(definition)], capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(definition.read_bytes(), original)
        output = self.root / "nested output/snapshot.json"
        passed = subprocess.run(command + ["--out", str(output)], capture_output=True, text=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertEqual(json.loads(passed.stdout)["counts"]["checks"], 2)
        self.assertFalse(json.loads(output.read_text(encoding="utf-8"))["is_acceptance_result"])

    def test_snapshot_outputs_preserve_dependencies_evidence_and_declared_directories(self):
        definition = self.root / "checks.json"
        definition.write_text(json.dumps(self.definition), encoding="utf-8")
        command = [sys.executable, "-B", str(Path(snapshot.__file__)), "snapshot", "--project", str(self.project), "--checks", str(definition)]
        for name in ["a.js", "evidence.json"]:
            path = self.project / name
            original = path.read_bytes()
            result = subprocess.run(command + ["--out", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_bytes(), original)
        nested = self.project / "assets"
        nested.mkdir()
        (nested / "asset.txt").write_text("preserve", encoding="utf-8")
        self.definition["checks"][0]["dependencies"] = ["assets"]
        definition.write_text(json.dumps(self.definition), encoding="utf-8")
        output = nested / "new.json"
        result = subprocess.run(command + ["--out", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_compare_output_preserves_evidence(self):
        for name in ["before.json", "after.json"]:
            (self.root / name).write_text(json.dumps(self.capture()), encoding="utf-8")
        evidence = self.project / "evidence.json"
        original = evidence.read_bytes()
        result = subprocess.run([sys.executable, "-B", str(Path(snapshot.__file__)), "compare",
            "--before", str(self.root / "before.json"), "--after", str(self.root / "after.json"),
            "--out", str(evidence)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(evidence.read_bytes(), original)

    def test_missing_declared_paths_cannot_be_created_by_snapshot_output(self):
        definition = self.root / "missing-checks.json"
        for field in ["dependencies", "tool_files", "evidence"]:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.definition)
                missing = "missing-" + field
                changed["checks"][0][field] = [missing]
                definition.write_text(json.dumps(changed), encoding="utf-8")
                before = self.capture(changed)["checks"]["A"][{"tool_files": "tools"}.get(field, field)]
                output = self.project / missing / "snapshot.json"
                result = subprocess.run([sys.executable, "-B", str(Path(snapshot.__file__)), "snapshot",
                    "--project", str(self.project), "--checks", str(definition), "--out", str(output)],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.parent.exists())
                after = self.capture(changed)["checks"]["A"][{"tool_files": "tools"}.get(field, field)]
                self.assertEqual(before, after)


def event(second, kind, payload):
    return {"timestamp": f"2026-10-19T00:00:{second:02d}Z", "type": kind, "payload": payload}


def tokens(inputs, cached, outputs, reasoning=0):
    return {"input_tokens": inputs, "cached_input_tokens": cached, "output_tokens": outputs,
            "reasoning_output_tokens": reasoning, "total_tokens": inputs + outputs}


def token_event(second, total, last=None):
    return event(second, "event_msg", {"type": "token_count", "info": {
        "total_token_usage": total, "last_token_usage": last or total}})


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="game-usage-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs = self.root / "logs"
        self.logs.mkdir()
        self.project = self.root / "project"
        self.project.mkdir()
        self.until = usage.instant("2026-10-19T00:00:59Z")

    def write(self, name, session_id, start, rows, parent=None, cwd=None):
        meta = {"id": session_id, "timestamp": f"2026-10-19T00:00:{start:02d}Z",
                "cwd": str(cwd or self.project), "source": "test"}
        if parent:
            meta["source"] = {"subagent": {"thread_spawn": {"parent_thread_id": parent}}}
        all_rows = [event(start, "session_meta", meta)] + rows
        path = self.logs / name
        path.write_text("\n".join(json.dumps(row) for row in all_rows) + "\n", encoding="utf-8")
        return path

    def run_usage(self, roots=None, since=None):
        return usage.run([self.logs], self.project, roots or ["root"], self.until, since)

    def test_duplicate_inherited_and_unrelated_logs_do_not_inflate_usage(self):
        one, two = tokens(100, 80, 5, 2), tokens(300, 240, 11, 3)
        self.write("root.jsonl", "root", 0, [token_event(1, one), token_event(2, one),
                   token_event(3, two, tokens(200, 160, 6, 1))])
        self.write("child.jsonl", "child", 4, [token_event(1, tokens(999, 0, 1)),
                   event(0, "session_meta", {"id": "inherited-parent"}), token_event(5, tokens(50, 10, 3))], "root")
        unrelated = self.write("unrelated.jsonl", "other", 0, [])
        with unrelated.open("a", encoding="utf-8") as stream:
            stream.write("invalid body must never be read for an unrelated root\n")
        result = self.run_usage()
        self.assertTrue(result["reliable_counters"])
        self.assertEqual(result["overall"]["input_tokens"], 350)
        self.assertEqual(result["overall"]["cached_input_tokens"], 250)
        self.assertEqual(result["overall"]["uncached_input_tokens"], 100)
        self.assertEqual(result["overall"]["recorded_calls"], 3)

    def test_since_uses_pre_window_counter_baseline(self):
        self.write("root.jsonl", "root", 0, [token_event(1, tokens(100, 80, 5)),
                   token_event(3, tokens(300, 240, 11), tokens(200, 160, 6))])
        result = self.run_usage(since=usage.instant("2026-10-19T00:00:02Z"))
        self.assertEqual(result["overall"]["input_tokens"], 200)
        self.assertEqual(result["overall"]["recorded_calls"], 1)
        self.assertTrue(result["reliable_counters"])

    def test_counter_reset_is_flagged_instead_of_claiming_reliable(self):
        self.write("root.jsonl", "root", 0, [token_event(1, tokens(100, 80, 5)), token_event(2, tokens(20, 0, 1))])
        self.assertFalse(self.run_usage()["reliable_counters"])

    def test_missing_and_overlapping_roots_fail(self):
        with self.assertRaises(ValueError):
            self.run_usage()
        self.write("root.jsonl", "root", 0, [])
        self.write("child.jsonl", "child", 1, [], "root")
        with self.assertRaises(ValueError):
            self.run_usage(["root", "child"])

    def test_zero_usage_and_until_boundary(self):
        self.write("root.jsonl", "root", 0, [token_event(4, tokens(100, 0, 5))])
        self.until = usage.instant("2026-10-19T00:00:03Z")
        result = self.run_usage()
        self.assertEqual(result["overall"]["avg_input"], 0)
        self.assertIsNone(result["overall"]["input_p90"])

    def test_bad_counter_delta_is_detected(self):
        self.write("root.jsonl", "root", 0, [token_event(1, tokens(100, 80, 5)),
                   token_event(3, tokens(300, 240, 11), tokens(1, 0, 1))])
        self.assertFalse(self.run_usage()["reliable_counters"])

    def test_invalid_intermediate_cache_cannot_be_hidden_by_final_total(self):
        self.write("root.jsonl", "root", 0, [token_event(1, tokens(100, 120, 10)),
                   token_event(3, tokens(200, 160, 20), tokens(100, 40, 10))])
        result = self.run_usage()
        self.assertFalse(result["reliable_counters"])
        self.assertFalse(result["consistency_checks"]["valid_per_event_usage"])

    def test_unchanged_counter_status_payload_is_not_another_usage_increment(self):
        first = tokens(100, 80, 10)
        status = tokens(0, 0, 0)
        status["total_tokens"] = 43000
        self.write("root.jsonl", "root", 0, [token_event(1, first), token_event(2, first, status),
                   token_event(3, tokens(200, 160, 20), tokens(100, 80, 10))])
        result = self.run_usage()
        self.assertTrue(result["reliable_counters"])
        self.assertEqual(result["overall"]["recorded_calls"], 2)
        self.assertEqual(result["overall"]["input_tokens"], 200)
        self.assertEqual(result["overall"]["ignored_duplicate_payload_anomalies"], 1)

    def test_negative_delta_or_noninteger_counter_is_rejected(self):
        self.write("root.jsonl", "root", 0, [token_event(1, tokens(100, 80, 10)),
                   token_event(3, tokens(200, 60, 20), tokens(100, -20, 10))])
        self.assertFalse(self.run_usage()["reliable_counters"])
        malformed = tokens(100, 80, 10)
        malformed["input_tokens"] = "100"
        self.write("root.jsonl", "root", 0, [token_event(1, malformed)])
        self.assertFalse(self.run_usage()["reliable_counters"])

    def test_usage_output_hardlink_cannot_overwrite_log(self):
        log = self.write("root.jsonl", "root", 0, [token_event(1, tokens(100, 80, 10))])
        output = self.root / "report.json"
        try:
            os.link(log, output)
        except OSError as exc:
            self.skipTest("Hardlinks unavailable: " + str(exc))
        original = log.read_bytes()
        command = [sys.executable, "-B", str(Path(usage.__file__)), "--log-dir", str(self.logs),
                   "--workspace", str(self.project), "--root-id", "root", "--out", str(output),
                   "--until", self.until.isoformat()]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(log.read_bytes(), original)


class PreflightTests(unittest.TestCase):
    """Synthetic Cocos 2.4 project: one upscaled sprite, one sharp sprite, one unrecorded audio file."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="preflight-test-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.project = root / "game"
        (self.project / "assets" / "tex").mkdir(parents=True)
        (self.project / "assets" / "sound").mkdir()
        (self.project / "project.json").write_text('{"engine":"cocos-creator-js","version":"2.4.15"}', encoding="utf-8")
        for name, uid, w in (("small.png", "f-small", 40), ("big.png", "f-big", 400)):
            meta = {"uuid": "t-" + uid, "subMetas": {name[:-4]: {"uuid": uid, "rawWidth": w, "rawHeight": w}}}
            (self.project / "assets" / "tex" / (name + ".meta")).write_text(json.dumps(meta), encoding="utf-8")
        scene = [{"__type__": "cc.SceneAsset"},
                 {"__type__": "cc.Node", "_name": "icon", "_contentSize": {"width": 120, "height": 120},
                  "_trs": {"array": [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]}},
                 {"__type__": "cc.Sprite", "node": {"__id__": 1}, "_type": 0, "_spriteFrame": {"__uuid__": "f-small"}},
                 {"__type__": "cc.Node", "_name": "logo", "_contentSize": {"width": 100, "height": 100},
                  "_trs": {"array": [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]}},
                 {"__type__": "cc.Sprite", "node": {"__id__": 3}, "_type": 0, "_spriteFrame": {"__uuid__": "f-big"}}]
        (self.project / "assets" / "Main.fire").write_text(json.dumps(scene), encoding="utf-8")
        (self.project / "assets" / "sound" / "click.mp3").write_bytes(b"ID3")
        self.out = root / "out"
        self.here = Path(__file__).resolve().parent

    def run_tool(self, *args):
        return subprocess.run([sys.executable, "-B", str(self.here / args[0]), *map(str, args[1:])],
                              capture_output=True, text=True, encoding="utf-8")

    def test_clarity_flags_only_the_upscaled_sprite(self):
        r = self.run_tool("audit_image_clarity.py", "--project", self.project)
        data = json.loads(r.stdout)
        self.assertEqual(r.returncode, 1)
        self.assertEqual((data["checked"], data["upscaled"]), (2, 1))
        self.assertEqual(data["worst"][0]["node"], "icon")

    def test_preflight_summarises_and_blocks(self):
        r = self.run_tool("preflight.py", "--project", self.project, "--levels", "20", "--out", self.out)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        rows = {x["check"]: x["status"] for x in json.loads((self.out / "preflight.json").read_text(encoding="utf-8"))["results"]}
        self.assertEqual(rows["音频来源"], "需处理")
        self.assertEqual(rows["上传包结构"], "跳过")
        # user 2026-10-24: design and art rows were checked at their own stage; the preflight only hints at them
        for title in ("清晰度", "排名扩展", "单调页面", "内置板块", "顶部资源栏", "关卡地图"):
            self.assertEqual(rows[title], "提示", title)
        self.assertNotIn("出错", rows.values())
        self.assertTrue((self.out / "preflight.md").is_file())
        out2 = self.out.parent / (self.out.name + "-strict")
        r = self.run_tool("preflight.py", "--project", self.project, "--levels", "20", "--recheck-earlier", "--out", out2)
        rows = {x["check"]: x["status"] for x in json.loads((out2 / "preflight.json").read_text(encoding="utf-8"))["results"]}
        self.assertEqual(rows["清晰度"], "需处理")
        self.assertEqual(rows["排名扩展"], "不适用")          # no ranking feature; missing old opt-in record must not demand one
        self.assertEqual(rows["单调页面"], "需处理")          # no page dumps yet
        self.assertEqual(rows["内置板块"], "需处理")          # nobody asked the user yet (docs/features.json)
        self.assertEqual(rows["顶部资源栏"], "需处理")        # no docs/top-bar.json yet
        self.assertEqual(rows["关卡地图"], "需处理")          # no level_plan.json yet

    def test_no_ad_skip_scan(self):
        (self.project / "assets" / "Fail.ts").write_text(
            "// 跳关 in a comment is fine\nexport function onSkipLevel() {}\nfunction skipTutorial() {}\n", encoding="utf-8")
        r = self.run_tool("audit_no_ad_skip.py", "--project", self.project)
        data = json.loads(r.stdout)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(data["blocking"], 1)
        (self.project / "assets" / "Fail.ts").write_text("function skipTutorial() {}\n", encoding="utf-8")
        self.assertEqual(self.run_tool("audit_no_ad_skip.py", "--project", self.project).returncode, 0)

    def test_preflight_refuses_output_inside_project(self):
        r = self.run_tool("preflight.py", "--project", self.project, "--out", self.project / "pf")
        self.assertEqual(r.returncode, 2)


class RarityUnlockTests(unittest.TestCase):
    """Rarity x five unlock types, 8-ad cap, R value bands, level unlocks only for maps (user rules 2026-10-20/22)."""
    SKINS = [("s01", "common", "free", 0, 0), ("s02", "common", "ads", 1, 0), ("s03", "common", "coins", 0, 100),
             ("s04", "common", "ads_or_coins", 2, 100), ("s05", "common", "ads_coins", 1, 50),
             ("s06", "rare", "ads", 3, 0), ("s07", "rare", "coins", 0, 175), ("s08", "rare", "ads_or_coins", 4, 200),
             ("s09", "rare", "ads_coins", 2, 75), ("s10", "epic", "ads", 5, 0), ("s11", "epic", "coins", 0, 275),
             ("s12", "epic", "ads_or_coins", 6, 300), ("s13", "epic", "ads_coins", 3, 125),
             ("s14", "legendary", "ads", 7, 0), ("s15", "legendary", "coins", 0, 375),
             ("s16", "legendary", "ads_or_coins", 8, 400), ("s17", "legendary", "ads_coins", 4, 175)]

    def rows(self):
        rows = [{"id": i, "group": "collectible", "order": n + 1, "rarity": r, "unlock": u, "ads": a, "coins": c}
                for n, (i, r, u, a, c) in enumerate(self.SKINS)]
        rows += [{"id": "m1", "group": "map", "order": 1, "rarity": "common", "unlock": "free", "ads": 0, "coins": 0},
                 {"id": "m2", "group": "map", "order": 2, "rarity": "rare", "unlock": "level", "level": 20,
                  "condition": "clear", "ads": 0, "coins": 0}]
        return rows

    def check(self, rows, rate=50):
        import audit_acquisition_progression as acq
        f = {k: k for k in ("id", "group", "order", "rarity", "unlock", "coins", "ads")}
        return acq.audit_rarity(rows, f, ["common", "rare", "epic", "legendary"], 40, rate)

    def test_default_design_passes(self):
        result = self.check(self.rows())
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_each_rule_blocks(self):
        cases = {
            "more than 8 ads": lambda r: r[15].update(ads=9, coins=450),
            "value outside band": lambda r: r[6].update(coins=120),
            "or-coins price not ads x R": lambda r: r[7].update(coins=260),
            "rarity down": lambda r: r[5].update(rarity="epic"),
            "missing ads_or_coins": lambda r: [x.update(unlock="ads", coins=0) for x in r if x["unlock"] == "ads_or_coins"],
            "numbers mismatch": lambda r: r[2].update(ads=1),
            "free after paid": lambda r: r[9].update(unlock="free", ads=0),
            "perfect-clear skin (user 2026-10-22: none)": lambda r: r.append({"id": "s_lv10", "group": "skin", "order": 50,
                "rarity": "epic", "unlock": "level", "level": 10, "condition": "perfect", "ads": 0, "coins": 0}),
            "level skin with an unknown condition": lambda r: r.append({"id": "s_lv20", "group": "skin", "order": 51,
                "rarity": "epic", "unlock": "level", "level": 20, "condition": "win", "ads": 0, "coins": 0}),
            "level item without level": lambda r: r[-1].pop("level"),
            "map levels not increasing": lambda r: r[-1].update(level=1, order=0) or r[-2].update(order=5),
        }
        for name, change in cases.items():
            rows = self.rows()
            change(rows)
            self.assertEqual(self.check(rows)["status"], "fail", name)

    def test_missing_rate_blocks(self):
        self.assertEqual(self.check(self.rows(), None)["status"], "fail")

class FrameGlitchTests(unittest.TestCase):
    """Synthetic 60 fps frames: a moving scene with a black flash, a fast flicker and a one-frame missing button."""
    def make(self, glitches):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow not installed")
        temp = tempfile.TemporaryDirectory(prefix="glitch-test-")
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name) / "frames"
        folder.mkdir()
        for i in range(240):
            im = Image.new("RGB", (180, 320), (191, 230, 255))
            dr = ImageDraw.Draw(im)
            x = (i * 3) % 200 - 10
            dr.ellipse((x, 60, x + 20, 80), fill=(255, 122, 162))
            button = (60, 179, 113)
            if glitches and 150 <= i < 210 and (i // 3) % 2:
                button = (255, 0, 0)
            if not (glitches and i == 120):
                dr.rectangle((40, 250, 140, 290), fill=button)
            if glitches and i in (90, 91):
                im = Image.new("RGB", (180, 320), (0, 0, 0))
            im.save(folder / f"{i:05d}_{int(i * 1000 / 60):07d}ms.png")
        return folder

    def run_tool(self, folder):
        here = Path(__file__).resolve().parent
        report = folder.parent / "report.json"
        r = subprocess.run([sys.executable, "-B", str(here / "audit_frame_glitches.py"), str(folder), "--report", str(report)],
                           capture_output=True, text=True, encoding="utf-8")
        return r.returncode, json.loads(report.read_text(encoding="utf-8"))

    def test_finds_flash_flicker_and_missing_frame(self):
        code, report = self.run_tool(self.make(True))
        self.assertEqual(code, 1)
        kinds = {e["type"] for e in report["checks"]}
        self.assertTrue({"flash_dark", "flicker", "one_frame_glitch"} <= kinds, kinds)
        self.assertTrue(all(len(e.get("evidence", [])) == 3 for e in report["checks"]))

    def test_clean_animation_passes(self):
        code, report = self.run_tool(self.make(False))
        self.assertEqual(code, 0, report["checks"])


class ContactSheetTests(unittest.TestCase):
    """Screenshots -> numbered overview sheets with a manifest the gate can bind to the build."""
    def test_sheets_and_manifest(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory(prefix="sheet-test-") as temp:
            root = Path(temp)
            shots = root / "shots"
            shots.mkdir()
            for i in range(10):
                Image.new("RGB", (75, 162), (20 * i, 200, 255 - 20 * i)).save(shots / f"page{i:02d}.png")
            review = root / "review.json"
            review.write_text(json.dumps({"binding": {"build_tag": "t1"}}))
            out = root / "sheets"
            tool = Path(__file__).with_name("make_contact_sheet.py")
            run = subprocess.run([sys.executable, str(tool), str(shots), "--out", str(out), "--binding", str(review)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            manifest = json.loads((out / "contact-sheets.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["total"], 10)
            self.assertEqual(len(manifest["sheets"]), 2)            # 8 per sheet by default
            self.assertEqual(manifest["binding"], {"build_tag": "t1"})
            self.assertEqual([x["n"] for s in manifest["sheets"] for x in s["items"]], list(range(1, 11)))
            again = subprocess.run([sys.executable, str(tool), str(shots), "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(again.returncode, 2)                     # never overwrites earlier sheets


class NoShareTests(unittest.TestCase):
    """User 2026-10-23: sharing cannot be used; an original game's share call is removed (above all in 英化)."""
    OK = ("TTMinis.game; canIUse('addShortcut'); addShortcut(); getShortcutMissionReward(); startEntranceMission();"
          " getEntranceMissionReward(); canReceiveReward; createRewardedVideoAd().onClose(r => r.isEnded); tt.hideShareMenu();\n")

    def run_audit(self, code):
        with tempfile.TemporaryDirectory(prefix="share-") as temp:
            src = Path(temp) / "assets" / "scripts"; src.mkdir(parents=True)
            (src / "Main.ts").write_text(code, encoding="utf-8")
            r = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("audit_platform_markers.py")), temp],
                               capture_output=True, text=True, encoding="utf-8")
            return r.returncode, json.loads(r.stdout) if r.stdout.strip() else r.stderr

    def test_share_call_in_source_fails(self):
        code, out = self.run_audit(self.OK)
        self.assertEqual(code, 0, out)                     # hideShareMenu (turning share off) is fine
        code, out = self.run_audit(self.OK + "onShare() { tt.shareAppMessage({ title: 'Beat my score!' }); }\n")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "share_feature_present_remove_it")
        self.assertIn("shareAppMessage", out["share_calls_in_source"])


class BannedUiTests(unittest.TestCase):
    """User rule 2026-10-20: play area >= 80%, no big white sheets or big solid blocks."""
    # Current home contract: currency top, side features above PLAY, at most five below PLAY
    HOME = {"name": "home", "kind": "page", "role": "home", "size": [390, 844], "buttons": [
        {"name": "settings", "rect": [14, 14, 48, 48]}, {"name": "TopBar/CoinsPlus", "rect": [150, 18, 40, 40]},
        {"name": "play", "rect": [85, 640, 220, 64], "primary": True, "label": "text"},
        {"name": "shop", "rect": [20, 430, 50, 50], "label": "small"}, {"name": "wardrobe", "rect": [320, 430, 50, 50], "label": "small"},
        {"name": "map", "rect": [144, 760, 50, 50], "label": "small"}, {"name": "help", "rect": [206, 760, 50, 50]},
        {"name": "BtnShortcut", "rect": [268, 760, 50, 50]}, {"name": "BtnRevisit", "rect": [330, 760, 50, 50]}]}

    def run_cov(self, layout, add_home=True):
        if add_home and not any(s.get("role") == "home" for s in layout["screens"]):
            layout = {"screens": layout["screens"] + [self.HOME]}
        with tempfile.TemporaryDirectory(prefix="ui-cov-") as temp:
            f = Path(temp) / "ui-layout.json"
            f.write_text(json.dumps(layout))
            r = subprocess.run([sys.executable, str(Path(__file__).with_name("audit_ui_coverage.py")), str(f), "--rules-selftest"],
                               capture_output=True, text=True)
            return r.returncode, json.loads(r.stdout) if r.stdout.strip() else r.stderr

    def test_home_needs_shortcut_and_revisit_and_share_is_banned(self):
        """User 2026-10-23: 英化 adds Add to Home Screen + Profile Revisit to the home without asking; no share at all."""
        play = {"name": "play", "kind": "gameplay", "size": [390, 844], "elements": [{"name": "pause", "rect": [330, 14, 44, 44]}]}
        code, out = self.run_cov({"screens": [play]})
        self.assertEqual(code, 0, out)
        bare = dict(self.HOME, buttons=[b for b in self.HOME["buttons"] if b["name"] not in ("BtnShortcut", "BtnRevisit")])
        code, out = self.run_cov({"screens": [play, bare]})
        text = json.dumps(out)
        self.assertEqual(code, 1)
        self.assertIn("no desktop-shortcut button", text)
        self.assertIn("no profile-revisit button", text)
        shared = dict(self.HOME, buttons=self.HOME["buttons"][:-1] + [
            {"name": "Canvas/Home/BtnRevisit", "rect": [330, 760, 50, 50]},
            {"name": "Canvas/Home/BtnGift", "rect": [20, 700, 50, 50], "text": "SHARE"}])
        result = {"name": "result", "kind": "popup", "size": [390, 844], "panel": [45, 250, 300, 340],
                  "safe": [60, 270, 270, 300], "contents": [{"name": "BtnShareWin", "rect": [100, 500, 190, 50]}]}
        code, out = self.run_cov({"screens": [play, shared, result]})
        text = json.dumps(out)
        self.assertEqual(code, 1)
        self.assertIn("share feature on home (Canvas/Home/BtnGift)", text)
        self.assertIn("share feature on result (BtnShareWin)", text)

    def test_crowded_hud_and_full_screen_popup_fail(self):
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [750, 1624], "elements": [
                {"name": "top", "rect": [0, 0, 750, 300]}, {"name": "pause", "rect": [650, 40, 80, 80]},
                {"name": "bottom", "rect": [0, 1300, 750, 324]},
                {"name": "tip", "rect": [100, 700, 550, 200], "temporary": True}]},
            {"name": "pause", "kind": "popup", "size": [750, 1624], "panel": [20, 80, 710, 1460],
             "safe": [60, 140, 630, 1340], "contents": [{"name": "resume", "rect": [200, 600, 350, 110]}]}]})
        self.assertEqual(code, 1)
        text = json.dumps(out)
        for needle in ("persistent UI covers", "overlap", "central play area", "popup panel covers"):
            self.assertIn(needle, text)

    def test_compact_layout_passes(self):
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [750, 1624], "elements": [
                {"name": "level_coins", "rect": [30, 60, 420, 80]}, {"name": "pause", "rect": [640, 60, 80, 80]},
                {"name": "boosters", "rect": [150, 1460, 450, 110]},
                {"name": "tip", "rect": [200, 180, 350, 80], "temporary": True}]},
            {"name": "pause", "kind": "popup", "size": [750, 1624], "panel": [95, 450, 560, 720],
             "safe": [135, 500, 480, 620], "decorations": [{"name": "corner", "rect": [95, 1100, 60, 70]}],
             "contents": [{"name": "title", "rect": [200, 520, 350, 80]}, {"name": "resume", "rect": [200, 980, 350, 100]}]},
            {"name": "shop", "kind": "page"}]})
        self.assertEqual(code, 0, out)

    def test_title_on_border_and_button_on_ornament_fail(self):
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [750, 1624], "elements": [{"name": "pause", "rect": [640, 60, 80, 80]}]},
            {"name": "shop", "kind": "popup", "size": [750, 1624], "panel": [95, 400, 560, 800], "safe": [135, 460, 480, 680],
             "decorations": [{"name": "corner_bl", "rect": [95, 1120, 70, 80]}],
             "contents": [{"name": "title_plaque", "rect": [180, 420, 390, 90]},
                          {"name": "buy", "rect": [150, 1060, 450, 110]}]},
            {"name": "levels", "kind": "page", "boxes": [{"name": "gift", "frame": [60, 300, 630, 700], "safe": [100, 350, 550, 600],
             "contents": [{"name": "status_plaque", "rect": [120, 320, 300, 70]}]}]}]})
        self.assertEqual(code, 1)
        text = json.dumps(out)
        for needle in ("title_plaque crosses the inner border", "buy overlaps frame ornament corner_bl",
                       "status_plaque crosses the inner border"):
            self.assertIn(needle, text)

    def test_popup_without_inner_box_is_rejected(self):
        code, _ = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [750, 1624], "elements": [{"name": "pause", "rect": [640, 60, 80, 80]}]},
            {"name": "pause", "kind": "popup", "size": [750, 1624], "panel": [95, 450, 560, 720]}]})
        self.assertEqual(code, 2)

    def test_crowded_text_tile_home_fails(self):
        tiles = [{"name": n, "rect": [25 + 117 * (i % 3), 517 + 93 * (i // 3), 106, 57], "label": "text"}
                 for i, n in enumerate(["wardrobe", "map", "missions", "rewards", "help", "album"])]
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [390, 844], "elements": [{"name": "pause", "rect": [330, 30, 44, 44]}]},
            {"name": "home", "kind": "page", "role": "home", "size": [390, 844],
             "buttons": tiles + [{"name": "play", "rect": [41, 419, 307, 54], "primary": True, "label": "text"}]}]})
        self.assertEqual(code, 1)
        text = json.dumps(out)
        for needle in ("is a text tile", "at most 5", "wider than 70%"):
            self.assertIn(needle, text)

    def test_currency_in_the_middle_and_scattered_icons_fail(self):
        # user 2026-10-23 (Hazel's Shelf Scramble home): coin bar in the middle of the screen, map at mid-left, skins at
        # mid-right, help and video pushed into the two bottom corners, a big empty space
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [390, 844], "elements": [{"name": "pause", "rect": [330, 30, 44, 44]}]},
            {"name": "home", "kind": "page", "role": "home", "size": [390, 844], "buttons": [
                {"name": "BtnSettings", "rect": [330, 130, 48, 48]}, {"name": "CoinBar/BtnAddCoins", "rect": [230, 330, 40, 40]},
                {"name": "BtnMap", "rect": [10, 430, 56, 56], "label": "small"}, {"name": "BtnSkins", "rect": [324, 430, 56, 56], "label": "small"},
                {"name": "BtnPlay", "rect": [95, 600, 200, 70], "primary": True, "label": "text"},
                {"name": "BtnHelp", "rect": [10, 770, 48, 48]}, {"name": "BtnVideo", "rect": [332, 770, 48, 48]}]}]}, add_home=False)
        self.assertEqual(code, 1)
        text = json.dumps(out)
        for needle in ("belongs to the resource bar at the very top", "no desktop-shortcut button", "no profile-revisit button"):
            self.assertIn(needle, text)

    def test_buttons_up_to_40_percent(self):
        # user 2026-10-23: buttons may cover up to 40% of the screen, not more
        big = dict(self.HOME, buttons=self.HOME["buttons"] + [{"name": "gift", "rect": [20, 380, 350, 250], "primary": True, "label": "text"}])
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [390, 844], "elements": [{"name": "pause", "rect": [330, 30, 44, 44]}]}, big]},
            add_home=False)
        self.assertNotIn("buttons cover", json.dumps(out))                     # about 36%: allowed now
        big["buttons"][-1]["rect"] = [20, 300, 350, 330]
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [390, 844], "elements": [{"name": "pause", "rect": [330, 30, 44, 44]}]}, big]},
            add_home=False)
        self.assertIn("(limit 40%)", json.dumps(out))

    def test_hud_in_the_middle_fails(self):
        code, out = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [390, 844], "elements": [{"name": "energy", "rect": [100, 380, 190, 60]}]}]})
        self.assertEqual(code, 1)
        self.assertIn("middle of the play area", json.dumps(out))

    def test_missing_home_page_is_rejected(self):
        code, _ = self.run_cov({"screens": [
            {"name": "play", "kind": "gameplay", "size": [750, 1624], "elements": [{"name": "pause", "rect": [640, 60, 80, 80]}]}]},
            add_home=False)
        self.assertEqual(code, 2)

    def test_dev_text_found(self):
        with tempfile.TemporaryDirectory(prefix="devtext-") as temp:
            proj = Path(temp); (proj / "assets").mkdir()
            (proj / "assets" / "Home.ts").write_text('// TODO placeholder\nlabel.string = "PLAYABLE PROTOTYPE";\nconsole.log("debug")\n')
            (proj / "assets" / "btn_placeholder.png").write_bytes(b"x")
            tool = str(Path(__file__).with_name("audit_dev_text.py"))
            r = subprocess.run([sys.executable, tool, "--project", str(proj)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("PLAYABLE PROTOTYPE", r.stdout)
            (proj / "assets" / "Home.ts").write_text('label.string = "PLAY";\n')
            r = subprocess.run([sys.executable, tool, "--project", str(proj)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)                        # placeholder art allowed before the art stage
            r = subprocess.run([sys.executable, tool, "--project", str(proj), "--final"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)

    def test_layout_without_gameplay_screen_is_rejected(self):
        code, _ = self.run_cov({"screens": [{"name": "shop", "kind": "page"}]})
        self.assertEqual(code, 2)

    def test_big_white_sheet_and_solid_block_are_measured(self):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow not installed")
        import audit_dark_area as dark
        with tempfile.TemporaryDirectory(prefix="ui-white-") as temp:
            white = Path(temp) / "white.png"
            im = Image.new("RGB", (360, 640), (150, 200, 240))
            d = ImageDraw.Draw(im)
            for x in range(0, 360, 12):                     # patterned, colourful background
                d.line((x, 0, x, 640), fill=(120, 190, 120), width=3)
            d.rounded_rectangle((20, 40, 340, 600), 30, fill=(250, 250, 250))
            im.save(white)
            m = dark.measure(white, Image)
            self.assertGreater(m["white_block_ratio"], 0.25)
            good = Path(temp) / "good.png"
            im = Image.new("RGB", (360, 640), (150, 200, 240))
            d = ImageDraw.Draw(im)
            for x in range(0, 360, 12):
                d.line((x, 0, x, 640), fill=(120, 190, 120), width=3)
            for y in range(200, 440, 10):                   # small textured cream panel
                d.line((90, y, 270, y), fill=(255, 236, 200) if y % 20 else (255, 220, 170), width=10)
            im.save(good)
            m = dark.measure(good, Image)
            self.assertLess(m["white_block_ratio"], 0.25)
            self.assertLess(m["white_gray_ratio"], 0.35)
            self.assertLess(m["plain_block_ratio"], 0.35)

    def test_dark_area_checks_only_negative_rules_without_brightness_floor(self):
        """User 2026-10-28: art rules are negative only. A muted, mid-dark but varied screen (the starter
        pack's own style) passes; large dark areas, a plain black backdrop and a big white sheet still fail;
        no minimum-brightness option or 'too dark overall' rule exists any more."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow not installed")
        import audit_dark_area as dark
        tool = str(Path(__file__).with_name("audit_dark_area.py"))
        muted = [(84, 98, 122), (104, 92, 118), (78, 112, 104), (118, 104, 86)]   # L* about 40-45, no bright colour

        def striped(size):
            im = Image.new("RGB", size)
            d = ImageDraw.Draw(im)
            for x in range(0, size[0], 3):                    # 3 px stripes: no colour > 25%, no plain 8 px cell
                d.line((x, 0, x, size[1]), fill=muted[(x // 3) % 4], width=3)
            return im

        def cli(path, *extra):
            out = Path(path).with_suffix(".report.json")
            r = subprocess.run([sys.executable, "-B", tool, str(path), "--out", str(out), *extra],
                               capture_output=True, text=True, timeout=120)
            report = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
            return r, report

        with tempfile.TemporaryDirectory(prefix="dark-negative-") as temp:
            muted_shot = Path(temp) / "muted.png"
            striped((180, 320)).save(muted_shot)
            m = dark.measure(muted_shot, Image)
            self.assertLess(m["avg_lstar"], 50)               # would have failed the removed "average L* >= 50" floor
            self.assertLess(m["dark_ratio"], 0.15)
            r, report = cli(muted_shot)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("min_avg_lstar", report)
            self.assertEqual(report["results"][0]["problems"], [])

            r = subprocess.run([sys.executable, "-B", tool, str(muted_shot), "--min-avg", "50"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 2)                 # a brightness floor can no longer be switched on

            night = Path(temp) / "night.png"                  # large dark area: still banned
            im = striped((180, 320))
            ImageDraw.Draw(im).rectangle((0, 0, 179, 200), fill=(12, 14, 22))
            im.save(night)
            r, report = cli(night)
            self.assertEqual(r.returncode, 1)
            self.assertIn("large dark area", report["results"][0]["problems"])

            backdrop = Path(temp) / "black-backdrop.png"      # popup on a plain black backdrop: still banned
            im = Image.new("RGB", (180, 320), (0, 0, 0))
            im.paste(striped((110, 150)), (35, 85))
            im.save(backdrop)
            r, report = cli(backdrop)
            self.assertEqual(r.returncode, 1)
            self.assertIn("plain black/solid backdrop around panel", report["results"][0]["problems"])

            sheet = Path(temp) / "white-sheet.png"            # big white sheet: still banned
            im = striped((180, 320))
            ImageDraw.Draw(im).rectangle((10, 20, 170, 300), fill=(250, 250, 250))
            im.save(sheet)
            r, report = cli(sheet)
            self.assertEqual(r.returncode, 1)
            self.assertIn("large plain white panel/sheet", report["results"][0]["problems"])


class StartupLoadingTests(unittest.TestCase):
    """LOAD-03 timing audit on synthetic chrome_touch reports (no browser)."""
    def make(self, root, mutate=None):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow not installed")
        import hashlib
        prof = {"cold": 3, "warm": 1, "budgets": {"feedback_ms": 500, "home_ms": 3000, "play_to_ready_ms": 1000}}
        plan = {"declared_at": "1970-01-01T00:00:00+00:00", "viewports": [[393, 852], [412, 732]],
                "profiles": {"local": dict(prof, network=None),
                             "first_network": dict(prof, network={"download_kbps": 10000, "upload_kbps": 5000, "latency_ms": 80}),
                             "slow_network": dict(prof, cold=1, warm=0, network={"download_kbps": 2000, "upload_kbps": 1000, "latency_ms": 150})},
                "loading_roi": {"bootstrap": [40, 40, 120, 120], "enter_level": [40, 40, 120, 120]},
                "animation_freeze_ms": 1000, "max_home_asset_kb": 500, "idle_timeout_ms": 3000, "old_deadline_ms": 4000}
        pf = root / "plan.json"; pf.write_text(json.dumps(plan))
        psha = hashlib.sha256(pf.read_bytes()).hexdigest()
        runs = []
        def run(name, vp, profile=None, fault=None, marks=None, frozen=False, requests=(), extra=None):
            d = root / name; fr = d / "frames"; fr.mkdir(parents=True)
            for i in range(0, getattr(mutate, "frames", 60)):
                im = Image.new("RGB", (360, int(360 * vp[1] / vp[0])), (200, 230, 255))
                dr = ImageDraw.Draw(im); k = 0 if frozen else i
                dr.pieslice((47, 47, 130, 130), k * 20, k * 20 + 90, fill=(255, 120, 0))
                im.save(fr / f"{i:05d}_{i * 100:07d}ms.jpg")
            rep = {"status": "completed_pending_business_and_visual_review", "startup_plan_sha256": psha,
                   "viewport_requested": {"width": vp[0], "height": vp[1]}, "profile": profile, "fault": fault,
                   "cache_mode": "cold", "cache_disabled": True, "entry_epoch": 1000.0,
                   "network_applied": plan["profiles"][profile]["network"] if profile else None,
                   "marks": marks or {"first_feedback": 100, "home_usable": 2500, "play_touch": 2600,
                                      "level_ready": 3300, "first_effect": 3400},
                   "requests": list(requests), "steps": [], "background": [],
                   "recording": {"dir": str(fr), "first_frame_epoch": 1000.0}}
            rep.update(extra or {})
            if mutate:
                mutate(name, rep)
            (d / "report.json").write_text(json.dumps(rep))
            runs.append(str(d))
        for vp in plan["viewports"]:
            for prof_name in plan["profiles"]:
                run("%s-%dx%d" % (prof_name, vp[0], vp[1]), vp, prof_name, frozen=bool(mutate and prof_name == "slow_network" and getattr(mutate, "freeze", False)))
                for cache in ('cold', 'warm'):
                    for repeat in range(1 if cache == 'cold' else 0, plan['profiles'][prof_name][cache]):
                        run("%s-%dx%d-%s-%d" % (prof_name, vp[0], vp[1], cache, repeat), vp, prof_name,
                            extra={"cache_mode": cache, "cache_disabled": cache == 'cold', "warmup_done": cache == 'warm'})
        full = {"first_feedback": 100, "home_usable": 4500, "play_touch": 4600, "level_ready": 5000, "first_effect": 5100}
        run("f-slow", [393, 852], fault="slow_progress", marks=full)
        run("f-bg", [393, 852], fault="background_wait", marks=full,
            extra={"background": [{"from_ms": 100, "to_ms": 4000, "visibility_while_away": "hidden"}]})
        run("f-stall", [393, 852], fault="stall_retry", marks=dict(full, retry_shown=4200),
            extra={"steps": [{"action": {"type": "unblock"}}]})
        run("f-late", [393, 852], fault="late_callback", marks=dict(full, old_result_arrived=5200))
        run("f-api", [393, 852], fault="optional_api_missing", marks=full, extra={"init_js_sha256": "a" * 64})
        run("f-modal", [393, 852], fault="native_modal_no_callback", marks=dict(full, fallback_prompt_shown=5300),
            extra={"init_js_sha256": "b" * 64})
        run("f-img", [393, 852], fault="image_no_callback", marks=dict(full, retry_shown=4000),
            extra={"held_requests": ["http://x/logo.png"], "steps": [{"action": {"type": "unhang"}}]})
        run("f-audio", [393, 852], fault="audio_fail", marks=full,
            requests=[{"url": "(failed) net::ERR_BLOCKED_BY_CLIENT", "failed": True, "t_ms": 300}])
        return pf, runs

    def audit(self, pf, runs):
        import audit_startup_loading as sl
        plan = json.loads(pf.read_text())
        import hashlib
        return sl.check(plan, runs, hashlib.sha256(pf.read_bytes()).hexdigest())

    def test_complete_matrix_passes(self):
        with tempfile.TemporaryDirectory() as t:
            runs, problems = self.audit(*self.make(Path(t)))
            self.assertEqual(problems, [])
            self.assertTrue(all(r["passed"] for r in runs), [r for r in runs if not r["passed"]])

    def test_slow_home_frozen_spinner_and_big_asset_fail(self):
        def mutate(name, rep):
            if name.startswith("first_network-393"):
                rep["marks"]["home_usable"] = 3500                     # over the 3000 ms budget
            if name.startswith("local-412"):
                rep["requests"] = [{"url": "http://x/hint_button.png", "bytes": 2100000, "t_ms": 900}]
        mutate.freeze = True
        with tempfile.TemporaryDirectory() as t:
            runs, problems = self.audit(*self.make(Path(t), mutate))
            text = json.dumps(runs)
            self.assertIn("home usable 3500 ms > 3000", text)
            self.assertIn("loading animation froze", text)
            self.assertIn("big asset loaded before home", text)
            self.assertTrue(problems)                                  # coverage now missing for those cells

    def test_slow_loading_screen_loose_plan_and_reentry_fail(self):
        # user 2026-10-23: loading animation too slow / hard to get into the game / cannot enter the game
        def mutate(name, rep):
            if name.startswith("local-393"):
                rep["requests"] = [{"url": "http://x/main.js", "bytes": 90000, "t_ms": 400}]   # done at 0.4 s, home at 6 s
                rep["marks"].update(home_usable=6000, play_touch=6100, level_ready=6500, first_effect=6600)
            if name.startswith("local-412"):
                rep["marks"].update(retry_touch=3500, retry_ready=6000)                         # retry takes 2.5 s
            if name.startswith("first_network-412"):
                rep["marks"].update(next_touch=3500)                                            # next level never ready
        mutate.frames = 70
        with tempfile.TemporaryDirectory() as t:
            pf, runs = self.make(Path(t), mutate)
            plan = json.loads(pf.read_text())
            plan["profiles"]["local"]["budgets"]["home_ms"] = 9000      # a loose plan does not help: the size rule still applies
            plan["animation_freeze_ms"] = 5000                             # stuck limits cannot be loosened
            pf.write_text(json.dumps(plan))
            import hashlib
            psha = hashlib.sha256(pf.read_bytes()).hexdigest()
            for r in runs:
                rp = Path(r) / "report.json"; rep = json.loads(rp.read_text()); rep["startup_plan_sha256"] = psha
                rp.write_text(json.dumps(rep))
            runs, problems = self.audit(pf, runs)
            text = json.dumps(runs)
            self.assertIn("home usable 6000 ms > 3025", text)
            self.assertIn("not explained by downloading", text)
            self.assertIn("after the last download finished", text)
            self.assertIn("enter level again (retry) 2500 ms > 1000", text)
            self.assertIn("next_touch tapped but next_ready never reached", text)
            self.assertTrue(any("looser than the stuck limit" in p for p in problems))

    def test_big_game_gets_time_for_what_it_really_loads(self):
        # user 2026-10-23: no fixed finish time - an 8 MB first screen on 10 Mbps may take 11 s, it is not stuck or wasted
        chunks = [{"url": "http://x/res/%02d.bin" % i, "bytes": 400 * 1024, "t_ms": 500 * (i + 1)} for i in range(20)]
        def mutate(name, rep):
            if name.startswith("first_network-393"):
                rep["requests"] = chunks
                rep["marks"].update(home_usable=11000, play_touch=11100, level_ready=11800, first_effect=11900)
        mutate.frames = 125
        with tempfile.TemporaryDirectory() as t:
            pf, runs = self.make(Path(t), mutate)
            plan = json.loads(pf.read_text())
            for prof in plan["profiles"].values():
                prof.pop("budgets")                                        # no product target: only the size rule
            pf.write_text(json.dumps(plan))
            import hashlib
            psha = hashlib.sha256(pf.read_bytes()).hexdigest()
            for r in runs:
                rp = Path(r) / "report.json"; rep = json.loads(rp.read_text()); rep["startup_plan_sha256"] = psha
                rp.write_text(json.dumps(rep))
            runs, problems = self.audit(pf, runs)
            self.assertEqual(problems, [])
            big = next(r for r in runs if r["run"].startswith("first_network-393"))
            self.assertTrue(big["passed"], big)
            self.assertGreater(big["home_usable_allowed_ms"], 11000)
            self.assertLess(big["home_usable_waste_ms"], 5000)                 # 11 s - 6.9 s download

    def test_missing_fault_and_foreign_plan_fail(self):
        def mutate(name, rep):
            if name == "local-393x852":
                rep["startup_plan_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as t:
            pf, runs = self.make(Path(t), mutate)
            runs = [r for r in runs if not r.endswith("f-stall")]
            runs, problems = self.audit(pf, runs)
            self.assertIn("fault test missing: stall_retry", problems)
            self.assertIn("not made for this startup plan", json.dumps(runs))

    def test_optional_api_must_not_block_startup(self):
        def mutate(name, rep):
            if name == "f-api":
                rep["marks"].pop("home_usable")                       # game stuck because showModal is missing
                rep["status"] = "failed"
        with tempfile.TemporaryDirectory() as t:
            runs, problems = self.audit(*self.make(Path(t), mutate))
            self.assertIn("optional SDK features never block startup", json.dumps(runs))

    def test_check_report_hook(self):
        import audit_startup_loading as sl
        good = {"tool": "audit_startup_loading", "passed": True, "failed": 0, "checked": 3, "binding": {"b": 1}}
        self.assertEqual(sl.check_report(good, None, {"b": 1}), [])
        self.assertTrue(sl.check_report(dict(good, passed=False, failed=1), None, {"b": 1}))
        self.assertTrue(sl.check_report(good, None, {"b": 2}))


class StartupContractTests(unittest.TestCase):
    """Rainy Duck 2026-10-21: patterns that kept games on the loading screen, and startup size."""
    def run_tool(self, proj, native=None, extra=()):
        cmd = [sys.executable, str(Path(__file__).with_name("audit_startup_contract.py")), "--project", str(proj)]
        if native:
            cmd += ["--native", str(native)]
        r = subprocess.run(cmd + list(extra), capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout or r.stderr)

    def test_bad_startup_code_and_big_startup_fail(self):
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t) / "proj"; (proj / "assets").mkdir(parents=True)
            (proj / "assets" / "Boot.ts").write_text(
                "if (!tt.showModal) { return; }\n"
                "setTimeout(() => this.failLoad(), 15000); // load deadline\n"
                "cc.director.loadScene('Home');\n"
                "cc.game.run(opts);\nfunction retry(){ cc.game.run(opts); }\n")
            native = Path(t) / "native"; (native / "sub" / "audio").mkdir(parents=True)
            (native / "game.json").write_text(json.dumps({"subpackages": [{"name": "audio", "root": "sub/audio"}]}))
            (native / "big.bin").write_bytes(b"0" * (11 * 1024 * 1024))
            (native / "bgm.mp3").write_bytes(b"0" * 1000)
            code, out = self.run_tool(proj, native)
            self.assertEqual(code, 1)
            text = json.dumps(out)
            for needle in ("optional_api_gate", "fixed_deadline", "direct_load_scene", "game_run_twice",
                           "startup download", "audio"):
                self.assertIn(needle, text)

    def test_clean_source_passes_but_native_requires_real_renderer(self):
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t) / "proj"; (proj / "assets").mkdir(parents=True); (proj / "docs").mkdir()
            (proj / "assets" / "Boot.ts").write_text("bundle.loadScene('Home', (e, s) => { if (gen === cur) director.runSceneImmediate(s); });\n"
                                                    "cc.director.loadScene('Credits');\n")
            (proj / "docs" / "startup-contract-review.json").write_text(json.dumps(
                {"assets/Boot.ts:2": "credits page after home; not part of startup, old callback harmless"}))
            native = Path(t) / "native"; native.mkdir()
            (native / "game.json").write_text("{}"); (native / "game.js").write_text("x")
            code, out = self.run_tool(proj, extra=["--source-only"])
            self.assertEqual(code, 0, out)
            code, out = self.run_tool(proj, native)
            self.assertEqual(code, 1, out)
            self.assertIn("requires --renderer-report", json.dumps(out))


class MachineLoadTests(unittest.TestCase):
    """User 2026-10-22/23: nothing waits for an occupied window; only the same game's file writes queue;
    cleanup closes only free/orphaned old windows, never a test that is still running."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lock-test-")
        self.addCleanup(self.temp.cleanup)
        self.env = dict(os.environ, GAME_SKILL_LOCK_DIR=self.temp.name)
        self.here = Path(__file__).resolve().parent

    def lock(self, *args, **kw):
        return subprocess.Popen([sys.executable, "-B", str(self.here / "heavy_lock.py"), *args], env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", **kw)

    def slots(self, *args):
        r = subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), *args], env=self.env,
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_same_game_write_waits_for_first(self):
        import time
        game = self.temp.name + "/gameA"
        first = self.lock("run", "--project", game, "--name", "A build", "--", sys.executable, "-c", "import time; time.sleep(4)")
        time.sleep(1)
        start = time.time()
        second = self.lock("run", "--project", game, "--name", "A build 2", "--", sys.executable, "-c", "print('B')")
        out, _ = second.communicate(timeout=60)
        first.wait(timeout=60)
        self.assertGreaterEqual(time.time() - start, 2.5)
        self.assertIn("B", out)
        self.assertIn("queued_behind_same_game", out)

    def test_no_project_and_tests_never_wait(self):
        import time
        game = self.temp.name + "/gameA"
        first = self.lock("run", "--project", game, "--name", "A build", "--", sys.executable, "-c", "import time; time.sleep(6)")
        time.sleep(1)
        for args in (["--project", self.temp.name + "/gameB", "--name", "B build"],   # another game
                     ["--name", "no project"]):                                           # old machine-wide lock retired
            start = time.time()
            out, _ = self.lock("run", *args, "--", sys.executable, "-c", "print('ran')").communicate(timeout=60)
            self.assertLess(time.time() - start, 3, args)
            self.assertIn("ran", out)
        for name in ("chrome_touch.py", "test_volume.js", "audit_audio_sources.py"):        # tests of the SAME busy game
            fake = Path(self.temp.name) / name
            fake.write_text("print('test ran')\n")
            start = time.time()
            out, _ = self.lock("run", "--project", game, "--name", "volume recheck", "--", sys.executable, str(fake)).communicate(timeout=60)
            self.assertLess(time.time() - start, 3, name)
            self.assertIn("test ran", out)
        start = time.time()
        busy = self.lock("run", "--project", game, "--name", "A again", "--no-wait", "--", sys.executable, "-c", "print('x')")
        out, _ = busy.communicate(timeout=60)
        self.assertEqual(busy.returncode, 75)
        self.assertLess(time.time() - start, 3)
        self.assertIn("same_game_write_busy", out)
        first.wait(timeout=60)

    def test_exit_code_and_stale_takeover(self):
        import hashlib
        game = Path(self.temp.name) / "gameC"
        lockdir = Path(self.temp.name) / ("project-" + hashlib.sha1(str(game.resolve()).lower().encode("utf-8")).hexdigest()[:12])
        lockdir.mkdir()
        (lockdir / "owner.json").write_text('{"pid": 999999, "name": "gone", "started_ts": 0}', encoding="utf-8")
        p = self.lock("run", "--project", str(game), "--name", "C", "--", sys.executable, "-c", "import sys; sys.exit(7)")
        p.communicate(timeout=60)
        self.assertEqual(p.returncode, 7)
        self.assertFalse(lockdir.exists())

    def test_sweep_closes_only_free_slots(self):
        import time
        live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(live.kill)
        user_preview = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(user_preview.kill)
        dead = subprocess.Popen([sys.executable, "-c", "pass"]); dead.wait()
        ids = {
            "live": self.slots("register", "--kind", "touch_run", "--pid", str(live.pid), "--name", "other session test")["slot"],
            "dead": self.slots("register", "--kind", "touch_run", "--pid", str(dead.pid), "--name", "crashed test")["slot"],
            "idle": self.slots("register", "--kind", "ego_space", "--space-id", "41", "--name", "old space")["slot"],
            "fresh": self.slots("register", "--kind", "ego_space", "--space-id", "42", "--name", "new space")["slot"],
            "trial": self.slots("register", "--kind", "preview", "--pid", str(user_preview.pid), "--name", "user trial", "--keep")["slot"],
            "old_ego_trial": self.slots("register", "--kind", "ego_space", "--space-id", "44", "--name", "left for the user")["slot"],
        }
        for key in ("idle", "trial", "old_ego_trial"):                      # pretend these were last used an hour ago
            path = Path(self.temp.name) / "browser-slots" / (ids[key] + ".json")
            data = json.loads(path.read_text(encoding="utf-8")); data["heartbeat_ts"] = time.time() - 3600
            if key == "old_ego_trial":
                data["heartbeat_ts"] = time.time(); data["keep"] = True   # an older version kept it for the user
            path.write_text(json.dumps(data), encoding="utf-8")
        listed = self.slots("sweep")
        self.assertEqual({x["id"] for x in listed["free_not_closed"]}, {ids["dead"], ids["idle"], ids["old_ego_trial"]})
        report = self.slots("sweep", "--close")
        self.assertEqual({x["id"] for x in report["freed"]}, {ids["dead"]})
        self.assertIn(ids["idle"], {x["id"] for x in report["review_candidates_not_closed"]})
        self.assertEqual({x["id"] for x in report["active"]}, {ids["live"], ids["fresh"], ids["trial"]})
        self.assertIsNone(live.poll())                    # another session's running test is never touched
        self.assertTrue(any(x["space_id"] == 41 for x in report["ego_spaces_to_finish_by_hand"]) or
                        any(x.get("ego") == "finished" for x in report["freed"]))
        self.assertIn("open a new one", report["rule"])

    def test_line_closes_what_it_opened_after_the_test(self):
        """User 2026-10-23: whatever the stage, once a test is done the session closes its own Ego windows itself."""
        mine = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(mine.kill); self.addCleanup(other.kill)
        preview = self.slots("register", "--kind", "preview", "--pid", str(mine.pid), "--name", "测试线 加载复测")["slot"]
        space = self.slots("register", "--kind", "ego_space", "--space-id", "51", "--name", "测试线 按钮点测")["slot"]
        user = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"]); self.addCleanup(user.kill)
        trial = self.slots("register", "--kind", "preview", "--pid", str(user.pid), "--name", "测试线 用户试玩", "--keep")["slot"]
        theirs = self.slots("register", "--kind", "touch_run", "--pid", str(other.pid), "--name", "美术线 截图")["slot"]
        r = subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), "check", "--name", "测试线"],
                           env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)                  # still open: the test may not be reported as done
        self.assertEqual(len(json.loads(r.stdout)["still_open"]), 3)
        env = dict(self.env, PATH="")                     # no ego-browser here: the finish code is handed back
        r = subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), "close", "--name", "测试线"],
                           env=env, capture_output=True, text=True, encoding="utf-8")
        out = json.loads(r.stdout)
        self.assertEqual(r.returncode, 2)
        self.assertEqual({c["id"] for c in out["closed"]}, {preview})
        self.assertEqual({c["id"] for c in out["cleanup_pending"]}, {space})
        self.assertNotIn("taskSpace(51)", json.dumps(out))
        self.assertEqual([k["id"] for k in out["kept_user_trial_preview"]], [trial])   # the Codex preview link
        mine.wait(timeout=10)                             # the preview process really stopped
        self.assertIsNone(other.poll())                   # another line's window is never touched
        left = {d["id"] for d in self.slots("list")}
        self.assertEqual(left, {space, trial, theirs})
        r = subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), "check", "--name", "测试线"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)                 # failed Ego cleanup must never become a passing check
        # Isolated readback fixture: owning Agent already finished the space, and the supported list is now empty.
        code = "import browser_slots as s;s.ego_list=lambda:{'spaces':[]};print(s.close(sid=__import__('sys').argv[1]))"
        r = subprocess.run([sys.executable, "-B", "-c", code, space], cwd=self.here, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.slots("check", "--name", "测试线")["ok"])
        subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), "close", "--id", trial],
                       env=env, capture_output=True, text=True, encoding="utf-8")   # user done: close it too
        self.assertEqual({d["id"] for d in self.slots("list")}, {theirs})
        user.wait(timeout=10)

    def test_ego_is_never_kept_or_handed_to_the_user(self):
        """User 2026-10-23: Ego is only for the agent's own tests; the user plays the local preview in Codex."""
        r = subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), "register", "--kind", "ego_space",
                            "--space-id", "61", "--name", "user trial", "--keep"], env=self.env, capture_output=True,
                           text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 2)
        self.assertIn("local preview", json.loads(r.stdout)["error"])
        touch = Path(__file__).resolve().parents[2] / "chrome-mobile-testing" / "scripts" / "chrome_touch.py"
        if not touch.is_file():
            touch = Path(__file__).resolve().parents[3] / "support-skills" / "chrome-mobile-testing" / "scripts" / "chrome_touch.py"
        r = subprocess.run([sys.executable, "-B", str(touch), "--url", "http://127.0.0.1:1/", "--plan", "x.json",
                            "--out", self.temp.name, "--handoff"], env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("never handed to the user", r.stderr)
        sid = self.slots("register", "--kind", "ego_space", "--space-id", "62", "--name", "测试线 截图")["slot"]
        env = dict(self.env, PATH="")
        r = subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), "ego-finish", "--space-id", "62", "70"],
                           env=env, capture_output=True, text=True, encoding="utf-8")
        out = json.loads(r.stdout)
        self.assertEqual(r.returncode, 2)                  # no ego-browser here: the finish code is handed back
        self.assertEqual([x["space_id"] for x in out["finished"]], [62, 70])
        self.assertNotIn("taskSpace(70)", json.dumps(out))
        self.assertIn(sid, {d["id"] for d in self.slots("list")})
        r = subprocess.run([sys.executable, "-B", str(self.here / "browser_slots.py"), "ego-list"], env=env,
                           capture_output=True, text=True, encoding="utf-8")
        self.assertIn("listTaskSpaces", json.loads(r.stdout)["ego_browser_nodejs"])

    def test_snapshot_is_private_copy(self):
        web = Path(self.temp.name) / "web-mobile"; web.mkdir()
        (web / "index.html").write_text("v1", encoding="utf-8")
        snap = Path(self.slots("snapshot", "--from", str(web))["snapshot"])
        (web / "index.html").write_text("v2 (a build is running)", encoding="utf-8")
        self.assertEqual((snap / "index.html").read_text(encoding="utf-8"), "v1")

    def test_cleanup_lists_without_closing(self):
        r = subprocess.run([sys.executable, "-B", str(self.here / "cleanup_machine.py")], env=self.env,
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0)
        self.assertIn("not closed", json.loads(r.stdout)["closed"])

    @unittest.skipIf(os.name == "nt", "orphan reparenting is checked on macOS/Linux")
    def test_cleanup_keeps_running_tests_and_closes_orphans(self):
        import time
        fake = Path(self.temp.name) / "chrome_touch.py"
        fake.write_text("import time\ntime.sleep(60)\n")
        working = subprocess.Popen([sys.executable, str(fake), "--working"])     # parent (this test) is alive
        self.addCleanup(working.kill)
        subprocess.run(["sh", "-c", f'"{sys.executable}" "{fake}" --orphan >/dev/null 2>&1 &'])   # parent exits at once
        time.sleep(1)
        out = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout
        orphan = [int(l.split()[0]) for l in out.splitlines() if "--orphan" in l and str(fake) in l]
        self.assertTrue(orphan)
        r = subprocess.run([sys.executable, "-B", str(self.here / "cleanup_machine.py"), "--close"], env=self.env,
                           capture_output=True, text=True, encoding="utf-8")
        report = json.loads(r.stdout)
        time.sleep(0.5)
        self.assertIsNone(working.poll())                 # still working: not closed
        self.assertNotIn(orphan[0], report["closed"])
        self.assertTrue(report["legacy_candidates_require_current_review"])
        # Clean only the exact ephemeral helper this test created, after current command recheck.
        check = subprocess.run(["ps", "-p", str(orphan[0]), "-o", "command="], capture_output=True, text=True).stdout
        if str(fake) in check and "--orphan" in check:
            import signal
            os.kill(orphan[0], signal.SIGTERM)
        self.assertIn(working.pid, [x["pid"] for x in report["still_working_not_touched"]])



class LogicCheckTests(unittest.TestCase):
    """逻辑检查（remake-test，用户 2026-10-23）：两份真实报告里的逻辑问题要在玩法做完时查出来。"""
    BAD = """import { PhysicsSystem2D, Node } from 'cc';
export class Game {
  canSound = true;
  start() {
    this.node.on(Node.EventType.TOUCH_MOVE, this.onMove, this);
    this.node.on(Node.EventType.TOUCH_END, this.onUp, this);
    this.node.on(Node.EventType.TOUCH_CANCEL, this.onUp, this);
    assetManager.loadBundle('levels', (err, b) => {
      if (err) { console.error(err); }
      this.ready(b);
    });
    localStorage.setItem('maxLevel', '3');
  }
  pause() { this.paused = true; }
  shuffle() { while (true) { if (this.ok()) break; } }
  dailyChallenge() { this.load(5); }
}
"""
    GOOD = """import { PhysicsSystem2D, Node, game, Game as G } from 'cc';
export class Game {
  round = 0;
  start() {
    this.node.on(Node.EventType.TOUCH_MOVE, this.onMove, this);
    this.node.on(Node.EventType.TOUCH_END, this.onUp, this);
    this.node.on(Node.EventType.TOUCH_CANCEL, this.onCancel, this);
    game.on(G.EVENT_HIDE, () => this.pause());
    const lv = Number(localStorage.getItem('maxLevel') || 1);
    try { localStorage.setItem('maxLevel', String(lv)); } catch (e) { this.showSaveError(); }
  }
  pause() { PhysicsSystem2D.instance.enabled = false; this.unscheduleAllCallbacks(); }
  shuffle() { for (let i = 0; i < 50; i++) { if (this.ok()) return; } this.fallback(); }
}
"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self.tmp.name) / "game"
        (self.proj / "assets" / "scripts").mkdir(parents=True)
        (self.proj / "assets" / "resources" / "levels").mkdir(parents=True)
        self.tool = str(Path(__file__).with_name("logic_check.py"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        r = subprocess.run([sys.executable, "-B", self.tool, "--project", str(self.proj), *args], capture_output=True, text=True)
        data = json.loads((self.proj / "docs" / "logic" / "logic-check.json").read_text(encoding="utf-8")) \
            if (self.proj / "docs" / "logic" / "logic-check.json").exists() and "--init" not in args else None
        return r, data

    def write(self, code, levels='{"levels":[{"a":1},{"a":2}]}'):
        (self.proj / "assets" / "scripts" / "Game.ts").write_text(code, encoding="utf-8")
        (self.proj / "assets" / "resources" / "levels" / "level_pack.json").write_text(levels, encoding="utf-8")

    def walk_all(self):
        ev = self.proj / "docs" / "logic" / "shots"
        ev.mkdir(parents=True, exist_ok=True)
        (ev / "f.png").write_bytes(b"x")
        flows = json.loads((self.proj / "docs" / "logic" / "flows.json").read_text(encoding="utf-8"))
        for f in flows["flows"]:
            f["status"], f["evidence"] = "pass", "docs/logic/shots/f.png"
        flows["flows"][13].update(status="n/a", evidence="", note="no shop in this game")
        # Synthetic unit fixture: real-game observations must never be generated from this.
        import logic_regressions as regressions
        import hashlib
        flows["regression_binding"] = {"source_sha256": regressions.source_digest(self.proj)}
        for row, spec in zip(flows["regressions"], regressions.CASES):
            row.update(status="pass", layer=spec[3][0],
                       observations={key: "Synthetic validator fixture observation for " + key for key in spec[4]},
                       evidence=[{"path": "docs/logic/shots/f.png", "sha256": hashlib.sha256(b"x").hexdigest()}])

        for row in flows['regressions']:
            if row['id'] == 'R07':
                row.update(drag_applicable=False, drag_absence_reason='Synthetic constant-only fixture has no drag mechanism')
            if row['id'] == 'R09':
                row['audio_channels'] = ['music', 'sfx']
                row['audio_samples'] = [dict(viewport=view, channel=channel, mode=mode,
                    signal_id='synthetic fixed segment ' + channel, trusted_touch=True,
                    rms_samples=[{'zero':0., 'mid':.05, 'full':.1, 'off':0., 'on':.1}[mode]] * 3)
                    for view in ([390,844], [375,667]) for channel in ('music','sfx')
                    for mode in ('zero','mid','full','off','on')]

        from test_button_state_check import save_fixture_report
        button_dir=self.proj
        button_ref=save_fixture_report(button_dir)
        flows['regressions'][5]['button_check']={'path':str((button_dir/button_ref['path']).resolve()),'sha256':button_ref['sha256']}
        (self.proj / "docs" / "logic" / "flows.json").write_text(json.dumps(flows), encoding="utf-8")

    def test_report_problems_are_found(self):
        self.write(self.BAD, '{"levels":[{"a":1},null,{"a":2}]}')
        r, data = self.run_tool()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        rules = {(f["rule"], f["severity"]) for f in data["findings"]}
        for rule in ("L-INPUT-CANCEL", "L-LOOP", "L-LOAD", "L-SAVE", "L-MODE", "L-PAUSE", "L-CONFIG"):
            self.assertIn((rule, "fail"), rules, rule)
        saves = " ".join(f["message"] for f in data["findings"] if f["rule"] == "L-SAVE")
        self.assertIn("maxLevel", saves)
        self.assertIn("canSound", saves)
        self.assertEqual(data["flow_problems"], 20)

    def test_triage_needs_a_reason_and_flows_need_evidence(self):
        self.write(self.BAD.replace("canSound = true;", ""))
        self.run_tool("--init")
        r, data = self.run_tool()
        items = [{"rule": f["rule"], "file": f["file"], "verdict": "by_design", "why": ""}
                 for f in data["findings"] if f["severity"] == "fail"]
        (self.proj / "docs" / "logic" / "triage.json").write_text(json.dumps({"items": items}), encoding="utf-8")
        r, data = self.run_tool()
        self.assertGreater(data["open_findings"], 0, "a verdict without why must not count")
        for t in items:
            t["why"] = "fixture: judged after reading the source"
        (self.proj / "docs" / "logic" / "triage.json").write_text(json.dumps({"items": items}), encoding="utf-8")
        r, data = self.run_tool()
        self.assertEqual(data["open_findings"], 0)
        self.assertEqual(r.returncode, 1, "untested flows still block")
        flows = json.loads((self.proj / "docs" / "logic" / "flows.json").read_text(encoding="utf-8"))
        for f in flows["flows"]:
            f["status"], f["evidence"] = "pass", "docs/logic/missing.png"
        (self.proj / "docs" / "logic" / "flows.json").write_text(json.dumps(flows), encoding="utf-8")
        r, data = self.run_tool()
        self.assertEqual(r.returncode, 1, "pass without an evidence file is not a pass")
        self.walk_all()
        r, data = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(data["tool"], "logic_check")
        self.assertTrue(data["passed"])

    def test_good_code_passes_after_real_flows(self):
        self.write(self.GOOD)
        self.run_tool("--init")
        r, data = self.run_tool()
        self.assertEqual([f for f in data["findings"] if f["severity"] == "fail"], [])
        self.walk_all()
        r, data = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_review_mode_only_reports(self):
        self.write(self.BAD)
        r, data = self.run_tool("--mode", "review")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(data["status"], "review")
        self.assertGreater(data["open_findings"], 5)
        self.assertIn("只列出", (self.proj / "docs" / "logic" / "logic-check.md").read_text(encoding="utf-8"))
        self.assertIn("Game {", (self.proj / "assets" / "scripts" / "Game.ts").read_text(encoding="utf-8"))


class TikTokZipTests(unittest.TestCase):
    """User 2026-10-23 (SquareRush UPLOADFIX): every package is the one uploadable TikTok platform package. The old package
    kept assets/resources in the main package (8,754,975 > 4,000,000 bytes) and was rejected by the platform."""
    HERE = Path(__file__).resolve().parent

    def native(self, main_extra=0, sub=True, independent=False, app="ttapp123"):
        t = Path(tempfile.mkdtemp(prefix="tiktok zip "))
        self.addCleanup(__import__("shutil").rmtree, t, True)
        n = t / "native"
        (n / "src").mkdir(parents=True)
        (n / "game.js").write_text("require('./src/settings.js');", encoding="utf-8")
        (n / "project.config.json").write_text(json.dumps({"appid": app}), encoding="utf-8")
        (n / "src/settings.js").write_text("window._CCSettings={subpackages:{resources:{}}};", encoding="utf-8")
        (n / "big-main.bin").write_bytes(os.urandom(64) * (main_extra // 64)) if main_extra else None
        res = (n / "subpackages/resources") if sub else (n / "assets/resources")
        res.mkdir(parents=True)
        (res / "game.js").write_text("// resources entry\n", encoding="utf-8")
        # v7.5 G1_growth_apis: the five TikTok growth calls must be in game JS; v7.7 G1k: a new game makes them only
        # through the kit TikTokMissionService / MissionFlow modules (2.4 bundle form, as Creator writes index.js)
        kit = self.HERE.parent / "assets/platform-kit/assets/tiktok-platform"
        (res / "index.js").write_text("".join(
            "cc._RF.push(module, 'u%d', '%s');\n%s\ncc._RF.pop();\n" % (i, m, (kit / (m + ".js")).read_text(encoding="utf-8"))
            for i, m in enumerate(("TikTokMissionService", "MissionFlow"))), encoding="utf-8")
        (res / "config.json").write_text("{}", encoding="utf-8")
        (res / "art.bin").write_bytes(b"a" * 5_000_000)            # big art: fine in a normal subpackage, never in main
        game = {"deviceOrientation": "portrait"}
        if sub:
            game["subpackages"] = [dict({"name": "resources", "root": "subpackages/resources/"},
                                        **({"independent": True} if independent else {}))]
        (n / "game.json").write_text(json.dumps(game), encoding="utf-8")
        return t, n

    def make(self, native, out, *extra, app="ttapp123"):
        p = subprocess.run([sys.executable, str(self.HERE / "make_tiktok_zip.py"), "--native", str(native), "--app-id", app,
                            "--out", str(out), *extra], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def test_valid_native_structure_still_requires_the_known_issue_gate(self):
        from make_tiktok_zip import native_problems
        t, n = self.native()
        problems, sizes, info = native_problems(n)
        self.assertFalse(problems, problems)
        self.assertLessEqual(info['main'], 4_000_000)
        out = t / 'out.zip'
        code, text = self.make(n, out)
        self.assertEqual(code, 2, text)
        self.assertIn('--review', text)
        self.assertFalse(out.exists())

    def test_resources_left_in_main_fail_structure_and_no_zip_is_written(self):
        from make_tiktok_zip import native_problems
        t, n = self.native(sub=False)
        problems, _, _ = native_problems(n)
        self.assertIn('main package', ' '.join(problems))
        code, text = self.make(n, t / 'out.zip')
        self.assertNotEqual(code, 0)
        self.assertFalse((t / 'out.zip').exists())

    def test_structural_rejections_remain_independent_of_writer_gate(self):
        from make_tiktok_zip import native_problems
        t, n = self.native()
        def rejected(path, expected):
            self.assertIn(expected.lower(), ' '.join(native_problems(path)[0]).lower())
        rejected(n.parent, 'outer folder')
        web = n.parent / 'web'; web.mkdir(); (web / 'index.html').write_text('<html>')
        rejected(web, 'web build')
        (n / 'inner.zip').write_bytes(b'PK'); rejected(n, 'zip-in-zip'); (n / 'inner.zip').unlink()
        (n / 'Main.ts').write_text('x'); rejected(n, 'source-project'); (n / 'Main.ts').unlink()
        (n / 'src/settings.js').write_text("var j='__QA_LEVEL_JUMP__';")
        rejected(n, 'level jump')
        t2, n2 = self.native(independent=True); rejected(n2, 'independent subpackage')

    def test_verifier_has_the_limits_built_in(self):
        import zipfile
        import verify_native_zip as vnz
        t = Path(tempfile.mkdtemp(prefix="vz "))
        self.addCleanup(__import__("shutil").rmtree, t, True)
        def z(name, files):
            p = t / name
            with zipfile.ZipFile(p, "w") as zz:
                for k, v in files.items():
                    zz.writestr(k, v)
            return p
        base = {"game.js": "x", "game.json": "{}", "project.config.json": json.dumps({"appid": "a"})}
        self.assertEqual(vnz.verify(z("ok.zip", base))["limits"]["main"], 4_000_000)
        with self.assertRaisesRegex(ValueError, "main package"):
            vnz.verify(z("big.zip", dict(base, **{"assets/resources/a.bin": b"0" * 4_100_000})))
        with self.assertRaisesRegex(ValueError, "Outer folder"):
            vnz.verify(z("outer.zip", {"Game/" + k: v for k, v in base.items()}))
        with self.assertRaisesRegex(ValueError, "Web build"):
            vnz.verify(z("web.zip", {"index.html": "<html>", "main.js": "x"}))
        with self.assertRaisesRegex(ValueError, "junk"):
            vnz.verify(z("mac.zip", dict(base, **{"__MACOSX/._game.js": "x"})))
        with self.assertRaisesRegex(ValueError, "limit 4000000"):
            vnz.verify(z("big2.zip", dict(base, **{"a.bin": b"0" * 4_100_000})), max_main=9_000_000)   # cannot be raised


if __name__ == "__main__":
    unittest.main(verbosity=2)
