"""A broken learning hook cannot revoke an actual verified ZIP/HTTP delivery."""
import unittest
from unittest.mock import patch
import test_delivery_scoped_preview as W

class LearningDeliveryIsolation(unittest.TestCase):
    def test_hook_failure_does_not_change_delivery_or_restart_renderer(self):
        case=W.ScopedPreviewDelivery('test_current_snapshot_passes_and_old_snapshot_refuses_without_changing_original_contract')
        case.setUp()
        try:
            with patch('production_hooks.collect_after_delivery',side_effect=RuntimeError('controlled learning failure')) as hook:
                case.test_current_snapshot_passes_and_old_snapshot_refuses_without_changing_original_contract()
            hook.assert_called_once()
            record=case.root/'delivery-current.json'
            self.assertTrue(record.is_file())
            import json
            self.assertTrue(json.loads(record.read_text())['delivery_ready'])
            self.assertFalse((case.root/'delivery-old.json').exists())
        finally:
            case.doCleanups()

if __name__=='__main__':unittest.main(verbosity=2)
