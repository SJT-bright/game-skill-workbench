import unittest
from unittest.mock import patch
import audit_page_richness as runtime
from clarity_policy import resolve_policy


def node(source=(250,250), render=(160,160), name='Ball'):
    return {'name': name, 'path': 'Canvas/'+name, 'rect': [.2,.2,.2,.2],
            'comps': {'sprite': {'frame':'ball', 'frame_size':list(source), 'css_display_size':list(render)}}}


class RuntimeClarityPolicyTests(unittest.TestCase):
    def test_actual_clear_sized_image_not_forced_to_two_times(self):
        with patch.object(runtime, 'CLARITY_POLICY', resolve_policy()):
            self.assertEqual([],runtime.low_res_problems([node()],[]))
            row=runtime.runtime_clarity_findings([node()],[])[0]
            self.assertEqual(1.5625,row['source_render_ratio'])
            self.assertFalse(row['blocking'])

    def test_below_reference_advisory_does_not_hide_real_defect(self):
        policy=resolve_policy()
        with patch.object(runtime,'CLARITY_POLICY',policy):
            messages=runtime.low_res_problems([node((80,80))],[])
        defects,advisories=runtime.split_clarity_messages(messages+['low_contrast: unreadable text'],policy)
        self.assertEqual(['low_contrast: unreadable text'],defects)
        self.assertEqual(1,len(advisories))
        self.assertIn('advisory',advisories[0])

    def test_explicit_strict_still_blocks_same_ratio(self):
        policy=resolve_policy(cli_preset='strict')
        with patch.object(runtime,'CLARITY_POLICY',policy):
            messages=runtime.low_res_problems([node()],[])
        defects,advisories=runtime.split_clarity_messages(messages,policy)
        self.assertEqual(1,len(defects));self.assertEqual([],advisories)
        self.assertIn('reference 2x',defects[0])

    def test_background_has_independently_configured_reference(self):
        n=node((200,200),name='Background')
        policy=resolve_policy(cli_preset='strict')
        with patch.object(runtime,'CLARITY_POLICY',policy):
            self.assertEqual(1.5,runtime.runtime_clarity_findings([n],[])[0]['threshold'])
            self.assertTrue(runtime.low_res_problems([n],[]))
        with patch.object(runtime,'CLARITY_POLICY',resolve_policy()):
            self.assertEqual([],runtime.low_res_problems([n],[]))

    def test_changed_reference_changes_exact_findings(self):
        with patch.object(runtime,'CLARITY_POLICY',resolve_policy(cli_min_ratio=.4)):
            self.assertEqual([],runtime.low_res_problems([node((80,80))],[]))
        with patch.object(runtime,'CLARITY_POLICY',resolve_policy(cli_min_ratio=1.2)):
            self.assertEqual(1,len(runtime.low_res_problems([node((80,80))],[])))

if __name__=='__main__':unittest.main()
