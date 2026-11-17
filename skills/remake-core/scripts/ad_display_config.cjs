'use strict';
// Portable setup for the existing AdDisplayPolicy. Project scripts are parsed, never executed.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const acorn = require('./vendor/acorn.cjs');
const KIT = path.resolve(__dirname, '../assets/platform-kit');
const Policy = require(path.join(KIT, 'assets/tiktok-platform/AdDisplayPolicy.js'));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');

function fail(message) { throw new Error(message); }
function keyOf(p) { return p && !p.computed && (p.key.name || p.key.value); }
function fields(object) {
  if (!object || object.type !== 'ObjectExpression') fail('配置必须是静态对象，不能执行项目脚本来读取。');
  const map = {};
  for (const p of object.properties) {
    const key = keyOf(p);
    if (p.type !== 'Property' || p.kind !== 'init' || p.method || typeof key !== 'string') fail('配置中存在计算字段或展开项，请先整理为静态配置。');
    if (Object.prototype.hasOwnProperty.call(map, key)) fail('重复配置字段：' + key);
    map[key] = p;
  }
  return map;
}
function literal(p, fallback) {
  if (!p) return fallback;
  if (p.value.type !== 'Literal') fail('配置字段需要静态字符串、布尔值或数字：' + keyOf(p));
  return p.value.value;
}
function parse(text) {
  const ast = acorn.parse(text, {ecmaVersion: 2020});
  const candidates = [];
  function walk(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'VariableDeclarator' && node.id.name === 'config' && node.init && node.init.type === 'ObjectExpression') {
      const map = fields(node.init);
      if (map.gameId && map.appId) candidates.push({object: node.init, map});
    }
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(walk);
      else if (value && typeof value === 'object') walk(value);
    }
  }
  walk(ast);
  if (candidates.length !== 1) fail('需要唯一的 PlatformConfig config 对象，实际找到 ' + candidates.length + ' 个。');
  const found = candidates[0], block = found.map.adDisplay && found.map.adDisplay.value;
  const ad = block ? fields(block) : {};
  const config = {gameId: literal(found.map.gameId), appId: literal(found.map.appId), adDisplay: {
    enabled: literal(ad.enabled, true), channel: literal(ad.channel, 'production'),
    remoteUrl: literal(ad.remoteUrl, ''), refreshAfterMs: literal(ad.refreshAfterMs, 60000),
    requestTimeoutMs: literal(ad.requestTimeoutMs, 1500)
  }};
  Policy.create(config, {storage: null, bindLifecycle: false}); // exact runtime validation, no network/cache
  if (config.adDisplay.remoteUrl) {
    const url = new URL(config.adDisplay.remoteUrl);
    if (url.protocol !== 'https:' || !url.hostname || url.username || url.password || url.hash) fail('远端地址必须是无账号密码、无片段的 HTTPS JSON 地址。');
  }
  return {...found, block, ad, config};
}
function projectConfig(project) {
  const root = path.resolve(project || '.');
  if (!fs.existsSync(path.join(root, 'assets'))) fail('不是 Cocos 工程：缺少 assets/。');
  function metadata(name) {
    try { return JSON.parse(fs.readFileSync(path.join(root, name), 'utf8').replace(/^\uFEFF/, '')); }
    catch (_) { return {}; }
  }
  const pack = metadata('package.json'), legacy = metadata('project.json');
  const version = String(pack.creator && pack.creator.version || legacy.version || '');
  const engine = version.startsWith('3.') ? 3 : version.startsWith('2.') ? 2 : null;
  if (!engine) fail('无法识别工程引擎；需要 project.json 的 2.x version 或 package.json 的 creator.version。');
  const names = ['PlatformConfig.js', 'PlatformConfig.plugin.js'];
  const matches = names.map(n => path.join(root, 'assets/tiktok-platform', n)).filter(p => fs.existsSync(p));
  if (matches.length !== 1) fail('需要先运行同包 tiktok_finalize.py source/sync，确保只有一份 PlatformConfig。');
  const file = matches[0];
  if ((engine === 3) !== file.endsWith('.plugin.js')) fail('Cocos ' + version + ' 与平台配置类型不匹配；先运行同包 source/sync，2.x 使用普通模块，3.x 使用插件。');
  if (fs.lstatSync(file).isSymbolicLink()) fail('保留项目符号链接，未修改配置。');
  const text = fs.readFileSync(file, 'utf8');
  return {root, file, text, engine, plugin: file.endsWith('.plugin.js'), parsed: parse(text)};
}
function replaceFields(text, object, map, changes) {
  const edits = [], additions = [];
  for (const [key, value] of Object.entries(changes)) {
    if (map[key]) edits.push({start: map[key].value.start, end: map[key].value.end, text: JSON.stringify(value)});
    else additions.push(JSON.stringify(key) + ': ' + JSON.stringify(value));
  }
  if (additions.length) {
    const last = object.properties[object.properties.length - 1];
    // Insert after the last real property, before existing trailing commas/comments.
    const at = last ? last.end : object.start + 1;
    edits.push({start: at, end: at, text: (last ? ',' : '') + '\n    ' + additions.join(',\n    ')});
  }
  edits.sort((a, b) => b.start - a.start);
  for (const e of edits) text = text.slice(0, e.start) + e.text + text.slice(e.end);
  return text;
}
function atomic(file, data) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  if (fs.existsSync(file) && fs.lstatSync(file).isSymbolicLink()) fail('拒绝覆盖符号链接：' + file);
  const temp = file + '.ad-display-' + crypto.randomBytes(6).toString('hex') + '.tmp';
  try { fs.writeFileSync(temp, data, {flag: 'wx'}); fs.renameSync(temp, file); }
  finally { if (fs.existsSync(temp)) fs.unlinkSync(temp); }
}
function configure(project, options) {
  const p = projectConfig(project), changes = {};
  if (options.remoteUrl !== undefined) changes.remoteUrl = options.remoteUrl;
  if (options.channel !== undefined) changes.channel = options.channel;
  if (options.enabled !== undefined) changes.enabled = options.enabled;
  if (!p.parsed.block) Object.assign(changes, {...p.parsed.config.adDisplay, ...changes});
  let text = p.parsed.block ? replaceFields(p.text, p.parsed.block, p.parsed.ad, changes)
    : replaceFields(p.text, p.parsed.object, p.parsed.map, {adDisplay: changes});
  const updated = parse(text); // invalid values cause zero project writes
  const changed = text !== p.text;
  let backup = null;
  if (changed && !options.dryRun) {
    backup = path.join(p.root, '.tiktok-kit/backups/ad-display', sha(p.text) + '.js');
    if (!fs.existsSync(backup)) atomic(backup, p.text);
    atomic(p.file, text);
  }
  return {tool: 'ad_display_config', command: 'configure', changed, dryRun: !!options.dryRun,
    project: p.root, file: p.file, configSha256: sha(text), backup,
    localEnabled: updated.config.adDisplay.enabled, remoteConfigured: !!updated.config.adDisplay.remoteUrl,
    liveVerified: false, next: '运行 check --require-remote；配置变化后按原流程 source/sync 再构建。'};
}
function check(project, requireRemote) {
  const p = projectConfig(project), cfg = p.parsed.config, problems = [];
  if (!p.parsed.block) problems.push('缺少显式 adDisplay 配置；先运行 configure。');
  if (requireRemote && !cfg.adDisplay.remoteUrl) problems.push('remoteUrl 为空：只有包内配置能力，尚不能后台控制已发布版本。');
  for (const name of ['PlatformConfig', 'AdDisplayPolicy', 'RewardedService']) {
    const rel = p.plugin ? 'plugins-3x/' + name + '.plugin.js' : 'assets/tiktok-platform/' + name + '.js';
    const target = path.join(path.dirname(p.file), name + (p.plugin ? '.plugin.js' : '.js'));
    if (name !== 'PlatformConfig' && (!fs.existsSync(target) || !fs.readFileSync(target).equals(fs.readFileSync(path.join(KIT, rel))))) {
      problems.push(name + ' 未安装或与本包不同；运行同包 source/sync 后复查。');
    }
    if (p.plugin) {
      let meta;
      try { meta = JSON.parse(fs.readFileSync(target + '.meta', 'utf8')); } catch (_) {}
      if (!meta || !meta.userData || meta.userData.isPlugin !== true || meta.userData.loadPluginInMiniGame !== true) problems.push(name + ' 的 3.x 插件元数据缺失或未启用。');
    }
  }
  return {tool: 'ad_display_config', command: 'check', passed: !problems.length,
    status: problems.length ? 'needs_setup' : cfg.adDisplay.remoteUrl ? 'remote_configured_not_probed' : 'package_config_only',
    project: p.root, file: p.file, engine: p.engine, configSha256: sha(p.text), gameId: cfg.gameId, appId: cfg.appId,
    channel: cfg.adDisplay.channel, localEnabled: cfg.adDisplay.enabled, remoteConfigured: !!cfg.adDisplay.remoteUrl,
    liveVerified: false, problems,
    scope: '配置与同包平台件核对；广告入口、所有实际广告类型及真机效果沿用项目原有定向广告验证。'};
}
function identity(config) {
  if (typeof config.gameId !== 'string' || !config.gameId || config.gameId === 'change-me' || !config.appId) fail('先用原平台配置流程填写本游戏 gameId、appId，再生成远端数据。');
  return {schemaVersion: 1, gameId: config.gameId, appId: config.appId, channel: config.adDisplay.channel};
}
function payload(project, enabled, revision, out) {
  if (typeof enabled !== 'boolean' || !Number.isSafeInteger(revision) || revision < 0) fail('enabled 必须为 true/false；revision 必须为非负安全整数。');
  if (!out || path.extname(out).toLowerCase() !== '.json') fail('payload 需要 --out 指向独立 .json 文件。');
  const p = projectConfig(project), value = {...identity(p.parsed.config), revision, ads: {enabled}};
  if (fs.existsSync(out)) {
    const old = JSON.parse(fs.readFileSync(out, 'utf8'));
    if (old.gameId !== value.gameId || old.appId !== value.appId || old.channel !== value.channel) fail('输出已有其他游戏或渠道数据，未覆盖。');
    if (!Number.isSafeInteger(old.revision) || revision <= old.revision) fail('覆盖已有配置时 revision 必须递增。');
  }
  atomic(path.resolve(out), JSON.stringify(value, null, 2) + '\n');
  return {tool: 'ad_display_config', command: 'payload', out: path.resolve(out), payload: value,
    uploaded: false, next: '将此 JSON 作为已有后台或 HTTPS 配置地址的响应；本命令不上传、不改变线上广告。'};
}
function fetchJSON(url, timeout) {
  return new Promise((resolve, reject) => {
    let settled = false, timer;
    function finish(error, value) {
      if (settled) return;
      settled = true; clearTimeout(timer);
      if (error) reject(error); else resolve(value);
    }
    const request = https.get(url, {headers: {'Accept': 'application/json'}, timeout}, response => {
      if (response.statusCode !== 200) { response.resume(); finish(new Error('远端需要 HTTP 200，实际为 ' + response.statusCode)); return; }
      const chunks = []; let bytes = 0;
      response.on('data', data => { bytes += data.length; if (bytes > 131072) { response.destroy(); finish(new Error('远端 JSON 超过 128 KiB。')); } else chunks.push(data); });
      response.on('error', finish);
      response.on('end', () => { try { finish(null, JSON.parse(Buffer.concat(chunks).toString('utf8'))); } catch (_) { finish(new Error('远端响应不是有效 JSON。')); } });
    });
    timer = setTimeout(() => request.destroy(new Error('远端配置请求超时。')), timeout);
    request.on('timeout', () => request.destroy(new Error('远端配置请求超时。')));
    request.on('error', finish);
  });
}
async function probe(project, transport = fetchJSON) {
  const setup = check(project, true);
  if (!setup.passed) fail(setup.problems.join('；'));
  const p = projectConfig(project), cfg = p.parsed.config;
  const data = await transport(cfg.adDisplay.remoteUrl, cfg.adDisplay.requestTimeoutMs);
  const policy = Policy.create(cfg, {storage: null, bindLifecycle: false,
    request: opts => { opts.success({statusCode: 200, data}); return {}; }});
  const state = await policy.refresh();
  if (state.lastOutcome !== 'accepted') fail('远端配置被实际策略拒绝：检查 schemaVersion、gameId、appId、channel、revision 和 ads.enabled。');
  return {...setup, command: 'probe', status: 'remote_response_verified', liveVerified: true,
    revision: state.revision, remoteEnabled: state.remoteEnabled, effectiveEnabled: state.enabled,
    cacheWritten: false, scope: '只读验证一次远端响应；未操作广告、玩家存档或线上配置，不代表所有设备即时生效。'};
}
function args(argv) {
  const command = argv.shift(), options = {};
  const allowed = {configure: ['project','remote-url','channel','enabled','dry-run','report'],
    check: ['project','require-remote','report'], payload: ['project','enabled','revision','out','report'], probe: ['project','report']};
  if (!allowed[command]) fail('用法：node ad_display_config.cjs <configure|check|payload|probe> --project <工程> [选项]。\nconfigure: --remote-url <HTTPS地址> [--channel production] [--enabled true|false] [--dry-run]\ncheck: [--require-remote]\npayload: --enabled true|false --revision <递增整数> --out <后台响应.json>\nprobe: 只读请求配置源并用真实策略校验响应。各命令可用 --report <回执.json>。');
  while (argv.length) {
    const token = argv.shift(), key = token.replace(/^--/, '');
    if (!token.startsWith('--') || !allowed[command].includes(key) || key in options) fail('未知或重复参数：' + token);
    if (['dry-run','require-remote'].includes(key)) options[key] = true;
    else { if (!argv.length || argv[0].startsWith('--')) fail('缺少参数值：' + token); options[key] = argv.shift(); }
  }
  if (!options.project) fail('需要 --project <工程>。');
  if (options.enabled !== undefined) { if (!['true','false'].includes(options.enabled)) fail('--enabled 只接受 true 或 false。'); options.enabled = options.enabled === 'true'; }
  if (options.revision !== undefined) { if (!/^\d+$/.test(options.revision)) fail('--revision 必须是非负整数。'); options.revision = Number(options.revision); }
  return {command, options};
}
async function main(argv) {
  if (!argv.length || argv.includes('--help') || argv.includes('-h')) {
    try { args([]); } catch (error) { process.stdout.write(error.message + '\n'); } return 0;
  }
  const {command, options: o} = args(argv);
  let result;
  if (command === 'configure') result = configure(o.project, {remoteUrl: o['remote-url'], channel: o.channel, enabled: o.enabled, dryRun: o['dry-run']});
  if (command === 'check') result = check(o.project, o['require-remote']);
  if (command === 'payload') result = payload(o.project, o.enabled, o.revision, o.out);
  if (command === 'probe') result = await probe(o.project);
  if (o.report) {
    const target = path.resolve(o.report), p = projectConfig(o.project);
    if (target === p.file || target === path.resolve(o.out || p.file)) fail('回执不能覆盖输入配置或后台 JSON。');
    atomic(target, JSON.stringify(result, null, 2) + '\n');
  }
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  return result.passed === false ? 1 : 0;
}
module.exports = {parse, configure, check, payload, probe, fetchJSON, main};
if (require.main === module) main(process.argv.slice(2)).then(code => { process.exitCode = code; }, error => {
  process.stderr.write(JSON.stringify({tool: 'ad_display_config', passed: false, error: error.message}) + '\n'); process.exitCode = 2;
});
