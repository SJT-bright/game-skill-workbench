"""Metadata migration over independently approved artifact scopes, not a game run."""
import json
import unittest
from unittest.mock import patch

import check_known_issues as gate
import known_issue_checkpoints as checkpoints
import test_known_issue_checkpoints as fixtures


class ScopedReviewMigration(unittest.TestCase):
    def test_registered_artifact_scope_can_migrate_an_existing_whole_tree_node(self):
        fixture = fixtures.CheckpointReuse('test_unchanged_rows_are_not_revalidated_and_keep_original_times')
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        catalog = json.loads(fixture.catalog.read_text())
        catalog['items'][0]['id'] = 'LOAD-01'
        fixture.save(fixture.catalog, catalog)
        fixture.review['checks']['LOAD-01'] = fixture.review['checks'].pop('UI-04')
        fixture.review['catalog_sha256'] = gate.sha(fixture.catalog.read_bytes())
        fixture.flush()
        self.assertEqual(gate.audit(fixture.args)['status'], 'passed')
        origin = gate.binding(fixture.args)
        (fixture.project / 'assets/icon.png').write_bytes(b'new deferred image')
        blocked = gate.audit(fixture.args)
        self.assertEqual(blocked['status'], 'blocked')
        self.assertIn('known.LOAD-01', blocked['repair_scope'])
        # Scope approval itself is independently exercised by the actual
        # startup CLI/consumer tests. This control isolates metadata routing.
        with patch.object(checkpoints, 'artifact_bindings', return_value={'known.LOAD-01': origin}):
            result = gate.audit(fixture.args)
            self.assertEqual(result['status'], 'passed', result)
            with patch.object(gate, 'check_row', side_effect=AssertionError('unchanged row revalidated')):
                self.assertEqual(gate.audit(fixture.args)['status'], 'passed')
        # Losing the independently validated scope must not inherit the new
        # metadata record as an unscoped whole-tree approval.
        self.assertEqual(gate.audit(fixture.args)['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
