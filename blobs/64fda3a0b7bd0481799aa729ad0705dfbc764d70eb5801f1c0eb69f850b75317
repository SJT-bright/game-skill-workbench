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
  ['激励广告兜底 rewarded-guard（埃及宝石/拇指弹球旧版/搭桥小能手三个夹具不装必失败、装上不锁死不迟到发奖；rewarded-timing 和 AdBoostKit 经 guard 结果不变；D2 放行标记）', 'rewarded-guard.test.js'],
  ['存档层 storage-guard（false/\'\'/undefined/数字读回 true）', 'storage-guard.test.js'],
  ['存档层 故意改坏必须被抓到', 'storage-guard-negative-controls.js'],
  ['首页双入口 HomeGrowthEntries（不支持提示/文字备用/5B/只发一次）', 'home-entries.test.js'],
  ['首页双入口 故意改坏必须被抓到', 'home-entries-negative-controls.js'],
  ['首页找空位 home_free_slot（6 个按钮的首页两个入口不压任何按钮、估坐标的旧做法会压、放不下报错、安全区、2.4/3.x prefab 和 ui_dump）', 'home-free-slot.test.js'],
  ['首页入口运行时找空位 HomeGrowthEntries.placeEntries（蛋壳特工队真实首页：旧固定坐标压底栏、2.4/3.x 新做法不压、放不下报错不动、和 home_free_slot 结果相同）', 'home-entries-slot.test.js'],
  ['首页入口也避开触摸节点 home-entries-touch（ad-boost WheelPanel.entry() 写法的普通节点+TOUCH_END、原版触摸按钮、整屏触摸背景和遮罩不挡、2.4/3.x；N 版和「背景也算障碍」两个反例）', 'home-entries-touch.test.js'],
  ['2.4 触摸 touch-coordinates 回来先清（切后台时按着的手指收到 TOUCH_CANCEL、同 id 下一下不丢；含 6 个反例）', 'touch-lifecycle-24.test.js'],
  ['3.x 触摸 tiktok-touch-3x（只给 screenX/screenY、装两次一层、只有 TTMinis.game、切后台时按着的手指收到 touchcancel；含 12 个反例）', 'touch-3x.test.js'],
  ['3.x 插件版 plugins-3x（同一套 rewarded-timing / kit 用例 + make_plugin_scripts --check 反例）', 'plugins-3x.test.js'],
  ['胶囊位置 CapsuleLayout（按点/按像素同一个设计坐标、黑边、2.4 和 3.x；含原样用像素的反例）', 'capsule-layout.test.js'],
  ['滚动障碍 CourseLane（真实可见范围、宽屏组数、出生/回收、复活淡出 ≥0.3 秒、2.4 和 3.x；含按设计宽度出生的反例）', 'course-lane.test.js'],
  ['弹窗和按钮 GameUIKit（遮罩吞点击、关掉一定 inactive、500ms 防连点、没绑函数当场报错、keep 复用、关闭键 ≥104、按下不缩放、迟到回调丢弃、禁用有提示、原版按钮包一层；每条带「照旧手写」反例；2.4 和 3.x 各跑）', 'game-ui-kit.test.js'],
  ['弹窗页面模板 GameUIKit 1.1（暂停按原因、Restart 整局重建、固定槽位、复活只认看完、结算 x2 走 grant、valueLabel 单行、onPageOpen；2.4 和 3.x 各跑，每条带旧写法反例）', 'game-ui-pages.test.js'],
  ['叠弹窗 GameUIKit.adoptPopup（AdBoostKit 弹窗进同一个记录，只暗最上面一层；release 重复无害、isOpen 变 false 也清掉；2.4 和 3.x 各跑，旧 1.1.0 暗两层）', 'game-ui-adopt.test.js'],
  ['物理时钟 PhysicsClock（2.4 enabledAccumulator 自动打开、推力按时间缩放后 60/120 帧同距离；含飞车 v3.1 写法和只开 accumulator 两个反例）', 'physics-clock.test.js'],
  ['3.x 启动看守 boot-guard-3x（10 秒重发/30 秒失败/只算前台/每帧≤1 秒/Retry 新请求旧回答作废/首页场景回调才算完成；含固定 15 秒总期限夹具和 11 个反例）', 'boot-3x.test.js'],
  ['宿主接口兜底 host-shim（缺 SDKVersion/getOpenDataContext/canIUse/getSystemInfoSync 抛错；含躲雨小鸭 v16、射击高手2048 夹具和 8 个反例）', 'host-shim.test.js'],
  ['一局状态 RunSession（按原因暂停、切后台、newRun 重建、旧回调和定时器作废、按秒移动；含单布尔暂停等 5 个反例）', 'run-session.test.js'],
  ['特效池 FxPool（120 次发射节点不涨、上限、按游戏时间回池、devWatch；含方块迷阵写法反例）', 'fx-pool.test.js'],
  ['资源加载 ResLoader（只收 ResKeys、一定有结果、10 秒重发 30 秒失败、空 JSON、ready 只认真成功；含甜品消除大师 v11 ResMgr 反例）', 'res-loader.test.js'],
  ['声音件 AudioService（music/sfx 分开、播放前查开关、首帧后加载、广告静音恢复、节流；含 7 个旧写法反例）', 'audio-service.test.js'],
  ['屏幕适配 ScreenFit（真实可见范围铺满背景、按钮组整体进安全区和胶囊下、只开一种 fit、2.4 和 3.x；含按设计尺寸铺背景、两种 fit 都开、只按锚点挤顶栏三个反例）', 'screen-fit.test.js'],
  ['触摸归属 TouchOwner（只认第一个手指、touchcancel 和切后台释放且只结束一次、按住 6 秒照样能拖、四个方向的滑动、按所在相机换算坐标、2.4 和 3.x；含 5 个旧写法反例）', 'touch-owner.test.js'],
  ['胶囊自动避让 CapsuleAuto（压在胶囊下的顶栏挪到胶囊下沿、左边金币和中间面板不动、顶部 Widget 改 top、开关；含照旧按需用的反例）', 'capsule-auto.test.js']
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
