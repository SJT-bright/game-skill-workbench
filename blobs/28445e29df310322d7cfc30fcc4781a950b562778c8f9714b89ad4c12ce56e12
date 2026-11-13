"""Exact invocation memo boundaries; all artifacts and commands are synthetic."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import audit_upload_startup as audit


class StartupInvocationMemo(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='startup-invocation-control-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scripts = self.root / 'candidate/remake-core/scripts'
        self.scripts.mkdir(parents=True)
        self.tool = self.scripts / 'audit_upload_startup.py'
        self.tool.write_text('# synthetic tool identity, never executed\n')
        guard = self.root / 'candidate/cocos-game-check/package-check/scripts/check_guard.cjs'
        guard.parent.mkdir(parents=True)
        guard.write_text('// synthetic guard identity, never executed\n')
        self.node = self.root / 'node'
        self.node.write_bytes(b'synthetic Node binary identity, never executed')
        self.files = {'game.js': b'var synthetic = 1;', 'icon.png': b'synthetic icon'}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(audit, '__file__', str(self.tool)))
        self.stack.enter_context(patch.object(audit.shutil, 'which', return_value=str(self.node)))
        self.stack.enter_context(patch.dict(os.environ, {'NODE_OPTIONS': '', 'NODE_PATH': ''}))
        from package_gates import adapter_fix
        local_gate = self.scripts / 'package_gates/adapter_fix.py'
        local_gate.parent.mkdir()
        local_gate.write_text('# synthetic gate file identity, never executed\n')
        self.stack.enter_context(patch.object(adapter_fix, '__file__', str(local_gate)))

    def producer(self, value=None, side_effect=None):
        value = value if value is not None else {'passed': True, 'errors': [], 'warnings': ['synthetic warning']}
        return self.stack.enter_context(patch.object(audit, '_audit_files_uncached',
            return_value=value, side_effect=side_effect))

    def test_exact_reuse_keeps_original_time_warnings_and_returns_copies(self):
        producer = self.producer()
        with audit.audit_invocation():
            first = audit.audit_files(self.files)
            first['warnings'].append('caller changed its own result')
            second = audit.audit_files(dict(self.files))
            self.assertEqual(second['warnings'], ['synthetic warning'])
            second['audit_invocation_reuse']['original_seconds'] = -1
            third = audit.audit_files(self.files)
        self.assertEqual(producer.call_count, 1)
        self.assertFalse(first['audit_invocation_reuse']['reused'])
        self.assertTrue(third['audit_invocation_reuse']['reused'])
        for key in ('original_at', 'original_seconds', 'binding_sha256'):
            self.assertEqual(first['audit_invocation_reuse'][key], third['audit_invocation_reuse'][key])

    def test_verdict_never_survives_context_or_independent_calls(self):
        producer = self.producer()
        audit.audit_files(self.files)
        audit.audit_files(self.files)
        with audit.audit_invocation():
            audit.audit_files(self.files)
            audit.audit_files(self.files)
        with audit.audit_invocation():
            audit.audit_files(self.files)
        self.assertEqual(producer.call_count, 4)

    def test_package_bytes_tool_binary_and_environment_each_invalidate(self):
        producer = self.producer()
        with audit.audit_invocation():
            audit.audit_files(self.files)
            self.files['icon.png'] = b'different synthetic icon'
            audit.audit_files(self.files)
            self.tool.write_text('# changed synthetic tool identity\n')
            audit.audit_files(self.files)
            self.node.write_bytes(b'different synthetic Node binary')
            audit.audit_files(self.files)
            with patch.dict(os.environ, {'STARTUP_MEMO_CONTROL_VALUE': 'changed'}):
                audit.audit_files(self.files)
            (self.scripts / 'new-helper.fixture').write_bytes(b'new dependency format')
            audit.audit_files(self.files)
        self.assertEqual(producer.call_count, 6)

    def test_changed_runtime_hook_invalidates(self):
        producer = self.producer()
        with audit.audit_invocation():
            audit.audit_files(self.files)
            with patch.object(audit, 'parse_package_source', return_value=None):
                audit.audit_files(self.files)
        self.assertEqual(producer.call_count, 2)

    def test_unknown_external_node_dependencies_and_symlinks_do_not_memoize(self):
        producer = self.producer()
        for variable in ('NODE_OPTIONS', 'NODE_PATH'):
            with self.subTest(variable=variable), patch.dict(os.environ, {variable: '/unbound/external'}):
                with audit.audit_invocation():
                    audit.audit_files(self.files)
                    audit.audit_files(self.files)
        (self.scripts / 'linked-helper').symlink_to(self.node)
        with audit.audit_invocation():
            audit.audit_files(self.files)
            audit.audit_files(self.files)
        self.assertEqual(producer.call_count, 6)

    def test_imported_gate_outside_the_bound_tree_cannot_memoize(self):
        from package_gates import adapter_fix
        producer = self.producer()
        external = self.root / 'external-gate.py'
        external.write_text('# unknown imported gate\n')
        with patch.object(adapter_fix, '__file__', str(external)), audit.audit_invocation():
            audit.audit_files(self.files)
            audit.audit_files(self.files)
        self.assertEqual(producer.call_count, 2)

    def test_failed_or_inconsistent_reports_keep_their_failure(self):
        for value in ({'passed': False, 'errors': ['original failure'], 'warnings': ['warning']},
                      {'passed': True, 'errors': ['inconsistent original failure']}):
            with self.subTest(value=value), patch.object(audit, '_audit_files_uncached', return_value=value) as producer:
                with audit.audit_invocation():
                    first = audit.audit_files(self.files)
                    second = audit.audit_files(self.files)
                self.assertEqual(first, value)
                self.assertEqual(second, value)
                self.assertEqual(producer.call_count, 2)

    def test_input_or_dependency_moving_during_execution_refuses_a_pass(self):
        def move_input(files):
            files['icon.png'] = b'changed during execution'
            return {'passed': True, 'errors': []}
        def move_tool(files):
            self.tool.write_text('# changed during execution\n')
            return {'passed': True, 'errors': []}
        for callback in (move_input, move_tool):
            with self.subTest(callback=callback.__name__), patch.object(audit, '_audit_files_uncached', side_effect=callback):
                with audit.audit_invocation(), self.assertRaisesRegex(ValueError, 'inputs changed during validation'):
                    audit.audit_files(self.files)

    def test_input_moving_during_reuse_refuses_old_pass(self):
        self.producer()
        original = audit._audit_memo_identity
        calls = []
        def moving(files):
            value = original(files)
            calls.append(1)
            if len(calls) == 3:
                files['icon.png'] = b'changed while reusing'
            return value
        with patch.object(audit, '_audit_memo_identity', side_effect=moving):
            with audit.audit_invocation():
                audit.audit_files(self.files)
                with self.assertRaisesRegex(ValueError, 'inputs changed during memo verification'):
                    audit.audit_files(self.files)

    def real_gate_setup(self):
        import make_tiktok_zip as writer
        self.native = self.root / 'Native'
        self.native.mkdir()
        payload = dict(self.files, **{'game.json': b'{"subpackages":[]}',
            'project.config.json': b'{"appid":"synthetic"}',
            'cocos/cocos2d-js-min.js': b'var synthetic={getTouchesByEvent:function(e,t){return [];}};'})
        for name, data in payload.items():
            path = self.native / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.stack.enter_context(patch.object(audit, 'parse_package_source', return_value=(0, '', {
            'dependencies': [], 'dynamic': [], 'native_entry_protocols': []}, False)))
        self.stack.enter_context(patch.object(audit, 'parser_fingerprint', return_value=('synthetic-parser',)))
        self.stack.enter_context(patch('upload_size_gate.enforce_tiktok_host', return_value=None))
        self.stack.enter_context(patch('package_gates.run', return_value={
            'blocks': [], 'warnings': [], 'gates': [], 'missing': []}))
        self.stack.enter_context(patch.object(writer, 'pre_home', return_value={}))
        def fake_command(command, **kwargs):
            self.assertEqual(Path(command[1]).name, 'probe_cocos2_touch_coordinates.cjs')
            return subprocess.CompletedProcess(command, 0, json.dumps({'schema': 'cocos2_touch_coordinates.v1',
                'passed': True, 'rows': [{'passed': True}]}), '')
        commands = self.stack.enter_context(patch.object(audit.subprocess, 'run', side_effect=fake_command))
        return writer, payload, commands

    def test_real_native_and_zip_startup_dispatch_share_one_probe_only_in_context(self):
        writer, payload, commands = self.real_gate_setup()
        with audit.audit_invocation():
            problems, sizes, _ = writer.native_problems(self.native)
            self.assertEqual(problems, [])
            out = self.root / 'synthetic.zip'
            writer.write_zip(self.native, sizes, out)
            verified = writer.vnz.verify(out, 'synthetic')
        self.assertEqual(verified['files'], len(payload))
        self.assertEqual(commands.call_count, 1)
        writer.vnz.verify(out, 'synthetic')
        self.assertEqual(commands.call_count, 2)

    def test_final_zip_crc_is_still_read_after_startup_memo_pass(self):
        writer, payload, commands = self.real_gate_setup()
        out = self.root / 'synthetic-stored.zip'
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as archive:
            for name, data in payload.items():
                archive.writestr(name, data)
        with audit.audit_invocation():
            writer.vnz.verify(out, 'synthetic')
            with zipfile.ZipFile(out) as archive:
                info = archive.getinfo('icon.png')
            damaged = bytearray(out.read_bytes())
            offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
            damaged[offset] ^= 1
            out.write_bytes(damaged)
            with self.assertRaisesRegex(zipfile.BadZipFile, 'CRC'):
                writer.vnz.verify(out, 'synthetic')
        self.assertEqual(commands.call_count, 1)

    def test_delivery_scope_shares_static_probe_but_next_delivery_reads_again(self):
        import make_tiktok_zip as writer
        import prepare_delivery as delivery
        _, payload, commands = self.real_gate_setup()
        out = self.root / 'synthetic-delivery.zip'
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as archive:
            for name, data in payload.items():
                archive.writestr(name, data)
        # Exercise the real public delivery invocation and real verifier twice,
        # as its size/receipt/package layers do. Only unrelated delivery setup is
        # stubbed; neither a real game nor a delivery approval is claimed.
        reads = []
        def layers(*args):
            for _ in range(2):
                result = writer.vnz.verify(out, 'synthetic')
                reads.append(result['sha256'])
            return {'fixture': True}
        with patch.object(delivery, '_prepare', side_effect=layers):
            delivery.prepare(out, self.native, 'synthetic', self.root / 'receipt.json')
            self.assertEqual(commands.call_count, 1)
            delivery.prepare(out, self.native, 'synthetic', self.root / 'receipt2.json')
        self.assertEqual(commands.call_count, 2)
        self.assertEqual(len(reads), 4)
        self.assertEqual(len(set(reads)), 1)


if __name__ == '__main__':
    unittest.main()
