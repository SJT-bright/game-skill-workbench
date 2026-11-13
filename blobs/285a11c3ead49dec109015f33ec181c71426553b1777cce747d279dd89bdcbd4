"""Synthetic A→B→C originals exercise loader seams; never game/art approval."""
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import art_capture_history as history
import art_iteration_plan as planner
import audit_page_richness
import extract_ui_layout
import test_art_capture_history as fixtures
from art_case_dependencies import digest, file_sha

SPRITE = Path(__file__).resolve().parents[2]/'remake-art/scripts/check_native_sprite_sources.py'
spec = importlib.util.spec_from_file_location('history_sprite_sources', SPRITE)
sprite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sprite)


class Consumers(unittest.TestCase):
    def test_three_transitions_keep_exact_original_files_and_quality_sha(self):
        f = fixtures.History()
        original_capture = f.capture
        def capture(owner, folder, case):
            # Extend this synthetic producer before its fixture proof is consumed.
            original_capture(folder, case)
            path = folder/('capture-ui-dump-'+case['id']+'.json')
            doc = history.read(path)
            doc['page'] = dict(width=10, height=20, dpr=1)
            doc['nodes'][0]['comps'] = {'sprite': {'frame': 'icon_'+case['id']}}
            path.write_text(json.dumps(doc))
            proof_path = history.store(owner.project)/'proofs'/(doc['art_capture_id']+'.json')
            proof = history.read(proof_path)
            proof.pop('seal')
            proof['dump'] = file_sha(path)
            proof_path.write_text(json.dumps(dict(proof, seal=digest(proof))))
        f.capture = types.MethodType(capture, f)
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.transition()
        checkpoint = f.root/'checkpoint-B.json'
        history.initialize(f.project, f.build, f.contract_path, checkpoint, f.new)
        f.write_source(f.text.replace('return 1', 'return 2').replace('return 9', 'return 8'))
        f.start()
        newest = f.root/'third'
        newest.mkdir()
        for case in [f.cases[0], f.cases[2]]:
            f.capture(newest, case)
        manifest = dict(schema=history.SCHEMA, project=str(f.project), baseline=str(checkpoint),
            baseline_sha256=file_sha(checkpoint), base_dumps=str(f.new), fresh_cases=['home', 'settings'], quality_refs=[])
        (newest/history.MANIFEST).write_text(json.dumps(manifest))
        verified = history.verify(f.project, f.build, newest)
        old_popup = f.new/'capture-ui-dump-popup.json'
        original_sha = file_sha(old_popup)
        loaded = [path for path, _ in extract_ui_layout.load_dumps([newest])]
        self.assertEqual(set(loaded), {Path(p) for p in verified['resolved_dumps']})
        self.assertIn(old_popup, loaded)
        richness_paths = {Path(row['_file']) for row in audit_page_richness.load([newest], project=f.project)}
        self.assertEqual(richness_paths, set(loaded))
        self.assertEqual(file_sha(old_popup), original_sha)
        self.assertEqual(set(sprite.observed_dump_files(newest)), set(loaded))
        self.assertEqual(sprite.captured_inventory(newest)['selected_frames'], ['icon_home', 'icon_popup', 'icon_settings'])
        data = dict(selected_cases=['slot-popup'], input_binding=dict(documents=[dict(file=str(old_popup))]))
        self.assertTrue(planner.first_piece_capture_current(data, {'slot-popup': 'popup'}, verified, newest))
        manifest['baseline_sha256'] = '0'*64
        (newest/history.MANIFEST).write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            extract_ui_layout.load_dumps([newest])
        with self.assertRaises(ValueError):
            list(sprite.observed_dump_files(newest))
        with self.assertRaises(ValueError):
            audit_page_richness.load([newest], project=f.project)

    def test_ordinary_sprite_observation_retains_non_dump_json_attachments(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            attachment = folder/'frames-attachment.json'
            attachment.write_text('{}')
            self.assertIn(attachment, list(sprite.observed_dump_files(folder)))


if __name__ == '__main__':
    unittest.main()
