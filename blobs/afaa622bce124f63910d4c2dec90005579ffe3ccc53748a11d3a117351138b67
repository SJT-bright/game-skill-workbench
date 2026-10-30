# 内置板块：玩法体验＋固定模板（两个板块都用，用户 2026-10-23）

每款游戏 = **它自己的玩法体验**（关卡怎么玩、手感、画面）＋**同一套内置板块**（货币、结算×2、首页礼盒、皮肤、关卡、广告机制）。内置板块按各自板块 Skill 的固定模板做，数值由工具生成，**AI 不自己发明**——每多一个自己设计的功能，就多一处 bug（用户原话："多做多错"）。

反面案例（用户 2026-10-23）：原游戏的按钮不审查全部留着，更多游戏（交叉推广）、排名、分享、七日签到一直出 bug；广告按钮连点发两次奖、广告前后卡顿；每款游戏的皮肤数量、价格、加成都不一样且乱填。

## 一、先删：多做多错

**不做、原有的也删掉**（英化和重塑都一样）：

| 删掉 | 包括 |
|---|---|
| 排名 | 排行榜、Weekly League、周赛、好友排行、名次牌、排名皮肤 |
| 交叉推广 | 更多游戏、互推、跳到别的小游戏（`navigateToMiniProgram`、`showMoreGamesModal` 等） |
| 分享 | 分享按钮、炫耀、邀请、分享得奖励（`shareAppMessage` 等，见 [tiktok-home-growth.md](tiktok-home-growth.md)） |

**保留**：首页的 Add to Home Screen（桌面快捷方式）和 Profile Revisit（个人主页回访）两个键（ART-05）。

**重塑必做：七日签到**（用户 2026-10-27 改回）：首页日历图标＋7 天签到弹窗，逻辑原样复制 `assets/checkin/DailyCheckin.ts`，只改 `checkin-config.json`；金币按 B 值，签到送的皮肤用已有的普通/稀有款。规则见签到（重塑包 remake-skins 板块，英化包不含），数值见经济规则（重塑包 remake-economy 板块，英化包不含）。

**英化先做按钮审查**：开工时把原游戏每个页面、每个弹窗的每个按钮列出来，判断能不能用、有没有用，写进 `docs/modules.json` 的 `button_audit`：

```json
{"page": "home", "button": "More Games", "works": false, "keep": false, "why": "cross-promotion, banned"}
{"page": "home", "button": "Rank", "works": true, "keep": false, "why": "ranking, banned"}
{"page": "pause", "button": "Feedback", "works": false, "keep": false, "why": "opens nothing"}
{"page": "home", "button": "Play", "works": true, "keep": true, "why": "starts the level"}
```

没有真实功能的、点了没反应的、上表里的，一律 `keep: false` 并在代码和场景里删掉（不是隐藏）。重塑只审查启动包源码里带来的按钮。

## 各板块正文在哪里（2026-10-27 拆分）

原来写在本页的二到六节已经搬到各自的板块 Skill，规则只在那里维护。本页保留"先删"清单和总记录/门禁表。

| 板块 | Skill | 正文 |
|---|---|---|
| 货币、结算×2、礼盒、独立广告领币 | remake-economy（重塑包 remake-economy 板块，英化包不含） | 经济规则（重塑包 remake-economy 板块，英化包不含） |
| 皮肤与道具 | remake-skins（重塑包 remake-skins 板块，英化包不含） | 皮肤规则（重塑包 remake-skins 板块，英化包不含） |
| 关卡数量、限定关、奖励关、难度曲线 | remake-levels（重塑包 remake-levels 板块，英化包不含） | 关卡规则（重塑包 remake-levels 板块，英化包不含）、难度曲线（重塑包 remake-levels 板块，英化包不含） |
| 广告按钮防重、不卡顿、体力广告 | remake-ads（重塑包 remake-ads 板块，英化包不含） | 广告机制（重塑包 remake-ads 板块，英化包不含） |

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
| LEVEL-01（设计关） | `audit_level_plan.py`：英化原关保留/不足补至70；重塑至少60关；新设计才查限定/奖励模板与3B |
| PAGE-01（美术关） | `audit_page_richness.py`：首页有礼盒和签到入口、过关页有×2大按钮＋下方 Claim 文字、背景不花哨、没有排名页 |
| ART-05 | `audit_ui_coverage.py`、`audit_platform_markers.py`：没有排名/更多游戏/分享按钮和调用 |
| MOD-02、FEAT-01、LEVEL-02 | 浏览器实测（上面第六节） |
