"""Known platform-guard input defect: source/compiled forms and existing gate integration."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import audit_startup_contract as source_audit
import audit_upload_startup as native_audit
import upload_size_gate as delivery_gate

HERE = Path(__file__).resolve().parent


def component(body, extra='', params=''):
    return ('cc.Class({extends:cc.Component,onLoad:function(' + params + '){' + body + '}' + extra + '});').encode()


BIND = "this.node.on('click',this.play,this);"
BAD = component('if(!CC_WECHATGAME){' + BIND + '}')


class PlatformInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which('node')
        if not cls.node:
            raise RuntimeError('Node.js is required, do not silently skip these checks')

    def scan(self, code):
        rc, _, result, _ = native_audit.parse_package_source(
            code, self.node, native_audit.parser_fingerprint())
        self.assertEqual(rc, 0, result)
        return result['platform_input_bindings']

    def rejected(self, code):
        scan = self.scan(code)
        self.assertTrue(scan['findings'], scan)
        return scan['findings'][0]

    def accepted(self, code):
        scan = self.scan(code)
        self.assertFalse(scan['findings'], scan)
        self.assertFalse(scan['unresolved'], scan)

    def test_original_guard_exposes_missing_true_binding(self):
        row = self.rejected(BAD)
        self.assertEqual(row['missing_when'], {'CC_WECHATGAME': True})
        self.assertEqual(row['bound_when'], {'CC_WECHATGAME': False})

    def test_actual_release_short_circuit_and_button_alias_shape(self):
        self.rejected(component('CC_WECHATGAME||(this.progressBar.node.active=!1,'
            'this.node.getComponent(cc.Button).node.on("click",this.play,this))'))

    def test_early_return(self):
        self.rejected(component('if(CC_WECHATGAME)return;' + BIND))

    def test_boolean_alias(self):
        self.rejected(component('var legacy=CC_WECHATGAME;if(!legacy){' + BIND + '}'))

    def test_global_qualified_flag_and_alias(self):
        self.rejected(component('if(!window.CC_WECHATGAME){' + BIND + '}'))
        self.rejected(component('var legacy=globalThis["CC_WECHATGAME"];if(!legacy){' + BIND + '}'))

    def test_unrelated_object_property_is_not_a_platform_macro(self):
        self.accepted(component('if(!this.CC_WECHATGAME){' + BIND + '}'))

    def test_button_node_local_alias(self):
        self.rejected(component('var btn=this.node.getComponent(cc.Button);'
            'if(!CC_BYTEDANCEGAME)btn.node.on("click",this.play,this);'))

    def test_conditional_expression_and_touch_symbol(self):
        self.rejected(component('CC_WECHATGAME?0:this.node.on(cc.Node.EventType.TOUCH_END,this.play,this);'))

    def test_local_helper(self):
        self.rejected(component('this.bindInput();',
            ',bindInput:function(){if(CC_WECHATGAME)return;' + BIND + '}'))

    def test_helper_parameters_and_local_scope(self):
        self.rejected(component('this.bindInput(this.node);',
            ',bindInput:function(node){if(CC_WECHATGAME)return;node.on("click",this.play,this);}'))
        self.accepted(component('var legacy=false;this.setup();if(!legacy){' + BIND + '}',
            ',setup:function(){var legacy=CC_WECHATGAME;}'))

    def test_nested_boolean_guards(self):
        self.rejected(component('if(!CC_WECHATGAME&&!CC_BYTEDANCEGAME){' + BIND + '}'))

    def test_typeof_guard(self):
        self.rejected(component('if(typeof CC_WECHATGAME!=="undefined"&&!CC_WECHATGAME){' + BIND + '}'))

    def test_unconditional_fix(self):
        self.accepted(component(BIND))

    def test_both_branches_bind_distinct_supported_handlers(self):
        self.accepted(component('if(CC_WECHATGAME){' + BIND +
            '}else{this.node.on("click",this.other,this);}'))

    def test_branch_hidden_node_is_not_a_dead_visible_button(self):
        self.accepted(component('if(CC_WECHATGAME){this.node.active=false;return;}' + BIND))

    def test_unconditional_binding_after_platform_specific_setup(self):
        self.accepted(component('if(CC_WECHATGAME)this.setupSDK();' + BIND))

    def test_unrelated_sdk_or_audio_branch_is_not_input(self):
        self.accepted(component('if(!CC_WECHATGAME)this.audio.playMusic();'))

    def test_comments_and_strings(self):
        self.accepted(component('// if(!CC_WECHATGAME)this.node.on("click",x);\n'
            'var text="CC_WECHATGAME || this.node.on";' + BIND))

    def test_local_shadowed_flag(self):
        self.accepted(component('if(!CC_WECHATGAME){' + BIND + '}', params='CC_WECHATGAME'))
        self.accepted(component('var CC_WECHATGAME=false;if(!CC_WECHATGAME){' + BIND + '}'))

    def test_shadowed_cc_and_non_cocos_objects(self):
        self.accepted(b'function example(cc){cc.Class({onLoad:function(){if(!CC_WECHATGAME){' + BIND.encode() + b'}}});}')
        self.accepted(b'const example={onLoad:function(){if(!CC_WECHATGAME){' + BIND.encode() + b'}}};')

    def test_direct_arrow_iife_is_not_skipped(self):
        self.rejected(component("(()=>{if(!CC_WECHATGAME){" + BIND + "}})();"))
        self.rejected(component("(()=>CC_WECHATGAME||this.node.on('click',this.play,this))();"))

    def test_regular_or_bound_function_iife_requires_review(self):
        for body in ["(function(){if(!CC_WECHATGAME){" + BIND + "}})();",
                     "(function(){if(!CC_WECHATGAME){" + BIND + "}}).call(this);"]:
            result = self.scan(component(body))
            self.assertFalse(result['findings'], result)
            self.assertTrue(result['unresolved'], result)

    def test_arrow_lexical_writes_or_async_context_require_review(self):
        for body in ["(()=>{var node=this.node;if(!CC_WECHATGAME)node.on('click',this.play,this);})();",
                     "var enabled=false;(()=>{enabled=CC_WECHATGAME;})();if(!enabled){" + BIND + "}",
                     "(async()=>{if(!CC_WECHATGAME){" + BIND + "}})();",
                     "(()=>{this.isLegacy=CC_WECHATGAME;})();if(!this.isLegacy){" + BIND + "}"]:
            result = self.scan(component(body))
            self.assertFalse(result['findings'], result)
            self.assertTrue(result['unresolved'], result)

    def test_hidden_arrow_branch_is_not_an_input_gap(self):
        self.accepted(component("(()=>{if(CC_WECHATGAME){this.node.active=false;return;}" + BIND + "})();"))

    def test_alternate_init_binding_is_review_not_component_failure(self):
        for extra in [",onEnable:function(){if(CC_WECHATGAME){" + BIND + "}}",
                      ",onEnable:function(){this.bindOther();},bindOther:function(){" + BIND + "}"]:
            result = self.scan(component('if(!CC_WECHATGAME){' + BIND + '}', extra))
            self.assertFalse(result['findings'], result)
            self.assertTrue(result['unresolved'], result)

    def test_other_init_visibility_change_is_review_not_visible_button_failure(self):
        for property_name in ['active', 'interactable', 'enabled']:
            result = self.scan(component('if(!CC_WECHATGAME){' + BIND + '}',
                ',onEnable:function(){this.node.' + property_name + '=!CC_WECHATGAME;}'))
            self.assertFalse(result['findings'], result)
            self.assertTrue(result['unresolved'], result)

    def test_alternative_input_event_is_not_total_input_loss(self):
        self.accepted(component("if(CC_WECHATGAME)this.node.on('touchend',this.play,this);"
                                "else this.node.on('click',this.play,this);"))

    def test_unrelated_other_lifecycle_sdk_listener_does_not_hide_gap(self):
        self.rejected(component('if(!CC_WECHATGAME){' + BIND + '}',
            ",onEnable:function(){this.sdk.on('close',this.afterAd,this);}"))

    def test_unsupported_control_flow_cannot_be_certified_by_this_scanner(self):
        result = self.scan(component('try{if(!CC_WECHATGAME){' + BIND + '}}catch(e){}'))
        self.assertTrue(result['unresolved'])

    def test_package_gate_reads_business_bundle_and_blocks(self):
        files = {'game.js': b"require('./assets/main/index.js');", 'game.json': b'{}',
                 'project.config.json': b'{"appid":"test"}', 'assets/main/index.js': BAD}
        before = native_audit.audit_files(files)
        self.assertFalse(before['passed'])
        self.assertTrue(any('platform input binding skipped' in e for e in before['errors']))
        self.assertEqual(before['platform_input_bindings']['findings'][0]['source'], 'assets/main/index.js')
        files['assets/main/index.js'] = component(BIND)
        after = native_audit.audit_files(files)
        self.assertTrue(after['passed'], after['errors'])

    def test_source_preflight_blocks_and_text_review_cannot_waive_proven_gap(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / 'assets').mkdir()
            (project / 'assets/start.js').write_bytes(BAD)
            hits = [h for h in source_audit.scan_source(project) if h['rule'] == 'platform_input_binding']
            self.assertEqual(len(hits), 1)
            (project / 'docs').mkdir()
            (project / 'docs/startup-contract-review.json').write_text(json.dumps({hits[0]['id']: 'browser clicked PLAY once'}))
            report = project / 'out.json'
            run = subprocess.run([sys.executable, str(HERE / 'audit_startup_contract.py'), '--project', str(project),
                                  '--source-only', '--out', str(report)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            data = json.loads(report.read_text())
            self.assertFalse(data['passed'])
            self.assertEqual(data['open_hits'], 1)

    def test_scanner_dependency_is_in_parse_cache_identity(self):
        self.assertEqual(len(native_audit.parser_fingerprint()), 3)

    def test_mandatory_zip_inspection_blocks_without_full_writer(self):
        files = {'game.js': b'boot();', 'game.json': b'{}', 'project.config.json': b'{"appid":"test"}',
                 'assets/main/index.js': BAD}
        with self.assertRaisesRegex(ValueError, 'platform input binding skipped'):
            delivery_gate.inspect_files(files)
        files['assets/main/index.js'] = component(BIND)
        result = delivery_gate.inspect_files(files)
        self.assertFalse(result['platform_input_bindings']['findings'])

    def test_delivery_refuses_unexecuted_input_scan(self):
        result = subprocess.CompletedProcess([], 0, '{"findings":[]}', '')
        with patch.object(delivery_gate.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'binding check did not run'):
                delivery_gate.enforce_tiktok_host({'game.js': b'boot();'})


if __name__ == '__main__':
    unittest.main()
