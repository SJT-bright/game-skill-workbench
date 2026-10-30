#!/usr/bin/env python3
"""TikTok gives touches only screenX/screenY; Cocos 2.4's converter and the Cocos 3.x minigame TouchInputSource both
read clientX/clientY (user 2026-10-28). Every Cocos 2.x and 3.x TikTok package is probed, whatever its adapter looks
like, only an installed coordinate fix passes, and a TikTok Cocos package whose probe cannot run never passes."""
from pathlib import Path
import unittest
from audit_upload_startup import audit_files

KIT = Path(__file__).resolve().parent.parent / 'assets/platform-kit/build-templates/bytedance'
# Cocos 2.4 CCInputManager.getTouchesByEvent shape: native (non-Firefox) path reads clientX/clientY only.
ENGINE = (b"var n={};var x={getTouchesByEvent:function(e,t){for(var o=[],i=this._glView,r,s,c=this._preTouchPoint,"
          b"a=e.changedTouches.length,l=0;l<a;l++)if(r=e.changedTouches[l]){var u;u=n.BROWSER_TYPE_FIREFOX===n.browserType?"
          b"i.convertToLocationInView(r.pageX,r.pageY,t):i.convertToLocationInView(r.clientX,r.clientY,t);"
          b"s=new cc.Touch(u.x,u.y,r.identifier);c=this.getPreTouch(s).getLocation();s._setPrevPoint(c.x,c.y);"
          b"this.setPreTouch(s);o.push(s)}return o},registerSystemEvent:function(){}};")

# Cocos 3.8 bytedance build shapes (minified as shipped): the engine copies `tt` with Object.keys/bind when cc is
# evaluated, and its minigame TouchInputSource subscribes through that copy and reads clientX/clientY.
ENGINE3 = (b'var to,eo,io={};$a=io,eo=tt,Object.keys(eo).forEach((function(t){"function"!=typeof eo[t]?$a[t]=eo[t]:'
           b'$a[t]=eo[t].bind(eo)})),io.tt={};var zB=function(){function t(){this._eventTarget=new Eo,this._registerEvent()}'
           b'var e=t.prototype;return e._registerEvent=function(){io.onTouchStart(this._createCallback("touch-start")),'
           b'io.onTouchMove(this._createCallback("touch-move")),io.onTouchEnd(this._createCallback("touch-end")),'
           b'io.onTouchCancel(this._createCallback("touch-cancel"))},e._createCallback=function(t){var e=this;return '
           b'function(i){for(var n=[],r=lh.windowSize,s=lh.devicePixelRatio,a=i.changedTouches.length,o=0;o<a;++o){'
           b'var h=i.changedTouches[o],u=h.identifier;if(null!==u){var l=e._getLocation(h,r,s),c=NB.getOrCreateTouch(u,l.x,l.y);'
           b'c&&("touch-end"!==t&&"touch-cancel"!==t||NB.releaseTouch(u),n.push(c))}}if(n.length>0){var f=new Kv(n,!1,t,'
           b'NB.getAllTouches());e._eventTarget.emit(t,f)}}},e._getLocation=function(t,e,i){var n=t.clientX*i,'
           b'r=e.height-t.clientY*i;return new hs(n,r)},e.on=function(t,e,i){this._eventTarget.on(t,e,i)},t}();')
# web-adapter.js stand-in: DOM touch listeners on tt plus the bound __globalAdapter copies, as the shipped adapter does.
WEB_ADAPTER = (b"window.__globalAdapter=window.__globalAdapter||{};['onTouchStart','onTouchMove','onTouchEnd','onTouchCancel']"
               b".forEach(function(k){window.__globalAdapter[k]=tt[k].bind(tt);});tt.onTouchStart(function(e){});")
# The SDK-wrapper fix shipped by Marlows r5 (marlow-touch.js) and Gimble's v9.1 (grotto-touch.js), reduced.
FIX3 = (b"module.exports=function(api){function point(v){if(!v||Number.isFinite(v.clientX)&&Number.isFinite(v.clientY))return v;"
        b"var c=Object.assign({},v);c.clientX=Number.isFinite(v.clientX)?v.clientX:v.screenX;"
        b"c.clientY=Number.isFinite(v.clientY)?v.clientY:v.screenY;return c;}"
        b"['Start','Move','End','Cancel'].forEach(function(s){var on=api['onTouch'+s];api['onTouch'+s]=function(fn){"
        b"return on.call(this,function(e){return fn.call(this,Object.assign({},e,{touches:Array.from(e.touches||[],point),"
        b"changedTouches:Array.from(e.changedTouches||[],point)}));});};});};")


def package(main=b"exports.ok=true;", game_extra=b""):
    return {'game.js': b"require('adapter-min.js');require('cocos/cocos2d-js-min.js');" + game_extra + b"require('./main');",
            'adapter-min.js': b"exports.ok=true;", 'cocos/cocos2d-js-min.js': ENGINE, 'main.js': main,
            'touch-coordinates.js': (KIT / 'touch-coordinates.js').read_bytes()}


# Creator 2.4.5+ minified shape (Basil): the converter passes a closure Vec2 `a` as 4th argument.
ENGINE_245 = (b"var n={},a={};var x={getTouchesByEvent:function(t,e){for(var i,r,s,o=[],c=this._glView,l=this._preTouchPoint,"
              b"h=t.changedTouches.length,u=0;u<h;u++)if(i=t.changedTouches[u]){var f;f=n.BROWSER_TYPE_FIREFOX===n.browserType?"
              b"c.convertToLocationInView(i.pageX,i.pageY,e,a):c.convertToLocationInView(i.clientX,i.clientY,e,a),"
              b"null!=i.identifier?(r=new cc.Touch(f.x,f.y,i.identifier),s=this.getPreTouch(r).getLocation(),"
              b"r._setPrevPoint(s.x,s.y),this.setPreTouch(r)):(r=new cc.Touch(f.x,f.y))._setPrevPoint(l.x,l.y),l.x=f.x,"
              b"l.y=f.y,o.push(r)}return o},registerSystemEvent:function(t){}};")
# Non-minified debug build cocos/cocos2d-js.js (MergeShot2048 v82): named function, `sys` and `_vec2` closures.
ENGINE_DEBUG = (b"var sys={},_vec2={};var x={\n      getTouchesByEvent: function getTouchesByEvent(event, pos) {\n"
                b"        var touchArr = [], locView = this._glView;\n        var touch_event, touch, preLocation;\n"
                b"        for (var i = 0; i < event.changedTouches.length; i++) {\n          touch_event = event.changedTouches[i];\n"
                b"          if (touch_event) {\n            var location = void 0;\n            location = sys.BROWSER_TYPE_FIREFOX === "
                b"sys.browserType ? locView.convertToLocationInView(touch_event.pageX, touch_event.pageY, pos, _vec2) : "
                b"locView.convertToLocationInView(touch_event.clientX, touch_event.clientY, pos, _vec2);\n"
                b"            touch = new cc.Touch(location.x, location.y, touch_event.identifier);\n"
                b"            preLocation = this.getPreTouch(touch).getLocation();\n"
                b"            touch._setPrevPoint(preLocation.x, preLocation.y);\n            this.setPreTouch(touch);\n"
                b"            touchArr.push(touch);\n          }\n        }\n        return touchArr;\n      },\n"
                b"      registerSystemEvent: function registerSystemEvent(element) {}\n};")
# Basil 0.4.0 tiktok-input.js (reduced): wraps the SDK onTouch* registrations before the adapter binds them.
TIKTOK_INPUT = (b"var sdk=typeof TTMinis!=='undefined'&&TTMinis.game?TTMinis.game:typeof tt!=='undefined'?tt:null;"
                b"if(sdk){var finite=function(v){return typeof v==='number'&&isFinite(v)};var point=function(p){var out=Object.assign({},p);"
                b"if(!finite(out.clientX)&&finite(out.screenX))out.clientX=out.screenX;"
                b"if(!finite(out.clientY)&&finite(out.screenY))out.clientY=out.screenY;return out};"
                b"['Start','Move','End','Cancel'].forEach(function(kind){var on='onTouch'+kind,register=sdk[on];"
                b"if(typeof register==='function')sdk[on]=function(callback){return register.call(this,function(event){"
                b"var e=Object.assign({},event);if(Array.isArray(e.touches))e.touches=e.touches.map(point);"
                b"if(Array.isArray(e.changedTouches))e.changedTouches=e.changedTouches.map(point);return callback.call(this,e)})}})}")


def input_package(name='tiktok-input.js', declare=False, late=False, require=None):
    """Basil layout: game.js requires an SDK touch wrapper before adapter-min.js; no converter fix."""
    req = (b"require('./" + name.encode() + b"');") if require is None else require
    decl = (b"// tiktok-touch-adapter: ./" + name.encode() + b"\n") if declare else b""
    game = decl + (b"" if late else req) + b"require('adapter-min.js');" + (req if late else b"") + \
        b"require('cocos/cocos2d-js-min.js');require('./main');"
    return {'game.js': game, 'adapter-min.js': b"exports.ok=true;", 'cocos/cocos2d-js-min.js': ENGINE_245,
            'main.js': b"exports.ok=true;", name: TIKTOK_INPUT}


def package3(before=b"", after=b"", late=b"", fix=FIX3):
    """Cocos 3.x TikTok layout: game.js -> web-adapter.js -> SystemJS -> cocos-js engine."""
    game = (b"loadCC();function loadCC(){" + before + b"require('./web-adapter');" + after +
            b"require('src/polyfills.bundle.js');require('src/system.bundle.js');System.warmup({});"
            b"System.import('./application.js').then(function(){" + late + b"});}")
    return {'game.js': game, 'game.json': b'{}', 'project.config.json': b'{"appid":"fixture"}',
            'web-adapter.js': WEB_ADAPTER, 'touch-fix.js': fix, 'src/polyfills.bundle.js': b"exports.ok=1;",
            'src/system.bundle.js': b"exports.ok=1;", 'cocos-js/cc.js': ENGINE3}


class TikTokTouchCoordinates(unittest.TestCase):
    def touch(self, files):
        report = audit_files(files)
        return report['touch_coordinates'], [e for e in report['errors'] if 'touch' in e.lower()]

    def test_missing_fix_is_rejected_even_without_tt_adapter_marker(self):
        probe, errors = self.touch(package())
        self.assertIsNotNone(probe, 'Cocos 2.x package must be probed, not skipped')
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_platform_kit_main_js_install_passes(self):
        probe, errors = self.touch(package(main=(KIT / 'main.js').read_bytes()))
        self.assertTrue(probe['passed'], probe)
        self.assertEqual(errors, [])

    def test_game_js_install_passes(self):
        probe, errors = self.touch(package(game_extra=b"require('./touch-coordinates').install(cc);"))
        self.assertTrue(probe['passed'], probe)
        self.assertEqual(errors, [])

    def test_broken_fix_file_is_rejected(self):
        files = package(main=(KIT / 'main.js').read_bytes())
        files['touch-coordinates.js'] = b"module.exports.install=function(cc){};"
        probe, errors = self.touch(files)
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    # v7.5 (Basil D2 problem 3, MergeShot2048 D6 item 5, Germ2048 D7 item 5)
    def test_strict_kit_layout_main_js_line_only_passes_and_fails_without_it(self):
        probe, errors = self.touch(package(main=(KIT / 'main.js').read_bytes()))
        self.assertTrue(probe['passed'], probe)
        main = (KIT / 'main.js').read_bytes().replace(b"require('./touch-coordinates').install(cc);", b"void 0;")
        probe, errors = self.touch(package(main=main))
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_main_js_line_counts_only_when_game_js_loads_main(self):
        files = package(main=(KIT / 'main.js').read_bytes())
        files['game.js'] = files['game.js'].replace(b"require('./main');", b"")
        probe, errors = self.touch(files)
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_creator_245_closure_vec2_alias_is_supported(self):
        files = package(main=(KIT / 'main.js').read_bytes())
        files['cocos/cocos2d-js-min.js'] = ENGINE_245
        probe, errors = self.touch(files)
        self.assertTrue(probe['passed'], probe)
        self.assertEqual(errors, [])
        files['main.js'] = b"exports.ok=true;"
        probe, errors = self.touch(files)
        self.assertFalse(probe['passed'])

    def test_debug_engine_cocos2d_js_is_probed(self):
        files = package(game_extra=b"require('./touch-coordinates').install(cc);")
        del files['cocos/cocos2d-js-min.js']
        files['cocos/cocos2d-js.js'] = ENGINE_DEBUG
        probe, errors = self.touch(files)
        self.assertIsNotNone(probe)
        self.assertTrue(probe['passed'], probe)
        files['game.js'] = files['game.js'].replace(b"require('./touch-coordinates').install(cc);", b"")
        probe, errors = self.touch(files)
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_tiktok_input_before_adapter_passes(self):
        probe, errors = self.touch(input_package())
        self.assertTrue(probe['passed'], probe)
        self.assertEqual(errors, [])

    def test_tiktok_input_deleted_is_rejected(self):
        files = input_package()
        del files['tiktok-input.js']
        probe, errors = self.touch(files)
        self.assertFalse(probe['passed'])
        self.assertTrue(any('missing' in e for e in errors), errors)
        probe, errors = self.touch(input_package(require=b""))
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_tiktok_input_after_adapter_is_rejected(self):
        probe, errors = self.touch(input_package(late=True))
        self.assertFalse(probe['passed'])
        self.assertTrue(any('too late' in e for e in errors), errors)

    def test_declared_adapter_module_passes_and_undeclared_name_fails(self):
        files = input_package(name='my-input.js', declare=True)
        probe, errors = self.touch(files)
        self.assertTrue(probe['passed'], probe)
        probe, errors = self.touch(input_package(name='my-input.js'))
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_tiktok_input_that_drops_screen_coordinates_is_rejected(self):
        files = input_package()
        files['tiktok-input.js'] = files['tiktok-input.js'].replace(b"out.clientX=out.screenX", b"out.clientX=undefined")
        probe, errors = self.touch(files)
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)


class Cocos3TikTokTouchCoordinates(unittest.TestCase):
    def audit(self, files):
        report = audit_files(files)
        return report, report['touch_coordinates'], [e for e in report['errors'] if 'touch' in e.lower()]

    def test_cocos3_without_fix_is_rejected_with_non_finite_coordinates(self):
        report, probe, errors = self.audit(package3())
        self.assertIsNotNone(probe, 'Cocos 3.x package must be probed, not skipped')
        self.assertEqual(probe['schema'], 'cocos3_touch_coordinates.v1')
        self.assertFalse(probe['passed'])
        self.assertFalse(report['passed'])
        self.assertTrue(any('Cocos3' in e and 'NaN' in e for e in errors), errors)

    def test_cocos3_fix_before_web_adapter_passes(self):
        report, probe, errors = self.audit(package3(before=b"require('./touch-fix')(tt);"))
        self.assertTrue(probe['passed'], probe)
        self.assertEqual(errors, [])
        self.assertTrue(report['passed'], report['errors'])
        self.assertEqual(probe['prefix']['executed_modules'], ['game.js', 'touch-fix.js', 'web-adapter.js'])

    def test_cocos3_fix_after_web_adapter_but_before_engine_passes(self):
        report, probe, errors = self.audit(package3(after=b"require('./touch-fix')(tt);"))
        self.assertTrue(probe['passed'], probe)
        self.assertEqual(errors, [])

    def test_cocos3_fix_installed_after_engine_load_is_rejected(self):
        report, probe, errors = self.audit(package3(late=b"require('./touch-fix')(tt);"))
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_cocos3_fix_that_maps_outside_the_screen_is_rejected(self):
        report, probe, errors = self.audit(package3(before=b"require('./touch-fix')(tt);",
                                                    fix=FIX3.replace(b":v.screenX;", b":v.screenX+1e4;")))
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)

    def test_cocos3_finite_in_screen_but_wrong_point_is_rejected(self):
        # Cocos 3.8 Vec2 turns a NaN location into 0, so an unconverted tap is finite and on-screen at (0, 0);
        # a halved coordinate is also on-screen. Both must fail on position.
        report, probe, errors = self.audit(package3(before=b"require('./touch-fix')(tt);",
                                                    fix=FIX3.replace(b":v.screenX;", b":v.screenX*0.5;")))
        self.assertFalse(probe['passed'])
        self.assertTrue(errors)
        report, probe, errors = self.audit(package3())
        start = next(r for r in probe['rows'] if r['id'] == 'sdk_screen_start')
        self.assertEqual(start['observed'], [{'id': 0, 'x': 0, 'y': 0}])
        self.assertEqual(start['raw_location'], [{'x': 'NaN', 'y': 'NaN'}])

    def test_cocos3_startup_prefix_failure_is_rejected(self):
        report, probe, errors = self.audit(package3(before=b"require('./touch-fix')(tt);",
                                                    fix=b"module.exports=function(api){throw Error('boom');};"))
        self.assertFalse(probe['passed'])
        self.assertTrue(any('boom' in e for e in errors), errors)


class NullTouchProbeIsNotAPass(unittest.TestCase):
    def test_unrecognised_cocos3_engine_fails_with_reason(self):
        files = package3(before=b"require('./touch-fix')(tt);")
        files['cocos-js/cc.js'] = b"var engine=true;"
        report = audit_files(files)
        self.assertIsNone(report['touch_coordinates'])
        self.assertFalse(report['passed'])
        self.assertTrue(any('touch coordinates unverified' in e for e in report['errors']), report['errors'])

    def test_unrecognised_cocos2_engine_fails_with_reason(self):
        files = package(main=(KIT / 'main.js').read_bytes())
        files['adapter-min.js'] = b"tt.onTouchStart(function(e){});"
        files['cocos/cocos2d-js-min.js'] = b"var engine=true;"
        report = audit_files(files)
        self.assertIsNone(report['touch_coordinates'])
        self.assertFalse(report['passed'])
        self.assertTrue(any('touch coordinates unverified' in e for e in report['errors']), report['errors'])

    def test_non_cocos_package_keeps_null_without_touch_error(self):
        files = {'game.js': b"require('./a');", 'a.js': b"exports.ok=1;", 'game.json': b'{}',
                 'project.config.json': b'{"appid":"fixture"}'}
        report = audit_files(files)
        self.assertIsNone(report['touch_coordinates'])
        self.assertTrue(report['passed'], report['errors'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
