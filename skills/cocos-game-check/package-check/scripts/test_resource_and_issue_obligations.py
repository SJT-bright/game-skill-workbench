"""Production discovery + real local retest runner; no full game CI/browser mocks claimed."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from check_package import native_files, write_archive
from test_package_checks import fixture, runtime_patch, APP, finalize_project
_RUNTIME = runtime_patch()
setUpModule, tearDownModule = _RUNTIME.start, _RUNTIME.stop
import audit_runtime_resources as resources
import package_issue_gate as issues
import package_obligations as obligations
from build_checked_zip import build
from prepare_delivery import prepare


def empty_history(project):
    project.mkdir(parents=True, exist_ok=True)
    issues.initialize(project)


class ResourceCoverage(unittest.TestCase):
    def files(self, source):
        return {'main.js': source.encode(), 'assets/main/config.json': json.dumps({
            'name': 'main', 'types': ['cc.SpriteFrame'],
            'paths': {'0': ['icons/a', 0], '1': ['icons/b', 0]}}).encode()}

    def test_mapping_omission_cannot_hide_behind_valid_remaining_row(self):
        files = self.files("const b=cc.assetManager.getBundle('main');const map={a:'icons/a',b:'icons/b'};b.load(map[choice],cc.SpriteFrame);")
        manifest = resources.generate(files)
        self.assertEqual(len(manifest['resources']), 2)
        resources.audit(files, manifest)
        with self.assertRaisesRegex(ValueError, 'omitted production'):
            resources.audit(files, {'resources': manifest['resources'][:1]})

    def test_unbounded_dynamic_path_is_not_waived_by_handwritten_rows(self):
        files = self.files("cc.assetManager.getBundle('main').load('icons/'+userInput,cc.SpriteFrame)")
        with self.assertRaisesRegex(ValueError, 'unresolved dynamic'):
            resources.audit(files, {'resources': [{'bundle':'main','path':'icons/a','type':'cc.SpriteFrame'}]})

    def test_load_dir_requires_every_catalog_match(self):
        files = self.files("cc.assetManager.getBundle('main').loadDir('icons',cc.SpriteFrame)")
        manifest = resources.generate(files)
        self.assertEqual(len(manifest['resources']), 2)
        with self.assertRaisesRegex(ValueError, 'omitted production'):
            resources.audit(files, {'resources': manifest['resources'][1:]})

    def test_callback_bundle_alias_and_finite_loop(self):
        files = self.files("cc.assetManager.loadBundle('main',(err,b)=>{for(const p of ['icons/a','icons/b'])b.load(p,cc.SpriteFrame)})")
        self.assertEqual(len(resources.generate(files)['resources']), 2)

    def test_destructured_loader_and_json_domain(self):
        files = {'main.js':b"const {load}=cc.resources;const map=require('./paths.json');load(map[key],cc.SpriteFrame)",
                 'paths.json':b'{"a":"icons/a","b":"icons/b"}',
                 'assets/resources/config.json': self.files('')['assets/main/config.json'].replace(b'"main"',b'"resources"')}
        self.assertEqual(len(resources.generate(files)['resources']), 2)

    def test_method_escape_refused_not_silently_skipped(self):
        files = self.files("external(cc.assetManager.getBundle('main').load)")
        with self.assertRaisesRegex(ValueError, 'unresolved dynamic'):
            resources.generate(files)

    def test_production_call_changed_invalidates_only_discovery_cache(self):
        files = self.files("cc.assetManager.getBundle('main').load('icons/a',cc.SpriteFrame)")
        manifest = resources.generate(files)
        files['main.js'] = b"cc.assetManager.getBundle('main').load('icons/b',cc.SpriteFrame)"
        with self.assertRaisesRegex(ValueError, 'omitted production'):
            resources.audit(files, manifest)

    def test_unrelated_text_or_comments_do_not_create_load_sites(self):
        files = self.files("const text='cc.resources.load(missing)';// bundle.load('missing')\n")
        self.assertEqual(resources.generate(files)['resources'], [])

    def test_specialized_adapter_cannot_mask_unsupported_business_module_calls(self):
        files = self.files("unknownLoader.load('icons/a',cc.SpriteFrame)")
        files['src/settings.json'] = b'{"CocosEngine":"3.8.8"}'
        files['cocos-js/cc.js'] = b'System.register'
        real_run = subprocess.run
        def adapter_or_parser(command, **kwargs):
            if command[1].endswith('scan_systemjs_resources.cjs'):
                masked = {name: '' for name in json.loads(kwargs['input'])['files']}
                return subprocess.CompletedProcess(command, 0, json.dumps({'schema':'cocos_resource_sites.v1','sites':[], 'escapes':[], 'root_files':masked}).encode(), b'')
            return real_run(command, **kwargs)
        with patch.object(resources.subprocess, 'run', side_effect=adapter_or_parser):
            with self.assertRaisesRegex(ValueError, 'unresolved dynamic'):
                resources.generate(files)

    def test_mutated_or_escaped_table_cannot_underdeclare_domain(self):
        for prefix in ["function alter(){map.b='icons/b'};alter();",
                       "const alias=map;alias.b='icons/b';",
                       "externalMutator(map);", "{const map={b:'icons/b'};}"]:
            with self.subTest(prefix=prefix):
                files=self.files("const map={a:'icons/a'};"+prefix+"cc.assetManager.getBundle('main').load(map[choice],cc.SpriteFrame)")
                with self.assertRaisesRegex(ValueError,'unresolved dynamic'):
                    resources.generate(files)

    def test_destructured_method_escape_and_dynamic_code_refused(self):
        for source in ["const{load}=cc.resources;external(load)", "eval(userSource)", "new Function(userSource)", "external.loadResArray(['icons/a'],cc.SpriteFrame)"]:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError,'unresolved dynamic'):
                    resources.generate(self.files(source))


class ReportedIssues(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root/'project'; empty_history(self.project)
        self.native = self.root/'native';self.negative=self.root/'negative';self.normal=self.root/'normal'
        for path,delta in [(self.native,1),(self.negative,2),(self.normal,1)]:
            path.mkdir();(path/'state.json').write_text(json.dumps({'delta':delta}))
        self.runner = self.root/'runner.py'
        self.runner.write_text("import argparse,json\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--native');p.add_argument('--case');a=p.parse_args();print(json.dumps({'observed':json.loads((Path(a.native)/'state.json').read_text())}))\n")
        self.cases = [{'id':'reward_once','assertions':[{'path':['delta'],'op':'eq','value':1}]}]

    def tearDown(self):
        self.temp.cleanup()

    def report(self):
        issues.register(self.project,self.native,'reward-duplicate','Reported duplicate reward', ['state.json'],self.cases,self.runner)

    def close(self):
        return issues.retest(self.project,self.native,'reward-duplicate',self.negative,self.normal,self.root/'retest')

    def test_missing_history_is_not_assumed_clean(self):
        other=self.root/'untracked';other.mkdir()
        with self.assertRaisesRegex(ValueError,'ledger/head missing'):issues.audit(other,self.native)

    def test_open_issue_cannot_be_packaged(self):
        self.report()
        with self.assertRaisesRegex(ValueError,'no passed retest'):issues.audit(self.project,self.native)

    def test_real_targeted_runner_closes_issue_without_replaying_on_every_audit(self):
        self.report();self.close()
        with patch.object(issues.subprocess,'run',side_effect=AssertionError('unrelated/full replay')):
            self.assertTrue(issues.audit(self.project,self.native)['passed'])

    def test_related_change_reopens_but_unrelated_change_reuses(self):
        self.report();self.close()
        (self.native/'unrelated.txt').write_text('unrelated')
        self.assertTrue(issues.audit(self.project,self.native)['passed'])
        (self.native/'state.json').write_text('{"delta":2}')
        with self.assertRaisesRegex(ValueError,'stale'):issues.audit(self.project,self.native)

    def test_failed_current_postcondition_does_not_close_issue(self):
        self.report();(self.native/'state.json').write_text('{"delta":2}')
        with self.assertRaisesRegex(ValueError,'postconditions'):self.close()
        with self.assertRaisesRegex(ValueError,'no passed retest'):issues.audit(self.project,self.native)

    def test_nonreproducing_negative_is_not_a_regression_pass(self):
        self.report();(self.negative/'state.json').write_text('{"delta":1}')
        with self.assertRaisesRegex(ValueError,'negative'):self.close()

    def test_issue_history_cannot_be_reset_or_truncated(self):
        self.report()
        with self.assertRaisesRegex(ValueError,'already exists'):issues.initialize(self.project)
        _,ledger,_=issues.paths(self.project);ledger.write_bytes(ledger.read_bytes().splitlines()[0]+b'\n')
        with self.assertRaisesRegex(ValueError,'changed/truncated'):issues.audit(self.project,self.native)

    def test_manual_closed_event_is_not_a_retest(self):
        self.report();issues.append(self.project,'closed',{'id':'reward-duplicate','status':'pass'})
        with self.assertRaisesRegex(ValueError,'manual closed/pass'):issues.audit(self.project,self.native)

    def test_modified_raw_or_runner_invalidates_pass(self):
        self.report();ref=self.close();proof=issues.read_ref(ref)
        raw=Path(proof['cases']['reward_once']['current']['path']);raw.write_text('{}')
        with self.assertRaisesRegex(ValueError,'evidence file missing/changed'):issues.audit(self.project,self.native)

    def test_fake_pass_flag_cannot_cover_wrong_observations(self):
        self.report();ref=self.close();proof=issues.read_ref(ref)
        raw=Path(proof['cases']['reward_once']['current']['path']);data=json.loads(raw.read_text());data['passed']=True;data['observed']['delta']=2;raw.write_text(json.dumps(data))
        proof['cases']['reward_once']['current']['sha256']=issues.sha(raw)
        path=self.root/'fake-proof.json';path.write_text(json.dumps(proof));issues.append(self.project,'retested',{'id':'reward-duplicate','proof':{'path':str(path),'sha256':issues.sha(path)}})
        with self.assertRaisesRegex(ValueError,'postconditions'):issues.audit(self.project,self.native)

    def test_reviewed_runner_revision_retains_report_and_requires_fresh_local_retest(self):
        self.report();self.close()
        self.runner.write_text(self.runner.read_text()+'# reviewed harness repair\n')
        with self.assertRaisesRegex(ValueError,'runner changed'):issues.audit(self.project,self.native)
        issues.revise_scope(self.project,self.native,'reward-duplicate',['state.json'],self.runner,'Fix reviewed local runner')
        with self.assertRaisesRegex(ValueError,'no passed retest'):issues.audit(self.project,self.native)
        issues.retest(self.project,self.native,'reward-duplicate',self.negative,self.normal,self.root/'retest-v2')
        self.assertTrue(issues.audit(self.project,self.native)['passed'])
        events,_=issues.load(self.project)
        self.assertEqual(events[1]['payload']['message'],'Reported duplicate reward')
        self.assertEqual(issues.issue_state(events)['reward-duplicate']['contract']['cases'],self.cases)

    def test_scope_revision_cannot_weaken_original_postconditions(self):
        self.report();events,_=issues.load(self.project);original=issues.issue_state(events)['reward-duplicate']['contract']
        updated=copy.deepcopy(original);updated['cases'][0]['assertions'][0]['value']=2
        issues.append(self.project,'scope_updated',{'id':'reward-duplicate','reason':'manual bypass','previous_contract_signature':issues.digest(original),'contract':updated})
        with self.assertRaisesRegex(ValueError,'weaken its postconditions'):issues.audit(self.project,self.native)

    def test_retest_output_preserves_fault_and_normal_control_trees(self):
        self.report()
        for tree in (self.native,self.negative,self.normal):
            output=tree/'evidence'
            with self.assertRaisesRegex(ValueError,'outside all Native/control'):
                issues.retest(self.project,self.native,'reward-duplicate',self.negative,self.normal,output)
            self.assertFalse(output.exists())


# Separate setup reuse without inherited test execution.
class EntryPoints(unittest.TestCase):
    def setUp(self):
        ReportedIssues.setUp(self)
        finalize_project(self.project)      # v7.7: the writers need a current source record (K5)
    tearDown=ReportedIssues.tearDown
    report=ReportedIssues.report

    def setup_package(self):
        files=fixture();config=json.loads(files['assets/main/config.json']);config.update(name='main',paths={'0':['fixture',0]},types=['cc.JsonAsset']);files['assets/main/config.json']=json.dumps(config).encode()
        for name,data in files.items():
            p=self.native/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        manifest=self.root/'resources.json';manifest.write_text('{"resources":[{"bundle":"main","path":"fixture","type":"cc.JsonAsset"}]}')
        return manifest

    def test_light_writer_open_issue_blocks_before_runtime_and_no_output(self):
        manifest=self.setup_package();self.report();out=self.root/'game.zip'
        with patch('build_checked_zip.audit_final_startup') as runtime:
            with self.assertRaisesRegex(ValueError,'no passed retest'):build(self.native,APP,out,resource_manifest=manifest,project=self.project)
            runtime.assert_not_called()
        self.assertFalse(out.exists())

    def test_new_issue_during_runtime_refuses_publication(self):
        manifest=self.setup_package();out=self.root/'game.zip'
        def runtime(*args,**kwargs):self.report();return {'passed':True}
        with patch('build_checked_zip.audit_final_startup',side_effect=runtime):
            with self.assertRaisesRegex(ValueError,'no passed retest'):build(self.native,APP,out,resource_manifest=manifest,project=self.project)
        self.assertFalse(out.exists())

    def test_delivery_cannot_skip_open_issue_or_manifest(self):
        manifest=self.setup_package();self.report();archive=self.root/'game.zip';write_archive(archive,native_files(self.native));record=self.root/'delivery.json';other=self.root/'other';other.mkdir()
        with patch('prepare_delivery.tempfile.gettempdir',return_value=str(other)),patch('prepare_delivery.audit_final_startup') as runtime:
            with self.assertRaisesRegex(ValueError,'no passed retest'):prepare(archive,self.native,APP,record,project=self.project,resource_manifest=manifest)
            runtime.assert_not_called()
        self.assertFalse(record.exists())

    def test_publication_guard_rejects_changed_manifest_and_preserves_local_scope(self):
        manifest=self.setup_package();files=native_files(self.native);checked=obligations.verify(files,self.native,self.project,manifest)
        manifest.write_text('{"resources":[]}')
        with self.assertRaises(ValueError):
            with obligations.publication_guard(files,self.native,self.project,manifest,checked):self.fail('published')

    def test_formal_writer_also_refuses_open_issue_before_full_ci(self):
        import make_tiktok_zip
        manifest=self.setup_package();self.report();out=self.root/'formal.zip'
        argv=['make_tiktok_zip.py','--native',str(self.native),'--app-id',APP,'--out',str(out),'--project',str(self.project),'--web',str(self.root/'web'),'--build-tag','fixture','--review',str(self.root/'review.json'),'--resource-manifest',str(manifest)]
        with patch.object(sys,'argv',argv),patch('audit_final_package_startup.audit_final_startup') as runtime:
            self.assertEqual(make_tiktok_zip.main(),1);runtime.assert_not_called()
        self.assertFalse(out.exists())


class KitMainStaticManifest(unittest.TestCase):
    """v7.7 W-G2: a finalized 2.4.15 new game (kit main.js) gets a static manifest. Its jsList scripts and the
    webp-decode-probe.js the kit main.js requires are listed and must exist; the writer's resource step accepts it."""
    setUp=EntryPoints.setUp
    tearDown=ReportedIssues.tearDown

    def setup_package(self, plugin=True):
        from test_package_checks import ENGINE_KIT_MAIN
        files=fixture(ENGINE_KIT_MAIN);config=json.loads(files['assets/main/config.json']);config.update(name='main',paths={'0':['fixture',0]},types=['cc.JsonAsset']);files['assets/main/config.json']=json.dumps(config).encode()
        if plugin:  # a jsList plugin script, as Creator writes one for a plugin-marked script
            files['src/settings.js']=files['src/settings.js'].replace(b'jsList:[]',b'jsList:["assets/plugins/fixture-plugin.js"]')
            files['src/assets/plugins/fixture-plugin.js']=b'window.fixturePlugin=1;\n'
        for name,data in files.items():
            p=self.native/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        manifest=self.root/'resources.json'
        manifest.write_text(json.dumps(resources.generate(native_files(self.native))))
        return manifest

    def test_static_manifest_lists_kit_scripts_and_writer_resource_step_accepts_it(self):
        manifest=self.setup_package()
        rows=json.loads(manifest.read_text())['script_files']
        self.assertEqual(sorted(r['path'] for r in rows),['src/assets/plugins/fixture-plugin.js','webp-decode-probe.js'])
        self.assertTrue(obligations.verify(native_files(self.native),self.native,self.project,manifest)['passed'])

    def test_light_writer_writes_zip_with_the_static_manifest(self):
        # only the browser parts are patched (startup runtime, Ego ad regression), as in the other writer tests
        import check_package
        manifest=self.setup_package();out=self.root/'game.zip'
        with patch('build_checked_zip.audit_final_startup',return_value={'passed':True,'patched':True}),\
             patch.object(check_package,'rewarded_ad_gate',return_value={'status':'patched_in_unit_test'}):
            result=build(self.native,APP,out,self.root/'report.json',resource_manifest=manifest,project=self.project)
        self.assertTrue(out.exists())
        listed=result['package_obligations']['resources']['kit_script_files']
        self.assertEqual(sorted(r['path'] for r in listed),['src/assets/plugins/fixture-plugin.js','webp-decode-probe.js'])

    def test_writer_refuses_package_missing_a_jslist_script(self):
        manifest=self.setup_package();(self.native/'src/assets/plugins/fixture-plugin.js').unlink();out=self.root/'game.zip'
        with self.assertRaisesRegex(ValueError,'kit main.js script file missing or empty: src/assets/plugins/fixture-plugin.js'):
            obligations.verify(native_files(self.native),self.native,self.project,manifest)
        # the writer's startup dependency check meets the missing jsList file first; either way no ZIP
        with patch('build_checked_zip.audit_final_startup') as runtime:
            with self.assertRaisesRegex(ValueError,'(missing startup dependency|kit main.js script file missing).*fixture-plugin.js'):build(self.native,APP,out,resource_manifest=manifest,project=self.project)
            runtime.assert_not_called()
        self.assertFalse(out.exists())

    def test_writer_refuses_package_missing_the_probe(self):
        manifest=self.setup_package(plugin=False);(self.native/'webp-decode-probe.js').unlink()
        with self.assertRaisesRegex(ValueError,'kit main.js script file missing or empty: webp-decode-probe.js'):
            obligations.verify(native_files(self.native),self.native,self.project,manifest)


if __name__=='__main__':unittest.main()
