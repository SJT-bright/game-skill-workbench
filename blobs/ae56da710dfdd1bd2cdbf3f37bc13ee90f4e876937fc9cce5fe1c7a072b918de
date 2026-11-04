'use strict';
// Each variant breaks one rule in a temporary copy of assets/tiktok-platform; home-entries.test.js MUST fail.
// Variants without `file` change HomeGrowthEntries.js.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var kitDir = path.join(__dirname, '..', 'assets', 'tiktok-platform');
var variants = [
  {name: 'unsupported_is_silent', before: "if (!flow.native) { this.toast(TEXT.unsupported); return 'unsupported'; }", after: "if (!flow.native) { return 'unsupported'; }"},
  {name: 'unsupported_fakes_success', before: "if (!flow.native) { this.toast(TEXT.unsupported); return 'unsupported'; }", after: ''},
  {name: 'taps_not_merged', before: "if (flow.view().busy) return 'busy';", after: ''},
  {name: 'no_text_fallback', before: "if (this.iconFallback[kind] === false) { this.iconFallback[kind] = true; this._render(); }", after: ''},
  {name: 'own_reward_amount', before: "try { return this.config.growthReward(); } catch (_) { return 0; }", after: 'return 25;'},
  {name: 'entries_hidden_without_sdk', before: '        node.active = true;\n', after: '        node.active = self.controller.flow.native;\n'},
  // 简化.11.3: the 简化.11.2 behaviour (first tap only queries, a second tap navigates) must fail.
  {name: 'first_tap_only_checks', before: 'flow.open(kind, {navigate: true});', after: 'flow.open(kind);'},
  // 简化.11.3: on the phone canIUse('startEntranceMission') answers undefined; requiring true broke every game.
  {name: 'canIUse_must_answer_true', file: 'TikTokMissionService.js', before: 'return candidate.canIUse(method) !== false;', after: 'return candidate.canIUse(method) === true;'},
  {name: 'collected_entry_refuses_to_open', file: 'MissionFlow.js', before: "if (this.phase === 'opening' || this.phase === 'checking') { this.message = TEXT.wait; this._render(); return; }",
    after: "if (this.phase === 'opening' || this.phase === 'checking') { this.message = TEXT.wait; this._render(); return; }\n  if (this.isClaimed(this.kind)) { this.message = TEXT.claimed; this._render(); return; }"}
];
function copyKit(dir) {
  fs.readdirSync(kitDir).forEach(function (f) { if (/\.js$/.test(f)) fs.copyFileSync(path.join(kitDir, f), path.join(dir, f)); });
}
var results = variants.map(function (v) {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'home-neg-'));
  copyKit(dir);
  var file = path.join(dir, v.file || 'HomeGrowthEntries.js'), text = fs.readFileSync(file, 'utf8');
  var applied = text.split(v.before).length === 2;
  fs.writeFileSync(file, applied ? text.replace(v.before, v.after) : text);
  var r = child.spawnSync(process.execPath, [path.join(__dirname, 'home-entries.test.js')],
    {encoding: 'utf8', timeout: 20000, env: Object.assign({}, process.env, {KIT_DIR: dir, HOME_ENTRIES: path.join(dir, 'HomeGrowthEntries.js')})});
  fs.rmSync(dir, {recursive: true, force: true});
  var caught = [];
  try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
  return {name: v.name, file: v.file || 'HomeGrowthEntries.js', mutation_applied: applied,
    test_failed_as_expected: applied && r.status !== 0 && caught.length > 0, caught_by: caught};
});
console.log(JSON.stringify(results, null, 2));
if (results.some(function (r) { return !r.test_failed_as_expected; })) process.exitCode = 1;
