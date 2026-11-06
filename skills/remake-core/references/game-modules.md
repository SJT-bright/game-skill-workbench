# 内置板块：玩法体验＋固定模板（两个板块都用，用户 2026-10-23）

每款游戏 = **它自己的玩法体验**（关卡怎么玩、手感、画面）＋**同一套内置板块**（货币、结算×2、首页礼盒、皮肤、关卡、广告机制）。内置板块按各自板块 Skill 的固定模板做，数值由工具生成，**AI 不自己发明**——每多一个自己设计的功能，就多一处 bug（用户原话："多做多错"）。

反面案例（用户 2026-10-23）：原游戏的按钮不审查全部留着，更多游戏（交叉推广）、排名、分享、七日签到一直出 bug；广告按钮连点发两次奖、广告前后卡顿；每款游戏的皮肤数量、价格、加成都不一样且乱填。

## 一、先删：多做多错

**不做、原有的也删掉**（英化和重塑都一样）：

| 删掉 | 包括 |
|---|---|
| 排名 | 联网/全服/好友排行榜、Weekly League、周赛、编出来的全服名次、排名皮肤（局内对本地机器人的名次、奖杯、段位可以用（Saul 10-31，见 no-social-features.md）） |
| 交叉推广 | 更多游戏、互推、跳到别的小游戏（`navigateToMiniProgram`、`showMoreGamesModal` 等） |
| 分享 | 分享按钮、炫耀、邀请、分享得奖励（`shareAppMessage` 等，见 [tiktok-home-growth.md](tiktok-home-growth.md)） |

**保留**：首页的 Add to Home Screen（桌面快捷方式）和 Profile Revisit（个人主页回访）两个键（ART-05）。

**重塑必做：七日签到**（用户 2026-10-27 改回）：首页日历图标＋7 天签到弹窗，逻辑原样复制 `assets/checkin/DailyCheckin.ts`，只改 `checkin-config.json`；金币按 B 值，签到送的皮肤用已有的普通/稀有款。规则见[签到](../../remake-skins/references/skin-bonus-and-checkin.md)，数值见[经济规则](../../remake-economy/references/economy-rules.md#四七日签到的数值用户-2026-10-27)。

**英化先做按钮审查**：开工时把原游戏每个页面、每个弹窗的每个按钮列出来，判断能不能用、有没有用，写进 `docs/modules.json` 的 `button_audit`：

```json
{"page": "home", "button": "More Games", "works": false, "keep": false, "why": "cross-promotion, banned"}
{"page": "home", "button": "World Rank", "works": true, "keep": false, "why": "global ranking, banned"}
{"page": "pause", "button": "Feedback", "works": false, "keep": false, "why": "opens nothing"}
{"page": "home", "button": "Play", "works": true, "keep": true, "why": "starts the level"}
```

没有真实功能的、点了没反应的、上表里的，一律 `keep: false` 并在代码和场景里删掉（不是隐藏）。重塑只审查启动包源码里带来的按钮。

## 一局的状态、定时、特效、移动：写玩法时就用零件（生成时预防 P11、P18，2026-11-04）

问题普查里「重开或切关后状态没清」23 款、「Resume 后卡住」「弹窗关不掉」一类很多、「卡顿」30 次。原因都是同几种写法：本局数据散在各处、重开只清一部分（割草分数、Pinecone 复活次数）；旧关的回调改了新关（大西瓜 `IsHit`）；一个 `paused` 布尔被弹窗和广告共用（甜点消消乐）；`setInterval` 每进一次场景开一个；特效播完不删（方块迷阵 120 次合并剩 86 个）；移动按帧走、不乘 `dt`（60/120 帧差一倍）。平台包两个零件把对的写法变成最省事的写法，**新游戏（自制、重塑）写玩法时必须这样写**：

| 要做的事 | 只这样写 | 不要这样写 |
|---|---|---|
| 本局数据（分数、复活次数、关卡状态、是否已撞） | 只放在 `session.state` 里；开局、Retry、下一关都调 `session.newRun(init)`，`init` 每次返回一个新对象 | 写在组件字段、全局变量、`globalData` 里，Retry 时逐个清 |
| 碰撞、动画结束、加载、广告结果、网络回包等异步回调 | 用 `session.guard(fn)` 包起来（换局后自动作废、拥有它的节点销毁后作废）；只能生效一次的（发奖、过关）用 `session.once(fn)` | 直接传函数，回调里再判断「是不是还在这一关」 |
| 定时 | `session.after(ms, fn)`、`session.every(ms, fn)`，暂停时不走、换局和切场景自动清 | `setInterval`、`setTimeout`、`this.schedule`、`scheduleOnce` |
| 暂停 | `var release = session.pause('popup')`，关窗时 `release()`；原因用 `'popup'`、`'ad'`、`'revive'`、`'settings'` 等；切后台由零件自动 `pause('hide')`；`isPaused()` 要等全部原因释放才是 false | 一个 `paused` 布尔；关窗时恢复「打开前的暂停状态」快照 |
| 每帧更新 | `update(dt) { var d = session.tick(dt); if (!d) return; ... }`，后面所有移动和计时都用 `d` | 每帧里自己判断各种暂停标志 |
| 移动、旋转、滚动 | `session.move(node, vx, vy, d)`（单位：每秒），其他量用 `RunSession.step(v, 每秒变化, d)`；物理推力用 `PhysicsClock.force(v, dt)` | `node.x += 5`（按帧固定步长） |
| 特效、子弹、飘字 | `FxPool.create(cc, {parent, make, reset, max, life})`，`pool.spawn(x, y)`，`update` 里 `pool.tick(d)`，换局 `pool.releaseAll()` | 每次 `new cc.Node` 或 `cc.instantiate`、播完不删；`update` 里造节点 |
| 障碍物、敌人、子弹的回收和隐藏（生成时预防 R4L2） | 图片、动画、碰撞体都挂在**同一个根节点**下，整个根节点一起回收：池子里的用 `pool.release(根节点)` / 到期自动回池，不进池的用 `session.recycle(根节点)`（要删再加 `{destroy: true}`），取出复用用 `pool.spawn` / `session.reuse(根节点)`。零件会关掉根节点和子节点上全部碰撞体、物理体（2.4 `cc.Collider`/`cc.PhysicsCollider`/`cc.RigidBody`，3.x `Collider2D`/`RigidBody2D`），停掉缓动、动作和组件 `schedule`，复用时只把它关掉的碰撞体打开；敌人的定时器在 `reset` 或 `onEnable` 里重新开，或用 `session.every(ms, fn, 根节点)` 绑在敌人上 | 自己写 `图片节点.active = false`、`图片节点.destroy()`、把动画子节点单独还给别的池；只关图不关碰撞体（回家快跑：蜗牛 5 秒后图没了，碰撞体还挡人） |
| 广告暂停 | ad-boost：`Kit.setup(session.adHooks())`（原因 `'ad'`，每次 `pauseGame` 对应一次 `resumeGame`） | 广告回调里直接改暂停布尔 |

- 零件文件：`remake-core/assets/platform-kit/parts/RunSession.js`、`parts/FxPool.js`，2.4 和 3.x 同一份（2.4 放进 `assets/tiktok-platform/` 用 `require('RunSession')`，3.x 当插件脚本，全局名 `TikTokRunSession`、`TikTokFxPool`）。接口说明在文件头注释里。
- 新游戏不手拷这两个文件：每次构建前的 `tiktok_finalize.py sync --board remake` 自动装好并按哈希换回（3.x 连插件 .meta）；英化游戏 sync 不装，要用时照上一条手拷（生成时预防 R4F1）。
- 场景主组件：`onLoad` 里 `session = RunSession.create(cc, {owner: this.node})`，`onDestroy` 里 `session.dispose()`、`pool.destroy()`。开发版可在 `onLoad` 里调一次 `FxPool.devWatch(cc)`：`update` 里造节点、场景节点数一直涨时打警告，正式版自动不生效。
- 暂停页、复活页、结算页（P05 模板）打开时 `session.pause(...)`，关掉时调它返回的 `release()`。「回首页」才用 `session.resumeAll()`。
- **英化游戏不改原版玩法代码**：原版的状态、定时器、特效写法照旧，只在 AI 新加的暂停、复活、广告入口用 `RunSession`（例如新加的复活页 `pause('revive')`、ad-boost 的 `adHooks()`）。
- 证据：`tests/run-session.test.js`（单个布尔暂停、Retry 只清一部分、旧碰撞回调、`setInterval`、每帧 `+= 5` 五个旧写法反例都判错）、`tests/fx-pool.test.js`（120 次发射节点数不涨；方块迷阵写法涨到 120）、`tests/entity-retire.test.js`（回收后碰撞体、物理体全关，复用再开，旧缓动和定时器不带到下一只；回家快跑只藏图片的写法留下看不见的挡人碰撞体）。都只是 Node 模拟，待真机复测。

### 买、做、退都进事务（经营类玩法，生成时预防 R4L3）

喵咪小吃铺一款出了 4 条：家具在 B 房间按 A 房间的价格扣钱、做菜等待时取消退回了已经用掉的食材、三条鱼做完显示肉类成品（成品图读到下一张订单）、公寓里同一个示例房间出现两次。原因都是买、做、退在结束时才去读会变的全局字段，没有锁，存档分几次写。**新游戏（自制、重塑）凡是花钱、花材料换东西的操作（商店、家具、做菜、合成、升级、出售）一律用平台包 `parts/ShopTx.js`**：

| 要做的事 | 只这样写 | 不要这样写 |
|---|---|---|
| 点「买 / 做 / 退」 | `var tx = shop.begin(kind, {lock: 'furniture:' + room + ':' + item, buttons: [按钮], snapshot: {订单、价格、配方}, cost: {coins: 价格, 'inv.fish': 3}})`；返回 null 就什么都不做 | 直接改 `coins`，按钮不锁，靠 500ms 防连点 |
| 等待、确认、动画之后 | 只读 `tx.snap`（价格、成品图、房间都从这里来） | 结束时再读 `this.currentPrice`、`orders[current]`、当前房间页签 |
| 做菜中途用掉材料 | `tx.consume({'inv.fish': 1})` | 开始就整份扣掉，取消时整份加回 |
| 完成 | `tx.commit({add: {coins: tx.snap.recipe.price}, apply: function (d) {...}}, onDone)`：扣费和发奖同一次 `SaveStore.grant`；只能领一次的订单给 `id: 'order:' + 订单id` | 先 `update` 扣钱、再 `update` 放东西 |
| 取消 | `tx.cancel()`：只扣已经 consume 的，其余本来就没扣 | 退回开始时扣的全部 |
| 商品表、示例房间 | `ShopTx.catalog(rows, {name: 'rooms'})`，重复 id 或只改了 id 的复制行当场报错 | 复制一行改个名当新示例 |

- sync 给新游戏自动装（2.4 `require('ShopTx')`，3.x 插件，全局 `TikTokShopTx`），英化游戏不装、原版经营代码不改。
- 证据：`tests/shop-tx.test.js`（四种旧写法都判错；连点两次只扣一次；存档失败钱和东西都不变、事务留着可重试）。只是 Node 模拟，待真机复测。

## 各板块正文在哪里（2026-10-27 拆分）

原来写在本页的二到六节已经搬到各自的板块 Skill，规则只在那里维护。本页保留"先删"清单和总记录/门禁表。

| 板块 | Skill | 正文 |
|---|---|---|
| 货币、结算×2、礼盒、独立广告领币 | [remake-economy](../../remake-economy/SKILL.md) | [经济规则](../../remake-economy/references/economy-rules.md) |
| 皮肤与道具 | [remake-skins](../../remake-skins/SKILL.md) | [皮肤规则](../../remake-skins/references/skin-rules.md) |
| 关卡数量、限定关、奖励关、难度曲线 | remake-levels（重塑包 remake-levels 板块，英化包不含） | 关卡规则（重塑包 remake-levels 板块，英化包不含）、难度曲线（重塑包 remake-levels 板块，英化包不含） |
| 广告按钮防重、不卡顿、体力广告 | [remake-ads](../../remake-ads/SKILL.md) | [广告机制](../../remake-ads/references/ad-mechanism.md) |

## 七、记录和检查

`docs/modules.json`（`audit_game_modules.py` 读）：

```json
{"schema": "game_modules.v1",
 "asked": "优化清单勾选框，用户 2026-10-23 回复：全部默认",
 "gameplay": "brick breaker, 70 levels",
 "currency": {"name": "Pearls", "icon": "pearl"},
 "skins": {"suitable": true, "why": "a ball hero and an ocean scene", "user_choice": true, "backgrounds": true},
 "gift_box": {"frames_dir": "assets/resources/ui/gift"},
 "button_audit": [{"page": "home", "button": "More Games", "works": false, "keep": false, "why": "cross-promotion, banned"}]}
```

| 门禁 | 查什么 |
|---|---|
| MOD-01（必查） | `audit_game_modules.py --project <工程> --binding <review.json> --out <报告>`：问过并记录、没有排名/更多游戏/分享、按钮审查、AdRewards.ts 未改且模拟通过（`modules_harness.mjs`）、皮肤表 skin.v1、限定皮肤来路（`final`/`every_10`）；**设计关**用 `design_check.py` 跑，最终总检测不重查（礼盒 10 帧在美术关 `art_check.py` 查） |
| ECON-01（设计关） | `audit_acquisition_progression.py`：皮肤表的数量（19＋限定款数）、台阶、加成 |
| LEVEL-01（设计关） | `audit_level_plan.py`：英化原关保留、不补关；重塑至少60关；新设计才查限定/奖励模板与3B |
| PAGE-01（美术关） | `audit_page_richness.py`：首页有礼盒和签到入口、过关页有×2大按钮＋下方 Claim 文字、背景不花哨、没有联网/全服排名页 |
| ART-05 | `audit_ui_coverage.py`、`audit_platform_markers.py`：没有联网/全服排名、更多游戏、分享按钮和调用（局内本地名次不算） |
| MOD-02、FEAT-01、LEVEL-02 | 浏览器实测（上面第六节） |
