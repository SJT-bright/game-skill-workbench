'use strict';
// Each variant breaks one startup protection in a temporary copy; boot.test.js MUST fail for each.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var src = path.join(__dirname, '..', 'build-templates', 'bytedance');
var variants = [
  {name: 'no_stall_watchdog', file: 'main.js', before: "fail('stalled', token);", after: 'void 0;'},
  {name: 'old_attempt_not_ignored', file: 'main.js', before: 'function current() { return token === generation && !retryShown; }',
    after: 'function current() { return true; }'},
  {name: 'background_time_counted', file: 'main.js', before: 'if (token !== generation || hiddenAt) { lastTick = now; return; }', after: 'if (token !== generation) { lastTick = now; return; }'},
  {name: 'bundle_error_ignored', file: 'main.js', before: "if (error) fail(name, token, error);\n        else next();", after: 'next();'},
  {name: 'touch_fix_missing', file: 'main.js', before: "try { require('./touch-coordinates').install(cc); } catch (touchError) { console.error('touch fix', touchError); }", after: ''},
  // v1.2 (D6 items 1, 3, 8)
  {name: 'load_guard_not_installed', file: 'main.js', before: '    installLoadGuard();\n', after: ''},
  {name: 'file_not_requested_again', file: 'main.js', before: 'if (policy.parallelAfter && attempts === 1 && waited >= policy.parallelAfter) again();', after: ''},
  {name: 'late_answer_dropped', file: 'main.js', before: 'if (done) return;                       // first answer already won\n              if (!error) { finish(null, value); return; }\n              if (mine !== attempts) return;',
    after: 'if (done) return;\n              if (mine !== attempts) return;\n              if (!error) { finish(null, value); return; }'},
  {name: 'background_counted_in_file_guard', file: 'main.js', before: 'if (!hiddenAt) waited += Math.min(1000, Math.max(0, now - last));', after: 'waited += now - last;'},
  {name: 'scene_error_silent', file: 'main.js', before: "if (error) { fail('scene', token, error); return; }\n        launched();", after: 'launched();'},
  {name: 'scene_not_watched', file: 'main.js', before: "      visibleProgress(95);\n      engineRunning = true;\n      cc.game.run(option, loadScene);", after: "      visibleProgress(100);\n      clearAttempt();\n      engineRunning = true;\n      cc.game.run(option, loadScene);"},
  {name: 'exception_not_caught', file: 'main.js', before: 'try { return fn.apply(this, arguments); } catch (error) { fail(name, token, error); }', after: 'return fn.apply(this, arguments);'},
  {name: 'setup_exception_not_caught', file: 'main.js', before: "    } catch (error) { fail('startup', token, error); }", after: '    } finally {}'},
  {name: 'long_frame_counted_fully', file: 'main.js', before: 'idle += Math.min(1000, Math.max(0, now - lastTick));', after: 'idle += now - lastTick;'},
  // v1.3 (kit 2.0)
  {name: 'storage_guard_missing', file: 'main.js', before: "  try { require('./storage-guard')(cc, platform); } catch (storageError) { console.error('storage guard', storageError); }\n", after: ''},
  {name: 'storage_guard_error_breaks_startup', file: 'main.js', before: "try { require('./storage-guard')(cc, platform); } catch (storageError) { console.error('storage guard', storageError); }", after: "require('./storage-guard')(cc, platform);"},
  {name: 'login_missing', file: 'main.js', before: "safeCall('login', {success: noop, fail: noop, complete: noop});", after: ''},
  {name: 'login_unguarded', file: 'main.js', before: "safeCall('login', {success: noop, fail: noop, complete: noop});", after: 'platform.login({});'},
  {name: 'login_sent_every_boot', file: 'main.js', before: 'if (!window.__tiktokKitLoginSent && platform', after: 'if (platform'},
  {name: 'webp_probe_always_on', file: 'main.js', before: 'if (window.__TIKTOK_KIT_WEBP_PROBE__ === true) {', after: 'if (true) {'},
  {name: 'webp_probe_not_run', file: 'main.js', before: "if (webpProbe && caps && !caps.webp) { visibleProgress(engineRunning ? 95 : 2); webpProbe(window, begin); return; }", after: ''},
  {name: 'webp_probe_after_scripts', file: 'main.js', before: 'webpProbe(window, begin); return; }', after: 'begin(); webpProbe(window, function () {}); return; }'},
  // v1.4 (W-D3): image decode guard on the real 2.4 parser
  {name: 'late_retry_shows_loading_again', file: 'main.js', before: "    if (sceneUp) { clearAttempt(); safeCall('hideLoading', {}); return; }\n", after: ''},
  {name: 'image_decode_not_guarded', file: 'main.js', before: '        parser.register(ext, bounded(decode, downloader, FILE));\n', after: ''},
  {name: 'image_guard_reads_private_table', file: 'main.js', before: 'var decode = downloader.downloadDomImage;', after: 'var decode = parser._parsers && parser._parsers[\'.png\'];'},
  {name: 'image_guard_wraps_parse_entry', file: 'main.js',
    before: "      ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.tiff', '.webp', '.image'].forEach(function (ext) {\n        parser.register(ext, bounded(decode, downloader, FILE));\n      });",
    after: "      var parse = parser.parse;\n      parser.parse = function (id, file, type, options, done) { bounded(function (f, o, cb) { parse.call(parser, id, f, type, o, cb); }, parser, FILE)(file, options, done); };"},
  // v1.5 (W-F1a): per-file re-request is progress, the watchdog waits for a guarded file
  {name: 'watchdog_ignores_waiting_file', file: 'main.js', before: "if (idle > STALL_MS && !guardsWaiting) fail('stalled', token);", after: "if (idle > STALL_MS) fail('stalled', token);"},
  {name: 'guard_count_never_released', file: 'main.js', before: 'guardsWaiting = Math.max(0, guardsWaiting - 1);', after: ''},
  {name: 'rerequest_not_counted_as_progress', file: 'main.js', before: 'function again() { if (!done) { noteProgress(); attempt(); } }', after: 'function again() { if (!done) attempt(); }'},
  // v1.6 (W-G1): the first Retry after a failed launch scene works
  {name: 'failed_scene_not_released', file: 'main.js', before: 'if (sceneFailed) { sceneFailed = false; releaseFailedScene(); }', after: 'if (sceneFailed) { sceneFailed = false; }'},
  {name: 'failed_scene_released_under_wrong_id', file: 'main.js', before: "var id = info.uuid + '@import';", after: 'var id = info.uuid;'},
  {name: 'superseded_scene_failure_not_recorded', file: 'main.js',
    before: "        if (error) { fail('scene', token, error); return; }\n        launched();\n      });\n      var found = cc.director.loadScene(settings.launchScene, function (error) {\n        if (error) sceneFailed = true;",
    after: "        if (error) { sceneFailed = true; fail('scene', token, error); return; }\n        launched();\n      });\n      var found = cc.director.loadScene(settings.launchScene, function (error) {\n        void 0;"}
];
var results = variants.map(function (v) {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'boot-neg-'));
  fs.readdirSync(src).forEach(function (f) { fs.copyFileSync(path.join(src, f), path.join(dir, f)); });
  var file = path.join(dir, v.file), text = fs.readFileSync(file, 'utf8'), applied = text.indexOf(v.before) >= 0;
  if (applied) fs.writeFileSync(file, text.replace(v.before, v.after));
  var r = child.spawnSync(process.execPath, [path.join(__dirname, 'boot.test.js')],
    {encoding: 'utf8', timeout: 20000, env: Object.assign({}, process.env, {BOOT_DIR: dir})});
  fs.rmSync(dir, {recursive: true, force: true});
  var caught = [];
  try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
  return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
});
console.log(JSON.stringify(results, null, 2));
if (results.some(function (r) { return !r.test_failed_as_expected; })) process.exitCode = 1;
