"""Synthetic consumer/negative controls, never game runtime evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
import audit_page_richness as richness
import official_loading as loading

HERE = Path(__file__).resolve().parent


class LoadingConsumers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='loading consumers ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'game'
        (self.project / 'assets').mkdir(parents=True)
        self.dumps = self.project / 'docs/test'
        self.dumps.mkdir(parents=True)
        (self.project / 'docs/art').mkdir()
        self.logo = self.project / 'assets/official.png'
        vendor = Path('/Applications/Cocos/Creator/2.4.15/CocosCreator.app/Contents/Resources/static/build-templates/shares/splash.png')
        if vendor.exists():
            self.logo.write_bytes(vendor.read_bytes())
        else:
            # Portable tests isolate matching behavior without registering a fake
            # production logo. The real catalog is tested when Creator is present.
            im = Image.new('RGBA', (547, 200));dr = ImageDraw.Draw(im)
            dr.rectangle((10, 45, 530, 155), fill=(40, 180, 240, 255));im.save(self.logo)
            catalog = self.root / 'test-only-catalog.json'
            catalog.write_text(json.dumps({'assets': [{'creator_versions': ['2.4.15'], 'sha256': loading.sha(self.logo), 'size': [547, 200]}]}))
            self.patch = patch.object(loading, 'CATALOG', catalog);self.patch.start();self.addCleanup(self.patch.stop)
        self.source = self.project / 'assets/loading.js'
        self.source.write_text('// Synthetic loader source fixture, not a game run.\n')
        self.data = []
        self.manifest = {'schema': 1, 'source_files': {'assets/official.png': loading.sha(self.logo), 'assets/loading.js': loading.sha(self.source)}, 'frames': []}
        self.screens = {'runtime_verified': True, 'screens': [{'id': 'wait', 'name': 'Loading'}, {'id': 'retry', 'name': 'Retry'}],
                        'required_viewports': [{'name': 'tall', 'width': 390, 'height': 844}, {'name': 'short', 'width': 360, 'height': 640}]}
        (self.project / 'docs/art/screens.json').write_text(json.dumps(self.screens))
        for phase, screen in [('engine_resources', 'wait'), ('retry', 'retry')]:
            for vp in self.screens['required_viewports']:
                width, height = vp['width'], vp['height']
                shot = self.dumps / f'{screen}-{width}.png'
                image = Image.new('RGB', (width, height), (23, 23, 23))
                logo = Image.open(self.logo).convert('RGBA').resize((164, 60), Image.Resampling.BILINEAR)
                image.paste(logo, (width//2-82, height//2-30), logo)
                dr = ImageDraw.Draw(image)
                label = 'Retry' if phase == 'retry' else 'Loading...'
                dr.text((width//2-25, round(height*.65)), label, fill=(255,255,255))
                image.save(shot)
                def node(path, rect, comps):
                    return {'path': path, 'name': path.rsplit('/',1)[-1], 'rect': rect, 'screen': rect, 'opacity': 1, 'comps': comps}
                text = node('Canvas/Status', [.3, .65, .4, .03], {'label': {'string': label, 'fontSize': 12, 'height': .03*height, 'color': [255,255,255]}})
                if phase == 'retry':text['comps']['button'] = {'interactable': True, 'enabled': True}
                d = {'tool': 'ui_dump', 'schema': 1, 'producer': 'chrome_touch.dump_ui', 'engine': '2.4.15',
                     'screen': screen, 'kind': 'page', 'purpose': 'other', 'viewport': vp, 'page': {'dpr': 1, 'width': width, 'height': height},
                     'canvas_css': [0,0,width,height], 'screenshot': shot.name, 'nodes': [
                         node('Canvas',[0,0,1,1],{}), node('Canvas/Bg',[0,0,1,1],{'graphics': {'fillColor': [23,23,23,255]}}),
                         node('Canvas/Logo',[(width/2-82)/width,(height/2-30)/height,164/width,60/height],
                              {'sprite': {'frame': 'cocos_official_logo', 'frame_size': [547,200], 'display_size': [164,60], 'css_display_size': [164,60]}}), text]}
                path = self.dumps / f'{screen}-ui-dump-{width}.json'
                path.write_text(json.dumps(d));d['_file'] = str(path);self.data.append(d)
                self.manifest['frames'].append({'dump': path.relative_to(self.project).as_posix(), 'dump_sha256': loading.sha(path),
                    'screenshot': shot.relative_to(self.project).as_posix(), 'screenshot_sha256': loading.sha(shot), 'screen': screen,
                    'viewport': [width,height], 'phase': phase, 'logo_node': 'Canvas/Logo', 'logo_asset': 'assets/official.png', 'creator_version': '2.4.15'})
        self.save()

    def save(self):
        (self.project / loading.MANIFEST).write_text(json.dumps(self.manifest))

    def refresh(self, d, screenshot=False):
        path = Path(d['_file']);path.write_text(json.dumps({k:v for k,v in d.items() if k != '_file'}))
        row = next(r for r in self.manifest['frames'] if loading.inside(self.project,r['dump']) == path.resolve())
        row['dump_sha256'] = loading.sha(path)
        if screenshot:row['screenshot_sha256'] = loading.sha(loading.screenshot(d))
        self.save()

    def errors(self, d=None):
        return richness.check(d or self.data[0], Image, self.project)[0]

    def cli(self, command):
        result = subprocess.run([sys.executable, '-B', *command], capture_output=True, text=True, timeout=120)
        return result

    def test_normal_and_retry_pass_real_page_consumer(self):
        for d in self.data:
            with self.subTest(screen=d['screen'],vp=d['viewport']):self.assertEqual(self.errors(d), [])

    def test_original_dark_cli_rejects_but_contextual_cli_accepts_actual_default_frame(self):
        image = str(loading.screenshot(self.data[0]))
        before = self.cli([str(HERE/'audit_dark_area.py'),image]);self.assertEqual(before.returncode,1)
        result = self.cli([str(HERE/'audit_dark_area.py'),image,'--project',str(self.project),'--dumps',str(self.dumps)])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_actual_affected_art_entry_closes_both_consumers(self):
        out = self.root / 'review'
        result = self.cli([str(HERE/'art_check.py'),'--loading-only','--project',str(self.project),'--dumps',str(self.dumps),'--out',str(out)])
        if not Path('/Applications/Cocos/Creator/2.4.15').exists():self.skipTest('subprocess needs installed official asset for the real unpatched catalog')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report = json.loads((out/'loading-presentation.json').read_text())
        self.assertTrue(report['passed']);self.assertEqual(report['checked'],4)
        self.assertEqual(report['tool'],'audit_official_loading');self.assertEqual(report['stage'],'presentation')
        dark = json.loads((out/'loading-presentation-dark.json').read_text());self.assertTrue(dark['passed'])

    def test_ordinary_home_or_gameplay_cannot_relabel_itself(self):
        d=self.data[0]
        for kind,purpose in [('home','home'),('gameplay','other'),('popup','other'),('page','home')]:
            d.update(kind=kind,purpose=purpose);self.refresh(d)
            self.assertTrue(self.errors(d))

    def test_name_or_flag_alone_never_exempts(self):
        (self.project/loading.MANIFEST).unlink()
        d=self.data[0];d['official_loading']=True
        self.assertTrue(self.errors(d))
        del d['official_loading'];d['screen']='loading'
        problems=richness.check(d,Image,None)[0]
        self.assertTrue(any(p.startswith('flat_background:') for p in problems))

    def test_missing_or_forged_official_logo_refused(self):
        for fake in [b'not an image',b'fake official branding']:
            self.logo.write_bytes(fake)
            self.manifest['source_files']['assets/official.png']=loading.sha(self.logo);self.save()
            self.assertTrue(self.errors())

    def test_current_source_dump_screenshot_and_binding_are_bound(self):
        self.source.write_text('changed');self.assertTrue(self.errors())
        self.source.write_text('// Synthetic loader source fixture, not a game run.\n')
        d=self.data[0];d['screen']='other';self.assertTrue(self.errors(d))
        d['screen']='wait';self.assertTrue(loading.audit(d,self.project,Image,{'build_tag':'new'})[0])
        shot=loading.screenshot(d);shot.write_bytes(b'changed capture');self.assertTrue(self.errors(d))

    def test_correct_asset_but_missing_or_modified_logo_pixels_refused(self):
        d=self.data[0];im=Image.open(loading.screenshot(d)).convert('RGB');ImageDraw.Draw(im).rectangle((110,380,280,460),fill=(23,23,23));im.save(loading.screenshot(d));self.refresh(d,True)
        self.assertTrue(any('unmodified original' in p for p in self.errors(d)))

    def test_actual_logo_stretch_clip_or_low_resolution_refused(self):
        d=self.data[0]
        logo=d['nodes'][2]
        logo['rect'][2]*=1.5;logo['screen']=logo['rect'];self.refresh(d)
        self.assertTrue(self.errors(d))
        logo['rect'][0]=-.01;self.refresh(d);self.assertTrue(self.errors(d))
        # Actually enlarge the rendered logo, not just a stale design-size field.
        logo['rect']=[45/390,367/844,300/390,110/844];logo['screen']=logo['rect']
        logo['comps']['sprite']['display_size']=[300,110];logo['comps']['sprite']['css_display_size']=[300,110]
        im=Image.new('RGB',(390,844),(23,23,23));source=Image.open(self.logo).convert('RGBA').resize((300,110),Image.Resampling.BILINEAR);im.paste(source,(45,367),source)
        ImageDraw.Draw(im).text((170,round(844*.65)),'Loading...',fill=(255,255,255));im.save(loading.screenshot(d));self.refresh(d,True)
        self.assertTrue(any(p.startswith('low_res:') for p in self.errors(d)),self.errors(d))

    def test_game_picture_story_or_omitted_pixels_not_waived(self):
        d=self.data[0];extra=copy.deepcopy(d['nodes'][2]);extra['path']='Canvas/Character';extra['comps']['sprite']['frame']='hero';d['nodes'].append(extra);self.refresh(d)
        self.assertTrue(self.errors(d));d['nodes'].pop()
        d['nodes'][-1]['comps']['label']['string']='My wonderful game';self.refresh(d);self.assertTrue(self.errors(d))
        d['nodes'][-1]['comps']['label']['string']='Loading...';im=Image.open(loading.screenshot(d)).convert('RGB');ImageDraw.Draw(im).rectangle((10,10,45,45),fill=(255,20,20));im.save(loading.screenshot(d));self.refresh(d,True);self.assertTrue(self.errors(d))

    def test_inoperable_retry_or_missing_ratio_stays_blocking(self):
        d=self.data[2];d['nodes'][-1]['comps']['button']['interactable']=False;self.refresh(d);self.assertTrue(self.errors(d))
        if not Path('/Applications/Cocos/Creator/2.4.15').exists():return
        out=self.root/'failed.json';r=self.cli([str(HERE/'audit_official_loading.py'),'--project',str(self.project),'--dumps',str(self.dumps),'--out',str(out)])
        self.assertNotEqual(r.returncode,0);self.assertFalse(json.loads(out.read_text())['passed'])

    def test_dom_preengine_capture_reaches_actual_pixel_and_page_check(self):
        result=subprocess.run(['node',str(HERE/'test_official_loading_dom.cjs'),'--dump'],capture_output=True,text=True,check=True)
        d=json.loads(result.stdout);base=self.data[0]
        for key in ['screen','kind','purpose','viewport','screenshot','producer']:
            d[key]=base[key]
        d['_file']=base['_file']
        row=self.manifest['frames'][0];row['phase']='cold_start';row['logo_node']='DOMLoading/Logo'
        logo=next(n for n in d['nodes'] if n['path']=='DOMLoading/Logo');r=logo['screen']
        box=[round(r[0]*390),round(r[1]*844),round((r[0]+r[2])*390),round((r[1]+r[3])*844)]
        im=Image.new('RGB',(390,844),(23,23,23));source=Image.open(self.logo).convert('RGBA').resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.BILINEAR);im.paste(source,(box[0],box[1]),source)
        ImageDraw.Draw(im).rectangle((109,677,196,680),fill=(61,197,222));im.save(loading.screenshot(d));self.refresh(d,True)
        self.assertEqual(self.errors(d),[])

    def test_evidence_writer_uses_real_captures_and_leaves_old_manifest_on_failure(self):
        if not Path('/Applications/Cocos/Creator/2.4.15').exists():self.skipTest('real unpatched subprocess catalog')
        target=self.project/loading.MANIFEST;before=target.read_bytes()
        cmd=[str(HERE/'official_loading.py'),'--project',str(self.project),'--dump',str(Path(self.data[0]['_file'])),
             '--logo-node','Canvas/Logo','--logo-asset','assets/official.png','--creator-version','2.4.15',
             '--phase','engine_resources','--source-file','assets/loading.js']
        r=self.cli(cmd);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        current=target.read_bytes();self.source.write_text('changed renderer')
        r=self.cli(cmd);self.assertNotEqual(r.returncode,0);self.assertEqual(target.read_bytes(),current)
        # A new capture set drops old frames and archives its exact bytes, not a pass relabel.
        r=self.cli(cmd+['--new-capture-set']);self.assertNotEqual(r.returncode,0);self.assertEqual(target.read_bytes(),current)
        # A distinct synthetic capture models the real producer's fresh t_ms.
        # Production use must recapture; the writer never edits a dump timestamp.
        d=self.data[0];d['t_ms']=123456
        Path(d['_file']).write_text(json.dumps({k:v for k,v in d.items() if k!='_file'}))
        r=self.cli(cmd+['--new-capture-set']);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(len(json.loads(target.read_text())['frames']),1)
        self.assertTrue(any(p.read_bytes()==current for p in target.parent.glob('official-loading-*.json')))

    def test_pure_fullscreen_progress_does_not_hide_extra_game_pixels(self):
        d=self.data[0];d['nodes'].append({'path':'Canvas/FakeProgress','name':'FakeProgress','opacity':1,'rect':[0,0,1,1],'screen':[0,0,1,1],'comps':{'progress':{'value':0.5}}})
        im=Image.open(loading.screenshot(d)).convert('RGB');ImageDraw.Draw(im).rectangle((10,10,45,45),fill=(255,20,20));im.save(loading.screenshot(d));self.refresh(d,True)
        self.assertTrue(any('unaccounted content' in p for p in self.errors(d)))

    def test_picture_inside_standard_text_box_is_refused(self):
        d=self.data[0];im=Image.open(loading.screenshot(d)).convert('RGB');ImageDraw.Draw(im).rectangle((125,550,150,562),fill=(250,30,20));im.save(loading.screenshot(d));self.refresh(d,True)
        self.assertTrue(any('non-text/game pixels' in p for p in self.errors(d)))

    def test_entire_declared_loading_state_cannot_be_omitted(self):
        if not Path('/Applications/Cocos/Creator/2.4.15').exists():self.skipTest('real unpatched subprocess catalog')
        self.screens['screens'].append({'id':'scene-load','name':'Scene loading','purpose':'loading'})
        (self.project/'docs/art/screens.json').write_text(json.dumps(self.screens))
        out=self.root/'missing-state.json';result=self.cli([str(HERE/'audit_official_loading.py'),'--project',str(self.project),'--dumps',str(self.dumps),'--out',str(out)])
        self.assertNotEqual(result.returncode,0);self.assertIn('scene-load',out.read_text())

    def test_creator3_original_asset_and_dpr2_keep_same_criteria(self):
        vendor=Path('/Applications/Cocos/Creator/3.8.8/CocosCreator.app/Contents/Resources/app.asar.unpacked/builtin/builder/static/logo/logo.png')
        if not vendor.exists():self.skipTest('real Creator3 original asset not installed')
        self.logo.write_bytes(vendor.read_bytes());self.manifest['source_files']['assets/official.png']=loading.sha(self.logo)
        for row,d in zip(self.manifest['frames'],self.data):
            row['creator_version']='3.8.8';d['engine']='3.8.8';d['page']['dpr']=2
            width,height=d['viewport']['width'],d['viewport']['height'];logo=d['nodes'][2]
            logo['rect']=[(width/2-28)/width,(height/2-40)/height,56/width,80/height];logo['screen']=logo['rect']
            logo['comps']['sprite'].update(frame_size=[140,200],display_size=[56,80],css_display_size=[56,80])
            im=Image.new('RGB',(width*2,height*2),(23,23,23));source=Image.open(self.logo).convert('RGBA').resize((112,160),Image.Resampling.BILINEAR);im.paste(source,(width-56,height-80),source)
            label=Image.new('RGBA',(width,height));ImageDraw.Draw(label).text((width//2-25,round(height*.65)),d['nodes'][-1]['comps']['label']['string'],fill=(255,255,255,255))
            label=label.resize(im.size,Image.Resampling.BILINEAR);im.paste(label,(0,0),label);im.save(loading.screenshot(d));self.refresh(d,True)
        with patch.object(loading,'CATALOG',HERE/'official_loading_assets.json'):
            for d in self.data:self.assertEqual(self.errors(d),[])

    def test_cocos_progress_metadata_stays_local_to_loading_audit(self):
        d=self.data[0];d['nodes']=d['nodes'][:3]
        d['nodes'].append({'path':'Canvas/Progress','name':'Progress','opacity':1,'rect':[.27,.7,.45,.02],'screen':[.27,.7,.45,.02],'comps':{},'loading_progress':{'value':.5}})
        d['nodes'].append({'path':'Canvas/Progress/Fill','name':'Fill','opacity':1,'rect':[110/390,600/844,88/390,5/844],'screen':[110/390,600/844,88/390,5/844],'comps':{'graphics':{'fillColor':[61,197,222,255]}}})
        im=Image.new('RGB',(390,844),(23,23,23));source=Image.open(self.logo).convert('RGBA').resize((164,60),Image.Resampling.BILINEAR);im.paste(source,(113,392),source)
        ImageDraw.Draw(im).rectangle((110,600,197,604),fill=(61,197,222));im.save(loading.screenshot(d));self.refresh(d,True)
        self.assertEqual(self.errors(d),[])
        self.assertNotIn('progress',d['nodes'][3]['comps'])

    def test_existing_pillow_constant_api_remains_supported(self):
        class LegacyImage:
            def __getattr__(self,name):
                if name=='Resampling':raise AttributeError(name)
                return getattr(Image,name)
        for d in self.data:
            self.assertEqual(richness.check(d,LegacyImage(),self.project)[0],[])

    def test_plain_game_capture_retains_original_rejection(self):
        d=copy.deepcopy(self.data[0]);d['kind']='home';d['purpose']='home';d['_file']=str(self.root/'unlisted-ui-dump-home.json')
        problems,stats=richness.check(d,Image,self.project)
        self.assertTrue(problems);self.assertNotIn('official_loading',stats)


if __name__ == '__main__':
    unittest.main()
