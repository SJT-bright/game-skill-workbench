'use strict';
// Runs SnakeVSBlock v32's original component tests against THIS kit's RewardedService.js and
// TikTokMissionService.js (with Snake's original PlatformConfig), in a temporary folder.
// Proves the kit copies behave exactly like the files that passed on device in SnakeVSBlock.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var kit = path.join(__dirname, '..', '..', 'assets', 'tiktok-platform');
var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kit-snake-'));
['RewardedService.js', 'TikTokMissionService.js'].forEach(function (f) {
  fs.copyFileSync(path.join(kit, f), path.join(dir, f));
});
fs.copyFileSync(path.join(__dirname, 'PlatformConfig.snake.js'), path.join(dir, 'PlatformConfig.js'));
['platform-components.test.js', 'sdk-resolution.test.js', 'negative-controls.js'].forEach(function (f) {
  fs.copyFileSync(path.join(__dirname, f), path.join(dir, f));
});
var out = [];
['platform-components.test.js', 'sdk-resolution.test.js', 'negative-controls.js'].forEach(function (f) {
  var r = child.spawnSync(process.execPath, [path.join(dir, f)], {cwd: dir, encoding: 'utf8', timeout: 30000});
  var passed = r.status === 0, detail = '';
  try {
    var json = JSON.parse(r.stdout.slice(r.stdout.indexOf('{')));
    var list = json.results || json.tests || [];
    detail = list.length + ' cases';
    if (f === 'negative-controls.js') passed = passed && list.every(function (x) { return x.expected_failure_observed; });
    else passed = passed && list.every(function (x) { return x.status === 'passed'; });
  } catch (_) { detail = 'no JSON output'; }
  out.push({file: f, passed: passed, exit: r.status, detail: detail, stderr: passed ? '' : String(r.stderr).slice(0, 400)});
});
fs.rmSync(dir, {recursive: true, force: true});
console.log(JSON.stringify(out, null, 2));
if (out.some(function (x) { return !x.passed; })) process.exitCode = 1;
