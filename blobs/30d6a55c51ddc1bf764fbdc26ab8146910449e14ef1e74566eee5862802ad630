'use strict';
// node tests/run-all.js  -> runs every kit test and negative control, prints one summary.
var child = require('child_process'), path = require('path');
var suites = [
  ['Snake 原测试（广告+回访组件，含4个反例）', 'snake-regression/run.js'],
  ['存档 + 主页两按钮流程', 'kit.test.js'],
  ['存档/流程 故意改坏必须被抓到', 'kit-negative-controls.js'],
  ['启动文件 main.js + 触摸修正', 'boot.test.js'],
  ['启动文件 故意改坏必须被抓到', 'boot-negative-controls.js'],
  ['工程检查 App ID（settings/bytedance.json）', 'check-kit-project.test.js'],
  ['激励广告计时 long200/late16/bgplay/bgload/hang/nocallback', 'rewarded-timing.test.js'],
  ['存档层 storage-guard（false/\'\'/undefined/数字读回 true）', 'storage-guard.test.js'],
  ['存档层 故意改坏必须被抓到', 'storage-guard-negative-controls.js'],
  ['首页双入口 HomeGrowthEntries（不支持提示/文字备用/5B/只发一次）', 'home-entries.test.js'],
  ['首页双入口 故意改坏必须被抓到', 'home-entries-negative-controls.js'],
  ['3.x 触摸 tiktok-touch-3x（只给 screenX/screenY、装两次一层、只有 TTMinis.game；含 8 个反例）', 'touch-3x.test.js'],
  ['3.x 插件版 plugins-3x（同一套 rewarded-timing / kit 用例 + make_plugin_scripts --check 反例）', 'plugins-3x.test.js'],
  ['胶囊位置 CapsuleLayout（按点/按像素同一个设计坐标、黑边、2.4 和 3.x；含原样用像素的反例）', 'capsule-layout.test.js'],
  ['滚动障碍 CourseLane（真实可见范围、宽屏组数、出生/回收、复活淡出 ≥0.3 秒、2.4 和 3.x；含按设计宽度出生的反例）', 'course-lane.test.js'],
  ['物理时钟 PhysicsClock（2.4 enabledAccumulator 自动打开、推力按时间缩放后 60/120 帧同距离；含飞车 v3.1 写法和只开 accumulator 两个反例）', 'physics-clock.test.js']
];
var ok = true;
suites.forEach(function (s) {
  var r = child.spawnSync(process.execPath, [path.join(__dirname, s[1])], {encoding: 'utf8', timeout: 120000});
  var pass = r.status === 0;
  ok = ok && pass;
  console.log((pass ? 'PASS ' : 'FAIL ') + s[0] + '  (' + s[1] + ')');
  if (!pass) console.log(String(r.stdout).slice(0, 1500) + String(r.stderr).slice(0, 500));
});
console.log(ok ? '\n全部通过（只代表 Node 模拟环境；真机扫码见 README 第五节）' : '\n有失败项');
if (!ok) process.exitCode = 1;
