'use strict';
// tools/check_kit_project.py on temporary projects built from the kit (files on disk are never changed).
// v1.2 (Germ2048, D7 item 6): settings/bytedance.json must exist with a numeric App ID; empty, testappId,
// non-numeric or a value different from PlatformConfig.js appId is refused. Needs python3.
var assert = require('assert'), fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var KIT = path.join(__dirname, '..');
var PY = process.env.PYTHON || 'python3';
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}
function copyDir(src, dst) {
  fs.mkdirSync(dst, {recursive: true});
  fs.readdirSync(src).forEach(function (f) {
    var s = path.join(src, f), d = path.join(dst, f);
    if (fs.statSync(s).isDirectory()) copyDir(s, d); else fs.copyFileSync(s, d);
  });
}
function project(bytedance, tweak) {
  var root = fs.mkdtempSync(path.join(os.tmpdir(), 'kit-check-'));
  fs.mkdirSync(path.join(root, 'assets', 'resources'), {recursive: true});
  fs.writeFileSync(path.join(root, 'project.json'), JSON.stringify({engine: 'cocos-creator-js', version: '2.4.15'}));
  copyDir(path.join(KIT, 'assets', 'tiktok-platform'), path.join(root, 'assets', 'tiktok-platform'));
  var cfg = path.join(root, 'assets', 'tiktok-platform', 'PlatformConfig.js');
  fs.writeFileSync(cfg, fs.readFileSync(cfg, 'utf8').replace("gameId: 'change-me'", "gameId: 'kitcheck'")
    .replace('normalLevelCoins: 0,', 'normalLevelCoins: 12,'));
  fs.writeFileSync(path.join(root, 'assets', 'resources.meta'), JSON.stringify({isBundle: true, compressionType: {bytedance: 'subpackage'}}));
  copyDir(path.join(KIT, 'build-templates'), path.join(root, 'build-templates'));
  // kit 2.0: parts/storage-guard.js sits next to main.js in the project (KIT_MANIFEST project_path)
  fs.copyFileSync(path.join(KIT, 'parts', 'storage-guard.js'), path.join(root, 'build-templates', 'bytedance', 'storage-guard.js'));
  if (bytedance !== null) {
    fs.mkdirSync(path.join(root, 'settings'));
    var text = bytedance === undefined ? fs.readFileSync(path.join(KIT, 'settings', 'bytedance.json'), 'utf8') : JSON.stringify(bytedance);
    fs.writeFileSync(path.join(root, 'settings', 'bytedance.json'), text);
  }
  if (tweak) tweak(root);
  return root;
}
function check(root) {
  var r = child.spawnSync(PY, ['-B', path.join(KIT, 'tools', 'check_kit_project.py'), '--project', root], {encoding: 'utf8', timeout: 60000});
  fs.rmSync(root, {recursive: true, force: true});
  var report = JSON.parse(r.stdout);
  return {code: r.status, errors: report.errors, warnings: report.warnings, version: report.kit_version};
}
function appidErrors(c) { return c.errors.filter(function (e) { return /bytedance\.json/.test(e) && /app ?id|missing/i.test(e); }); }

test('kit_template_project_passes', function () {
  var c = check(project());
  assert.strictEqual(c.code, 0, JSON.stringify(c.errors));
});
test('kit_template_appid_is_numeric_and_matches_platform_config', function () {
  var tpl = JSON.parse(fs.readFileSync(path.join(KIT, 'settings', 'bytedance.json'), 'utf8'));
  assert(/^[1-9][0-9]{9,24}$/.test(tpl.appid));
  assert(fs.readFileSync(path.join(KIT, 'assets', 'tiktok-platform', 'PlatformConfig.js'), 'utf8').indexOf("appId: '" + tpl.appid + "'") >= 0);
  assert.strictEqual(tpl.startSceneAssetBundle, false); assert.strictEqual(tpl.REMOTE_SERVER_ROOT, '');
});
[['missing_file', null], ['no_appid', {startSceneAssetBundle: false, REMOTE_SERVER_ROOT: ''}],
 ['empty_appid', {appid: '', startSceneAssetBundle: false, REMOTE_SERVER_ROOT: ''}],
 ['testappId', {appid: 'testappId', startSceneAssetBundle: false, REMOTE_SERVER_ROOT: ''}],
 ['non_numeric', {appid: 'tt12345abc', startSceneAssetBundle: false, REMOTE_SERVER_ROOT: ''}],
 ['other_app_id', {appid: '7000000000000000001', startSceneAssetBundle: false, REMOTE_SERVER_ROOT: ''}]].forEach(function (v) {
  test('appid_' + v[0] + '_is_refused', function () {
    var c = check(project(v[1]));
    assert.strictEqual(c.code, 1, v[0] + ' must fail');
    assert(appidErrors(c).length >= 1, JSON.stringify(c.errors));
  });
});
// kit 2.0 (v7.7): storage-guard.js next to main.js, HomeGrowthEntries.js, growthReward() fixed at 5B.
function edit(rel, from, to) {
  return function (root) { var p = path.join(root, rel); fs.writeFileSync(p, fs.readFileSync(p, 'utf8').replace(from, to)); };
}
var CFG = 'assets/tiktok-platform/PlatformConfig.js';
test('kit2_report_names_kit_version_2', function () {
  var c = check(project());
  assert.strictEqual(c.version, '2.0');
});
[['storage_guard_missing', function (root) { fs.unlinkSync(path.join(root, 'build-templates', 'bytedance', 'storage-guard.js')); }, /storage-guard\.js/],
 ['storage_guard_changed', edit('build-templates/bytedance/storage-guard.js', 'SAVESTORE_KEY.test', 'false &&'), /storage-guard\.js was changed/],
 ['home_entries_missing', function (root) { fs.unlinkSync(path.join(root, 'assets', 'tiktok-platform', 'HomeGrowthEntries.js')); }, /HomeGrowthEntries\.js/],
 ['home_entries_changed', edit('assets/tiktok-platform/HomeGrowthEntries.js', 'Available in TikTok', 'Done'), /HomeGrowthEntries\.js was changed/],
 ['growth_reward_amount_changed', edit(CFG, 'config.GROWTH_REWARD_B = 5;', 'config.GROWTH_REWARD_B = 10;'), /growthReward/],
 ['growth_reward_removed', edit(CFG, 'config.growthReward = function', 'config.unused = function'), /growthReward/],
 ['normal_level_coins_unset', edit(CFG, 'normalLevelCoins: 12,', 'normalLevelCoins: 0,'), /normalLevelCoins/],
 ['main_js_v12_line_removed', edit('build-templates/bytedance/main.js', "require('./storage-guard')(cc, platform);", ''), /main\.js was changed/]].forEach(function (v) {
  test('kit2_' + v[0] + '_is_refused', function () {
    var c = check(project(undefined, v[1]));
    assert.strictEqual(c.code, 1, v[0] + ' must fail');
    assert(c.errors.some(function (e) { return v[2].test(e); }), JSON.stringify(c.errors));
  });
});
test('kit2_own_file_in_build_templates_is_a_warning_only', function () {
  var c = check(project(undefined, function (root) {
    fs.writeFileSync(path.join(root, 'build-templates', 'bytedance', 'native-load-guard.js'), 'module.exports = 1;\n');
  }));
  assert.strictEqual(c.code, 0, JSON.stringify(c.errors));
  assert(c.warnings.some(function (w) { return /native-load-guard\.js/.test(w); }), JSON.stringify(c.warnings));
});
test('kit2_direct_check_shortcut_call_is_a_warning', function () {
  var c = check(project(undefined, function (root) {
    fs.writeFileSync(path.join(root, 'assets', 'Home.js'), 'tt.checkShortcut({success: function () {}});\n');
  }));
  assert(c.warnings.some(function (w) { return /Home\.js/.test(w); }), JSON.stringify(c.warnings));
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
console.log(JSON.stringify({suite: 'check_kit_project', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
if (failed.length) process.exitCode = 1;
