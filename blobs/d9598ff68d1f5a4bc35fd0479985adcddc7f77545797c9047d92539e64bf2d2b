'use strict';
// Shared start-of-check guard for the Skill's Node probes (总表 P20, 问题普查 T20; Python side: check_guard.py).
// probe_cocos2_touch_coordinates.cjs --help used to fail with "Unexpected end of JSON input": the probes read a JSON
// payload on stdin or paths in argv, and --help / no input reached JSON.parse or fs.readFileSync. With this guard:
//   cli({usage})      --help / -h prints the usage and exits 0.
//   cli({minArgs:n})  fewer than n positional arguments prints a not_run line and exits 2 (never a pass).
//   stdinJson(tool)   reads stdin once; empty input or bad JSON is a not_run line, exit 2.
// Standard library only; Node 16+.
const fs = require('fs');
const NOT_RUN_EXIT = 2;

function notRun(tool, reason, extra) {
  const report = Object.assign({tool, status: 'not_run', passed: false, checked: 0, reason}, extra || {});
  process.stdout.write(JSON.stringify(report) + '\n');
  process.exit(NOT_RUN_EXIT);
}

function cli(opts) {
  const o = opts || {};
  const args = process.argv.slice(2);
  const tool = o.tool || require('path').basename(process.argv[1] || 'probe');
  if (args.some(a => a === '--help' || a === '-h')) {
    process.stdout.write(String(o.usage || tool).trim() + '\n');
    process.exit(0);
  }
  if (o.minArgs && args.length < o.minArgs) {
    notRun(tool, 'missing arguments: ' + String(o.usage || '').trim().split('\n')[0]);
  }
  return args;
}

function stdinText(tool) {
  let text = '';
  try { text = fs.readFileSync(0, 'utf8'); } catch (e) { text = ''; }
  if (!text.trim()) notRun(tool, 'no JSON payload on stdin: this probe is run by its Python check script, not by hand');
  return text;
}

function stdinJson(tool) {
  const text = stdinText(tool);
  try { return JSON.parse(text); } catch (e) { return notRun(tool, 'stdin is not JSON: ' + e.message); }
}

module.exports = {cli, notRun, stdinText, stdinJson, NOT_RUN_EXIT};
