"""Fingerprint declared check inputs and select rechecks; never issue acceptance passes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def file_hash(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def inspect_paths(project, declared, allow_external=False):
    if not isinstance(declared, list) or any(not isinstance(p, str) or not p for p in declared):
        raise ValueError("Paths must be a list of nonempty strings")
    files, missing, declared_paths = {}, [], []
    for name in declared:
        source = Path(name)
        source = source if source.is_absolute() else project / source
        resolved = source.resolve()
        if not allow_external and not resolved.is_relative_to(project):
            raise ValueError("Input escapes project: " + name)
        if source.is_symlink():
            raise ValueError("Declare concrete paths, not symlinks: " + name)
        declared_paths.append({"path": str(resolved), "directory": source.is_dir()})
        if not source.exists():
            missing.append(name)
            continue
        paths = sorted(source.rglob("*")) if source.is_dir() else [source]
        found = False
        for path in paths:
            if path.is_symlink():
                raise ValueError("Symlink input: " + str(path))
            if not path.is_file():
                continue
            real = path.resolve()
            if not allow_external and not real.is_relative_to(project):
                raise ValueError("Input escapes project: " + str(path))
            key = real.relative_to(project).as_posix() if real.is_relative_to(project) else str(real)
            files[key] = file_hash(real)
            found = True
        if not found:
            missing.append(name + " (empty directory)")
    return {"files": dict(sorted(files.items())), "missing": sorted(missing),
            "declared_paths": sorted(declared_paths, key=lambda row: row["path"])}


def capture(project, definition):
    project = Path(project).resolve(strict=True)
    if not project.is_dir():
        raise ValueError("Project must be a directory")
    if definition.get("schema_version") != 1 or not isinstance(definition.get("checks"), list) or not definition["checks"]:
        raise ValueError("Expected schema_version=1 and nonempty checks")
    checks = {}
    for item in definition["checks"]:
        check_id = item.get("id")
        if not isinstance(check_id, str) or not check_id or check_id in checks:
            raise ValueError("Check IDs must be nonempty and unique")
        if not item.get("scope") or not isinstance(item.get("context"), dict) or not item["context"]:
            raise ValueError("Every check needs scope and nonempty context: " + check_id)
        if not item.get("dependencies"):
            raise ValueError("Dependencies must be explicit: " + check_id)
        payload = {
            "scope": item["scope"], "context": item["context"],
            "dependencies": inspect_paths(project, item["dependencies"]),
            "tools": inspect_paths(project, item.get("tool_files", []), allow_external=True),
        }
        evidence = inspect_paths(project, item.get("evidence", []))
        checks[check_id] = {
            **payload, "fingerprint": digest(payload), "evidence": evidence,
            "complete_inputs": not payload["dependencies"]["missing"] and not payload["tools"]["missing"],
        }
    return {"schema_version": 1, "project": str(project), "checks": checks,
            "is_acceptance_result": False}


def validate_snapshot(value):
    if value.get("schema_version") != 1 or not value.get("project") or not isinstance(value.get("checks"), dict):
        raise ValueError("Invalid snapshot")
    for check_id, row in value["checks"].items():
        payload = {key: row[key] for key in ("scope", "context", "dependencies", "tools")}
        if row.get("fingerprint") != digest(payload):
            raise ValueError("Snapshot fingerprint mismatch: " + check_id)
        complete = not row["dependencies"]["missing"] and not row["tools"]["missing"]
        if row.get("complete_inputs") is not complete:
            raise ValueError("Snapshot completeness mismatch: " + check_id)


def protect_output(output, snapshots):
    destination = output.resolve()
    for value in snapshots:
        for row in value["checks"].values():
            for section in ("dependencies", "tools", "evidence"):
                for item in row[section].get("declared_paths", []):
                    source = Path(item["path"]).resolve()
                    if destination == source or destination.is_relative_to(source):
                        raise ValueError("Output overlaps declared inputs/evidence: " + str(output))


def compare(before, after):
    validate_snapshot(before)
    validate_snapshot(after)
    selected = {"needs_run": [], "review_existing_evidence": [], "cannot_reuse": [], "removed_checks": []}
    reasons = {}
    for check_id, row in after["checks"].items():
        old = before["checks"].get(check_id)
        if not row["complete_inputs"]:
            group, reason = "cannot_reuse", "missing declared inputs or tools"
        elif old is None:
            group, reason = "needs_run", "new check"
        elif before["project"] != after["project"]:
            group, reason = "needs_run", "project location changed; review environment"
        elif old["fingerprint"] != row["fingerprint"] or not old["complete_inputs"]:
            group, reason = "needs_run", "dependencies, tools, scope or context changed"
        elif not row["evidence"]["files"] or row["evidence"]["missing"] or row["evidence"] != old["evidence"]:
            group, reason = "cannot_reuse", "evidence missing, unbound or changed"
        else:
            group, reason = "review_existing_evidence", "same declared inputs and evidence; prior pass and coverage still require review"
        selected[group].append(check_id)
        reasons[check_id] = reason
    selected["removed_checks"] = sorted(set(before["checks"]) - set(after["checks"]))
    return {"schema_version": 1, **selected, "reasons": reasons, "is_acceptance_result": False,
            "limitation": "Declared dependency coverage and actual prior result must be reviewed; unchanged fingerprints never create a pass."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--project", type=Path, required=True)
    snap.add_argument("--checks", type=Path, required=True)
    snap.add_argument("--out", type=Path, required=True)
    diff = sub.add_parser("compare")
    diff.add_argument("--before", type=Path, required=True)
    diff.add_argument("--after", type=Path, required=True)
    diff.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    inputs = [args.checks] if args.command == "snapshot" else [args.before, args.after]
    if args.out.resolve() in [p.resolve() for p in inputs]:
        parser.error("Output must not overwrite an input")
    try:
        if args.out.exists() or args.out.is_symlink():
            raise ValueError("Output already exists; choose a new JSON path")
        if args.command == "snapshot":
            result = capture(args.project, read_json(args.checks))
            protect_output(args.out, [result])
            counts = {"checks": len(result["checks"]), "incomplete": sum(not r["complete_inputs"] for r in result["checks"].values())}
        else:
            before, after = read_json(args.before), read_json(args.after)
            result = compare(before, after)
            protect_output(args.out, [before, after])
            counts = {k: len(result[k]) for k in ("needs_run", "review_existing_evidence", "cannot_reuse", "removed_checks")}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({"out": str(args.out), "counts": counts, "is_acceptance_result": False}, ensure_ascii=False))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"error": str(exc), "is_acceptance_result": False}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
