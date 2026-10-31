# TikTok 平台包 2.0（Cocos Creator 2.4.15，重塑/自制游戏专用；3.x 插件版见第七节）

2.0（2026-10-29，重塑 Skill v7.7）：出包时由 `tiktok_finalize` 自动装上标准件，再由门禁 `kit_parts` 直接读包里的字节证明装上了（第六节）。新增存档层 `parts/storage-guard.js`、首页双入口组件 `HomeGrowthEntries.js`、启动件 `main.js` v1.6（v1.3：装存档层、一次静默登录、WebP 例外时才加载标准探针；v1.4：图片解码看守接到 2.4 真正的图片解析器，场景出来后再点 Retry 不会把加载遮罩盖回去；在 2.4.4 / 2.4.6 / 2.4.13 真包上宿主实跑通过，finalize 在这四个版本上都换平台包 `main.js`；v1.5：数字不变，单个文件重发算进度，文件还在自己的 30 秒里时 10 秒总看守不出 Retry，所以卡一个文件只在它真失败时出 Retry，重发后进了首页也不会压着 "Load failed"；v1.6：启动场景因为图片超时加载失败后，第一次点 Retry 就能进场景，以前第一次 Retry 一定马上又失败、要点第二次）；平台包 `main.js` 总是带着 `webp-decode-probe.js` 一起放进包根（只放脚本，不放探针图、不插开关行，不开 WebP 例外时它不执行）；`KIT_MANIFEST.json` 加 `parts` 段，是所有哈希的唯一来源。

v1.1（2026-10-27）：卡住判定 20 秒 → 10 秒（skill 规定 10 秒无进展必须出 Retry）；放进重塑 Skill 的 `remake-core/assets/platform-kit/`，原样用平台包的游戏不再单独做 Retry 专项测试。

**必须遵循（Saul 2026-10-29）**：每个 TikTok 游戏都按 [TikTok 固定适配](../../../cocos-game-check/references/tiktok-fixed-adaptation.md) 做；本包就是那页说的“标准件”，新游戏直接引用，不手写、不另抄一份。

这一包是每个自制游戏都一样的 **TikTok 部分**：启动加载、激励广告、桌面快捷方式、个人主页回访、存档。
玩法、美术、关卡、货币数值都不在这里。

**规则只有一条：除了 `PlatformConfig.js`，其他文件整份复制，一个字都不改。**
要改就改平台包本身，升版本号（1.1 → 2.0），重新跑测试，再发给所有游戏。

---

## 一、包里有什么、从哪来

| 文件 | 作用 | 来源 | 状态 |
|---|---|---|---|
| `assets/tiktok-platform/PlatformConfig.js` | App ID、广告位、存档名、B（加桌面/回访奖励 5B） | 新整理 | **每个游戏只改这一个** |
| `assets/tiktok-platform/RewardedService.js` | 激励广告：每次新建、只有看完才发奖、防叠开；只在请求阶段 15 秒超时（切后台不计），开播后不判超时，开播 30 秒无回调时 `onExitAvailable` 通知显示 X、`exit()` 收尾，超时或按 X 后解绑旧回调并立刻放开下一次请求；游戏切后台/回前台时调 `onHide()`/`onShow()` | 以 SnakeVSBlock v32 为底，v7.4（2026-10-28）按 Basil 超时规则改写 | Snake 回归用例 + 出包前广告回归（Marlows r5 10/10）通过 |
| `assets/tiktok-platform/TikTokMissionService.js` | 快捷方式/回访的 4 个 TikTok 接口 | SnakeVSBlock v32，逐字节相同 | 已在 Snake 中通过 |
| `assets/tiktok-platform/SaveStore.js` | 存档：一个 key、一个字符串、写后读回比对；v7.5：读回 true/false/undefined 或抛错时，用 `getStorageInfoSync().keys` 判断有没有这个 key，没有就是新存档（写默认值），不再报 \"Saved value is unavailable\"；读档后发一次登录（不等结果，失败或没有接口都不影响任何流程） | 平台包新写 | Node 测试通过，**待第一次扫码** |
| `assets/tiktok-platform/MissionFlow.js` | 主页两个按钮的完整流程（不画界面）；v7.5：判断是不是真机用和 `TikTokMissionService.js` 一样的顺序（TTMinis.game / tt / wx），只有 tt 的环境不再显示 LOCAL PREVIEW；2.0：不给 `reward` 时自己按 `growthReward()`（5B）加到 `coins`，文案 `+N Coins` | 平台包新写 | Node 测试通过，**待第一次扫码** |
| `assets/tiktok-platform/HomeGrowthEntries.js` | 2.0 新增：首页底排两个固定入口（Add to Home / Profile Revisit）。奖励只读 `growthReward()`，没有改数额的参数；没有 TikTok 运行环境时点按提示 "Available in TikTok"，入口不隐藏；图标缺失或 2 秒没加载出来就显示文字；请求中的连点合并成一次 | 平台包新写 | Node 测试通过，**待真机复测** |
| `build-templates/bytedance/main.js` | 启动：每一步失败或卡住都在 20 秒内出可见 Retry，10 秒没进度就提示；v7.5：包内每个文件 10 秒没结果再请求一次（先到的结果为准），30 秒算失败，切后台不计时、每帧最多计 1 秒；启动异常会被接住并显示，不会停在 \"Starting...\"；v1.3（2.0）：触摸修正之后装 `storage-guard.js`（出错不挡启动），启动时发一次静默登录（不等结果），只有包里设了 `__TIKTOK_KIT_WEBP_PROBE__ = true` 才加载 `webp-decode-probe.js`；v1.4：图片解码（小游戏里图片在解析这一步才真正解码，`downloader.downloadDomImage`，引擎没有超时）也按同一规则 10 秒重发、30 秒算失败；v1.2～v1.3 找的 `parser._parsers` 在所有 2.4 引擎里都不存在，这一半以前没生效；场景已经出来后点到迟到的 Retry，只关掉加载提示，不再盖一个一直不消失的 "Loading 95%"；v1.5：10 秒重发、30 秒失败、后台不计时这几个数字不变，单个文件重发算进度，而且有文件还在自己的 30 秒里时，10 秒总看守等它（它 10 秒重发、30 秒失败，失败会经这一步的出错回调出 Retry）：卡一个文件只在它真失败时出 Retry，重发后进了首页不会压着 "Load failed"（v1.4 两个 10 秒同时到期，宿主每秒约 1 帧时 Retry 先弹出）；v1.6：启动场景的 JSON 已经反序列化、它用的图片超时导致场景失败时，引擎把这份已被改写的 JSON 留在文件缓存（`cc.assetManager._files`）里，场景又不进解析缓存，下一次加载就拿它再反序列化一次，马上失败（调试版引擎报 \"Can not deserialize the same JSON data again\"，去掉这条调试检查的正式版报 `TypeError: Cannot read properties of undefined (reading '0')`），所以以前第一次 Retry 一定失败、第二次才进得去；Retry 重新加载场景前先从缓存里删掉这一项（2.4.4 / 2.4.6 / 2.4.13 / 2.4.15 引擎这段代码相同），计时数字不变。`main.js` 第 33 行在开关里 require `./webp-decode-probe`，静态启动依赖检查不看 `if`，所以 finalize 装平台包 `main.js` 时总是把 `webp-decode-probe.js` 一起放进包根（`KIT_MANIFEST` 的 `startup24.extra_files`，K1 查它的哈希） | MetalMaster r5 + 1 行触摸修正，v7.5 按射击高手2048 v82 的加载守卫改写 | Node 测试通过，**待真机复测** |
| `build-templates/bytedance/touch-coordinates.js` | TikTok 触点只有 screenX/screenY、Cocos 2.4 读 clientX/clientY：不装就按钮点不动（必装，探针校验） | StarPop v50，逐字节相同（交付包根目录和源码 `build-templates/bytedance/` 都是 `1aeb690c…`）。注意：躲雨小鸭 v20、射击高手 pkg85 用的 `0369875d…` 是另一份代码，不是这个文件 | StarPop v50 没有找到扫码确认记录，**待真机复测** |
| `parts/storage-guard.js` | 2.0 新增存档层：写入一律存文字（数字、布尔转成字符串）；读到 null/undefined/''/false/true 时用 `getStorageInfoSync().keys` 判断键在不在，不在就当新玩家（返回 null）；读出对象原样给；SaveStore 的键原样读（SaveStore 自己判断坏档）。工程里放在 `build-templates/bytedance/storage-guard.js`（`KIT_MANIFEST.json` 的 `project_path`），由 `main.js` 在游戏脚本之前装上 | 射击高手2048 v85 的 `storage-guard.js` + TobinsGem/Tansys 的键列表判断 | Node 测试通过，**待真机复测** |
| `settings/bytedance.json` | 字节构建设置模板：数字 App ID（7683427172773644296 是多款游戏共用的测试组 ID，相同是正常的）、首场景分包关、REMOTE_SERVER_ROOT 空。没有它命令行出包会是 `testappId` | 细菌2048 build2 起验证过的写法 | 检查脚本强制 |
| `webp-probe/cocos2.4/` | 老游戏保留 WebP 时用的标准探针：`webp-decode-probe.js` + `loading/webp-probe.webp`（放主包），用 TikTok 的 createImage 真解码这张图，解出宽高才开 WebP，5 秒没回应算不开、显示 Retry、点了重新检测 | Mabel's Meadow r8，逐字节相同 | `test_webp_decode_probe.cjs` 通过，**待真机复测** |
| `webp-probe/cocos3.x-reference/` | 已有 3.x 游戏的参考件：`webp-probe.js`（`check(cc, sdk, timeout, done)` / `apply(cc, ok)`）、`webp-check.webp`、`boot-loading.js` | LunasJade v0.10.1；v7.5 去掉了 data: 备用 | `test_webp_decode_probe.cjs` 通过，**待真机复测** |
| `tools/check_kit_project.py` | 一条命令检查工程（2.0：还查 storage-guard.js、HomeGrowthEntries.js、`growthReward()` 固定 5B、`normalLevelCoins` 已填） | 平台包新写 | — |
| `tests/` | 全部测试 | Snake 原测试 + 平台包新测试 | 全部通过 |
| `KIT_MANIFEST.json` | `files`：每个文件的 SHA256 和旧版本哈希；`parts`：每个标准件放在包里哪、加载行插在哪、怎么认自写件、新旧游戏各怎么处理；`includes` 引入 3.x 的 `parts-3x/KIT_PARTS_3X.json` | — | 检查脚本、`tiktok_finalize`、`kit_parts` 门禁都只读它 |
| `build-templates/bytedance-mini-game/tiktok-touch-3x.js`、`plugins-3x/`、`parts-3x/`、`tools/make_plugin_scripts.py` | 3.x 用的触摸修正和插件版平台包（第七节） | Marlows R6 `marlow-touch.js` 改通用名；插件版由 2.4 模块生成 | Node 测试通过，**待真机复测** |

---

## 二、构建规则（7 个通过的自制游戏总结出来的共同点）

1. **引擎固定 Cocos Creator 2.4.15**，构建平台选 **ByteDance Mini Game（字节小游戏）**，不要用 Web Mobile。
2. **`assets/resources` 设为 Asset Bundle，压缩类型 ByteDance 选"小游戏分包"**。大图、音频都放这里，主包才能 ≤ 4MB。
3. **WebP 规则（全 Skill 统一这一条）：新游戏图片只用 PNG / JPG，不用 WebP**。（手机能显示 WebP、但引擎的判断说不支持时，引擎会跳过所有 WebP 图，报 3121、卡在加载失败页或首页全空白）**老游戏要保留 WebP，必须带标准探针**（2.4 用 `webp-probe/cocos2.4/`，3.x 参考 `webp-probe/cocos3.x-reference/`），探针解码主包里一张真实的 .webp 文件，不用 data: URI；出包检查（G4）会拦住没有探针、探针用 data: URI 或探针图不在主包的包。本平台包工程里不能有 .webp（`check_kit_project.py` 拒绝）。
4. **ByteDance 构建设置里"首场景分包 Start Scene Asset Bundle"关掉，REMOTE_SERVER_ROOT 留空**。不从外网下载任何东西。工程里必须有 `settings/bytedance.json`（复制平台包的 `settings/bytedance.json`），`appid` 是数字 App ID 并和 `PlatformConfig.js` 的 `appId` 一样；空的、`testappId`、非数字都会被 `check_kit_project.py` 拒绝（改 `settings/builder.json` 对命令行出包无效）。
5. **`build-templates/bytedance/` 里只放平台包的 `main.js`、`touch-coordinates.js` 和 `storage-guard.js`（2.0）**。不放 `game.js`、`game.json`，让编辑器自己生成，这样引擎文件名永远对；放了别的文件，`check_kit_project.py` 给警告，出包前 `tiktok_finalize.py source` 会把它们移到 `.tiktok-kit/removed/`。触摸修正装在 `main.js` 里那一行 `require('./touch-coordinates').install(cc)`，存档层装在下面一行 `require('./storage-guard')(cc, platform)`，触摸探针按真实启动链认它（编辑器的 `game.js` 加载 `main.js`，`main.js` 里有这一行就通过；删掉这一行就拒绝出包）。
   - 不用平台包的老游戏，探针还认：`game.js` 里的同一行；在适配器（`adapter-min.js` / `adapter.js`）之前 require 的 SDK 触摸包装模块 `tiktok-input.js`（Basil 的写法）；或者工程自己命名的模块，在 `game.js` 里加一行声明 `// tiktok-touch-adapter: ./文件名.js` 并在适配器之前 require 它。模块缺失、在适配器之后才装，都判不合格。引擎文件 `cocos/cocos2d-js-min.js`（发布版）和 `cocos/cocos2d-js.js`（调试版）都会被探测，Creator 2.4.5 起转换函数里的闭包变量也已支持。
   - 触摸探针不只管 2.4：`remake-core/scripts/audit_upload_startup.py` 对 Cocos 3.x 包（`web-adapter.js` + `cocos-js/`）也跑 `probe_cocos3_touch_coordinates.cjs`。3.x 包不用本包的 `touch-coordinates.js`，要在 `game.js` 里、引擎加载（`System.warmup`）之前给 `tt.onTouch*` 装坐标修正（例：Marlows r5 的 `marlow-touch.js`、Gimble's v9.1 的 `grotto-touch.js`），只给 `identifier/screenX/screenY/force` 时引擎坐标必须有限、在屏幕内、落在点按位置上。**探针结果为空（`touch_coordinates: null`）不算通过**，认不出引擎触摸转换的 TikTok Cocos 包直接失败。
6. 不调用分享、排行榜、更多游戏（skill 原规则）。
7. 游戏代码不直接调用 `createRewardedVideoAd`、`addShortcut` 这类 TikTok 接口，统一通过平台包。

---

## 三、新游戏怎么接（给 AI 照做）

### 第 1 步：复制

- 把 `assets/tiktok-platform/` 整个文件夹复制到游戏的 `assets/` 下（2.0 起 6 个文件，含 `HomeGrowthEntries.js`）。
- 把 `build-templates/bytedance/` 里的两个文件和 `parts/storage-guard.js` 复制到游戏工程的 `build-templates/bytedance/`（一共三个文件）。
- 把 `settings/bytedance.json` 复制到游戏工程的 `settings/`（已有就核对 `appid`）。
- 2.0 起这一步出包时也会自动做：`tiktok_finalize.py source` 把缺的补上、被改过的换回平台包原文件（旧游戏只报告）。手动复制仍然是起项目时的做法，自动这一步是兜底。

### 第 2 步：改配置（唯一要改的文件）

`PlatformConfig.js`：

- `gameId` 改成这个游戏的英文小写名，比如 `'juicerelax'`。
- `appId`、`clientKey`、三个广告位从电脑上的 `~/.game-skill/ad-config.json` 抄过来（skill 的统一广告配置），不填 Client Secret。
- `placementMap` 里列出这个游戏用到的广告位置，比如 `revive`、`double_coins`、`gift`、`hint`、`skin`。没列出的位置会返回 `unconfigured`，不会乱播。
- `normalLevelCoins` 填本游戏的 B（= `unlock_table.json` 的 `normal_level_coins`）。加桌面、主页回访各发一次 `config.growthReward()` = 5B（Saul 2026-10-29，等于一次首页礼盒基础奖励；没有首页礼盒的游戏也是 5B）。不填时 `growthReward()` 抛错，领奖写入被拒、不发奖也不记已领取，kit 测试里有这条用例。

### 第 3 步：存档（金币和"已领取"必须在同一个存档里）

```js
var SaveStore = require('SaveStore');
var save = new SaveStore({coins: 0, level: 1, skins: {}});   // 默认值
save.load();                                                  // 游戏启动时一次

var data = save.get();                                        // 读：拿到一份拷贝
var r = save.update(function (d) { d.coins += 30; });         // 写：只能这样改
if (!r.ok) showToast('Could not save. Please try again.');    // 写失败：不发奖、不改界面
```

- 一次操作要改的东西（比如扣金币 + 解锁皮肤）放在**同一个 update** 里。
- `r.ok` 是 false 时，存档和内存都没变，游戏当作没发生。

### 第 4 步：激励广告

```js
var RewardedService = require('RewardedService');
var ads = new RewardedService();              // 整个游戏只建一个

// 结算页"看广告 ×2"按钮
var panelAlive = true;
ads.request({
  placementKey: 'double_coins', ownerId: 'result',
  isCurrent: function () { return panelAlive && cc.isValid(panelNode); }
}).then(function (r) {
  if (!r.rewarded) { showToast(r.message); return; }       // 取消/失败/超时：每种都有英文提示
  var s = save.update(function (d) { d.coins += doubled; });
  if (!s.ok) showToast('Could not save. Please try again.');
});

// 弹窗关闭时
panelAlive = false; ads.cancelOwner('result');
```

- 只有用户**完整看完**（`onClose` 里 `isEnded === true`）才 `rewarded: true`。
- 浏览器里没有 TikTok，`r.status` 是 `unsupported`，不会发奖。
- 金额怎么算仍用 skill 里的 `AdRewards.ts`，平台包只负责"播广告 + 看没看完"。

### 第 5 步：主页两个按钮

**2.0 起首页底排用固定组件 `HomeGrowthEntries.js`**（底排只放这两个入口，规则 U3）：在首页底排放两个按钮节点，把组件挂在它们的父节点上，两个节点拖进 `shortcutNode` / `profileNode`，首页脚本里：

```js
this.getComponent('HomeGrowthEntries').init(save, {onGranted: function (kind, data) { topBar.setCoins(data.coins); }});
```

奖励固定是 `growthReward()`（5B），组件没有改数额的参数；不支持时提示 "Available in TikTok"；图标没加载出来显示文字。需要自己画弹窗时，才按下面的写法直接用 `MissionFlow`（不传 `reward` 时它也自己发 `growthReward()`）。

```js
var MissionFlow = require('MissionFlow');
var config = require('PlatformConfig');
var amount = config.growthReward();   // 5B；第 2 步没填 normalLevelCoins 会在这里抛错，本地第一次打开首页就能发现
var flow = new MissionFlow({
  store: save,
  reward: function (kind, d) { d.coins += config.growthReward(); },   // 只改 d；固定 5B
  rewardText: {shortcut: '+' + amount + ' Coins', profile: '+' + amount + ' Coins'},
  render: function (v) {
    panel.active = v.open;
    if (!v.open) return;
    titleLabel.string = v.kind === 'shortcut' ? 'ADD TO HOME SCREEN' : 'REVISIT FROM PROFILE';
    messageLabel.string = v.message;                           // 每种结果都有字，直接显示
    mainButton.interactable = v.action !== 'none' && !v.busy;
    mainButtonLabel.string = v.busy ? 'PLEASE WAIT' : (v.action === 'check' ? 'CHECK REWARD' : 'GO');
    claimedBadge.active = v.claimed;
  },
  onGranted: function (kind, data) { topBar.setCoins(data.coins); }
});

homeShortcutIcon.on('click', function () { flow.open('shortcut'); });
profileRevisitIcon.on('click', function () { flow.open('profile'); });
mainButton.on('click', function () { if (flow.view().action === 'check') flow.check(); else flow.start(); });
closeX.on('click', function () { flow.close(); });
cc.game.on(cc.game.EVENT_SHOW, function () { flow.onShow(); });   // 从 TikTok 回来
// 组件 update(dt) 里：flow.tick();   主页销毁时：flow.dispose();
```

`MissionFlow` 已经处理好的事（以前每个游戏都在这里出过 bug）：

- 查询中途离开 TikTok 再回来：旧查询作废，自动发新查询，旧结果迟到也不发奖。
- 连点"检查"只发一次请求；最多 10 秒一定结束（不接 `tick` 也会结束）。
- 失败、超时、不支持、无资格：都有英文提示，没有"点了没反应"。
- 只有 `canReceiveReward === true` 才发奖；金币和"已领取"一次存进去；存档失败不发奖，可以再点重试。
- 每个入口每个存档只领一次；坏存档恢复后视为已领，不会重复送。

弹窗的美术（面板、插图、按钮图）还是每个游戏按 skill 的美术规则自己做，`MissionFlow` 只给文字和状态。

---

## 四、检查和测试

```sh
# 检查一个游戏工程（文件没被改、构建规则对）
python3 tools/check_kit_project.py --project /路径/游戏工程

# 跑平台包全部测试（改平台包后必须跑）
node tests/run-all.js
```

测试内容（2026-10-29 kit 2.0，`run-all.js` 13 组全过；v1.4、v1.5 后重跑仍 13 组全过）：

- **Snake 原测试**：广告 + 回访组件 20 项、接口兼容 8 项、4 个故意改坏的反例，证明这两个文件和 Snake 里通过的版本行为一样。
- **存档 + 主页流程**（`kit.test.js`）：33 项，场景来自 skill 记录过的故障（离开再回来、连点、超时、complete-only、存档失败、旧结果覆盖新结果、只有 tt 的真机环境、读档读到 true/undefined/抛错、缺 key 的新存档、登录失败不影响流程……）；2.0 加：SaveStore 和 storage-guard 一起跑结果不变、不传 reward 时按 `growthReward()` 发奖（B 未填不发、可重试）。
- **启动文件**（`boot.test.js`）：43 项（正常启动、分包失败 Retry、分包无响应 10 秒提示、旧回调不重复启动、后台不计时、触摸修正；v7.5 加：包内文件 10 秒重发、30 秒失败、每帧最多计 1 秒、场景出错/卡住出 Retry、启动异常显示 Retry、Retry 跳过已完成步骤；2.0 加：storage-guard 在游戏脚本前装上、登录只发一次且不等结果、登录抛错/失败/没有接口都不影响启动、WebP 探针只在开关打开时加载、每次 Retry 先重新探测；v1.4 加：假解析器按真 2.4 的样子写（处理函数表不公开、同一个 id 的第二次请求并到第一次上），图片解码 10 秒重发、30 秒失败后下一次请求重新解码、后台不计时、出错重试一次、plist 等非图片解析不包、场景出来后的 Retry 不再显示加载；v1.5 加 4 项：每秒约 1 帧时卡一个首页图、重发后进首页不出 "Load failed"，一直卡只在 30 秒文件失败时出 Retry（10 秒、20 秒都不出），文件有结果后 10 秒总看守照常工作，重发本身算进度；v1.6 加 4 项：假引擎按真 2.4 的样子加载场景（场景 JSON 进文件缓存、原地反序列化、依赖失败时缓存不删），场景图片超时后点一次 Retry 就进场景，图片一直卡时 Retry 后不会马上又失败、等图片真失败才再出 Retry，被取代的那次场景失败也会被清掉，正常启动和没有缓存接口的引擎不受影响）。
- **工程检查**（`check-kit-project.test.js`）：19 项（模板通过；App ID 缺文件、没有 appid、空、testappId、非数字、和 PlatformConfig 不一致都拒绝；2.0 加：缺或改 storage-guard.js、缺或改 HomeGrowthEntries.js、5B 改成别的数、删掉 growthReward、B 没填、main.js 删掉存档层那一行都拒绝；build-templates 里的自写件和游戏代码直接调 `checkShortcut` 只警告）。
- **激励广告计时**：8 项，按 v7.4 口径（请求 15 秒只算前台、开播后不计时、30 秒无回调出 X、超时/X/取消后迟到的视频不发奖）：视频 200 秒、16 秒后才开播、播放中切后台、加载中切后台、一直加载不出来、开播后没有回调、取消后迟到看完、isEnded 不是 true。旧的 v7.3 `RewardedService.js` 跑这套会失败 7 项。
- **存档层**（`storage-guard.test.js`）：16 项（读到 null/undefined/''/false/0/true、数字和布尔写入转文字、键列表判新玩家、读出对象原样、装两次只一层、SaveStore 键原样读）。
- **首页双入口**（`home-entries.test.js`）：7 项（不支持时提示、图标失败显示文字、奖励等于 `growthReward()`、连点只发一次）。
- **3.x**：`touch-3x.test.js` 15 项、`plugins-3x.test.js` 21 项（第七节）。
- **反例**：存档/流程 14 个、启动 32 个（v1.4 加 4 个：图片解码不包、照旧读 `_parsers`、改成包 `parser.parse` 入口、迟到 Retry 又显示加载；v1.5 加 3 个：总看守不等等待中的文件、等待计数不减、重发不算进度；v1.6 加 3 个：失败的场景不清缓存、按错的 id 清、被取代的那次失败不记）、存档层 8 个、首页入口 6 个故意改坏的版本，测试都会变红（另有 Snake 4 个、3.x 触摸 8 个）。证明测试能抓错，不是摆设。

---

## 五、现在的验证程度（如实）

- `TikTokMissionService.js` 和 SnakeVSBlock v32 逐字节相同，原游戏已扫码通过。`touch-coordinates.js` 和 StarPop v50 逐字节相同，但 StarPop v50 没有找到用户扫码确认的记录，**待真机复测**（2026-10-29 R1 核对；以前写的"已在 StarPop 中通过"没有证据）。`RewardedService.js` 在 v7.4 按 Basil 超时规则改写（见 `remake-ads/references/ad-timeout-and-regression.md`），由 Snake 回归用例和出包前 10 个广告用例证明，还没有新的真机扫码记录。
- `main.js` 以 MetalMaster 已通过的原文件为底，加了一行触摸修正，v7.5 又按射击高手2048 v82 改写了加载守卫和 Retry，2.0 又加了存档层、登录和 WebP 例外开关，**只在 Node 模拟环境测过，待真机复测**。它按 Cocos 2.4.15 编辑器的 `main.js` 约定写；v7.7 在模拟宿主里用 finalize 后的真包实跑过 2.4.4（DotsDelivery v40）、2.4.6（BobbysBeat v22）、2.4.13（射击高手 pkg81）：首页和第 1 关都正常，所以 `startup24.needs.engine_versions` 是这四个版本，finalize 在它们上面都换平台包 `main.js`；其他 2.4.x 保留自己的 `main.js`、只插触摸和存档两行并警告。宿主不等于真机。
- `webp-probe/` 两套探针件都是从游戏包里拿来的（2.4 来自 Mabel's Meadow r8，3.x 来自 LunasJade v0.10.1 并去掉 data: 备用），**都待真机复测**。
- `SaveStore.js`、`MissionFlow.js`、`HomeGrowthEntries.js`、`storage-guard.js`（以射击高手 v85 真机版为底改写）是新写或改写的，只在 Node 模拟环境测过。
- 所有测试都是模拟环境，**不等于手机扫码通过、不等于真实广告能播**。2.0 以后每个新游戏都会自动装上这些件，一处出错就是所有新游戏一起出错；第一款 v7.7 新游戏扫码通过之前，交付回复里写明"标准件待真机复测"。

**所以 2.0 的用法**：先用下一个新游戏接入，上传扫码，测一遍"进游戏 → 点按钮有反应 → 看广告 → 加桌面回来领奖 → 个人主页回来领奖 → 关掉重开奖励和进度还在"。全部正常后，把 `KIT_MANIFEST.json` 里这几项的状态改成"已扫码通过"，之后所有游戏照搬。
如果扫码出问题，只修平台包、升版本号，不要在单个游戏里改。

---

## 六、在重塑 Skill 里的位置（2026-10-27 已接入）

- 平台包放在重塑 Skill 的 `remake-core/assets/platform-kit/`，规则写在 `cocos-game-check/startup` 板块的"防卡住固定做法"。
- 出包门禁：工程原样用平台包（`check_kit_project.py` 通过，打包出来的 `main.js`、`touch-coordinates.js` 和平台包逐字节一致）时，不再要求单独交 Retry 专项证据；"冷启动进首页 → 真实触摸 → 玩法有反应"的启动证明照样必须做。
- 启动包工坊的适配以后单独做；工坊包里带平台包时，要原字节、版本号和 `KIT_MANIFEST.json` 一致。

### 2.0（v7.7）：出包时自动装、门禁证明装上了

- 出包分两段，都由 `remake-core/scripts/tiktok_finalize.py` 做：构建前 `source` 段把平台包文件放进工程（缺的补、改过的换回）、换图片格式、写 App ID；构建后写包入口里的 native 段在 `game.js` 插加载行、放包根文件、压 PNG。两段都只读 `KIT_MANIFEST.json`。
- `parts` 里 2.4 和通用的件：`touch24`（触摸）、`startup24`（`main.js`，含静默登录检查）、`storage24`（存档层）、`webp_probe24`（只在 `--keep-webp-exception` 时装）、`rewarded`、`missions`（MissionFlow + TikTokMissionService）、`home_entries`、`savestore`、`platform_config`（唯一可改）。3.x 的件在 `parts-3x/KIT_PARTS_3X.json`（`touch3x`、`storage3x` 和 5 个插件件），由 `includes` 合进来，名字不能重复。
- 产物的 `main.js` 是平台包原文件时，触摸和存档层由它自己装（`wiring` 里 `when: kit_main` 那条，只核对）；不是时（英化工程、旧游戏），在 `game.js` 的 `__globalAdapter.adaptEngine();` 后面各插一行，行尾带 `// tiktok-kit:<件名>:2.0`，第二次跑看到同一行就不再插。插在适配器之后是因为两个件都要用 `cc`（StarPop v50、射击高手 pkg85 都是这个位置）。
- v7.7 W-F1a：装平台包 `main.js` 时同时放 `webp-decode-probe.js`（只放脚本）；自写启动件还被包里别的文件 require 时不移走、给 `K_W_own_startup_kept` 警告；移走后 `game.js` 里注释掉的那一行写成 `require_removed(`，不会再被当成加载语句（射击高手 pkg81 的 "missing entry require: ./native-load-guard" 就是这行注释引起的）；源码段发现游戏自带和平台包模块同名的脚本（Cocos 2.4 模块名全局唯一，MabelsMeadow r8 自带 `TikTokMissionService.js`、旧 `MissionFlow.js`），新游戏连 `.meta` 一起移到 `.tiktok-kit/removed/<原路径>` 并警告，旧游戏只报告；2.4.4 适配器（DotsDelivery v40）没有 SDKVersion 判断、包内文件不做 fs.access，算已修好写法。游戏自己的打包步骤（例如 MabelsMeadow 的 `scripts/prepare-native-package.py` 把 `config/*.json` 放到包根）仍由游戏自己在写包入口之前做，不是平台包件。
- 门禁 `package_gates/kit_parts.py` 直接读包里的字节和清单比：文件哈希（K1）、加载行正好一次且位置对（K2）、同类件只有一层（K3）。新游戏不过就出不了包；旧游戏（遗留名单上的）只补缺了一定坏的件，其余只警告。

---

## 七、Cocos 3.x：插件版平台包

- 3.x 工程用 `plugins-3x/` 里的 5 个 `*.plugin.js`（PlatformConfig、TikTokMissionService、RewardedService、SaveStore、MissionFlow），放进工程 `assets/tiktok-platform/`，在编辑器里勾"导入为插件"并在原生和小游戏里加载（`tiktok_finalize.py source` 会写好 `.meta`）。它们由 `tools/make_plugin_scripts.py` 从 2.4 模块生成，BEGIN 和 END 之间和 2.4 模块逐字节相同；改了 2.4 的 5 个模块或 `parts/storage-guard.js` 以后必须先跑 `python3 -B tools/make_plugin_scripts.py`，再跑 `--check`，不跑的话 `plugins-3x.test.js` 会故意变红。
- 游戏代码用 `globalThis.TikTokKit.RewardedService`、`TikTokKit.SaveStore`、`TikTokKit.MissionFlow` 等，不 `require`。
- `PlatformConfig.plugin.js` 只改 BEGIN 和 END 之间的 `gameId`、`appId`、`placementMap`、`normalLevelCoins`，和 2.4 一样（生成的文件头也这样写）；加桌面、回访奖励 `growthReward()` 固定 5B，不改。
- 3.x 没有 `HomeGrowthEntries`（它是 2.4 的 `cc.Class` 组件），首页底排两个入口直接用 `TikTokKit.MissionFlow`（不传 `reward` 时自己发 `growthReward()`）。
- 触摸修正 `build-templates/bytedance-mini-game/tiktok-touch-3x.js` 插在 `game.js` 的 `require('./web-adapter')` 之前；存档层 `storage-guard.js` 插在它之后（之前插时 `window.localStorage` 还不存在，什么都装不上，Marlows R4 实测）。v7.7 不给 3.x 装启动件（没有真机通过的底子）。
