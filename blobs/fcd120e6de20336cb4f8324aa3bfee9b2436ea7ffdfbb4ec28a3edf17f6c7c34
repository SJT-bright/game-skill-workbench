#!/usr/bin/env python3
"""TikTok gives touches only screenX/screenY; Cocos 2.4's converter reads clientX/clientY (user 2026-10-28).
Every Cocos 2.x package is probed, whatever its adapter looks like, and only the installed converter fix passes."""
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


def package(main=b"exports.ok=true;", game_extra=b""):
    return {'game.js': b"require('adapter-min.js');require('cocos/cocos2d-js-min.js');" + game_extra + b"require('./main');",
            'adapter-min.js': b"exports.ok=true;", 'cocos/cocos2d-js-min.js': ENGINE, 'main.js': main,
            'touch-coordinates.js': (KIT / 'touch-coordinates.js').read_bytes()}


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


if __name__ == '__main__':
    unittest.main(verbosity=2)
