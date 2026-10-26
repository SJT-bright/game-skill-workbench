# 内置板块：玩法体验＋固定模板（两个板块都用，用户 2026-10-23）

每款游戏 = **它自己的玩法体验**（关卡怎么玩、手感、画面）＋**同一套内置板块**（货币、结算×2、首页礼盒、皮肤、关卡、广告机制）。内置板块按本页的固定模板做，数值由工具生成，**AI 不自己发明**——每多一个自己设计的功能，就多一处 bug（用户原话："多做多错"）。

反面案例（用户 2026-10-23）：原游戏的按钮不审查全部留着，更多游戏（交叉推广）、排名、分享、七日签到一直出 bug；广告按钮连点发两次奖、广告前后卡顿；每款游戏的皮肤数量、价格、加成都不一样且乱填。

## 一、先删：多做多错

**不做、原有的也删掉**（英化和重塑都一样）：

| 删掉 | 包括 |
|---|---|
| 排名 | 排行榜、Weekly League、周赛、好友排行、名次牌、排名皮肤 |
| 七日签到 | 签到弹窗、每日登录奖励、首页日历图标、签到皮肤 |
| 交叉推广 | 更多游戏、互推、跳到别的小游戏（`navigateToMiniProgram`、`showMoreGamesModal` 等） |
| 分享 | 分享按钮、炫耀、邀请、分享得奖励（`shareAppMessage` 等，见 [tiktok-home-growth.md](tiktok-home-growth.md)） |

**保留**：首页的 Add to Home Screen（桌面快捷方式）和 Profile Revisit（个人主页回访）两个键（ART-05）。

**英化先做按钮审查**：开工时把原游戏每个页面、每个弹窗的每个按钮列出来，判断能不能用、有没有用，写进 `docs/modules.json` 的 `button_audit`：

```json
{"page": "home", "button": "More Games", "works": false, "keep": false, "why": "cross-promotion, banned"}
{"page": "home", "button": "Rank", "works": true, "keep": false, "why": "ranking, banned"}
{"page": "pause", "button": "Feedback", "works": false, "keep": false, "why": "opens nothing"}
{"page": "home", "button": "Play", "works": true, "keep": true, "why": "starts the level"}
```

没有真实功能的、点了没反应的、上表里的，一律 `keep: false` 并在代码和场景里删掉（不是隐藏）。重塑只审查启动包源码里带来的按钮。

## 二、货币和结算×2
- **Per-level currency (rule 21)**: read the rolled `coins` stored in `level_plan.json`; do not recompute a fixed amount. The plan stores `coins_base` / `coins_band` / `coins_roll` / `coins` and `reward_seed`; retry never re-rolls; the x2 ad uses the rolled value; bonus = 3x the chapter median; limited coin reward = the sum of the previous 5 rolled values.
（每款游戏都有）

- **每款游戏都有一种货币**，按题材起名字和画图标（海底 Pearls、糖果 Candies、森林 Acorns；只有宝藏/商店题材用普通金币），写进 `docs/modules.json` 的 `currency`，放在顶部资源栏（[top-bar-and-level-map.md](top-bar-and-level-map.md) 第一节）。英化原来有货币就沿用。
- **每关结束都有"看广告×2"**（无尽游戏：每局结束）。按钮是一整张生成的按钮图（`btn_x2_COINS` 这类，节点名 `BtnDouble`），在 NEXT 上面、比 NEXT 大一点；旁边小字按钮"No thanks"只领原数。
- 金额从 `AdRewards.resultReward(levelCoins, bonusPct(...))` 算：`total` 是不看广告的数，`doubled` 是看完广告的数（×2）。看完才发、只发一次；取消/失败照常发 `total`。
- 失败的关（有关卡游戏）不发货币，所以没有×2；无尽游戏的每局结算都有。

## 三、首页礼盒

- 首页下方功能按钮那排有一个**礼盒**（节点/图名带 `gift`）：**10 帧动画**（轻摇、发光、盖子跳一下，循环），按游戏画风生成 10 张同尺寸的图（≥128 px），放在 `docs/modules.json` 的 `gift_box.frames_dir`。10 帧动画是美术，只在美术关由 `art_check.py` 的"礼盒10帧动画（首页礼盒）"行查，设计关和最终总检测都不查帧数（用户 2026-10-24）。
- 点礼盒 → 小弹窗（礼盒大图＋货币数＋"Watch ad"按钮）→ 看完广告 → 货币飞到顶部资源栏。
- **一局一次**：领完礼盒变成静止、灰一点；每打完一关（无尽：每局）又能领一次（`onRoundEnd`），不累积多次。
- **越往后越多**：`giftReward = round5(max(R, 0.1 × 下一款皮肤价格) + 0.5R × floor(已通关数/10))`——通关越多、买的皮肤越多（下一款越贵），礼盒越大，正好帮玩家攒下一款皮肤。皮肤全买齐时按最贵那款算。

## 四、皮肤板块（默认要，问用户）

### 1. 先判断适不适合，再问用户

- 看游戏有没有**主角**（一个角色、一辆车、一个球、一把刀……能换外观的东西）和**能换的场景背景**。看不出来时看源码和截图，必要时网上搜这类游戏的皮肤做法，写进 `skins.why`。
- 适合时**默认要**。英化写在优化清单（[模板8](../assets/session-relay-templates.md) 第九节）、重塑在写规格时，用勾选框问：

> **内置板块**（默认都要，不要的把 ☑ 改成 ☐）
> ☑ 皮肤板块：20 款主角皮肤＋10 款背景，价格、加成按固定模板，限定皮肤排第一（我的判断：适合，因为……）
> ☑ 背景皮肤（游戏有能换的场景时）

- 回答写进 `docs/modules.json` 的 `skins.user_choice`（和 `backgrounds`）、`asked` 写怎么问的。未回复时只可按默认拟定方案；尚未获批的英化优化清单不得提前实施。不适合时（没有能换外观的主角）写 `suitable: false` 和原因，不做。

### 2. 数量、稀有度、价格、加成（工具生成，不手填）

```
python scripts/make_skin_table.py --R <中等难度一关的货币> --levels [--final-level <最后一个限定关，≥70>] [--limited-mode final|every_10] [--no-backgrounds] --out assets/resources/config/unlock_table.json
python scripts/make_skin_table.py --R <R> --endless --out assets/resources/config/unlock_table.json
```

| | 主角皮肤（20 款） | 背景（10 款） |
|---|---|---|
| 排第一 | 限定皮肤（变暗显示，写明怎么得到） | — |
| 免费 | 1 款初始形象 | 1 款初始场景 |
| Common | 7 款，加成 5–10% | 3 款，加成 2–5% |
| Rare | 6 款，11–20% | 3 款，6–10% |
| Epic | 3 款，21–32% | 2 款，11–16% |
| Legendary | 2 款，33–50% | 1 款，17–25% |
| 限定 | 1 款，51–60% | — |

- **只用货币买**。第一款付费 = 2R，后面每款比前一款贵 1R（common）/ 4R（rare）/ 10R（epic）/ 20R（legendary）——R=50 时：100、150…400，600…1600，2100、2600、3100，4100、5100，像 50/200/500/1000 这样越往后差距越大。看广告解锁皮肤取消了（贵的皮肤要远超 8 个广告）；看广告试用照旧（[rarity-unlock-design.md](rarity-unlock-design.md) 第四节）。
- **限定皮肤**：有关卡游戏打过限定关获得，只能在那里拿；两种格式任选（用户 2026-10-24）：`final` 只有最后一个限定关送一款（`hero_limited`），`every_10` 每个限定关各送一款（`hero_limited_10`、`hero_limited_20`…，全部排在最前面）；无尽游戏用大量货币（最贵皮肤的 1.5 倍）＋6 次广告解锁。不在试用弹窗里。
- 只填 `name` 和 `art`，数字不改；`audit_acquisition_progression.py` 按 `module: skin.v1` 查数量、台阶、加成和限定皮肤。

### 3. 画得越来越精致

common 一个配饰（帽子、眼镜、围巾）→ rare 换配色＋配饰 → epic 整套服装 → legendary 整套服装＋特效（拖尾、光芒）→ **限定最精致**（主题服装、多个配饰、光环、自己的待机动画）。背景同理：common 换色调，legendary 是完整的新场景。背景皮肤也要守"背景不花哨"（[page-richness.md](page-richness.md)）。

### 4. 加成和界面

- 过关货币 = 基础 ×（1 + 主角皮肤加成 + 背景加成），四舍五入，**只算当前装备的**（每组一个），`AdRewards.bonusPct` 算。看广告试用的皮肤，试用那一关也有加成（试用弹窗写"Try it: +30% coins this level!"）。
- 皮肤页两个标签（Heroes / Backgrounds）；第一格是限定皮肤（变暗剪影＋"Clear Lv.<关数>"或价格＋广告次数；`every_10` 时前几格都是限定皮肤）；后面按价格从低到高；卡片上货币小图标＋"+18%"，已装备的有"Equipped"。
- 详情写"+18% coins every level"；结算页货币下面多一行"Skin bonus +9"。
- 换皮肤立刻生效，背景皮肤换完游戏背景马上变；重开后一致。

## 五、关卡板块

- **有关卡**（通关型）：至少 70 关（不到 70 补到 ≥70，原有超过 70 关完整保留，多于 70 也行，用户 2026-10-24）、一定有地图、难度逐关递增（[top-bar-and-level-map.md](top-bar-and-level-map.md) 第二到五节）。
  - **每 10 关一个限定关**：第 10、20、30…关，地图节点是**华丽的大边框**（金边、宝石、皇冠），难度照常，第一次打过给大量货币并解锁下一章；**限定皮肤：`final` 只有最后一个限定关送，`every_10` 每个限定关各送一款**（关卡表 `limited_skin_mode`、皮肤表 `limited_mode` 写同一个）。
  - **每 10 关一个奖励关**：位置由 `make_level_plan.py --seed` 按种子随机（不在每段第 1 关和最后 2 关），比这段最简单的普通关还简单，给 **3 倍货币**，结算看广告变 **6 倍**；地图节点**画成货币图标**。
  - `python scripts/make_level_plan.py --levels <≥70> --coins <R> --limited-skin hero_limited --limited-skin-mode final|every_10 --seed <数字> --out assets/resources/config/level_plan.json`
- **无尽**：没有地图（`--endless`）；每局结束有×2、礼盒按局数涨，限定皮肤用货币＋广告。

## 六、广告机制板块（和玩法体验分开）

广告设计的独立入口为 [cocos-game-ad-design](../../cocos-game-ad-design/SKILL.md)，统一盘点触发、收益、频率和免费路径；本页和 `AdRewards.ts` 继续维护具体公式与模块契约。

bug 常常出在广告按钮那里（连点、回调来两次、关掉后还能点、广告前后卡顿）。所以广告奖励**不在每款游戏里重写**：

- 把 `assets/modules/AdRewards.ts` **原样复制**进游戏（`audit_game_modules.py` 比对 SHA-256），结算×2、奖励关 3→6 倍、礼盒、皮肤价格、加成全从它算；数值只来自 `unlock_table.json` 和 `level_plan.json` 两个文件。
- **每个广告按钮**都用 `createAdGate()`：点下去 `token = adGateStart(g)` 返回 false 就直接 return（广告进行中再点无效）；每次请求捕获自己的 token，任何回调都先 `adGateFinish(g, token, completed)`，返回 true 才发奖（只发一次）。按钮在广告期间变灰。旧 token 的回调不能解锁或奖励新请求；局次离开须取消该 owner，SDK会话未真实终止前不并发show。模块只做去重和数值，真实 SDK 完成、持久化事务和界面恢复仍按 AD/STORAGE 门禁。
- **不卡顿**：广告前先暂停游戏和音乐、停掉物理和计时；发奖动画用对象池，不在回调里加载资源或建大量节点；广告回来后恢复音乐、恢复输入。广告调用本身按 [tiktok-native-iaa.md](tiktok-native-iaa.md)。
- **玩法体验**（关卡、手感、画面）照各自的规则做；广告板块只管"什么时候给、给多少、只给一次"。

**测试重点**（MOD-02，浏览器里实测）：①每关/每局结束都有×2，看完正好 2 倍、只发一次；②礼盒点开→广告→货币（动画帧在美术关已查），一局一次，通关越多越大；③每个广告按钮连点 3 下只播一次、只发一次；取消/失败不发、按钮恢复；④广告前后、发奖动画不卡（录屏或看 FPS）；⑤重开后金币和礼盒状态一致。奖励关 3→6 倍、限定皮肤按 LEVEL-02 测，皮肤按 FEAT-01 测。

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
| MOD-01（必查） | `audit_game_modules.py --project <工程> --binding <review.json> --out <报告>`：问过并记录、没有排名/签到/更多游戏/分享、按钮审查、AdRewards.ts 未改且模拟通过（`modules_harness.mjs`）、皮肤表 skin.v1、限定皮肤来路（`final`/`every_10`）；**设计关**用 `design_check.py` 跑，最终总检测不重查（礼盒 10 帧在美术关 `art_check.py` 查） |
| ECON-01（设计关） | `audit_acquisition_progression.py`：皮肤表的数量（19＋限定款数）、台阶、加成 |
| LEVEL-01（设计关） | `audit_level_plan.py`：≥70 关、每 10 关的限定关和种子奖励关、3 倍、限定皮肤格式 `final`/`every_10` |
| PAGE-01（美术关） | `audit_page_richness.py`：首页有礼盒、过关页有×2、背景不花哨、没有排名/签到页 |
| ART-05 | `audit_ui_coverage.py`、`audit_platform_markers.py`：没有排名/签到/更多游戏/分享按钮和调用 |
| MOD-02、FEAT-01、LEVEL-02 | 浏览器实测（上面第六节） |


### 有体力游戏的广告补充（用户 2026-10-24）

游戏已有体力系统时必须提供“看激励广告增加 3 格体力”的入口；完整观看一次只入账 +3，取消/失败/超时不发、不扣体力，免费关闭可用。奖励预览与按钮准确表达 +3，不能标成 ×2。保留现有自然恢复与免费获得渠道；按原上限限制广告资格，容量不足 3 格时不播放，避免观看后只兑现 +1/+2。检查空体力、可容纳 +3、满体力、重复回调与保存恢复。无体力游戏不因此新增体力系统。
