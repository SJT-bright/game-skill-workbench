#!/usr/bin/env python3
"""Run explicitly delegated local Grok tasks without a GUI or PTY."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

DEFAULT_MODEL = "grok-4.7-build-fast"
STOP_REQUESTED = False


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def absolute_path(value, label):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError(label + " must be an absolute path")
    return Path(value).resolve()


def inside(path, scope):
    return path == scope or scope in path.parents


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def load_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object")
    for key, default in (("max_parallel", 3), ("timeout_seconds", 1800), ("max_turns", 30)):
        data.setdefault(key, default)
        if type(data[key]) is not int or data[key] <= 0:
            raise ValueError(key + " must be a positive integer")
    data.setdefault("model", DEFAULT_MODEL)
    if not isinstance(data["model"], str) or not re.fullmatch(r"[a-zA-Z0-9._-]+", data["model"]):
        raise ValueError("invalid model ID")
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("jobs must be a nonempty list")
    ids, owners = set(), []
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("each job must be an object")
        name = job.get("id")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) or name in ids:
            raise ValueError("job IDs must be unique lowercase names")
        ids.add(name)
        for field in ("cwd", "prompt_file"):
            job[field] = str(absolute_path(job.get(field), name + "." + field))
        if not Path(job["cwd"]).is_dir():
            raise ValueError(name + ": cwd is not a directory")
        if not Path(job["prompt_file"]).read_text(encoding="utf-8").strip():
            raise ValueError(name + ": prompt is empty")
        for field in ("write_paths", "expected_files"):
            job.setdefault(field, [])
            if not isinstance(job[field], list):
                raise ValueError(name + ": " + field + " must be a list")
            job[field] = [str(absolute_path(p, name + "." + field)) for p in job[field]]
            if len(set(job[field])) != len(job[field]):
                raise ValueError(name + ": duplicate " + field)
        if bool(job["write_paths"]) != bool(job["expected_files"]):
            raise ValueError(name + ": provide both write_paths and expected_files, or leave both empty for result-only tasks")
        job.setdefault("enable_web", False)
        if type(job["enable_web"]) is not bool:
            raise ValueError(name + ": enable_web must be a boolean")
        for p in map(Path, job["expected_files"]):
            if not any(inside(p, Path(scope)) for scope in job["write_paths"]):
                raise ValueError(name + ": expected file is outside write_paths")
        for scope in map(Path, job["write_paths"]):
            for other, owner in owners:
                if owner != name and (inside(scope, other) or inside(other, scope)):
                    raise ValueError("overlapping writes: " + owner + " / " + name)
            owners.append((scope, name))
    return data


def grok_env():
    env = os.environ.copy()
    # Preserve the existing account; do not silently fall back to API credits.
    env.pop("XAI_API_KEY", None)
    env["GROK_AGENT_DASHBOARD"] = "0"
    env["GROK_DISABLE_AUTOUPDATER"] = "1"
    return env


def preflight(cli, model):
    help_run = subprocess.run([cli, "--help"], capture_output=True, text=True, encoding='utf-8', timeout=20)
    required = ("--cwd", "--prompt-file", "--session-id", "--model", "--max-turns",
                "--output-format", "--permission-mode", "--allow", "--deny",
                "--disable-web-search", "--no-subagents", "--no-plan", "--verbatim")
    if help_run.returncode or any(flag not in help_run.stdout for flag in required):
        raise ValueError("Grok CLI flags changed; inspect --help before running")
    models = subprocess.run([cli, "models"], capture_output=True, text=True, encoding='utf-8',
                            env=grok_env(), timeout=30)
    output = models.stdout + models.stderr
    if models.returncode or "You are logged in with grok.com." not in output:
        raise ValueError("existing grok.com login unavailable; no automatic login or API fallback")
    available = re.findall(r"^\s*[-*]\s+([a-zA-Z0-9._-]+)(?:\s|$)", output, re.M)
    if model not in available:
        raise ValueError("requested model is unavailable: " + model)


def command(cli, job, config, request, session_id):
    cmd = [cli, "--cwd", job["cwd"], "--prompt-file", str(request), "--verbatim",
           "--session-id", session_id, "--model", config["model"],
           "--output-format", "json", "--max-turns", str(config["max_turns"]),
           "--permission-mode", "bypassPermissions", "--no-subagents", "--no-plan",
           "--deny", "MCPTool"]
    if not job["enable_web"]:
        cmd += ["--disable-web-search"]
    return cmd


def stop_group(proc):
    if os.name == "nt":
        # Scoped to this runner-owned PID; never kill applications by name.
        subprocess.run(["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        return
    # Only the group created by this runner; also clean surviving shell children.
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def finish(item, forced_status=None):
    proc, receipt, folder = item["proc"], item["receipt"], item["folder"]
    proc.wait()
    item["stdout"].close()
    item["stderr"].close()
    receipt.update(exit_code=proc.returncode, ended_at=now(),
                   duration_seconds=round(time.monotonic() - item["start"], 3))
    receipt["status"] = forced_status or "failed"
    try:
        raw = json.loads((folder / "raw.json").read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Grok output is not an object")
        for key in ("usage", "modelUsage", "num_turns", "stopReason", "requestId",
                    "usage_is_incomplete", "cost_is_partial", "total_cost_usd"):
            receipt[key] = raw.get(key)
        value = raw.get("text", raw.get("result", ""))
        (folder / "result.txt").write_text(value if isinstance(value, str) else
                                           json.dumps(value, ensure_ascii=False), encoding="utf-8")
        if not forced_status:
            if proc.returncode or raw.get("is_error") or raw.get("isError") or raw.get("type") == "error":
                raise ValueError("Grok failed; inspect raw.json and stderr.txt")
            if raw.get("stopReason") != "end_turn":
                raise ValueError("Grok did not end normally")
            if raw.get("sessionId") != receipt["session_id"]:
                raise ValueError("Grok returned a different session ID")
            model_usage = raw.get("modelUsage")
            if not isinstance(model_usage, dict) or receipt["requested_model"] not in model_usage:
                raise ValueError("requested model is not confirmed by modelUsage")
            if any(v is None for v in receipt["files_after"].values()):
                raise ValueError("expected output file is missing")
            if not item["job"]["expected_files"] and (not isinstance(value, str) or not value.strip()):
                raise ValueError("result-only task returned no text")
            receipt["status"] = "completed_pending_review"
    except (ValueError, OSError) as exc:
        receipt["error"] = str(exc)
    save_json(folder / "receipt.json", receipt)
    return receipt


def on_signal(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True


def run(config, cli, out):
    out.mkdir(parents=True, exist_ok=False)
    save_json(out / "manifest.json", config)
    summary = {"status": "running", "started_at": now(), "runner_pid": os.getpid(),
               "requested_model": config["model"], "max_parallel": config["max_parallel"],
               "jobs": {j["id"]: {"status": "queued"} for j in config["jobs"]}}
    queue, active = list(config["jobs"]), {}

    def update():
        save_json(out / "summary.json", summary)

    def complete(name, item, forced=None):
        stop_group(item["proc"])
        receipt = item["receipt"]
        receipt["files_after"] = {p: fingerprint(Path(p)) for p in item["job"]["expected_files"]}
        receipt["changed_files"] = [p for p, h in receipt["files_after"].items()
                                    if h != receipt["files_before"][p]]
        summary["jobs"][name] = finish(item, forced)
        print(json.dumps({"job": name, "status": summary["jobs"][name]["status"]}, ensure_ascii=False), flush=True)
        update()

    update()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, on_signal)
    try:
        while queue or active:
            if STOP_REQUESTED:
                break
            while queue and len(active) < config["max_parallel"] and not STOP_REQUESTED:
                job = queue.pop(0)
                folder = out / job["id"]
                folder.mkdir()
                request = folder / "request.txt"
                task = Path(job["prompt_file"]).read_text(encoding="utf-8")
                rules = ("用户明确指定你在本地后台完成下面的任务。按要求执行并给出所需结果，遵循项目规则；"
                         "旧的 Grok 自动委派白名单不限制此次明确指定的任务。仅修改声明路径，"
                         "写入路径为空时不主动修改原文件，返回用户需要的分析、文字或执行结果。"
                         "不得操作桌面或打开聊天/终端窗口，不增加任务外操作；"
                         "发布、外部发送、购买、安装或替换正式应用只在该具体任务已明确授权时执行。"
                         "不启动未要求的常驻服务、不启动模型子代理、不接触凭据。"
                         "完成后说明实际产物和验证结果。允许写入路径：" +
                         json.dumps(job["write_paths"], ensure_ascii=False) + "\n\n任务：\n")
                request.write_text(rules + task, encoding="utf-8")
                receipt = {"status": "starting", "session_id": str(uuid.uuid4()),
                           "requested_model": config["model"], "auth_route": "existing_grok_com_login",
                           "cwd": job["cwd"], "started_at": now(), "total_cost_usd": None,
                           "request_sha256": fingerprint(request),
                           "files_before": {p: fingerprint(Path(p)) for p in job["expected_files"]}}
                save_json(folder / "receipt.json", receipt)
                stdout = (folder / "raw.json").open("w", encoding="utf-8")
                stderr = (folder / "stderr.txt").open("w", encoding="utf-8")
                try:
                    proc = subprocess.Popen(command(cli, job, config, request, receipt["session_id"]),
                                            cwd=job["cwd"], stdin=subprocess.DEVNULL,
                                            stdout=stdout, stderr=stderr, env=grok_env(),
                                            start_new_session=(os.name != "nt"), creationflags=(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0))
                except Exception:
                    stdout.close()
                    stderr.close()
                    raise
                receipt.update(status="running", pid=proc.pid)
                save_json(folder / "receipt.json", receipt)
                active[job["id"]] = {"proc": proc, "receipt": receipt, "job": job,
                                     "folder": folder, "stdout": stdout, "stderr": stderr,
                                     "start": time.monotonic()}
                summary["jobs"][job["id"]] = dict(receipt)
                update()
                print(json.dumps({"job": job["id"], "status": "running", "pid": proc.pid,
                                  "session_id": receipt["session_id"]}), flush=True)
            for name, item in list(active.items()):
                if item["proc"].poll() is not None:
                    complete(name, item)
                    del active[name]
                elif time.monotonic() - item["start"] >= config["timeout_seconds"]:
                    complete(name, item, "timed_out")
                    del active[name]
            if queue or active:
                time.sleep(0.2)
    except Exception as exc:
        summary["error"] = str(exc)
    finally:
        for name, item in active.items():
            complete(name, item, "cancelled" if STOP_REQUESTED else "runner_failed")
        for receipt in summary["jobs"].values():
            if receipt["status"] in ("queued", "starting", "running"):
                receipt["status"] = "cancelled" if STOP_REQUESTED else "not_started"
        summary["status"] = ("cancelled" if STOP_REQUESTED else
                             "completed_pending_review" if all(j["status"] == "completed_pending_review"
                                                               for j in summary["jobs"].values()) else "failed")
        summary["ended_at"] = now()
        update()
    print(json.dumps({"status": summary["status"], "summary": str(out / "summary.json")}, ensure_ascii=False), flush=True)
    return 130 if STOP_REQUESTED else 0 if summary["status"] == "completed_pending_review" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        config = load_manifest(args.manifest)
        if args.dry_run:
            print(json.dumps({"status": "validated", "model": config["model"],
                              "jobs": [j["id"] for j in config["jobs"]],
                              "max_parallel": config["max_parallel"]}, ensure_ascii=False))
            return 0
        if not args.out_dir:
            parser.error("--out-dir is required unless --dry-run")
        cli = args.cli or (Path.home() / ".grok/bin" / ("grok.exe" if os.name == "nt" else "grok"))
        if not cli.is_file():
            cli = Path(shutil.which("grok") or str(cli))
        out = args.out_dir.resolve()
        if out.exists():
            raise ValueError("out-dir already exists; use a fresh receipt directory")
        if any(inside(out, Path(p)) or inside(Path(p), out)
               for job in config["jobs"] for p in job["write_paths"]):
            raise ValueError("receipt directory must not overlap job write_paths")
        preflight(str(cli), config["model"])
        return run(config, str(cli), out)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
