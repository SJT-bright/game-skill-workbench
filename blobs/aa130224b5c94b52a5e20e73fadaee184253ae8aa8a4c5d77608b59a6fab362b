"""Portable receiver/domain regressions. No game, browser or private file fixtures."""
import copy
import hashlib
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import audit_runtime_resources as resources


class ResourceAdaptation(unittest.TestCase):
    def setUp(self):
        resources._CACHE.clear()

    def files(self, source, *, system=False):
        catalog = {'name':'resources','types':['cc.SpriteFrame','cc.JsonAsset','cc.TTFFont','cc.BitmapFont'],
                   'paths':{'0':['icons/a',0],'1':['icons/b',0],'2':['config/game',1],
                            '3':['fonts/regular',2],'4':['fonts/bitmap',3]}}
        data = {'main.js':source.encode(),'assets/resources/config.json':json.dumps(catalog).encode()}
        if system:
            data.update({'src/settings.json':b'{"CocosEngine":"3.8.8"}','cocos-js/cc.js':b'System.register'})
        return data

    def test_unrelated_registry_updates_do_not_change_package_signature(self):
        data = self.files("cc.resources.load(chosen,cc.SpriteFrame)")
        source = data['main.js']
        registry = {'fixture': {'source_sha256': {'main.js': hashlib.sha256(source).hexdigest()},
                    'resolutions': {'main.js:0': {'kind':'load','bundles':['resources'],
                      'paths':['icons/a'],'type':'cc.SpriteFrame','unknown_receiver':False,
                      'reason':'Synthetic finite selection.'}}, 'escapes':{}}}
        registry_path = resources.HERE/'reviewed_resource_profiles.json'
        original_read = Path.read_bytes
        def read(path):
            return json.dumps(registry).encode() if path == registry_path else original_read(path)
        with patch.object(resources, '_reviewed_profiles', lambda: registry), \
             patch.object(Path, 'read_bytes', autospec=True, side_effect=read):
            manifest = resources.generate(data)
            first = resources.audit(data, manifest)
            registry['another-game'] = {'source_sha256': {'other.js':'0'*64},
                                       'resolutions':{}, 'escapes':{}}
            self.assertEqual(first, resources.audit(data, manifest))
            registry['fixture']['resolutions']['main.js:0']['paths'] = ['icons/b']
            with self.assertRaisesRegex(ValueError, 'omitted production'):
                resources.audit(data, manifest)

    def test_concrete_nonresource_methods_do_not_create_cocos_requests(self):
        for source in ["const store={load(k){return k}};store.load('slot')",
                       "const s={n:0,load(){this.n++}};s['load']()",
                       "class Store{load(){return 1}};const s=new Store();s.load()",
                       "const s={load:()=>1};s.load()",
                       "const ad=tt.createRewardedVideoAd({});ad.load()"]:
            with self.subTest(source=source):
                self.assertEqual(resources.generate(self.files(source))['resources'], [])

    def test_reassigned_escaped_or_unknown_receivers_remain_refused(self):
        for source in ["let s={load(){}};s=cc.resources;s.load(input,cc.SpriteFrame)",
                       "const s={load(){}};s.load=cc.resources.load;s.load(input,cc.SpriteFrame)",
                       "const s={load(){}};externalMutator(s);s.load(input,cc.SpriteFrame)",
                       "class S{load(){}};const s=new S();S.prototype.load=cc.resources.load;s.load(input,cc.SpriteFrame)",
                       "class S{load(){}};const s=new S();const p=S.prototype;p.load=cc.resources.load;s.load(input,cc.SpriteFrame)",
                       "let ad=tt.createRewardedVideoAd({});ad=cc.resources;ad.load(input,cc.SpriteFrame)",
                       "tt={createRewardedVideoAd(){return cc.resources}};const ad=tt.createRewardedVideoAd();ad.load(input,cc.SpriteFrame)",
                       "unknown.load(input,cc.SpriteFrame)", "cc.resources[method](input,cc.SpriteFrame)"]:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError,'unresolved dynamic'):
                    resources.generate(self.files(source))

    def test_local_wrapper_body_still_contributes_real_requests(self):
        source="const s={load(){cc.resources.load('icons/a',cc.SpriteFrame)}};s.load()"
        manifest=resources.generate(self.files(source));self.assertEqual(len(manifest['resources']),1)
        with self.assertRaisesRegex(ValueError,'omitted production'):
            resources.audit(self.files(source),{'resources':[]})
        with self.assertRaisesRegex(ValueError,'unresolved dynamic'):
            resources.generate(self.files(source.replace("'icons/a'",'userInput')))

    def system_source(self, argument="'config/game'", module='Scene'):
        return "System.register('"+module+"',['cc'],function(e){var r,J;return{setters:[function(cc){r=cc.resources;J=cc.JsonAsset}],execute(){r.load("+argument+",J)}}})"

    def test_standard_systemjs_has_no_private_art_requirement(self):
        for module in ['Scene','chunks:///_virtual/Art.ts']:
            with self.subTest(module=module):
                for version in ['3.8.8','3.8.7']:
                    data=self.files(self.system_source(module=module),system=True);data['src/settings.json']=json.dumps({'CocosEngine':version}).encode()
                    self.assertEqual(len(resources.generate(data)['resources']),1)

    def test_systemjs_alias_domains_and_type_safety(self):
        source="System.register('Scene',['cc'],function(e){var c;return{setters:[function(m){c=m}],execute(){for(const p of ['icons/a','icons/b'])c.resources.load(p,c.SpriteFrame)}}})"
        manifest=resources.generate(self.files(source,system=True));self.assertEqual(len(manifest['resources']),2)
        with self.assertRaisesRegex(ValueError,'omitted production'):
            resources.audit(self.files(source,system=True),{'resources':manifest['resources'][:1]})
        with self.assertRaisesRegex(ValueError,'unresolved dynamic'):
            resources.generate(self.files(self.system_source('input'),system=True))
        with self.assertRaisesRegex(ValueError,'missing/type mismatch'):
            resources.generate(self.files(self.system_source("'icons/a'"),system=True))

    def test_systemjs_settings_checks_stay_outside_inventory_cache(self):
        data=self.files(self.system_source(),system=True);resources.generate(data)
        data['src/settings.json']=b'{"CocosEngine":"3.8.8","assets":{"server":"https://invalid.example"}}'
        with self.assertRaisesRegex(ValueError,'remote SystemJS'):
            resources.generate(data)
        data['src/settings.json']=b'{"CocosEngine":"3.8.8","scripting":{"scriptPackages":["project://missing.js"]}}'
        with self.assertRaisesRegex(ValueError,'missing SystemJS script'):
            resources.generate(data)

    def test_generic_warmup_protocol_is_local_and_does_not_hide_resource_calls(self):
        source=self.system_source()+";System.warmup({importMap:require('./src/import-map.js').default,importMapUrl:'src/import-map.js',defaultHandler:(url)=>require('.'+url),handlers:{'project:':(url)=>require(url)}})"
        data=self.files(source,system=True)
        data['src/import-map.js']=b"exports.default={imports:{cc:'../cocos-js/cc.js',extra:'../extra.js'}}"
        data['extra.js']=b"module.exports={};"
        manifest=resources.generate(data);self.assertEqual(len(manifest['resources']),1)
        del data['extra.js']
        with self.assertRaises(ValueError):resources.generate(data)
        data['extra.js']=b"cc.resources.load(missing,cc.SpriteFrame)"
        with self.assertRaisesRegex(ValueError,'unresolved dynamic'):resources.generate(data)
        data['extra.js']=b"module.exports={};"
        data['src/import-map.js']=b"exports.default={imports:{cc:'https://invalid.example/engine.js'}}"
        with self.assertRaisesRegex(ValueError,'nonlocal SystemJS'):resources.generate(data)

    def test_warmup_delegation_cannot_mask_unknown_functions_or_changed_maps(self):
        prefix=self.system_source()
        config="{importMap:require('./src/import-map.js').default,importMapUrl:'src/import-map.js',defaultHandler:(url)=>require('.'+url),handlers:{'project:':(url)=>require(url)}}"
        for mutation in ['extra_callback','extra_statement','shadowed_System','shadowed_require','reassigned_System','handler_named_require','unknown_map','mutated_map','spread','duplicate']:
            with self.subTest(mutation=mutation):
                source=prefix+';System.warmup('+config+')';mapping="exports.default={imports:{cc:'../cocos-js/cc.js'}}"
                if mutation=='extra_callback':source=source.replace(",handlers:",",extra:(url)=>require(url),handlers:")
                elif mutation=='extra_statement':source=source.replace("(url)=>require('.'+url)","(url)=>{touch(url);return require('.'+url)}")
                elif mutation=='shadowed_System':source='function boot(System){'+source+'}'
                elif mutation=='shadowed_require':source='function boot(require){'+source+'}'
                elif mutation=='reassigned_System':source='System.warmup=unknown;'+source
                elif mutation=='handler_named_require':source=source.replace("(url)=>require(url)","(require)=>require(require)")
                elif mutation=='unknown_map':source=source.replace("require('./src/import-map.js').default",'unknownMap')
                elif mutation=='mutated_map':mapping+=";exports.default.imports.cc='https://invalid.example/engine.js'"
                elif mutation=='spread':source=source.replace("{importMap:",'{...unknownConfig,importMap:')
                elif mutation=='duplicate':source=source.replace("{importMap:",'{importMap:unknownMap,importMap:')
                data=self.files(source,system=True);data['src/import-map.js']=mapping.encode()
                with self.assertRaises(ValueError):resources.generate(data)
        # An unrelated local parameter does not shadow the actual global call.
        source=prefix+';function unrelated(System,require){return 1};System.warmup('+config+')'
        data=self.files(source,system=True);data['src/import-map.js']=b"exports.default={imports:{cc:'../cocos-js/cc.js'}}"
        self.assertEqual(len(resources.generate(data)['resources']),1)

    def test_font_base_class_accepts_only_known_font_subclasses(self):
        for path in ['fonts/regular','fonts/bitmap']:
            with self.subTest(path=path):
                self.assertEqual(len(resources.generate(self.files("cc.resources.load('"+path+"',cc.Font)"))['resources']),1)
        with self.assertRaisesRegex(ValueError,'missing/type mismatch'):
            resources.generate(self.files("cc.resources.load('config/game',cc.Font)"))
        with self.assertRaisesRegex(ValueError,'missing/type mismatch'):
            resources.generate(self.files("cc.resources.load('fonts/regular',cc.SpriteFrame)"))

    def test_debug_catalog_class_names_preserve_path_and_type_checks(self):
        source="cc.resources.load('icons/a',cc.SpriteFrame)"
        data={'main.js':source.encode(),'assets/resources/config.json':json.dumps({'name':'resources','types':[], 'paths':{'0':['icons/a','cc.SpriteFrame']}}).encode()}
        self.assertEqual(len(resources.generate(data)['resources']),1)
        wrong=copy.deepcopy(data);wrong['assets/resources/config.json']=json.dumps({'name':'resources','types':[],'paths':{'0':['icons/a','cc.JsonAsset']}}).encode()
        with self.assertRaisesRegex(ValueError,'missing/type mismatch'):resources.generate(wrong)
        for row in [['icons/a',True],['icons/a',-1],['icons/a','bad type'],[42,'cc.SpriteFrame'],['icons/a']]:
            with self.subTest(row=row):
                broken=copy.deepcopy(data);broken['assets/resources/config.json']=json.dumps({'name':'resources','types':[],'paths':{'0':row}}).encode()
                with self.assertRaisesRegex(ValueError,'invalid bundle resource'):resources.generate(broken)

    def dynamic_profile_fixture(self):
        source="const bundle=cc.assetManager.getBundle('cosmetics');bundle.load(selected,cc.SpriteFrame)"
        asset='assets/resources/import/unlocks.json'
        data={'main.js':source.encode(),asset:json.dumps([1,0,0,[['cc.JsonAsset',['_name','json'],1]],[[0,0,1,3]],[[0,'unlock_table',{'items':[{'id':'hero_01'},{'id':'hero_02'},{'id':'bg_01'}]}]]]).encode(),
              'assets/cosmetics/config.json':json.dumps({'name':'cosmetics','types':['cc.SpriteFrame'],'paths':{'0':['hero_02',0]}}).encode()}
        profile={'source_sha256':{'main.js':hashlib.sha256(source.encode()).hexdigest()},
                 'data_domains':{'items':{'kind':'mira-cosmetics-unlock-v1','path':asset,'asset_name':'unlock_table'}},
                 'resolutions':{'main.js:'+str(source.index('bundle.load')):{'kind':'load','bundles':['cosmetics'],'type':'cc.SpriteFrame','unknown_receiver':False,'data_domain':'items','reason':'Synthetic current-data contract'}},'escapes':[]}
        return data,asset,{'synthetic':profile}

    def test_changed_json_domain_cannot_reuse_fixed_id_list_or_cached_pass(self):
        data,asset,profiles=self.dynamic_profile_fixture()
        with patch.object(resources,'_reviewed_profiles',return_value=profiles):
            manifest=resources.generate(data);self.assertEqual(len(manifest['resources']),1)
            value=json.loads(data[asset]);value[5][0][2]['items'].append({'id':'hero_03'});data[asset]=json.dumps(value).encode()
            with self.assertRaisesRegex(ValueError,'missing/type mismatch'):
                resources.generate(data)
            catalog=json.loads(data['assets/cosmetics/config.json']);catalog['paths']['1']=['hero_03',0];data['assets/cosmetics/config.json']=json.dumps(catalog).encode()
            self.assertEqual(len(resources.generate(data)['resources']),2)
            with self.assertRaisesRegex(ValueError,'omitted production'):
                resources.audit(data,manifest)

    def test_profile_data_missing_or_malformed_is_not_silently_optional(self):
        for mutation in ['delete','empty','duplicate','unknown_id']:
            data,asset,profiles=self.dynamic_profile_fixture()
            with self.subTest(mutation=mutation),patch.object(resources,'_reviewed_profiles',return_value=profiles):
                resources.generate(data)
                if mutation=='delete':del data[asset]
                elif mutation=='empty':data[asset]=b''
                else:
                    value=json.loads(data[asset]);value[5][0][2]['items'].append({'id':'hero_02' if mutation=='duplicate' else 'unexpected'});data[asset]=json.dumps(value).encode()
                with self.assertRaises(ValueError):resources.generate(data)

    def test_unknown_new_program_does_not_inherit_reviewed_profile(self):
        data,asset,profiles=self.dynamic_profile_fixture()
        with patch.object(resources,'_reviewed_profiles',return_value=profiles):
            resources.generate(data);data['new.js']=b"cc.resources.load(userInput,cc.SpriteFrame)"
            with self.assertRaisesRegex(ValueError,'unresolved dynamic'):
                resources.generate(data)


    def test_exact_profile_json_pin_is_not_a_catalog_pin(self):
        data,asset,profiles=self.dynamic_profile_fixture()
        profile=profiles['synthetic'];profile.pop('data_domains')
        resolution=next(iter(profile['resolutions'].values()));resolution.pop('data_domain');resolution['paths']=['hero_02']
        profile['data_digest_kind']='serialized-json-assets-v1'
        profile['data_digest']=hashlib.sha256(json.dumps(resources._serialized_asset_data_hashes(data),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with patch.object(resources,'_reviewed_profiles',return_value=profiles):
            resources.generate(data)
            catalog=json.loads(data['assets/cosmetics/config.json']);catalog['debug_metadata']={'time':1};data['assets/cosmetics/config.json']=json.dumps(catalog).encode()
            self.assertEqual(len(resources.generate(data)['resources']),1)
            data[asset]+=b' '
            with self.assertRaisesRegex(ValueError,'unresolved dynamic'):resources.generate(data)

    def test_referenced_profile_is_revalidated_before_warm_cache(self):
        data,asset,profiles=self.dynamic_profile_fixture();profile=profiles['synthetic']
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'profile.json';raw=json.dumps(profile).encode();path.write_bytes(raw)
            stub={'synthetic':{'source_sha256':profile['source_sha256'],'profile_ref':{'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}}}
            with patch.object(resources,'_reviewed_profiles',return_value=stub):
                resources.generate(data)
                path.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'profile changed or missing'):resources.generate(data)
                path.write_bytes(raw);resources.generate(data);path.unlink()
                with self.assertRaisesRegex(ValueError,'profile changed or missing'):resources.generate(data)
            path.write_bytes(raw)
            with patch.object(resources,'HERE',Path(temp)),patch.object(resources,'_reviewed_profiles',return_value={'synthetic':{'source_sha256':profile['source_sha256'],'profile_ref':{'path':'profile.json','sha256':hashlib.sha256(raw).hexdigest()}}}):
                self.assertEqual(len(resources._matching_reviewed_profiles(data,profile['source_sha256'])),1)
            changed=dict(profile,source_sha256={});path.write_text(json.dumps(changed));stub['synthetic']['profile_ref']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with patch.object(resources,'_reviewed_profiles',return_value=stub):
                with self.assertRaisesRegex(ValueError,'source identity differs'):resources.generate(data)


if __name__=='__main__':unittest.main()
