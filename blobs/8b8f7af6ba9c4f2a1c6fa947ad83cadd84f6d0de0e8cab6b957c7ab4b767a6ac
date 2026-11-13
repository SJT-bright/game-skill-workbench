"""Assembly regressions use synthetic geometry, never a game acceptance result."""
import copy
import unittest
from unittest.mock import patch

import audit_page_richness as audit


def node(path, rect, **comps):
    return {'path':path, 'name':path.rsplit('/', 1)[-1], 'rect':rect,
            'comps':comps, 'opacity':1, 'order':1}


def fixture():
    root = 'Canvas/Popup/RewardCard'
    return {'kind':'popup', 'purpose':'reward', 'viewport':{'width':375, 'height':667},
            '_file':'/synthetic-only/fixture-ui-dump.json', 'nodes':[
        node(root, [.1,.1,.8,.3]),
        node(root+'/CardSurface', [.1,.1,.8,.3], sprite={
            'frame':'panel', 'sliced':True, 'inner':[.14,.16,.72,.18],
            'frame_size':[964,1381], 'css_display_size':[300,200.1], 'insets':[80]*4}),
        node(root+'/Rewards/Coin', [.2,.2,.06,.04], sprite={
            'frame':'img_coin', 'frame_size':[548,553], 'css_display_size':[22.5,26.68]}),
        node(root+'/Rewards/Hint', [.5,.2,.06,.04], sprite={
            'frame':'img_hint', 'frame_size':[452,458], 'css_display_size':[22.5,26.68]}),
        node(root+'/DayNumber/G0', [.4,.1,.03,.03], sprite={'frame':'digit_7'})]}


class SpriteAssembly(unittest.TestCase):
    def inspect(self, data):
        return audit.sprite_assembly_findings(data, data['nodes'])

    def test_real_shaped_fault_detects_both_causes_without_ratio_threshold(self):
        d=fixture(); d['nodes'][1]['comps']['sprite']['inner']=[.14,.2,.72,.01499]
        d['nodes'][3]['comps']['sprite']['frame']='btn_hint'
        result=self.inspect(d)
        self.assertEqual({p.split(':',1)[0] for p in result['reviews']},
                         {'sliced_reward_content_exceeds_inner','reward_button_thumbnail'})
        self.assertTrue(all(row['auto_regenerate'] is False for row in result['measurements']))
        self.assertAlmostEqual(result['measurements'][0]['inner_css_size'][1],9.99833)

    def test_normal_populated_slice_and_icon_pass(self):
        result=self.inspect(fixture())
        self.assertEqual([],result['problems']); self.assertEqual([],result['reviews'])
        self.assertEqual('within_measured_center',result['measurements'][0]['status'])

    def test_single_defect_controls_isolate_each_cause(self):
        d=fixture(); d['nodes'][1]['comps']['sprite']['inner'][3]=.01499
        self.assertEqual(['sliced_reward_content_exceeds_inner'],
                         [p.split(':',1)[0] for p in self.inspect(d)['reviews']])
        d=fixture(); d['nodes'][3]['comps']['sprite']['frame']='btn_hint'
        self.assertEqual(['reward_button_thumbnail'],[p.split(':',1)[0] for p in self.inspect(d)['reviews']])

    def test_larger_source_does_not_hide_wrong_composition(self):
        d=fixture(); d['nodes'][1]['comps']['sprite']['inner'][3]=.01499
        d['nodes'][3]['comps']['sprite'].update(frame='btn_hint',frame_size=[9000,9000])
        self.assertEqual(2,len(self.inspect(d)['reviews']))

    def test_measured_zero_center_is_not_silently_unmeasured(self):
        d=fixture(); d['nodes'][1]['comps']['sprite']['inner'][3]=0
        self.assertEqual('unmeasured',self.inspect(d)['measurements'][0]['status'])
        self.assertTrue(self.inspect(d)['reviews'])

    def test_missing_geometry_is_visible_review_not_an_invented_fit(self):
        d=fixture(); del d['nodes'][1]['comps']['sprite']['inner']
        result=self.inspect(d)
        self.assertEqual([],result['problems']); self.assertEqual(1,len(result['reviews']))
        self.assertEqual('unmeasured',result['measurements'][0]['status'])

    def test_missing_viewport_or_invalid_measurements_are_not_passed_as_fits(self):
        for bad in (None, float('nan'), -1):
            with self.subTest(bad=bad):
                d=fixture(); d['viewport']['height']=bad
                self.assertEqual('unmeasured',self.inspect(d)['measurements'][0]['status'])

    def test_two_css_rounding_tolerance_is_not_a_reserve_multiplier(self):
        d=fixture(); d['nodes'][1]['comps']['sprite']['inner'][1]=.2
        d['nodes'][1]['comps']['sprite']['inner'][3]=(26.68-1.5)/667
        self.assertEqual([],self.inspect(d)['reviews'])
        d['nodes'][1]['comps']['sprite']['inner'][3]=(26.68-2.5)/667
        self.assertTrue(self.inspect(d)['reviews'])

    def test_card_caption_on_rim_and_declared_decoration_may_overhang(self):
        d=fixture();d['nodes'].append(node('Canvas/Popup/RewardCard/Rewards/Decorations/Badge',
            [.05,.05,.9,.5],sprite={'frame':'img_badge'}))
        self.assertEqual([],self.inspect(d)['problems'])

    def test_real_button_disabled_button_and_art_child_keep_action_role(self):
        for disabled,child in ((False,False),(True,False),(False,True),(True,True)):
            with self.subTest(disabled=disabled,child=child):
                d=fixture(); n=d['nodes'][3];n['comps']['sprite']['frame']='btn_hint'
                if child:
                    d['nodes'].append(node(n['path'],n['rect'],button={'interactable':not disabled}))
                    n['path']+='/Art';n['name']='Art'
                else:n['comps']['button']={'interactable':not disabled}
                self.assertFalse(any(p.startswith('reward_button_thumbnail:') for p in self.inspect(d)['problems']))

    def test_unrelated_action_and_pure_symbol_not_reward_thumbnails(self):
        d=fixture(); n=d['nodes'][3];n['comps']['sprite']['frame']='btn_close'
        self.assertEqual([],self.inspect(d)['problems'])
        n['path']='Canvas/Popup/ClaimArt';n['name']='ClaimArt';n['comps']['sprite']['frame']='btn_claim'
        self.assertEqual([],self.inspect(d)['problems'])

    def test_progress_and_tiled_assets_not_forced_to_reward_card_rules(self):
        for frame in ('progress_bg','bar','meter_fill'):
            d=fixture();d['nodes'][1]['comps']['sprite'].update(frame=frame,inner=[.14,.2,.72,.001])
            self.assertEqual([],self.inspect(d)['problems'])
        d=fixture();d['nodes'][1]['comps']['sprite'].update(tiled=True,inner=[.14,.2,.72,.001])
        self.assertEqual([],self.inspect(d)['problems'])

    def test_other_card_and_invisible_content_not_mixed_in(self):
        d=fixture(); n=node('Canvas/Popup/OtherCard/Rewards/Hint',[.1,.1,.9,.9],sprite={'frame':'img_hint'})
        d['nodes'].append(n)
        self.assertEqual([],self.inspect(d)['problems'])
        d['nodes'][3]['active']=False;d['nodes'][3]['comps']['sprite']['frame']='btn_hint'
        self.assertEqual([],self.inspect(d)['problems'])

    def test_read_only_and_ordinary_stretch_and_clarity_rules_unchanged(self):
        d=fixture();before=copy.deepcopy(d);self.inspect(d);self.assertEqual(before,d)
        plain=node('Canvas/Caption',[.1,.1,.2,.1],sprite={
            'frame':'txt_example','frame_size':[400,400],'display_size':[400,80]})
        self.assertTrue(audit.squash_problems([plain],[]))

    def test_existing_page_checker_calls_same_assembly_owner(self):
        d=fixture(); d['nodes'][1]['comps']['sprite']['inner'][3]=.01499
        d['nodes'][3]['comps']['sprite']['frame']='btn_hint'
        with patch.object(audit,'OPTIONAL',{}), patch.object(audit,'CAPTION_FRAMES',['btn_hint']):
            problems,stats=audit.check(d,None)
        self.assertTrue(any(p.startswith('sliced_reward_content_exceeds_inner:') for p in stats['sprite_assembly']['reviews']))
        self.assertTrue(any(p.startswith('reward_button_thumbnail:') for p in problems))
        self.assertIn('sprite_assembly',stats)


    def test_name_alone_cannot_prove_baked_words(self):
        d=fixture();d['nodes'][3]['comps']['sprite']['frame']='btn_star'
        result=self.inspect(d)
        self.assertEqual([],result['problems'])
        self.assertTrue(result['reviews'])
        self.assertFalse(result['measurements'][-1]['caption_confirmed'])

    def test_existing_caption_declaration_confirms_role_mismatch(self):
        d=fixture();d['nodes'][3]['comps']['sprite']['frame']='btn_hint'
        with patch.object(audit,'CAPTION_FRAMES',['btn_hint']):
            result=self.inspect(d)
        self.assertTrue(any(p.startswith('reward_button_thumbnail:') for p in result['problems']))
        self.assertFalse(result['reviews'])

    def test_second_independent_surface_does_not_own_rewards(self):
        d=fixture();d['nodes'].append(node('Canvas/Popup/RewardCard/SecondSurface',
            [.8,.1,.1,.1],sprite={'frame':'panel','sliced':True,'inner':[.81,.11,.01,.01]}))
        result=self.inspect(d)
        self.assertEqual([],result['problems']);self.assertEqual([],result['reviews'])
        self.assertEqual(1,len(result['measurements']))

    def test_positions_and_outer_overflow_measured_without_guessing_design(self):
        d=fixture();d['nodes'][3]['rect'][0]=.88
        result=self.inspect(d)
        self.assertEqual([],result['problems'])
        self.assertTrue(any(p.startswith('reward_content_outside_card:') for p in result['reviews']))
        self.assertTrue(result['measurements'][0]['outer_crossing'])
        self.assertNotEqual('within_measured_center',result['measurements'][0]['status'])

    def test_generic_content_roles_are_reviewed_not_silently_assumed(self):
        d=fixture();d['nodes'][1]['comps']['sprite']['inner'][3]=.01499
        for n in d['nodes']:n['path']=n['path'].replace('/Rewards/','/Contents/')
        result=self.inspect(d)
        self.assertEqual([],result['problems'])
        self.assertTrue(any(p.startswith('reward_content_role_unresolved:') for p in result['reviews']))
        self.assertTrue(any(p.startswith('sliced_reward_content_exceeds_inner:') for p in result['reviews']))

    def test_visual_review_carrier_preserves_origin_and_separates_ratio_advice(self):
        report={'pages':[{'screen':'reward','file':'/original/ui-dump.json',
            'advisories':['low_res: advisory only'],
            'visual_reviews':['sliced_reward_content_exceeds_inner: inspect original']}]}
        self.assertEqual(audit.assembly_visual_reviews(report),[{
            'screen':'reward','file':'/original/ui-dump.json',
            'issue':'sliced_reward_content_exceeds_inner: inspect original'}])


if __name__=='__main__':unittest.main()
