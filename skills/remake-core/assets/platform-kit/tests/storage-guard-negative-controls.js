'use strict';
// Each variant breaks one rule of parts/storage-guard.js in a temporary copy; storage-guard.test.js MUST fail.
var fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var src = path.join(__dirname, '..', 'parts', 'storage-guard.js');
var variants = [
  {name: 'numbers_written_raw', before: "if (typeof value !== 'string') { note(key, 'as_text_' + typeof value); value = text(value); }", after: ''},
  {name: 'false_read_returned', before: "if (value === '' && present === true) return '';", after: "if (value === false) return false;\n      if (value === '' && present === true) return '';"},
  {name: 'empty_string_returned_without_key_list', before: "if (value === '' && present === true) return '';", after: "if (value === '') return '';"},
  {name: 'boolean_true_read_returned', before: "if (typeof value === 'number') return String(value);", after: "if (typeof value === 'number') return String(value);\n      if (value === true) return value;"},
  {name: 'throw_not_caught', before: "if (listed(key) === false) { note(key, 'throw_absent'); return null; }", after: ''},
  {name: 'object_read_stringified', before: "if (value && typeof value === 'object') return value;", after: "if (value && typeof value === 'object') return JSON.stringify(value);"},
  {name: 'installs_twice', before: '|| storage.getItem.__tiktokKitStorageGuard) return false;', after: ') return false;'},
  {name: 'savestore_key_guarded', before: 'if (SAVESTORE_KEY.test(String(key))) return read.call(storage, key);', after: ''}
];
var results = variants.map(function (v) {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'storage-neg-'));
  var file = path.join(dir, 'storage-guard.js'), text = fs.readFileSync(src, 'utf8'), applied = text.indexOf(v.before) >= 0;
  fs.writeFileSync(file, applied ? text.replace(v.before, v.after) : text);
  var r = child.spawnSync(process.execPath, [path.join(__dirname, 'storage-guard.test.js')],
    {encoding: 'utf8', timeout: 20000, env: Object.assign({}, process.env, {STORAGE_GUARD: file})});
  fs.rmSync(dir, {recursive: true, force: true});
  var caught = [];
  try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
  return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
});
console.log(JSON.stringify(results, null, 2));
if (results.some(function (r) { return !r.test_failed_as_expected; })) process.exitCode = 1;
