#!/usr/bin/env python3
"""Read local host/tool availability without starting apps, logging in or installing anything."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def platform_policy(system):
    if system == "Windows":
        return {"supported_host": True, "python_command": "py -3", "venv_python": "Scripts/python.exe",
                "grok_binary": "grok.exe", "process_group": "CREATE_NEW_PROCESS_GROUP; stop only runner-owned PID tree",
                "shell_family": "PowerShell"}
    if system == "Darwin":
        return {"supported_host": True, "python_command": "python3", "venv_python": "bin/python",
                "grok_binary": "grok", "process_group": "start_new_session; stop only runner-owned POSIX process group",
                "shell_family": "POSIX shell"}
    return {"supported_host": False, "reason": "Host outside this Windows/macOS adaptation scope"}


def existing_binary(names, candidates=()):
    for name in names:
        found = shutil.which(name)
        if found:
            return str(Path(found).resolve())
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return str(path.resolve())
    return None


def probe():
    system = platform.system()
    policy = platform_policy(system)
    home = Path.home()
    chrome_candidates = []
    if system == "Windows":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            if os.environ.get(variable):
                chrome_candidates.append(Path(os.environ[variable]) / "Google/Chrome/Application/chrome.exe")
    elif system == "Darwin":
        chrome_candidates = [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                             home / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    tools = {
        "node": existing_binary(["node"]),
        "ego_browser": existing_binary(["ego-browser"]),
        "grok": existing_binary(["grok"], [home / ".grok/bin" / policy["grok_binary"]]) if policy["supported_host"] else None,
        "chrome": existing_binary(["chrome", "google-chrome"], chrome_candidates),
    }
    return {"schema": "gameskills.host.v1", "system": system, "policy": policy,
            "skill_root": str(Path(__file__).resolve().parents[2]),
            "python": {"executable": sys.executable, "version": platform.python_version()},
            "tools": {name: {"found": bool(path), "path": path} for name, path in tools.items()},
            "read_only_probe": True, "apps_started": False,
            "limits": "PATH/file existence is not runtime, authentication, browser touch or device acceptance. No credential files read. Existing user/project executor choice remains authoritative; do not silently change tools."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="Optional new JSON report; existing files are never overwritten")
    args = parser.parse_args()
    result = probe()
    try:
        if args.out:
            if args.out.exists() or args.out.is_symlink():
                raise ValueError("Output already exists; choose a new report path")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
            print(json.dumps({"out": str(args.out), "system": result["system"],
                              "supported_host": result["policy"]["supported_host"], "read_only_probe": True}, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["policy"]["supported_host"] else 2
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
