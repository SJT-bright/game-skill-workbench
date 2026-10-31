'use strict';
// Each variant breaks one rule of HomeGrowthEntries.js in a temporary copy; home-entries.test.js MUST fail.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var src = path.join(__dirname, '..', 'assets', 'tiktok-platform', 'HomeGrowthEntries.js');
var variants = [
  {name: 'unsupported_is_silent', before: "if (!flow.native) { this.toast(TEXT.unsupported); return 'unsupported'; }", after: "if (!flow.native) { return 'unsupported'; }"},
  {name: 'unsupported_fakes_success', before: "if (!flow.native) { this.toast(TEXT.unsupported); return 'unsupported'; }", after: ''},
  {name: 'taps_not_merged', before: "if (view.busy) return 'busy';", after: ''},
  {name: 'no_text_fallback', before: "if (this.iconFallback[kind] === false) { this.iconFallback[kind] = true; this._render(); }", after: ''},
  {name: 'own_reward_amount', before: "try { return this.config.growthReward(); } catch (_) { return 0; }", after: 'return 25;'},
  {name: 'entries_hidden_without_sdk', before: '        node.active = true;\n', after: '        node.active = self.controller.flow.native;\n'}
];
var results = variants.map(function (v) {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'home-neg-'));
  var file = path.join(dir, 'HomeGrowthEntries.js'), text = fs.readFileSync(src, 'utf8'), applied = text.indexOf(v.before) >= 0;
  fs.writeFileSync(file, applied ? text.replace(v.before, v.after) : text);
  var r = child.spawnSync(process.execPath, [path.join(__dirname, 'home-entries.test.js')],
    {encoding: 'utf8', timeout: 20000, env: Object.assign({}, process.env, {HOME_ENTRIES: file})});
  fs.rmSync(dir, {recursive: true, force: true});
  var caught = [];
  try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
  return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
});
console.log(JSON.stringify(results, null, 2));
if (results.some(function (r) { return !r.test_failed_as_expected; })) process.exitCode = 1;
