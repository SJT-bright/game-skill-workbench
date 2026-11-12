'use strict';
// Proves kit.test.js can catch real mistakes: each variant breaks one guarantee in a temporary copy
// of assets/tiktok-platform (files on disk are never changed). Every variant MUST make kit.test.js fail.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var src = path.join(__dirname, '..', 'assets', 'tiktok-platform');
var variants = [
  {name: 'ordinary_foreground_reuses_previous_task', file: 'MissionFlow.js',
    before: "entry.scene === 'desktop_shortcut' ? 'shortcut' : null",
    after: "entry.scene === 'desktop_shortcut' ? 'shortcut' : this.kind"},
  {name: 'old_answer_can_update_panel', file: 'MissionFlow.js',
    before: 'if (!isCurrent() || op !== self.op) return;\n    self.pendingCheck = null;', after: 'self.pendingCheck = null;'},
  {name: 'failed_save_reported_as_success', file: 'MissionFlow.js',
    before: 'if (result.ok) {', after: 'if (true) {'},
  {name: 'non_success_result_is_silent', file: 'MissionFlow.js',
    before: "self.message = r.status === 'ineligible' ? TEXT.notReady : r.message;\n    self._render();\n  });\n  return this.pendingCheck;",
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
    before: "catch (_) { return this._unavailable('saved_data_malformed'); }", after: 'catch (_) { return this._fresh(); }'},
  // v1.2 (D4 1.3, D4 6, D6 4/9)
  {name: 'mission_sdk_lookup_only_ttminis', file: 'MissionFlow.js',
    before: "typeof tt !== 'undefined' && tt,\n    typeof wx !== 'undefined' && wx",
    after: "false,\n    false"},
  // 简化.11.3: a runtime whose mission methods exist but has no canIUse must still count as TikTok.
  {name: 'flow_native_requires_canIUse', file: 'MissionFlow.js',
    before: "var names = ['canIUse', 'addShortcut', 'startEntranceMission', 'getShortcutMissionReward', 'getEntranceMissionReward'];",
    after: "var names = ['canIUse'];"},
  {name: 'unreadable_value_not_checked_against_storage_keys', file: 'SaveStore.js',
    before: "if (absent && (threw || isUnreadable(raw) || raw === null || raw === '')) return this._fresh();", after: ''},
  {name: 'missing_key_defaults_not_written', file: 'SaveStore.js',
    before: 'var written = this._write(this.data);', after: 'var written = null;'},
  {name: 'login_never_sent', file: 'SaveStore.js',
    before: 'this._loginOnce();\n  return result;', after: 'return result;'},
  {name: 'login_awaited_inside_load', file: 'SaveStore.js',
    before: "try { if (typeof setTimeout === 'function') setTimeout(send, 0); else send(); } catch (_) {}", after: 'send();'},
  // 简化.11.13 P10: grant / best
  {name: 'grant_calls_ui_even_when_save_failed', file: 'SaveStore.js',
    before: "if (!r.ok) { if (problem) r.error = problem; return r; }", after: "if (!r.ok) { if (problem) r.error = problem; if (typeof onDone === 'function') onDone(r); return r; }"},
  {name: 'grant_claim_id_not_checked', file: 'SaveStore.js',
    before: "var same = this._result(true); same.already = true; return same;", after: ''},
  {name: 'grant_claim_id_not_written', file: 'SaveStore.js',
    before: "draft.meta.grants[id] = (draft.meta.grantSeq", after: "draft.meta.grantsLost = (draft.meta.grantSeq"},
  {name: 'best_overwrites_with_lower', file: 'SaveStore.js',
    before: "if (current !== null && score <= current) {", after: "if (current !== null && score === current) {"},
  {name: 'best_skips_first_record', file: 'SaveStore.js',
    before: "if (current !== null && score <= current) {", after: "if (current === null || score <= current) {"},
  {name: 'grant_numeric_text_not_accepted', file: 'SaveStore.js',
    before: "if (typeof value === 'string' && value.trim() !== '' && isFinite(Number(value))) return Number(value);", after: ''}
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
