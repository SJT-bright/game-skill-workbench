# TikTok 平台包 v1.1（Cocos Creator 2.4.15，重塑/自制游戏专用）

v1.1（2026-10-27）：卡住判定 20 秒 → 10 秒（skill 规定 10 秒无进展必须出 Retry）；放进重塑 Skill 的 `remake-core/assets/platform-kit/`，原样用平台包的游戏不再单独做 Retry 专项测试。

这一包是每个自制游戏都一样的 **TikTok 部分**：启动加载、激励广告、桌面快捷方式、个人主页回访、存档。
玩法、美术、关卡、货币数值都不在这里。

**规则只有一条：除了 `PlatformConfig.js`，其他文件整份复制，一个字都不改。**
要改就改平台包本身，升版本号（v1 → v2），重新跑测试，再发给所有游戏。

---

## 一、包里有什么、从哪来

| 文件 | 作用 | 来源 | 状态 |
|---|---|---|---|
| `assets/tiktok-platform/PlatformConfig.js` | App ID、广告位、存档名 | 新整理 | **每个游戏只改这一个** |
| `assets/tiktok-platform/RewardedService.js` | 激励广告：每次新建、只有看完才发奖、超时、防叠开 | SnakeVSBlock v32，逐字节相同 | 已在 Snake 中通过 |
| `assets/tiktok-platform/TikTokMissionService.js` | 快捷方式/回访的 4 个 TikTok 接口 | SnakeVSBlock v32，逐字节相同 | 已在 Snake 中通过 |
| `assets/tiktok-platform/SaveStore.js` | 存档：一个 key、一个字符串、写后读回比对 | 平台包新写 | Node 测试通过，**待第一次扫码** |
| `assets/tiktok-platform/MissionFlow.js` | 主页两个按钮的完整流程（不画界面） | 平台包新写 | Node 测试通过，**待第一次扫码** |
| `build-templates/bytedance/main.js` | 启动：每一步失败都有 Retry，10 秒没进度就提示 | MetalMaster r5 + 1 行触摸修正 | 原文件已在 MetalMaster 中通过 |
| `build-templates/bytedance/touch-coordinates.js` | TikTok 触点只有 screenX/screenY、Cocos 2.4 读 clientX/clientY：不装就按钮点不动（必装，探针校验） | StarPop v50，逐字节相同 | 已在 StarPop 中通过 |
| `tools/check_kit_project.py` | 一条命令检查工程 | 平台包新写 | — |
| `tests/` | 全部测试 | Snake 原测试 + 平台包新测试 | 全部通过 |
| `KIT_MANIFEST.json` | 每个文件的 SHA256 | — | 检查脚本用它比对 |

---

## 二、构建规则（7 个通过的自制游戏总结出来的共同点）

1. **引擎固定 Cocos Creator 2.4.15**，构建平台选 **ByteDance Mini Game（字节小游戏）**，不要用 Web Mobile。
2. **`assets/resources` 设为 Asset Bundle，压缩类型 ByteDance 选"小游戏分包"**。大图、音频都放这里，主包才能 ≤ 4MB。
3. **图片只用 PNG / JPG，不要 WebP**。（以前出现过手机把 WebP 判断错导致进不去）
4. **ByteDance 构建设置里"首场景分包 Start Scene Asset Bundle"关掉，REMOTE_SERVER_ROOT 留空**。不从外网下载任何东西。
5. **`build-templates/bytedance/` 里只放平台包的 `main.js` 和 `touch-coordinates.js`**。不放 `game.js`、`game.json`，让编辑器自己生成，这样引擎文件名永远对。
6. 不调用分享、排行榜、更多游戏（skill 原规则）。
7. 游戏代码不直接调用 `createRewardedVideoAd`、`addShortcut` 这类 TikTok 接口，统一通过平台包。

---

## 三、新游戏怎么接（给 AI 照做）

### 第 1 步：复制

- 把 `assets/tiktok-platform/` 整个文件夹复制到游戏的 `assets/` 下。
- 把 `build-templates/bytedance/` 里的两个文件复制到游戏工程的 `build-templates/bytedance/`。

### 第 2 步：改配置（唯一要改的文件）

`PlatformConfig.js`：

- `gameId` 改成这个游戏的英文小写名，比如 `'juicerelax'`。
- `appId`、`clientKey`、三个广告位从电脑上的 `~/.game-skill/ad-config.json` 抄过来（skill 的统一广告配置），不填 Client Secret。
- `placementMap` 里列出这个游戏用到的广告位置，比如 `revive`、`double_coins`、`gift`、`hint`、`skin`。没列出的位置会返回 `unconfigured`，不会乱播。

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

```js
var MissionFlow = require('MissionFlow');
var flow = new MissionFlow({
  store: save,
  reward: function (kind, d) { d.coins += 25; },              // 只改 d
  rewardText: {shortcut: '+25 Coins', profile: '+25 Coins'},
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

测试内容：

- **Snake 原测试**：广告 + 回访组件 20 项、接口兼容 8 项、4 个故意改坏的反例，证明这两个文件和 Snake 里通过的版本行为一样。
- **存档 + 主页流程**：20 项，场景来自 skill 记录过的故障（离开再回来、连点、超时、complete-only、存档失败、旧结果覆盖新结果……）。
- **启动文件**：8 项（正常启动、分包失败 Retry、分包无响应 10 秒提示、旧回调不重复启动、后台不计时、触摸修正）。
- **反例**：存档/流程 9 个、启动 5 个故意改坏的版本，测试都会变红。证明测试能抓错，不是摆设。

---

## 五、现在的验证程度（如实）

- `RewardedService.js`、`TikTokMissionService.js`、`touch-coordinates.js` 和原游戏逐字节相同，原游戏已扫码通过。
- `main.js` 是 MetalMaster 已通过的原文件加了一行触摸修正，**这个组合还没在手机上扫过**。
- `SaveStore.js`、`MissionFlow.js` 是新写的，只在 Node 模拟环境测过。
- 所有测试都是模拟环境，**不等于手机扫码通过、不等于真实广告能播**。

**所以 v1.1 的用法**：先用下一个新游戏接入，上传扫码，测一遍"进游戏 → 看广告 → 加桌面回来领奖 → 个人主页回来领奖 → 关掉重开奖励还在"。全部正常后，把 `KIT_MANIFEST.json` 里这几项的状态改成"已扫码通过"，之后所有游戏照搬。
如果扫码出问题，只修平台包、升 v2，不要在单个游戏里改。

---

## 六、在重塑 Skill 里的位置（2026-10-27 已接入）

- 平台包放在重塑 Skill 的 `remake-core/assets/platform-kit/`，规则写在 `cocos-game-check/startup` 板块的"防卡住固定做法"。
- 出包门禁：工程原样用平台包（`check_kit_project.py` 通过，打包出来的 `main.js`、`touch-coordinates.js` 和平台包逐字节一致）时，不再要求单独交 Retry 专项证据；"冷启动进首页 → 真实触摸 → 玩法有反应"的启动证明照样必须做。
- 启动包工坊的适配以后单独做；工坊包里带平台包时，要原字节、版本号和 `KIT_MANIFEST.json` 一致。
