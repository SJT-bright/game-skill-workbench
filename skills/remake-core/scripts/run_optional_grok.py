#!/usr/bin/env python3
"""Optionally invoke the installed Grok runner; unavailable is a main-agent handoff, not a game failure."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def invoke(mode, manifest, out_dir, skills_dir=None, cli=None, dry_run=False):
    if mode == 'off':
        return {'status': 'skipped', 'reason': 'disabled', 'next': 'main_agent', 'model_called': False}
    skills_dir = Path(skills_dir) if skills_dir else Path(__file__).resolve().parents[2]
    runner = skills_dir / 'grok-background-maker/scripts/run_jobs.py'
    candidate = Path(cli).expanduser() if cli else Path(shutil.which('grok') or Path.home() / '.grok/bin/grok')
    if not runner.is_file() or not candidate.is_file() or not os.access(candidate, os.X_OK):
        return {'status': 'skipped', 'reason': 'optional_cli_or_runner_unavailable', 'next': 'main_agent', 'model_called': False}
    out_dir = Path(out_dir).expanduser().absolute()
    if out_dir.exists():
        return {'status': 'fallback_required', 'reason': 'receipt_directory_already_exists', 'next': 'main_agent', 'model_called': False}
    out_dir.mkdir(parents=True)
    config = json.loads(Path(manifest).expanduser().read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict):
        raise ValueError('manifest must be an object')
    config.setdefault('max_parallel', 1)
    config.setdefault('timeout_seconds', 120)
    config.setdefault('max_turns', 4)
    prepared = out_dir / 'bounded-manifest.json'
    prepared.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    command = [sys.executable, str(runner), '--manifest', str(prepared), '--cli', str(candidate)]
    command += ['--dry-run'] if dry_run else ['--out-dir', str(out_dir / 'grok-run')]
    try:
        # The underlying runner owns per-task timeout, signals and child-group cleanup.
        with (out_dir / 'runner.stdout.txt').open('w', encoding='utf-8') as stdout, (out_dir / 'runner.stderr.txt').open('w', encoding='utf-8') as stderr:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False)
        answer = {'status': ('validated_no_model_call' if dry_run else 'completed_pending_review') if result.returncode == 0 else 'fallback_required',
                  'runner_exit_code': result.returncode, 'receipt_dir': str(out_dir),
                  'next': 'main_agent_review' if result.returncode == 0 else 'main_agent',
                  'model_called': False if dry_run else 'see_runner_receipt'}
    except OSError as error:
        answer = {'status': 'fallback_required', 'reason': str(error), 'receipt_dir': str(out_dir), 'next': 'main_agent', 'model_called': False}
    (out_dir / 'optional-grok.json').write_text(json.dumps(answer, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['auto', 'off'], default='auto')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--skills-dir', type=Path)
    parser.add_argument('--cli', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        answer = invoke(args.mode, args.manifest, args.out_dir, args.skills_dir, args.cli, args.dry_run)
    except (OSError, ValueError) as error:
        answer = {'status': 'fallback_required', 'reason': str(error), 'next': 'main_agent', 'model_called': False}
    print(json.dumps(answer, ensure_ascii=False))
    # Workflow callers inspect status; a missing optional service never blocks the game pipeline.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
