#!/usr/bin/env python3
"""Legacy STORAGE-01 diagnostics remain useful but never satisfy v3 coverage.

Synthetic schema/replay unit fixtures only; no Cocos, SDK or phone acceptance.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

if os.environ.get('SKILL_TEST_DEPS'):
    sys.path.insert(1, str(Path(os.environ['SKILL_TEST_DEPS']).resolve()))
from audit_native_storage_contract import BASE_CASES, digest, replay, validate

NEEDS_UPGRADE = 'needs_upgrade: v1/v2 do not prove cold-upgrade bridge coverage'


def run():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        native = root / 'native'; native.mkdir()
        current = native / 'main.js'; current.write_text('fixed', encoding='utf-8')
        old = root / 'old.js'; old.write_text('known-bad', encoding='utf-8')
        runner = root / 'runner.py'
        runner.write_text(
            'import argparse,hashlib,json\n'
            'p=argparse.ArgumentParser();p.add_argument("--bundle");p.add_argument("--adapter");a=p.parse_args()\n'
            'h=lambda q:hashlib.sha256(open(q,"rb").read()).hexdigest()\n'
            'cases={k:"pass" for k in ' + repr(BASE_CASES) + '} if "native" in a.bundle else {"missing_empty_string":"fail"}\n'
            'print(json.dumps({"runner_sha256":h(__file__),"bundle_sha256":h(a.bundle),"adapter_sha256":h(a.adapter),"cases":cases}))\n',
            encoding='utf-8')
        binding = {'source_sha256': 's', 'native_tree_sha256': 'n', 'web_tree_sha256': 'w', 'build_tag': 'b'}

        def record(bundle, label):
            raw = root / (label + '.json')
            result = subprocess.run([sys.executable, str(runner), '--bundle', str(bundle), '--adapter', str(bundle)],
                                    capture_output=True, text=True, check=True)
            raw.write_text(result.stdout, encoding='utf-8')
            return {'bundle': str(bundle), 'bundle_sha256': digest(bundle),
                    'adapter': str(bundle), 'adapter_sha256': digest(bundle),
                    'raw_report': str(raw), 'raw_sha256': digest(raw)}

        trace = {'schema': 'native_storage_trace.v1', 'binding': binding,
                 'execution': {'runner': str(runner), 'runner_sha256': digest(runner),
                               'command': [sys.executable, str(runner), '--bundle', '{bundle}', '--adapter', '{adapter}']},
                 'current': record(current, 'current'), 'negative_control': record(old, 'negative')}

        def expect(*specific):
            actual = validate(trace, native, binding)
            expected = [NEEDS_UPGRADE, *specific]
            # Exact diagnostics ensure a permanent needs_upgrade does not mask
            # broken stale-byte/negative/case detection in this legacy fixture.
            assert sorted(actual) == sorted(expected), (actual, expected)

        expect(); assert replay(trace) == []
        trace['current']['bundle_sha256'] = 'wrong'
        expect('current bytes changed')
        trace['current']['bundle_sha256'] = digest(current)
        trace['binding'] = {'build_tag': 'stale'}
        expect('current build binding')
        trace['binding'] = binding
        negative_raw = Path(trace['negative_control']['raw_report'])
        negative = json.loads(negative_raw.read_text())
        negative['cases']['missing_empty_string'] = 'pass'
        negative_raw.write_text(json.dumps(negative))
        trace['negative_control']['raw_sha256'] = digest(negative_raw)
        expect('negative did not reproduce missing-empty-string defect')
        negative['cases']['missing_empty_string'] = 'fail'
        negative_raw.write_text(json.dumps(negative))
        trace['negative_control']['raw_sha256'] = digest(negative_raw)
        current_raw = Path(trace['current']['raw_report'])
        result = json.loads(current_raw.read_text())
        del result['cases']['reopen_map']
        current_raw.write_text(json.dumps(result)); trace['current']['raw_sha256'] = digest(current_raw)
        expect('current case missing or failed: reopen_map (requires pass)')
        result['cases']['reopen_map'] = 'pass'; result['cases']['completed_reward_once'] = 'fail'
        current_raw.write_text(json.dumps(result)); trace['current']['raw_sha256'] = digest(current_raw)
        expect('current case missing or failed: completed_reward_once (requires pass)')
        result['cases']['completed_reward_once'] = 'pass'
        current_raw.write_text(json.dumps(result)); trace['current']['raw_sha256'] = digest(current_raw)
        expect(); assert replay(trace) == []

        # CLI must expose the policy upgrade boundary, not issue a fresh pass.
        trace_path = root / 'trace.json'; trace_path.write_text(json.dumps(trace))
        binding_path = root / 'binding.json'; binding_path.write_text(json.dumps({'binding': binding}))
        report_path = root / 'report.json'
        cli = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('audit_native_storage_contract.py')),
                              '--trace', str(trace_path), '--native', str(native), '--binding', str(binding_path),
                              '--out', str(report_path)], capture_output=True, text=True)
        report = json.loads(report_path.read_text())
        assert cli.returncode == 1 and report['status'] == 'needs_upgrade' and report['passed'] is False
        assert report['errors'] == [NEEDS_UPGRADE], report

        result['cases']['reopen_map'] = 'fail'
        current_raw.write_text(json.dumps(result)); trace['current']['raw_sha256'] = digest(current_raw)
        assert replay(trace) == ['current actual runner output does not match raw report']
    print('STORAGE-01 legacy gate regression passed: exact needs_upgrade, stale bytes/binding, bad negative, missing/failed case, forged raw replay, CLI refusal')


if __name__ == '__main__':
    run()
