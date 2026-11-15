"""Generic producer/checker contracts; fixtures never stand for a game's acceptance."""
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(os.environ.get('DETECTION_SCRIPTS', Path(__file__).resolve().parent))
sys.path.insert(0, str(HERE))
C = importlib.import_module('audit_copy_quality')
A = importlib.import_module('art_check')
R = importlib.import_module('audit_page_richness')
P = importlib.import_module('page_registry')
B = importlib.import_module('audit_bitmap_letter_fonts')


class Contracts(unittest.TestCase):
    def test_clipping_does_not_reduce_the_measured_font_size(self):
        node = {'screen': [0, 0, .2, .02], 'unclipped_screen': [0, -.02, .2, .04],
                'comps': {'label': {'height': 40, 'fontSize': 20}}}
        self.assertEqual(R.font_css_size({'canvas_css': [0, 0, 375, 1000]}, node), 20)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='shared UI contracts ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root/'assets/fonts').mkdir(parents=True)
        (self.root/'docs/logic').mkdir(parents=True)
        self.original = (copy.deepcopy(R.SPRITE_ART_SOURCES), copy.deepcopy(R.GENERATED_TEXT_SOURCES),
                         copy.deepcopy(getattr(R,'GLYPH_ART_SOURCES',{})), list(R.CAPTION_FRAMES))
        self.addCleanup(self.restore)

    def restore(self):
        R.SPRITE_ART_SOURCES,R.GENERATED_TEXT_SOURCES,R.GLYPH_ART_SOURCES,R.CAPTION_FRAMES=self.original

    def glossary(self, terms):
        p=self.root/'glossary.json';p.write_text(json.dumps({'terms':terms}));return p

    def test_mapping_glossary_keeps_banned_terms(self):
        self.assertEqual(C.read_glossary(self.glossary({'Coins':['Gold']}))['terms'],{'Coins':['Gold']})

    def test_historical_term_records_keep_variants(self):
        p=self.glossary([{'zh':'金币','en':'Coins','purpose':'HUD','banned':['Gold']},
                         {'canonical':'Energy','variants':['Strength']}])
        self.assertEqual(C.read_glossary(p)['terms'],{'Coins':['Gold'],'Energy':['Strength']})

    def test_unknown_terms_list_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError,'terms\\[0\\]'):
            C.read_glossary(self.glossary(['Coins']))

    def test_string_variants_are_not_iterated_character_by_character(self):
        with self.assertRaisesRegex(ValueError,'banned variants'):
            C.read_glossary(self.glossary({'Coins':'Gold'}))

    def test_copy_cli_returns_structured_error_for_bad_glossary(self):
        p=subprocess.run([sys.executable,'-B',str(HERE/'audit_copy_quality.py'),'--project',str(self.root),
                          '--glossary',str(self.glossary(['Coins']))],capture_output=True,text=True)
        self.assertEqual(p.returncode,2,p.stdout+p.stderr)
        report=json.loads(p.stdout);self.assertEqual(report['status'],'error')
        self.assertIn('terms[0]',report['error']);self.assertNotIn('Traceback',p.stderr)

    def test_failed_child_does_not_say_passed(self):
        detail=A.subcheck_detail(2,{'error':'terms must be an object'},'通过',output='')
        self.assertIn('terms must be an object',detail);self.assertNotEqual(detail,'通过')
        self.assertEqual(A.subcheck_detail(0,{},'通过'),'通过')

    def pages(self):
        return {'schema':'pages.v1','pages':[{'id':'home','name':'Home','kind':'home','node':'Canvas/Home'},
            {'id':'level','name':'Level','kind':'gameplay','pause':{'none':'no pause in this fixture'}}],
            'not_reachable':[{'prefab':'MoreGameLayer','why':'removed old promotional route'}],
            'text_not_shown':[{'text':'Legacy text','why':'replaced by complete word art'}]}

    def test_page_scope_is_generated_from_the_same_source(self):
        doc=self.pages();self.assertEqual(P.validate(doc),[])
        screens=P.screens_doc(doc,'source-sha')
        self.assertEqual(screens['not_reachable'],doc['not_reachable'])
        self.assertEqual(screens['text_not_shown'],doc['text_not_shown'])
        self.assertFalse(screens['runtime_verified'])

    def test_scope_needs_a_concrete_reason(self):
        doc=self.pages();doc['not_reachable'][0].pop('why')
        self.assertTrue(any('not_reachable' in e for e in P.validate(doc)))

    def runtime(self, nodes):
        return {'screen':'home','purpose':'home','nodes':nodes,'art_capture_id':'sealed-origin'}

    def node(self, name='Body', text='Changes are saved automatically.', **extra):
        n={'name':name,'path':'Canvas/Popup/'+name,'order':5,'opacity':1,'rect':[.2,.2,.6,.05],
           'ui_role':'body_text','ui_role_source':'GameUIKit',
           'comps':{'label':{'string':text,'font':'BodyFont','font_kind':'ttf','fontSize':18,'color':[230,180,200],
                             'system_font':False,'bold':False}}}
        n.update(extra);return n

    def test_short_complete_body_is_not_a_fixed_word(self):
        n=self.node();self.assertTrue(R.produced_body_text(n,[n],[]))
        found=R.text_problems({'_file':str(self.root/'dump.json'),'canvas_css':[0,0,375,667]},[n],[],None)
        self.assertFalse(any(x.startswith(('font_text:','plain_text:')) for x in found),found)

    def test_body_role_does_not_waive_dark_fill(self):
        n=self.node();n['comps']['label'].update(color=[60,35,60],fontSize=32)
        found=R.text_problems({'_file':str(self.root/'dump.json'),'canvas_css':[0,0,375,667]},[n],[],None)
        self.assertTrue(any(x.startswith('dark_bold_text:') for x in found),found)

    def test_actual_css_controls_size_rule_not_design_font_size(self):
        n=self.node();n['comps']['label'].update(color=[60,35,60],fontSize=30,height=60)
        n['rect']=[.2,.2,.6,30/667]
        d={'_file':str(self.root/'dump.json'),'canvas_css':[0,0,375,667]}
        self.assertAlmostEqual(R.font_css_size(d,n),15)
        self.assertFalse(any(x.startswith('dark_bold_text:') for x in R.text_problems(d,[n],[],None)))
        n['rect'][3]=32/667
        self.assertTrue(any(x.startswith('dark_bold_text:') for x in R.text_problems(d,[n],[],None)))
        n['rect'][3]=30/667;n['comps']['label']['bold']=True
        self.assertTrue(any(x.startswith('dark_bold_text:') for x in R.text_problems(d,[n],[],None)))

    def test_button_and_missing_producer_cannot_claim_body_exception(self):
        n=self.node();b={'name':'Button','path':'Canvas/Popup','comps':{'button':{}},'rect':[0,0,1,1]}
        self.assertFalse(R.produced_body_text(n,[b,n],[b]))
        n.pop('ui_role_source');self.assertFalse(R.produced_body_text(n,[n],[]))

    def test_short_fixed_name_still_requires_art(self):
        n=self.node(text='Vanilla Garden');self.assertFalse(R.produced_body_text(n,[n],[]))
        self.assertTrue(any(x.startswith('font_text:') for x in R.text_problems({'_file':str(self.root/'dump.json'),'canvas_css':[0,0,375,667]},[n],[],None)))

    def test_claim_role_needs_actual_button(self):
        n=self.node('Action',text='');n.update(ui_role='result_claim_link');n['comps']={'button':{'enabled':True}}
        self.assertTrue(R.is_claim_link(n,[n]))
        n['comps']={};self.assertFalse(R.is_claim_link(n,[n]))

    def test_claim_visual_geometry_ignores_large_transparent_hit_area(self):
        double={'name':'BtnDouble','path':'Canvas/Double','rect':[.1,.2,.8,.1],'comps':{'button':{}}}
        link={'name':'LinkClaim','path':'Canvas/LinkClaim','rect':[.1,.32,.8,.1],'comps':{'button':{}}}
        word={'name':'Word','path':'Canvas/LinkClaim/Word','rect':[.4,.35,.2,.025],'comps':{'sprite':{'frame':'txt_claim'}}}
        self.assertEqual(R.result_claim_problems([double,link],lambda b:b['name'],[double,link,word]),[])
        word['comps']['sprite']['frame']='btn_claim';R.CAPTION_FRAMES=['btn_claim']
        self.assertTrue(any('whole button plate' in x for x in R.result_claim_problems([double,link],lambda b:b['name'],[double,link,word])))

    def test_formal_collector_exports_producer_roles_and_actual_glyph_rect_in_both_apis(self):
        for api in ('2','3'):
            p=subprocess.run(['node',str(HERE/'test_ui_dump_mock.js'),api,'semantic_roles'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);d=json.loads(p.stdout)
            nodes={n['name']:n for n in d['nodes']}
            self.assertEqual(nodes['Body']['ui_role'],'body_text')
            self.assertNotIn('ui_role',nodes['UnverifiedRole'])
            sprite=nodes['Glyph']['comps']['sprite']
            self.assertEqual(sprite['source_font_uuid'],'font-1')
            self.assertEqual(sprite['source_glyph_code'],48)
            self.assertEqual(sprite['source_glyph_rect'],[4,8,10,20])

    def test_unverified_original_page_does_not_become_seen(self):
        doc=self.pages();folder=self.root/'captures';folder.mkdir()
        (folder/'capture-ui-dump-home.json').write_text(json.dumps(self.runtime([
            {'path':'Canvas/Home','rect':[0,0,1,1],'comps':{'sprite':{'frame':'home'}}}])))
        self.assertEqual(P.verified_page_observations(self.root,folder,doc),({},[]))

    def test_verified_exact_root_counts_but_hidden_and_ambiguous_do_not(self):
        from art_capture_history import digest
        doc=self.pages();folder=self.root/'captures';folder.mkdir()
        store=self.root/'.tiktok-kit/art-rounds';(store/'snapshots').mkdir(parents=True)
        snap={'build':str(self.root/'web'),'project':str(self.root)};version=digest(snap)
        (store/'current.json').write_text(json.dumps({'version':version}))
        (store/'snapshots'/(version+'.json')).write_text(json.dumps(snap))
        dump=folder/'capture-ui-dump-home.json'
        root={'path':'Canvas/Home','rect':[0,0,1,1],'comps':{'sprite':{'frame':'home'}}}
        with patch('art_round_check.run',return_value={'ready':True,'resolved_dumps':[str(dump)]}):
            dump.write_text(json.dumps(self.runtime([root])))
            self.assertIn('home',P.verified_page_observations(self.root,folder,doc)[0])
            dump.write_text(json.dumps(self.runtime([dict(root,opacity=0)])))
            self.assertEqual(P.verified_page_observations(self.root,folder,doc)[0],{})
            dump.write_text(json.dumps(self.runtime([root,root])))
            self.assertEqual(P.verified_page_observations(self.root,folder,doc)[0],{})

    def mask(self, opacity=1):
        return {'name':'Mask','path':'Canvas/Mask','rect':[0,0,1,1],'order':8,'opacity':opacity,
                'comps':{'block_input':True,'sprite':{'frame':'opaque','filled':False}}}

    def test_sem_transparent_blocker_keeps_underlay(self):
        from PIL import Image
        image=self.root/'opaque.png';Image.new('RGBA',(2,2),'white').save(image)
        R.SPRITE_ART_SOURCES={'opaque':{'path':image}}
        self.assertEqual(R.modal_masks([self.mask(.6)]),[])

    def test_true_opaque_source_can_hide_lower_node(self):
        from PIL import Image
        image=self.root/'opaque.png';Image.new('RGBA',(2,2),'white').save(image)
        R.SPRITE_ART_SOURCES={'opaque':{'path':image}}
        masks=R.modal_masks([self.mask()]);self.assertEqual(len(masks),1)
        self.assertTrue(R.fully_occluded({'rect':[.2,.2,.1,.1],'order':1},masks))
        self.assertFalse(R.fully_occluded({'rect':[.2,.2,.1,.1],'order':9},masks))

    def test_holes_filled_sprite_and_unknown_graphics_cannot_hide_underlay(self):
        from PIL import Image
        image=self.root/'holes.png';im=Image.new('RGBA',(2,2),'white');im.putpixel((0,0),(0,0,0,0));im.save(image)
        R.SPRITE_ART_SOURCES={'opaque':{'path':image}}
        self.assertEqual(R.modal_masks([self.mask()]),[])
        im=Image.new('RGBA',(2,2),'white');im.save(image)
        m=self.mask();m['comps']['sprite']['filled']=True
        self.assertEqual(R.modal_masks([m]),[])
        m['comps']={'block_input':True,'graphics':{'fillColor':[0,0,0,255]}}
        self.assertEqual(R.modal_masks([m]),[])

    def font(self, extra):
        path=self.root/'assets/fonts/numeric.fnt';chars='0123456789'+extra
        rows=['info face="numbers" size=32','common lineHeight=40','page id=0 file="numbers.png"']
        for i,char in enumerate(chars):
            x=400 if char in 'xX×' else i*12
            rows.append('char id=%d x=%d y=0 width=10 height=20 page=0' % (ord(char),x))
        path.write_text('\n'.join(rows));Path(str(path)+'.meta').write_text('{"uuid":"font-1"}')
        (self.root/'docs/english').mkdir(exist_ok=True)
        (self.root/'docs/english/charset.json').write_text(json.dumps({'value_charset':chars,
            'fonts':[{'font':'assets/fonts/numeric.fnt','has':chars}]}))
        return path

    def test_numeric_units_and_proven_multiplication_alias_pass(self):
        self.font('BKMxX×');self.assertTrue(B.audit(self.root)['passed'],B.audit(self.root))

    def test_arbitrary_letter_alias_is_not_a_numeric_exception(self):
        path=self.font('BKMxXaA')
        path.write_text(path.read_text().replace('id=97 x=204','id=97 x=216'))
        report=B.audit(self.root)
        self.assertFalse(report['passed'])

    def test_same_x_X_without_real_times_glyph_is_not_exempt(self):
        self.font('BKMxX');report=B.audit(self.root)
        self.assertIn('letter_case_alias',{x['kind'] for x in report['findings']})

    def test_dynamic_glyph_source_needs_real_font_identity_and_rect(self):
        path=self.font('×')
        from PIL import Image
        Image.new('RGBA',(512,32),'white').save(path.parent/'numbers.png')
        R.GLYPH_ART_SOURCES=R.load_glyph_sources(self.root)
        n={'comps':{'sprite':{'source_font_uuid':'font-1','source_glyph_code':48,
                             'source_glyph_rect':[0,0,10,20],'frame_size':[10,20]}}}
        self.assertIsNotNone(R.generated_source(n))
        n['comps']['sprite']['source_glyph_rect']=[2,0,10,20]
        self.assertIsNone(R.generated_source(n))

    def test_whole_button_without_glyph_mask_cannot_falsely_prove_text_colour(self):
        from PIL import Image
        dump=self.root/'dump.json';dump.write_text('{}');Image.new('RGB',(100,100),(255,220,100)).save(self.root/'shot.png')
        d={'_file':str(dump),'screenshot':'shot.png'}
        R.CAPTION_FRAMES=['btn_play']
        button={'name':'Play','path':'Canvas/Play','rect':[0,0,1,1],'comps':{'sprite':{'frame':'btn_play'}}}
        groups,_,unknown=R.colour_samples(d,[button],Image)
        self.assertEqual(groups,{});self.assertEqual(unknown,['Canvas/Play'])


if __name__=='__main__':
    unittest.main(verbosity=2)
