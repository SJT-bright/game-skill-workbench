'use strict';
// Each variant breaks one startup protection in a temporary copy; boot.test.js MUST fail for each.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var src = path.join(__dirname, '..', 'build-templates', 'bytedance');
var variants = [
  {name: 'no_stall_watchdog', file: 'main.js', before: "fail('stalled', token);", after: 'void 0;'},
  {name: 'old_attempt_not_ignored', file: 'main.js', before: 'function current() { return token === generation && !retryShown; }',
    after: 'function current() { return true; }'},
  {name: 'background_time_counted', file: 'main.js', before: 'if (token !== generation || hiddenAt) return;', after: 'if (token !== generation) return;'},
  {name: 'bundle_error_ignored', file: 'main.js', before: "if (error) fail(name, token);\n        else next();", after: 'next();'},
  {name: 'touch_fix_missing', file: 'main.js', before: "try { require('./touch-coordinates').install(cc); } catch (touchError) { console.error('touch fix', touchError); }", after: ''}
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
