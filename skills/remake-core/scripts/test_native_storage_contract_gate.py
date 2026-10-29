#!/usr/bin/env python3
"""Regression check for STORAGE-01's own refusal and replay behavior."""
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from audit_native_storage_contract import CASES, digest, replay, validate


def run():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        native = root / 'native'
        native.mkdir()
        current = native / 'main.js'
        current.write_text('fixed', encoding='utf-8')
        old = root / 'old.js'
        old.write_text('known-bad', encoding='utf-8')
        runner = root / 'runner.py'
        runner.write_text(
            'import argparse,hashlib,json\n'
            'p=argparse.ArgumentParser();p.add_argument("--bundle");p.add_argument("--adapter");a=p.parse_args()\n'
            'h=lambda q:hashlib.sha256(open(q,"rb").read()).hexdigest()\n'
            'cases={k:"pass" for k in ' + repr(CASES) + '} if "native" in a.bundle else {"missing_empty_string":"fail"}\n'
            'print(json.dumps({"runner_sha256":h(__file__),"bundle_sha256":h(a.bundle),"adapter_sha256":h(a.adapter),"cases":cases}))\n',
            encoding='utf-8')
        binding = {'source_sha256': 's', 'native_tree_sha256': 'n', 'web_tree_sha256': 'w', 'build_tag': 'b'}

        def record(bundle, label):
            raw = root / (label + '.json')
            result = subprocess.run(['python3', str(runner), '--bundle', str(bundle), '--adapter', str(bundle)],
                                    capture_output=True, text=True, check=True)
            raw.write_text(result.stdout, encoding='utf-8')
            return {'bundle': str(bundle), 'bundle_sha256': digest(bundle),
                    'adapter': str(bundle), 'adapter_sha256': digest(bundle),
                    'raw_report': str(raw), 'raw_sha256': digest(raw)}

        trace = {'schema': 'native_storage_trace.v1', 'binding': binding,
                 'execution': {'runner': str(runner), 'runner_sha256': digest(runner),
                               'command': ['python3', str(runner), '--bundle', '{bundle}', '--adapter', '{adapter}']},
                 'current': record(current, 'current'), 'negative_control': record(old, 'negative')}
        assert not validate(trace, native, binding) and not replay(trace)
        trace['current']['bundle_sha256'] = 'wrong'
        assert validate(trace, native, binding)
        trace['current']['bundle_sha256'] = digest(current)
        negative_raw = Path(trace['negative_control']['raw_report'])
        negative = json.loads(negative_raw.read_text())
        negative['cases']['missing_empty_string'] = 'pass'
        negative_raw.write_text(json.dumps(negative))
        trace['negative_control']['raw_sha256'] = digest(negative_raw)
        assert validate(trace, native, binding)
        negative['cases']['missing_empty_string'] = 'fail'
        negative_raw.write_text(json.dumps(negative))
        trace['negative_control']['raw_sha256'] = digest(negative_raw)
        current_raw = Path(trace['current']['raw_report'])
        result = json.loads(current_raw.read_text())
        del result['cases']['reopen_map']
        current_raw.write_text(json.dumps(result))
        trace['current']['raw_sha256'] = digest(current_raw)
        assert validate(trace, native, binding)
        result['cases']['reopen_map'] = 'pass'
        result['cases']['completed_reward_once'] = 'fail'
        current_raw.write_text(json.dumps(result))
        trace['current']['raw_sha256'] = digest(current_raw)
        assert validate(trace, native, binding)
        result['cases']['completed_reward_once'] = 'pass'
        result['cases']['reopen_map'] = 'pass'
        current_raw.write_text(json.dumps(result))
        trace['current']['raw_sha256'] = digest(current_raw)
        assert not validate(trace, native, binding) and not replay(trace)
        result['cases']['reopen_map'] = 'fail'
        current_raw.write_text(json.dumps(result))
        trace['current']['raw_sha256'] = digest(current_raw)
        assert replay(trace)
    print('STORAGE-01 gate regression passed: valid, stale bytes, bad negative, missing/failed case, forged raw replay')


if __name__ == '__main__':
    run()
