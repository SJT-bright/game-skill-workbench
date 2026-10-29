'use strict';
// Proves kit.test.js can catch real mistakes: each variant breaks one guarantee in a temporary copy
// of assets/tiktok-platform (files on disk are never changed). Every variant MUST make kit.test.js fail.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var src = path.join(__dirname, '..', 'assets', 'tiktok-platform');
var variants = [
  {name: 'coming_back_does_not_cancel_old_query', file: 'MissionFlow.js',
    before: 'this.missions.onResume();          // old query is cancelled and its lock released\n  this.version++; this.op++;',
    after: ''},
  {name: 'old_answer_can_update_panel', file: 'MissionFlow.js',
    before: 'if (!isCurrent() || op !== self.op) return;\n    self.pendingCheck = null;', after: 'self.pendingCheck = null;'},
  {name: 'failed_save_reported_as_success', file: 'MissionFlow.js',
    before: 'if (result.ok) {', after: 'if (true) {'},
  {name: 'non_success_result_is_silent', file: 'MissionFlow.js',
    before: "self.message = r.status === 'unsupported' && !self.native ? TEXT.preview : r.message;\n    self._render();\n  });\n  return this.pendingCheck;",
    after: '});\n  return this.pendingCheck;'},
  {name: 'no_own_timer_by_default', file: 'MissionFlow.js',
    before: 'options.missionTimeoutMs ? {timeoutMs: options.missionTimeoutMs} : undefined',
    after: '{autoPoll: false, timeoutMs: options.missionTimeoutMs}'},
  {name: 'claim_flag_not_checked_before_paying', file: 'MissionFlow.js',
    before: "if (draft.platformClaims[kind] === true) return false;\n    draft.platformClaims[kind] = true;", after: ''},
  {name: 'memory_changed_before_save_verified', file: 'SaveStore.js',
    before: 'var error = this._write(draft);\n  if (error) return this._result(false, error);\n  this.data = draft;',
    after: 'this.data = draft;\n  var error = this._write(draft);\n  if (error) return this._result(false, error);'},
  {name: 'readback_not_compared', file: 'SaveStore.js',
    before: 'if (back === text) return null;', after: 'return null;'},
  {name: 'corrupt_save_treated_as_new', file: 'SaveStore.js',
    before: 'fresh.meta.recoveredFromCorrupt = this.now();', after: ''}
];
var results = variants.map(function (v) {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kit-neg-'));
  fs.readdirSync(src).forEach(function (f) { fs.copyFileSync(path.join(src, f), path.join(dir, f)); });
  var file = path.join(dir, v.file), text = fs.readFileSync(file, 'utf8');
  var applied = text.indexOf(v.before) >= 0;
  if (applied) fs.writeFileSync(file, text.replace(v.before, v.after));
  var r = child.spawnSync(process.execPath, [path.join(__dirname, 'kit.test.js')],
    {encoding: 'utf8', timeout: 20000, env: Object.assign({}, process.env, {KIT_DIR: dir})});
  fs.rmSync(dir, {recursive: true, force: true});
  var caught = [];
  try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
  return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
});
console.log(JSON.stringify(results, null, 2));
if (results.some(function (r) { return !r.test_failed_as_expected; })) process.exitCode = 1;
