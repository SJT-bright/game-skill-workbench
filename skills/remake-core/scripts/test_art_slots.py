from pathlib import Path
import json,tempfile,unittest
from PIL import Image
from audit_art_slots import run

class Capture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.pic=root/'same.png';Image.new('RGB',(100,100),'blue').save(self.pic)
        self.config=root/'slots.json';self.dump=root/'capture.json'
        self.case=dict(id='mail',screen='mail',viewport_width=100,expected_width=100,expected_height=100,
                       owner='card',inside=[.1,.1,.9,.9],children=['card/count'])
        self.nodes=[dict(path='card',screen=[0,0,1,1]),dict(path='card/count',screen=[.2,.2,.5,.5])]
    def run_case(self,screen='mail'):
        self.config.write_text(json.dumps({'cases':[self.case]}))
        self.dump.write_text(json.dumps(dict(screen=screen,viewport={'width':100},nodes=self.nodes,screenshot='same.png')))
        return run(self.config,[self.dump],[self.pic])['passed']
    def test_inside(self):self.assertTrue(self.run_case())
    def test_clipping_must_not_conceal_overflow(self):
        self.nodes[1]['unclipped_screen']=[-.1,.2,.5,.5];self.assertFalse(self.run_case())
    def test_sibling_collision_not_needed_for_failure(self):
        self.nodes[1]['screen']=[.04,.2,.5,.5];self.assertFalse(self.run_case())
    def test_wrong_page(self):self.assertFalse(self.run_case('lobby'))
    def test_duplicate_owner(self):
        self.nodes.append(self.nodes[0]);self.assertFalse(self.run_case())
    def test_missing_rule(self):
        del self.case['inside'];self.assertFalse(self.run_case())
    def test_wrong_resolution(self):
        self.case['expected_width']=200;self.assertFalse(self.run_case())

    def test_icon_title_gap_in_css_pixels(self):
        self.case['horizontal_gap'] = {'left': 'card/icon', 'right': 'card/count', 'min_css_px': 3}
        self.case['expected_width'] = 200
        Image.new('RGB', (200, 100), 'blue').save(self.pic)
        icon = dict(path='card/icon', screen=[.10, .25, .07, .1])
        self.nodes.append(icon)
        self.assertTrue(self.run_case())  # Exactly 3 CSS pixels, 6 screenshot pixels.
        icon['unclipped_screen'] = [.10, .25, .09, .1]
        self.assertFalse(self.run_case())  # Still inside parent, but only 1 CSS pixel.
        icon['unclipped_screen'][2] = .15
        self.assertFalse(self.run_case())
        self.nodes.pop()
        self.assertFalse(self.run_case())

class ExactCaptureCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.case=dict(id='home',screen='home',capture_case='home-phone',viewport_width=100,viewport_height=100,
                       expected_width=100,expected_height=100,owner='card',inside=[0,0,1,1],children=['card/count'])
        self.nodes=[dict(path='card',screen=[0,0,1,1]),dict(path='card/count',screen=[.2,.2,.5,.5])]
        self.config=self.root/'slots.json'
        self.dumps=[];self.shots=[]
        for name in ['home-phone','zz-home-after-win-phone']:
            shot=self.root/(name+'.png');Image.new('RGB',(100,100),'blue').save(shot)
            dump=self.root/('capture-ui-dump-'+name+'.json')
            dump.write_text(json.dumps(dict(screen='home',viewport={'width':100,'height':100},nodes=self.nodes,screenshot=shot.name)))
            self.dumps.append(dump);self.shots.append(shot)
    def result(self):
        self.config.write_text(json.dumps({'cases':[self.case]}))
        return run(self.config,self.dumps,self.shots)
    def test_exact_initial_and_after_win_can_share_page(self):
        self.assertTrue(self.result()['passed'])
        self.case['capture_case']='zz-home-after-win-phone'
        self.assertTrue(self.result()['passed'])
    def test_without_selector_remains_ambiguous(self):
        self.case.pop('capture_case');self.assertFalse(self.result()['passed'])
    def test_missing_case_and_mismatched_attachment_fail(self):
        self.case['capture_case']='missing';self.assertFalse(self.result()['passed'])
        self.case['capture_case']='home-phone'
        d=json.loads(self.dumps[0].read_text());d['screenshot']=self.shots[1].name
        self.dumps[0].write_text(json.dumps(d));self.assertFalse(self.result()['passed'])
    def test_duplicate_exact_capture_still_fails(self):
        self.dumps.append(self.dumps[0]);self.assertFalse(self.result()['passed'])
    def test_first_piece_uses_same_selector(self):
        from audit_art_slots import first_piece_documents
        self.config.write_text(json.dumps({'cases':[self.case]}))
        docs=[dict(json.loads(p.read_text()),_file=str(p)) for p in self.dumps]
        selected,_,_=first_piece_documents(self.config,docs,['home'])
        self.assertEqual(selected[0]['_file'],str(self.dumps[0]))
        self.case.pop('capture_case');self.config.write_text(json.dumps({'cases':[self.case]}))
        with self.assertRaisesRegex(ValueError,'ambiguous'):first_piece_documents(self.config,docs,['home'])
