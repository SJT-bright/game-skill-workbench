"""Independent CSS design budgets. Geometry fixtures, never browser acceptance evidence."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
import art_production
from audit_art_slots import run, validate_display_budget


class DisplayBudget(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.config=self.root/'visual-slots.json'
        self.case=dict(id='reward-small',screen='reward',viewport_width=390,viewport_height=844,
                       expected_width=780,expected_height=1688,owner='Canvas/Reward',
                       display_budget=dict(unit='css_px',nodes=[dict(path='Canvas/Reward/Video',frame='icon-video',
                           expected_css=[48,48],tolerance_css_px=1,tolerance_ratio=.02)]))
        self.doc=dict(screen='reward',viewport=dict(width=390,height=844),page=dict(width=390,height=844,dpr=2),
                      canvas_css=[20,30,350,780],screenshot='reward.png',nodes=[
                          dict(path='Canvas/Reward',screen=[.05,.05,.9,.9]),
                          dict(path='Canvas/Reward/Video',screen=[.2,.2,48/350,48/780],opacity=1,
                               comps=dict(sprite=dict(frame='icon-video',frame_size=[1024,1024])))])
        self.pic=self.root/'reward.png';self.dump=self.root/'reward.json'
        Image.new('RGB',(780,1688),'navy').save(self.pic)

    def result(self):
        self.config.write_text(json.dumps(dict(cases=[self.case])))
        self.dump.write_text(json.dumps(self.doc))
        return run(self.config,[self.dump],[self.pic])

    def test_normal_high_resolution_letterbox_and_dpr(self):
        row=self.result()['cases'][0]
        self.assertTrue(row['passed'],row)
        self.assertEqual(row['checks'][0]['actual_css'],[48,48])

    def test_proportionally_five_times_larger_stays_crisp_but_fails(self):
        node=self.doc['nodes'][1]
        node['screen'][2:]=[240/350,240/780]
        # Still fits the owner; pixel density and aspect ratio are both healthy.
        result=self.result();self.assertFalse(result['passed'])
        self.assertEqual(result['cases'][0]['checks'][0]['actual_css'],[240,240])

    def test_owner_growth_cannot_raise_budget(self):
        self.doc['nodes'][0]['screen']=[0,0,5,5]
        self.doc['nodes'][1]['screen']=[.1,.1,240/350,240/780]
        self.case.update(inside=[0,0,1,1],children=['Canvas/Reward/Video'])
        row=self.result()['cases'][0]
        self.assertTrue(row['checks'][0]['passed'])
        self.assertFalse(row['checks'][1]['passed'])

    def test_clipped_fragment_does_not_hide_larger_node(self):
        self.doc['nodes'][1]['unclipped_screen']=[.2,.2,240/350,240/780]
        self.assertFalse(self.result()['passed'])

    def test_same_width_two_heights_have_distinct_budgets(self):
        second=copy.deepcopy(self.case);second.update(id='reward-tall',viewport_height=900,expected_height=1800)
        second['display_budget']['nodes'][0]['expected_css']=[52.5,52.5]
        doc=copy.deepcopy(self.doc);doc['viewport']['height']=doc['page']['height']=900
        doc['canvas_css']=[20,30,350,840];doc['screenshot']='tall.png'
        doc['nodes'][1]['screen'][2:]=[52.5/350,52.5/840]
        image=self.root/'tall.png';Image.new('RGB',(780,1800),'navy').save(image)
        dump=self.root/'tall.json';dump.write_text(json.dumps(doc));self.dump.write_text(json.dumps(self.doc))
        self.config.write_text(json.dumps(dict(cases=[self.case,second])))
        self.assertTrue(run(self.config,[self.dump,dump],[self.pic,image])['passed'])

    def test_missing_or_ambiguous_node_and_wrong_frame(self):
        original=copy.deepcopy(self.doc)
        for mutation in ('missing','duplicate','frame','no-frame','no-sprite','no-frame-size'):
            with self.subTest(mutation=mutation):
                self.doc=copy.deepcopy(original)
                if mutation=='missing':self.doc['nodes'].pop()
                elif mutation=='duplicate':self.doc['nodes'].append(copy.deepcopy(self.doc['nodes'][1]))
                elif mutation=='frame':self.doc['nodes'][1]['comps']['sprite']['frame']='other-video'
                elif mutation=='no-frame':del self.doc['nodes'][1]['comps']['sprite']['frame']
                elif mutation=='no-sprite':self.doc['nodes'][1]['comps']={}
                else:del self.doc['nodes'][1]['comps']['sprite']['frame_size']
                self.assertFalse(self.result()['passed'])

    def test_missing_capture_coordinate_metadata(self):
        original=copy.deepcopy(self.doc)
        for key in ('canvas_css','page','viewport'):
            with self.subTest(key=key):
                self.doc=copy.deepcopy(original);del self.doc[key]
                self.assertFalse(self.result()['passed'])
        self.doc=original;self.doc['page']['width']=391
        self.assertFalse(self.result()['passed'])

    def test_hidden_transparent_or_missing_effective_opacity(self):
        original=copy.deepcopy(self.doc)
        for mutation in ('missing','transparent','hidden','sprite-transparent','negative'):
            with self.subTest(mutation=mutation):
                self.doc=copy.deepcopy(original);node=self.doc['nodes'][1]
                if mutation=='missing':del node['opacity']
                elif mutation=='transparent':node['opacity']=0
                elif mutation=='hidden':node['visible']=False
                elif mutation=='negative':node['opacity']=-1
                else:node['comps']['sprite']['alpha']=0
                self.assertFalse(self.result()['passed'])

    def test_missing_invalid_axes_identity_and_tolerance_are_refused(self):
        original=copy.deepcopy(self.case)
        changes=[lambda c:c.pop('viewport_height'),
                 lambda c:c.update(display_budget=None),
                 lambda c:c['display_budget'].update(nodes=[]),
                 lambda c:c['display_budget'].update(unit='source_px')]
        for field,value in [('expected_css',[48]),('expected_css',[48,0]),('expected_css',[48,float('nan')]),
                            ('expected_css',[48,True]),('frame',''),('path',''),('tolerance_css_px',3),
                            ('tolerance_ratio',1),('tolerance_ratio',.5),('tolerance_ratio',float('inf'))]:
            changes.append(lambda c,f=field,v=value:c['display_budget']['nodes'][0].update({f:v}))
        for change in changes:
            self.case=copy.deepcopy(original);change(self.case)
            self.assertFalse(self.result()['passed'])
            with self.assertRaises(ValueError):validate_display_budget(self.case)

    def test_per_axis_tolerance_does_not_conceal_large_or_small_axis(self):
        self.doc['nodes'][1]['screen'][2:]=[48.9/350,47.1/780]
        self.assertTrue(self.result()['passed'])
        self.doc['nodes'][1]['screen'][3]=46/780
        self.assertFalse(self.result()['passed'])

    def test_legacy_case_does_not_require_new_metadata(self):
        del self.case['display_budget'];del self.case['viewport_height']
        self.case.update(inside=[0,0,1,1],children=['Canvas/Reward/Video'])
        del self.doc['page'];del self.doc['canvas_css'];del self.doc['nodes'][1]['comps']
        self.assertTrue(self.result()['passed'])

    def test_production_manifest_binds_budget_and_rejects_bad_new_rule(self):
        source=self.root/'docs/art/source';shutil.copytree(art_production.ART.parent/'examples/fixed-caption',source)
        (self.root/'assets').mkdir();output=self.root/'assets/claim.png'
        command=[sys.executable,'-B',str(art_production.ART/'compose_fixed_button.py'),
                 str(source/'recipe.json'),str(output),'--project',str(self.root),'--asset-id','claim','--cases',self.case['id']]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        manifest=self.root/art_production.MANIFEST;data=json.loads(manifest.read_text())
        data['cases']=[self.case];manifest.write_text(json.dumps(data))
        self.assertTrue(art_production.audit(self.root)['passed'])
        before=art_production.fingerprint(self.root)
        data['cases'][0]['display_budget']['nodes'][0]['expected_css']=[49,49]
        manifest.write_text(json.dumps(data));after=art_production.fingerprint(self.root)
        self.assertNotEqual(before['sha256'],after['sha256'])
        data['cases'][0].update(inside=[0,0,1,1],children=['Canvas/Reward/Video'])
        data['cases'][0]['display_budget']['nodes'][0]['expected_css']=[49]
        manifest.write_text(json.dumps(data))
        self.assertFalse(art_production.audit(self.root)['passed'])
        with self.assertRaises(ValueError):art_production.fingerprint(self.root)


if __name__=='__main__':unittest.main()
