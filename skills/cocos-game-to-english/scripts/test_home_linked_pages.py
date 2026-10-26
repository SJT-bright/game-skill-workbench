"""Behavioral contracts for optional HOME-linked runtime page annotations."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from extract_ui_layout import build

class LinkedPages(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def dump(self,screen,kind,width=390,height=844,dpr=1,buttons=True):
        nodes=[{'name':'BtnShortcut','path':'Canvas/BtnShortcut','rect':[.1,.2,.2,.1],
                'comps':{'button':{},'sprite':{'frame':'icon_home'}}}] if buttons else []
        p=self.root/(screen+'-'+str(width)+'-'+str(dpr)+'-ui-dump.json')
        p.write_text(json.dumps({'tool':'ui_dump','screen':screen,'kind':kind,'page':{'width':width,'height':height,'dpr':dpr},'canvas_css':[0,0,width,height],'nodes':nodes}))
        return p
    def extract(self,linked=None,other=None,empty=False):
        home=self.dump('home','home',buttons=False);page=self.dump('profile','page',buttons=not empty,**(other or {}));args=None
        if linked is not None:
            args=self.root/'overrides.json';args.write_text(json.dumps({'home_entry_pages':linked}))
        result=build([home,page],args)
        return next(s for s in result['screens'] if s.get('role')=='home'),page
    def test_no_implicit_borrowing(self):
        home,_=self.extract();self.assertNotIn('entry_names',home)
    def test_declared_matching_page_uses_runtime_button_and_hash(self):
        home,page=self.extract(['profile']);self.assertEqual(home['entry_names'],['Canvas/BtnShortcut'])
        source=home['home_entry_sources'][0];self.assertEqual(source['screen'],'profile')
        self.assertEqual(source['source_dump']['sha256'],hashlib.sha256(page.read_bytes()).hexdigest())
    def test_same_framebuffer_different_css_is_not_borrowed(self):
        home,_=self.extract(['profile'],{'width':195,'height':422,'dpr':2});self.assertNotIn('entry_names',home)
    def test_different_dpr_is_not_borrowed(self):
        home,_=self.extract(['profile'],{'dpr':2});self.assertNotIn('entry_names',home)
    def test_empty_dump_does_not_fabricate_entry(self):
        home,_=self.extract(['profile'],empty=True);self.assertNotIn('entry_names',home)
    def test_unknown_dump_rejected(self):
        with self.assertRaisesRegex(ValueError,'no runtime dump'):self.extract(['missing'])
    def test_invalid_annotation_rejected(self):
        for value in ['profile',[None],[''],['profile','profile']]:
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'home_entry_pages'):self.extract(value)

if __name__=='__main__':unittest.main()
