"""Synthetic bad/good fixtures for the v7.9 package-local-file gates in package_gates.network:
H15_package_read_via_request, H16_font_path_as_family, H17_resource_path_missing (block for a new game, warn for a
legacy game). The real Pinecone builds are checked too when their ZIPs are on this machine (skipped otherwise).
Run: python3 -B test_package_gates_local_files.py"""
import json
import os
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
from package_gates import network  # noqa: E402

LOCAL = ('H15_package_read_via_request', 'H16_font_path_as_family', 'H17_resource_path_missing')
RES_CONFIG = {'paths': {'0': ['art/home/bg', 1], '1': ['config/levels', 2], '2': ['fonts/Body', 3],
                        '3': ['art/ui/btn/spriteFrame', 4]}, 'scenes': {}, 'name': 'resources'}
EXTRA_CONFIG = {'paths': {'0': ['skins/fox', 1]}, 'scenes': {}, 'name': 'skins'}


def pkg(index_js, extra=None):
    files = {
        'game.json': json.dumps({'subpackages': [{'name': 'resources', 'root': 'subpackages/resources/'},
                                                 {'name': 'skins', 'root': 'subpackages/skins/'}]}).encode(),
        'cocos/cocos2d-js-min.js': b'/* engine */ var cc={};cc.assetManager.downloader.downloadFile(u,{},p,c);',
        'adapter-min.js': b'/* adapter */ var x=new XMLHttpRequest;x.open("GET","src/settings.js");',
        'game.js': b'require("adapter-min.js");require("./main");',
        'main.js': b'',
        'assets/main/config.json': json.dumps({'paths': {}, 'scenes': {'db://assets/Game.fire': 0}}).encode(),
        'subpackages/resources/config.json': json.dumps(RES_CONFIG).encode(),
        'subpackages/skins/config.3fa2c.json': json.dumps(EXTRA_CONFIG).encode(),
        'assets/main/index.js': index_js.encode(),
    }
    files.update(extra or {})
    return files


def found(files, policy='new'):
    return {f['id']: f for f in network.check(gates.PackageView(files, policy=policy)) if f['id'] in LOCAL}


# Pinecone check_build_2415 (minified, shortened): the boot loader's file reader is not inside a browser branch
PINE_BAD = ('t.prototype.load=function(t,e,i,n){var s=this,o=this.epoch,a=cc.assetManager,r=cc.resources.'
            'getInfoWithPath(t,e);if(r){var c,h=!1,l=function(t,e,n){var h=cc.sys.isBrowser?t+"?r="+Date.now():t;'
            'try{var d=a.downloader.downloadFile(h,{responseType:e,timeout:0},function(){},function(t,e){n(t,e)})}'
            'catch(p){n(p)}};c=a.utils.getUrlWithUuid(r.uuid,{isNative:!1});l(c,"json",function(){})}};')
# Pinecone fix1: the same reader only in if(cc.sys.isBrowser){...}; the phone uses cc.resources.load
PINE_FIXED = ('t.prototype.load=function(t,e,i,n){var a=cc.assetManager,r=cc.resources.getInfoWithPath(t,e);'
              'if(r){if(cc.sys.isBrowser){var u,l=function(t,e,n){try{var d=a.downloader.downloadFile(t,'
              '{responseType:e,timeout:0},function(){},function(t,e){n(t,e)})}catch(f){n(f)}};l(u,"json",n)}'
              'else try{cc.resources.load(t,e,function(){},n)}catch(f){n(f)}}};')
FONT_BAD = ('if(n instanceof cc.Font){var c=n.nativeUrl;if(cc.sys.isBrowser&&"undefined"!=typeof FontFace)x();'
            'else{var h=a.downloader._downloaders[".ttf"];if("function"!=typeof h)return void u(new Error("no"));'
            'h(c,{},function(t,e){o===s.epoch&&(!t&&e?(n._nativeAsset=e,u(null,n)):u(t))})}}')
FONT_FIXED = ('cc.resources.load("fonts/Body",cc.Font,function(i,n){if(!i&&n instanceof cc.Font){var s=n._nativeAsset;'
              'if("string"!=typeof s||/[\\/\\\\]|\\.(ttf|otf|woff2?)$/i.test(s))return void h(new Error("bad"));h(null,n)}})')


class PackageRead(unittest.TestCase):
    def test_pinecone_bad_reader_blocks(self):
        hit = found(pkg(PINE_BAD))
        self.assertEqual(sorted(hit), ['H15_package_read_via_request'])
        self.assertEqual(hit['H15_package_read_via_request']['level'], 'block')
        self.assertIn('downloadFile(h,', hit['H15_package_read_via_request']['evidence'][0]['context'])

    def test_pinecone_fixed_reader_passes(self):
        self.assertEqual(found(pkg(PINE_FIXED)), {})

    def test_browser_guards_pass(self):
        for js in ('cc.sys.isBrowser&&a.downloader.downloadFile(u,{},p,c);',
                   'var r=cc.sys.isBrowser?a.downloader.downloadFile(u,{},p,c):null;',
                   'if(!cc.sys.isBrowser){fs.readFile(u)}else{a.downloader.downloadFile(u,{},p,c)}',
                   'var s=!0===cc.sys.isBrowser,r=1;if(s&&"undefined"!=typeof Blob){a.downloader.downloadFile(u,{},p,c)}',
                   'if(cc.sys.isBrowser||!r||"function"!=typeof r.getFileSystemManager){a.downloader.downloadFile(s,{})}'
                   'else{r.getFileSystemManager().readFile({filePath:s})}',
                   'if(cc.sys.isNative||a&&a.getFileSystemManager){a.getFileSystemManager().readFile({})}'
                   'else{a.downloader.downloadFile(u,{},p,c)}',
                   'a.downloader.downloadFile("https://cdn.example.com/x.json",{},p,c);'):
            self.assertEqual(found(pkg(js)), {}, js)

    def test_phone_branches_block(self):
        for js in ('if(cc.sys.isBrowser||x){a.downloader.downloadFile(u,{},p,c)}',
                   'if(!cc.sys.isBrowser){a.downloader.downloadFile(u,{},p,c)}',
                   'var x=new XMLHttpRequest;x.open("GET","config/levels.json",!0);',
                   'var x=new XMLHttpRequest;x.open("GET",n.nativeUrl,!0);',
                   'tt.request({url:"data/levels.json",success:f});'):
            self.assertEqual(sorted(found(pkg(js))), ['H15_package_read_via_request'], js)

    def test_remote_requests_pass(self):
        for js in ('var x=new XMLHttpRequest;x.open("GET","https://api.example.com/a",!0);',
                   'var x=new XMLHttpRequest;x.open("POST",this.URL);',
                   'tt.request({url:"https://api.example.com/a"});'):
            self.assertEqual(found(pkg(js)), {}, js)

    def test_engine_and_adapter_not_scanned(self):
        self.assertEqual(found(pkg('')), {})


class FontFamily(unittest.TestCase):
    def test_font_path_stored_as_family_blocks(self):
        hit = found(pkg(FONT_BAD))
        self.assertEqual(sorted(hit), ['H16_font_path_as_family'])
        self.assertIn('_nativeAsset=e', hit['H16_font_path_as_family']['evidence'][0]['context'])

    def test_font_family_set_directly_blocks(self):
        js = 'var f=cc.assetManager.downloader._downloaders[".otf"];f(u,{},function(t,e){l.fontFamily=e});'
        self.assertEqual(sorted(found(pkg(js))), ['H16_font_path_as_family'])

    def test_engine_font_pipeline_passes(self):
        self.assertEqual(found(pkg(FONT_FIXED)), {})

    def test_font_downloader_used_for_bytes_only_passes(self):
        js = 'var f=a.downloader._downloaders[".ttf"];f(u,{},function(t,e){t||(cache[u]=e)});'
        self.assertEqual(found(pkg(js)), {})


class ResourcePath(unittest.TestCase):
    def test_missing_literal_paths_block(self):
        for js in ('cc.resources.load("art/home/missing",cc.SpriteFrame,f);',
                   'cc.loader.loadRes("config/levelz",f);',
                   'cc.resources.loadDir("audio",f);',
                   'cc.assetManager.getBundle("skins").load("skins/cat",f);',
                   'cc.assetManager.loadBundle("skins",function(e,b){b.load("skins/cat",cc.SpriteFrame,f)});',
                   'cc.assetManager.loadBundle("skins",(e,b)=>{b.loadDir("hats",f)});'):
            hit = found(pkg(js))
            self.assertEqual(sorted(hit), ['H17_resource_path_missing'], js)

    def test_present_paths_pass(self):
        js = ('cc.resources.load("art/home/bg",cc.SpriteFrame,f);cc.resources.load("config/levels.json",f);'
              'cc.loader.loadRes("fonts/Body",cc.Font,f);cc.resources.loadDir("art",f);cc.resources.loadDir("art/",f);'
              'cc.resources.loadDir("",f);cc.resources.load("art/ui/btn",cc.SpriteFrame,f);'
              'cc.resources.load("art/ui/btn/spriteFrame",f);cc.assetManager.getBundle("skins").load("skins/fox",f);'
              'cc.assetManager.loadBundle("skins",function(e,b){b.load("skins/fox",f)});')
        self.assertEqual(found(pkg(js)), {})

    def test_dynamic_paths_and_unknown_bundles_are_skipped(self):
        js = ('cc.resources.load("art/"+name,f);cc.resources.load(path,f);var g="artUI";'
              'cc.assetManager.loadBundle(g,function(e,b){b.load("nothing",f)});'
              'cc.assetManager.loadBundle("ghost",function(e,b){b.load("nothing",f)});x.load("nothing",f);')
        self.assertEqual(found(pkg(js)), {})


class Policy(unittest.TestCase):
    def test_legacy_game_only_warns(self):
        js = PINE_BAD + FONT_BAD + 'cc.resources.load("art/home/missing",f);'
        result = gates.run(pkg(js), modules=('network',), policy='legacy')
        self.assertEqual(sorted(f['id'] for f in result['warnings'] if f['id'] in LOCAL), sorted(LOCAL))
        self.assertEqual([f['id'] for f in result['blocks'] if f['id'] in LOCAL], [])
        result = gates.run(pkg(js), modules=('network',), policy='new')
        self.assertEqual(sorted(f['id'] for f in result['blocks'] if f['id'] in LOCAL), sorted(LOCAL))

    def test_evidence_is_capped_at_six(self):
        js = ''.join('cc.resources.load("gone/%d",f);' % i for i in range(9))
        hit = found(pkg(js))['H17_resource_path_missing']
        self.assertEqual(len(hit['evidence']), 6)


PINECONE = Path(os.environ.get('PINECONE_DIR', '/Users/sijunting/Downloads/！自制游戏/！交付游戏/2子午-Pinecone（自制）'))
PINE_ZIPS = {'bad': PINECONE / '_work' / 'PineconePath_check_build_2415.zip',
             'fix1': PINECONE / 'PineconePath_TikTok_Test_fix1_20261029.zip',
             'fix2': PINECONE / 'PineconePath_TikTok_Test_fix2_20261029.zip'}


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        return {i.filename: z.read(i) for i in z.infolist()
                if not i.is_dir() and not i.filename.startswith('__MACOSX/')}


@unittest.skipUnless(all(p.is_file() for p in PINE_ZIPS.values()), 'Pinecone ZIPs not on this machine')
class RealPinecone(unittest.TestCase):
    def test_bad_build_blocks_and_fixed_builds_pass(self):
        self.assertEqual(sorted(found(read_zip(PINE_ZIPS['bad']))),
                         ['H15_package_read_via_request', 'H16_font_path_as_family'])
        self.assertEqual(found(read_zip(PINE_ZIPS['fix1'])), {})
        self.assertEqual(found(read_zip(PINE_ZIPS['fix2'])), {})


if __name__ == '__main__':
    unittest.main()
