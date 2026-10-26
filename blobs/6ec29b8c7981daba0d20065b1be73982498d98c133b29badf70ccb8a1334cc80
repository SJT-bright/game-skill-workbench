"""Portable source-inventory calibration; never executes input/game code."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import input_owner_inventory as inventory
import button_state_check as buttons
import logic_regressions as regressions
from test_button_state_check import fixture


class InputOwnerInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='input source inventory ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'assets').mkdir()
        inventory._CACHE.clear()

    def source(self, code, extension='.js'):
        p = self.root / 'assets' / ('controls' + extension)
        p.write_text(code)
        return p

    def status(self, code, extension='.js'):
        return inventory.inspect_source(self.source(code, extension))['status']

    def test_comments_strings_and_regex_are_not_touch_owners(self):
        cases = [
            '// TOUCH_START pointerId\nexport const price=10;',
            '/* node.on(TOUCH_START,e=>e.getID()); */ const x=1;',
            'export const help="touchstart/getID are examples";',
            'const pattern=/TOUCH_START getID pointerId/;',
            'const help=`TOUCH_START touchId getID`;',
            'function f(){return /TOUCH_START getID/;}',
            "const calculate=new Function('x','return x*2');",
        ]
        for code in cases:
            with self.subTest(code=code):
                self.assertEqual(self.status(code), 'none')

    def test_unused_identifiers_and_type_only_declarations_are_not_owners(self):
        cases = [
            ('const pointerId=3; const TOUCH_START=1;', '.js'),
            ("node.on('touchstart',()=>{});function metadata(pointerId){return 3}", '.js'),
            ("node.on('touchstart',()=>{});const obj={pointerId:1};", '.js'),
            ('interface EventDoc { TOUCH_START:string; getID():number; pointerId:number }', '.ts'),
            ('import {pointerId} from "metadata"; const help="TOUCH_START";', '.js'),
        ]
        for code, ext in cases:
            with self.subTest(code=code):
                self.assertEqual(self.status(code, ext), 'none')

    def test_real_input_registration_and_identity_are_owners(self):
        cases = [
            "const id=event.getID(); node.on(TOUCH_START,onStart);",
            "node.on('touchstart',e=>{this.touchId=e.getID()});",
            "node.on('touch-start',e=>{this.touchId=e.getID()});",
            "canvas.addEventListener('pointerdown',e=>{active=e.pointerId});",
            "tt.onTouchStart(e=>{this.touchId=e.touchId});",
            "node['on'](EventType['TOUCH_START'], e=>{this['touchId']=e['getID']()});",
            "node.once(`touchstart`,e=>{this.touchId=e.getID()});",
            r"node.on('touch\u0073tart',e=>{this['touch\u0049d']=e['get\u0049D']()});",
        ]
        for code in cases:
            with self.subTest(code=code):
                self.assertEqual(self.status(code), 'owner')

    def test_finite_event_registration_and_owner_method_aliases_are_covered(self):
        cases = [
            'const down=Node.EventType.TOUCH_START;node.on(down,e=>{this.touchId=e.getID()});',
            "const start='touchstart'; const get=e.getID; node.on(start,()=>{this.touchId=get()});",
            'const{TOUCH_START:down}=Node.EventType;node.on(down,e=>{const{pointerId:id}=e;this.pointerId=id});',
            "const bind=tt.onTouchStart;bind(e=>{this.touchId=e.getID()});",
            "const{onTouchStart:bind}=tt;bind(e=>{this.touchId=e.getID()});",
            "const on=node.on.bind(node);const get=e.getID.bind(e);on('touchstart',()=>{this.touchId=get()});",
            "const{on}=node;on('touchstart',e=>{this.touchId=e.getID()});",
            "const{getID:get}=e;node.on('touchstart',()=>{this.touchId=get()});",
        ]
        for code in cases:
            with self.subTest(code=code):
                self.assertEqual(self.status(code), 'owner')

    def test_common_typescript_owner_is_covered_without_transpiler(self):
        code = """@ccclass('Touch') export class Touch extends Component {
          private touchId:number|null=null;
          onLoad(){this.node.on(Node.EventType.TOUCH_START,this.start,this)}
          start(e:EventTouch):void{this.touchId=e.getID()}
        }"""
        self.assertEqual(self.status(code, '.ts'), 'owner')
        self.assertEqual(self.status('const down=Node.EventType.TOUCH_START as const;node.on(down,e=>{this.touchId=e.getID()});', '.ts'), 'owner')

    def test_unknown_protocol_dynamic_code_and_bad_input_cannot_be_absent(self):
        for code in [
            'node.on(config.inputEvent,e=>{this.touchId=e.getID()});',
            "node[registration]('touchstart',e=>{this.touchId=e.getID()});",
            "bindCustom('touchstart',e=>{this.touchId=e.getID()});",
            'const get=e.getID;external(get);node.on(TOUCH_START,onStart);',
            'const bind=tt.onTouchStart;external(bind,e=>{this.touchId=e.getID()});',
            "eval(\"node.on('touchstart',e=>this.touchId=e.getID())\");",
            "new Function(\"TOUCH_START getID\");",
            'TOUCH_START touchId getID',
            "node.on('touchstart', e=>{ this.touchId=e.getID()",
        ]:
            with self.subTest(code=code):
                self.assertEqual(self.status(code), 'unresolved')

    def test_both_consumers_agree_on_normal_and_real_and_unknown_sources(self):
        for code, wanted in [
            ('// TOUCH_START pointerId\nexport const price=10;', 'none'),
            ('export const help="touchstart/getID are examples";', 'none'),
            ("node.on('touchstart',e=>{this.touchId=e.getID()});", 'owner'),
            ('node.on(config.event,e=>{this.touchId=e.getID()});', 'unresolved'),
        ]:
            with self.subTest(code=code):
                p = self.source(code)
                plan, run = fixture(self.root)
                plan['business_sources'] = [buttons.file_ref(self.root, p)]
                run['business_sources'] = plan['business_sources']
                result = buttons.validate(plan, run, self.root)
                self.assertEqual(result['passed'], wanted == 'none', result)
                self.assertEqual(regressions.input_owner_sources(self.root), [] if wanted == 'none' else [p.resolve()])

    def test_pure_inventory_is_reused_across_consumers_and_invalidated_by_bytes(self):
        p = self.source("node.on('touchstart',e=>{this.touchId=e.getID()});")
        real_run = inventory.subprocess.run
        with patch.object(inventory.subprocess, 'run', wraps=real_run) as parse:
            first = inventory.inspect_source(p)
            self.assertEqual(first['status'], 'owner')
            self.assertEqual(regressions.input_owner_sources(self.root), [p.resolve()])
            self.assertEqual(parse.call_count, 1)
            first['status'] = 'none'
            self.assertEqual(inventory.inspect_source(p)['status'], 'owner')
            p.write_text('export const help="touchstart/getID are examples";')
            self.assertEqual(inventory.inspect_source(p)['status'], 'none')
            self.assertEqual(parse.call_count, 2)

    def test_new_files_are_batched_once_and_existing_sources_reuse_inventory(self):
        paths = []
        for index in range(6):
            p = self.root / 'assets' / ('owner' + str(index) + '.js')
            p.write_text("node.on('touchstart',e=>{this.touchId=e.getID()});const marker=" + str(index))
            paths.append(p)
        real_run = inventory.subprocess.run
        with patch.object(inventory.subprocess, 'run', wraps=real_run) as parse:
            self.assertEqual([r['status'] for r in inventory.inspect_sources(paths)], ['owner'] * 6)
            self.assertEqual(parse.call_count, 1)
            self.assertEqual(regressions.input_owner_sources(self.root), sorted(p.resolve() for p in paths))
            self.assertEqual(parse.call_count, 1)

    def test_missing_parser_runtime_is_unresolved_not_pass(self):
        p = self.source("node.on('touchstart',e=>{this.touchId=e.getID()});")
        with patch.object(inventory.shutil, 'which', return_value=None):
            self.assertEqual(inventory.inspect_source(p)['status'], 'unresolved')

    def test_full_assets_inventory_includes_commonjs_and_module_sources(self):
        for ext in ['.cjs', '.mjs']:
            with self.subTest(extension=ext):
                p = self.source("node.on('touchstart',e=>{this.touchId=e.getID()});", ext)
                self.assertIn(p.resolve(), regressions.input_owner_sources(self.root))


if __name__ == '__main__':
    unittest.main(verbosity=2)
