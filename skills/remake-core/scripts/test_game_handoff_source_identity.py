"""Source identity choreography controls. Package/receipt acceptance is mocked.

Tiny source ZIPs exercise original handoff functions; no official game writer,
CLI, browser, engine or real game acceptance is executed by these controls.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import game_handoff as H
import source_hygiene as hygiene


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SourceIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='source-identity-工程 ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root/'工程 Game'
        (self.project/'assets').mkdir(parents=True)
        (self.project/'assets/main.js').write_text('const fixture=1;')
        self.game = self.root/'opaque-fixture.zip'
        self.game.write_bytes(b'opaque fixture, not a playable or uploadable game')
        self.source = self.root/'source.zip'; self.write_source('first')
        self.writer = self.root/'writer-fixture.json'; self.writer.write_text('{"fixture":true}')
        self.delivery = self.root/'delivery.json'
        self.delivery.write_text(json.dumps({'delivery_ready':True, 'archive':str(self.game), 'sha256':digest(self.game)}))
        self.output = self.root/'standalone.zip'
        p = patch.object(H, 'package', lambda *a, **k: ({'passed':True, 'sha256':digest(self.game), 'errors':[]}, {}))
        p.start(); self.addCleanup(p.stop)
        p = patch.object(H, 'receipt_status', lambda *a, **k: {'entry':'official', 'receipt':str(self.writer)})
        p.start(); self.addCleanup(p.stop)

    def write_source(self, tag, code='const fixture=1;'):
        with zipfile.ZipFile(self.source, 'w') as z:
            z.writestr('assets/main.js', code); z.writestr('assets/icon.txt', tag)

    def deliver(self):
        return H.deliver(self.delivery, self.project, source=self.source)

    def no_new_evidence(self):
        self.assertFalse(list(self.root.glob('*_交接证据*.zip')))
        self.assertFalse(list(self.root.glob('.handoff-*')))
        self.assertFalse(self.output.exists())

    def test_hygiene_replacement_cannot_reset_inner_source_baseline(self):
        original = hygiene.audit
        def changed(path, *a, **k):
            result = original(path, *a, **k)
            if Path(path) == self.source: self.write_source('changed during hygiene')
            return result
        with patch.object(hygiene, 'audit', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.deliver()
        self.no_new_evidence()

    def test_source_hash_precedes_final_logical_identity(self):
        original = H.source_identity; swapped = []
        def changed(path):
            result = original(path)
            if Path(path) == self.source and not swapped:
                self.write_source('changed after logical read', code='const fixture=999;'); swapped.append(True)
            return result
        with patch.object(H, 'source_identity', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.deliver()
        self.no_new_evidence()

    def test_staged_archive_mutation_is_refused_before_publication(self):
        original = zipfile.ZipFile.writestr
        def changed(z, name, *a, **k):
            result = original(z, name, *a, **k)
            if name == 'manifest.json': self.write_source('changed while writing evidence')
            return result
        with patch.object(zipfile.ZipFile, 'writestr', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.deliver()
        self.no_new_evidence()

    def test_source_change_at_publication_is_refused_and_own_output_removed(self):
        original = H.os.link
        def changed(*a, **k):
            result = original(*a, **k); self.write_source('changed at publication'); return result
        with patch.object(H.os, 'link', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.deliver()
        self.no_new_evidence()

    def test_link_created_then_interrupted_removes_only_own_complete_output(self):
        original = H.os.link
        def changed(*a, **k):
            original(*a, **k)
            raise OSError('controlled interruption immediately after link')
        with patch.object(H.os, 'link', changed), self.assertRaisesRegex(OSError, 'controlled interruption'):
            self.deliver()
        self.no_new_evidence()

    def test_competing_identical_content_with_different_inode_is_preserved(self):
        import shutil
        competitor = []
        def existing(src, dst, *a, **k):
            shutil.copyfile(src, dst); competitor.append(Path(dst))
            raise FileExistsError('controlled competing artifact')
        with patch.object(H.os, 'link', existing), self.assertRaises(FileExistsError):
            self.deliver()
        self.assertTrue(competitor[0].is_file())
        with zipfile.ZipFile(competitor[0]) as z: self.assertIn('manifest.json', z.namelist())

    def test_source_change_after_export_is_refused_by_deliver(self):
        original = H.export
        def changed(*a, **k):
            result = original(*a, **k); self.write_source('changed before final return'); return result
        with patch.object(H, 'export', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.deliver()
        self.no_new_evidence()

    def test_existing_evidence_is_preserved_when_reuse_source_changes(self):
        first = self.deliver(); evidence = Path(first['evidence_zip']); previous = evidence.read_bytes()
        original = H._evidence_for
        def changed(*a, **k):
            result = original(*a, **k)
            if result: self.write_source('changed during reuse')
            return result
        with patch.object(H, '_evidence_for', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.deliver()
        self.assertEqual(evidence.read_bytes(), previous)
        self.assertEqual(len(list(self.root.glob('*_交接证据*.zip'))), 1)

    def test_normal_same_input_reuses_both_artifacts_and_preserves_metadata(self):
        first = self.deliver(); second = self.deliver()
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertEqual(second['made'], {'source_zip':False, 'evidence_zip':False})
        self.assertEqual(first['source_zip'], second['source_zip'])
        self.assertEqual(first['evidence_zip'], second['evidence_zip'])
        with zipfile.ZipFile(first['evidence_zip']) as z: manifest = json.loads(z.read('manifest.json'))
        self.assertEqual(manifest['source_zip']['sha256'], digest(self.source))
        for result in [first, second]:
            self.assertEqual(result['sha256']['source_zip'], digest(self.source))
            timing = result['timings']; self.assertGreater(timing['verification_seconds'], 0)
            self.assertAlmostEqual(timing['total_seconds'], timing['verification_seconds'] + timing['packaging_seconds'])
            self.assertEqual(timing['game_execution_seconds'], 0)
        self.assertEqual(second['timings']['packaging_seconds'], 0)

    def test_standalone_export_owns_its_initial_source_identity(self):
        original = hygiene.audit
        def changed(path, *a, **k):
            result = original(path, *a, **k); self.write_source('changed in standalone hygiene'); return result
        with patch.object(hygiene, 'audit', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
            H.export(self.game, self.source, self.delivery, self.output)
        self.no_new_evidence()

    def test_supplied_expected_digest_adds_constraint_and_never_bypasses_actual_hash(self):
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            H.export(self.game, self.source, self.delivery, self.output, expected_source_sha256='0'*64)
        self.no_new_evidence()
        with self.assertRaisesRegex(ValueError, 'expected source SHA'):
            H.export(self.game, self.source, self.delivery, self.output, expected_source_sha256='passed')
        self.no_new_evidence()

    def test_missing_source_before_or_during_export_refuses_without_success_artifact(self):
        self.source.unlink()
        with self.assertRaisesRegex(ValueError, 'actual delivered source ZIP'):
            H.export(self.game, self.source, self.delivery, self.output)
        self.write_source('restored'); original = hygiene.audit
        def removed(path, *a, **k):
            result = original(path, *a, **k); self.source.unlink(); return result
        with patch.object(hygiene, 'audit', removed), self.assertRaises(OSError): self.deliver()
        self.no_new_evidence()

    def test_concurrently_replaced_output_is_preserved_on_refusal(self):
        original = H.os.link; externally_changed = []
        def changed(src, dst, *a, **k):
            result = original(src, dst, *a, **k); Path(dst).write_bytes(b'external bytes'); externally_changed.append(Path(dst)); return result
        with patch.object(H.os, 'link', changed), self.assertRaisesRegex(ValueError, 'output changed'):
            self.deliver()
        self.assertEqual(externally_changed[0].read_bytes(), b'external bytes')

    def test_project_change_before_final_return_refuses_only_own_new_evidence(self):
        original = H.export
        def changed(*a, **k):
            result = original(*a, **k); (self.project/'assets/main.js').write_text('const fixture=2;'); return result
        with patch.object(H, 'export', changed), self.assertRaisesRegex(ValueError, 'project changed'):
            self.deliver()
        self.no_new_evidence()

    def test_source_zip_hashing_uses_bounded_stream_reads(self):
        original = Path.read_bytes
        def read(path):
            if Path(path) == self.source: raise AssertionError('unbounded full source read')
            return original(path)
        with patch.object(Path, 'read_bytes', read): result = self.deliver()
        self.assertEqual(result['sha256']['source_zip'], digest(self.source))

    def test_delivery_record_or_game_change_at_commit_refuses(self):
        original = H.os.link
        for which in ['delivery', 'game']:
            self.delivery.write_text(json.dumps({'delivery_ready':True, 'archive':str(self.game), 'sha256':digest(self.game)}))
            def changed(*a, **k):
                result = original(*a, **k)
                (self.delivery if which == 'delivery' else self.game).write_bytes(b'changed input')
                return result
            with patch.object(H.os, 'link', changed), self.assertRaisesRegex(ValueError, 'inputs changed'):
                self.deliver()
            self.no_new_evidence()


if __name__ == '__main__': unittest.main()
