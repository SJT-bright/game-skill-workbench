"""Summarize explicit Codex session roots and descendants without exporting chat text."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include timezone")
    return parsed


def records(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                if line.endswith("\n"):
                    raise
                break  # A concurrently written final line is incomplete.


def percentile(values, q):
    return sorted(values)[round((len(values) - 1) * q)] if values else None


def numeric_counts(value):
    return (isinstance(value, dict) and all(k in value for k in ("input_tokens", "output_tokens", "total_tokens"))
            and all(type(value.get(k, 0)) is int for k in FIELDS))


def valid_counts(value):
    return (numeric_counts(value) and all(value.get(k, 0) >= 0 for k in FIELDS)
            and value.get("cached_input_tokens", 0) <= value.get("input_tokens", 0)
            and value.get("reasoning_output_tokens", 0) <= value.get("output_tokens", 0)
            and value.get("input_tokens", 0) + value.get("output_tokens", 0) == value.get("total_tokens", 0))


def analyze(path, meta, until, since=None):
    result = {"id": meta["id"], "path": str(path), "totals": {k: 0 for k in FIELDS},
              "recorded_calls": 0, "duplicate_token_events": 0, "usage_mismatches": 0,
              "counter_resets": 0, "invalid_usage_events": 0, "ignored_duplicate_payload_anomalies": 0,
              "wait_tool_calls": 0, "tool_calls": 0}
    created, previous, samples = instant(meta["timestamp"]), None, []
    for entry in records(path):
        if not entry.get("timestamp"):
            continue
        stamp = instant(entry["timestamp"])
        if stamp < created or stamp > until:
            continue
        payload = entry.get("payload", {})
        included = since is None or stamp >= since
        if entry.get("type") == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if not info:
                continue
            total, last = info.get("total_token_usage", {}), info.get("last_token_usage", {})
            if previous is not None and previous == total:
                result["duplicate_token_events"] += int(included)
                result["ignored_duplicate_payload_anomalies"] += int(included and not valid_counts(last))
                continue  # An unchanged counter is not another model response or usage increment.
            if not numeric_counts(total) or not numeric_counts(last):
                result["invalid_usage_events"] += 1
                previous = None
                continue
            malformed = not valid_counts(total) or not valid_counts(last)
            reset = previous is not None and total.get("total_tokens", 0) < previous.get("total_tokens", 0)
            if reset:
                previous = None
                result["counter_resets"] += int(included)
            delta = {key: total.get(key, 0) - (previous or {}).get(key, 0) for key in FIELDS}
            result["invalid_usage_events"] += int(malformed or not valid_counts(delta))
            if included:
                result["usage_mismatches"] += int(any(delta[k] != last.get(k, 0) for k in FIELDS))
                for key in FIELDS:
                    result["totals"][key] += delta[key]
                result["recorded_calls"] += 1
                samples.append(last.get("input_tokens", 0))
            previous = total  # Keep the pre-since baseline; never charge inherited counters again.
        elif included and entry.get("type") == "response_item" and payload.get("type") in ("function_call", "custom_tool_call"):
            name = payload.get("name", "")
            args = payload.get("arguments", payload.get("input", ""))
            args = args if isinstance(args, str) else json.dumps(args)
            result["tool_calls"] += 1
            if re.search(r"wait|sleep|write_stdin", name, re.I) or re.search(r"tools\.(?:wait|write_stdin)\s*\(", args):
                result["wait_tool_calls"] += 1
    result["input_samples"] = samples
    return result


def summarize(rows):
    totals = {key: sum(row["totals"][key] for row in rows) for key in FIELDS}
    calls = sum(row["recorded_calls"] for row in rows)
    samples = [value for row in rows for value in row["input_samples"]]
    totals.update({"sessions": len(rows), "recorded_calls": calls,
                   "uncached_input_tokens": totals["input_tokens"] - totals["cached_input_tokens"],
                   "avg_input": round(totals["input_tokens"] / calls) if calls else 0,
                   "input_p90": percentile(samples, .9), "input_max": max(samples, default=0),
                   "tool_calls": sum(row["tool_calls"] for row in rows),
                   "wait_tool_calls": sum(row["wait_tool_calls"] for row in rows),
                   "ignored_duplicate_payload_anomalies": sum(row["ignored_duplicate_payload_anomalies"] for row in rows)})
    return totals


def run(log_dirs, workspace, roots, until, since=None):
    workspace = Path(workspace).resolve()
    scoped = {}
    files = sorted({p.resolve() for folder in log_dirs for p in folder.rglob("*.jsonl")})
    for path in files:
        first = next(records(path), {})
        if first.get("type") != "session_meta":
            continue
        meta = first["payload"]  # Later session_meta entries can be inherited parent history.
        if not meta.get("cwd"):
            continue
        cwd = Path(meta.get("cwd", "").removeprefix("\\\\?\\")).resolve()
        if not cwd.is_relative_to(workspace) or instant(meta["timestamp"]) > until:
            continue
        if meta["id"] in scoped:
            raise ValueError("Duplicate session ID; choose one log copy: " + meta["id"])
        scoped[meta["id"]] = (path, meta)
    missing = set(roots) - set(scoped)
    if missing:
        raise ValueError("Explicit roots not found in supplied log directories/workspace: " + ", ".join(sorted(missing)))

    def root_of(session_id):
        seen = set()
        while session_id in scoped and session_id not in seen:
            if session_id in roots:
                return session_id
            seen.add(session_id)
            meta = scoped[session_id][1]
            source = meta.get("source", {})
            spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
            session_id = spawn.get("parent_thread_id") or meta.get("forked_from_id")
        return None

    for root in roots:
        meta = scoped[root][1]
        source = meta.get("source", {})
        spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
        ancestor = spawn.get("parent_thread_id") or meta.get("forked_from_id")
        if ancestor and root_of(ancestor):
            raise ValueError("Explicit roots overlap; supply only the highest selected root: " + root)
    rows = []
    for session_id, (path, meta) in scoped.items():
        root = root_of(session_id)
        if root:
            row = analyze(path, meta, until, since)
            row["root_id"] = root
            rows.append(row)
    checks = {
        "valid_per_event_usage": all(not r["invalid_usage_events"] for r in rows),
        "no_counter_resets": all(not r["counter_resets"] for r in rows),
        "cumulative_deltas_equal_last_usage": all(not r["usage_mismatches"] for r in rows),
        "token_arithmetic": all(r["totals"]["input_tokens"] + r["totals"]["output_tokens"] == r["totals"]["total_tokens"] for r in rows),
        "cache_is_subset_of_input": all(0 <= r["totals"]["cached_input_tokens"] <= r["totals"]["input_tokens"] for r in rows),
        "reasoning_is_subset_of_output": all(0 <= r["totals"]["reasoning_output_tokens"] <= r["totals"]["output_tokens"] for r in rows),
    }
    groups = {root: summarize([r for r in rows if r["root_id"] == root]) for root in roots}
    overall = summarize(rows)
    for row in rows:
        samples = row.pop("input_samples")
        row["input_p90"] = percentile(samples, .9)
    return {"schema_version": 1, "workspace": str(workspace), "since": since.isoformat() if since else None,
            "until": until.isoformat(), "overall": overall, "groups": groups,
            "consistency_checks": checks, "reliable_counters": all(checks.values()), "sessions": rows,
            "limits": "Only supplied log directories/roots and discovered descendants within workspace. Missing child logs are unknown; an incomplete trailing line is excluded. Calls are unique increasing usage snapshots; unchanged counters are ignored, with malformed duplicate payloads counted separately. Cache is part of input, reasoning is part of output. Wait counts include legitimate waits. Event timestamps define the window; since may include a response that started earlier. No billed-request count, fees, quota conversion, image-generation cost or claimed savings."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", action="append", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--root-id", action="append", required=True)
    parser.add_argument("--since")
    parser.add_argument("--until", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        until, since = instant(args.until), instant(args.since) if args.since else None
        if since and since > until:
            raise ValueError("since must not be later than until")
        if len(set(args.root_id)) != len(args.root_id):
            raise ValueError("Root IDs must be unique")
        if any(not folder.is_dir() for folder in args.log_dir):
            raise ValueError("Every --log-dir must exist")
        if args.out.suffix.lower() == ".jsonl":
            raise ValueError("Output cannot overwrite a JSONL log")
        if args.out.exists() or args.out.is_symlink():
            raise ValueError("Output already exists; choose a new JSON path")
        result = run(args.log_dir, args.workspace, args.root_id, until, since)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({"out": str(args.out), "overall": result["overall"],
                          "reliable_counters": result["reliable_counters"]}, ensure_ascii=False))
        return 0 if result["reliable_counters"] else 2
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
