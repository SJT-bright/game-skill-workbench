---
name: remake-core
description: "共享脚本与规则库（英化包内供统一检查 cocos-game-check 和美工调用；触发词：检查脚本库、症状对照）。英化流程不使用其中的重塑板块规则（关卡、经济、皮肤、签到、教程等），英化只做 cocos-game-to-english 列出的事。"
---

> **英化包说明（Saul 2026-10-28，10-31 补）**：本库在英化包里只作为脚本与规则库，供 cocos-game-check、remake-art 和广告、货币两个板块调用；文中指向重塑板块（关卡、经济、皮肤、广告、引导等）的内容默认不适用于英化，英化按 [英化入口](../cocos-game-to-english/SKILL.md) 只做固定几项，其中结算 x2、看广告复活、领奖窗勾选框、广告计时和广告回归按本包的 [广告板块](../remake-ads/SKILL.md) 做，数额按 [货币板块](../remake-economy/SKILL.md)；Saul 要求创新玩法时，新加的部分按这些板块做（广告、货币在本包里，关卡、皮肤、引导在重塑包里）。


# 游戏 Skill 总合同与共享工具库

修订：`2026-10-27.modules-v6`。本 Skill 不做具体板块，只放三样东西：**大家共用的总规则**、**症状该找哪个板块**、**所有板块共用的脚本和模块**（`scripts/`、`assets/`、`examples/`）。每条板块规则只在它自己的板块 Skill 里写一次，这里只链接。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做，它高于各板块里与之冲突的旧说法；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

## 一、整个包怎么分层

| 层 | Skill | 负责 |
|---|---|---|
| 流程入口 | 重塑（重塑包 remake-game 板块，英化包不含） | 只管阶段顺序和确认点，到哪一步就调用哪个板块。英化和评审不在本包（用户 2026-10-27：重塑与英化完全分开，英化用独立的英化Skill包） |
| 制作板块 | 见下表 | 各自板块的规则、工具、修改步骤、联动和验收 |
| 收尾 | [测试与修复](../cocos-game-check/test/README.md)、[出包](../cocos-game-check/package/README.md)、[最终包检查](../cocos-game-check/package-check/README.md) | 功能验收、打包与包检查 |
| 工具 | [Ego浏览器](../ego-browser/SKILL.md)、[触屏脚本](../chrome-mobile-testing/SKILL.md)、[手机触控验收](../mobile-touch-computer-use/SKILL.md)、桌面多Agent（重塑包 desktop-agent-orchestrator 板块，英化包不含）、Grok 三件套 | 被上面各层调用 |

## 二、制作板块

| 板块 | Skill | 管什么 |
|---|---|---|
| 玩法与规格 | remake-game（重塑包 remake-game 板块，英化包不含） | 核心玩法、启动包导入、项目规格、手感 |
| 关卡 | remake-levels（重塑包 remake-levels 板块，英化包不含） | 关数（重塑≥60；英化不补关）、限定关、奖励关、波浪分档难度、关卡地图与顶部栏 |
| 经济 | [remake-economy](../remake-economy/SKILL.md) | B值、普通关收入、五档预算、结算×2、礼盒、独立广告领币、钱包事务 |
| 皮肤与道具 | remake-skins（重塑包 remake-skins 板块，英化包不含） | 皮肤数量、稀有度、解锁方式、加成、皮肤页、试用弹窗、道具商店 |
| 广告 | [remake-ads](../remake-ads/SKILL.md) | 广告入口、频率、防连点只发一次、不卡顿、SDK与测试ID、复活、难关看广告提示、广告模拟 |
| 美术与UI | [remake-art](../remake-art/SKILL.md) | 画风、页面布局、按钮、图片字、图标、动效、首页和设置页 |
| 新手引导 | remake-onboarding（重塑包 remake-onboarding 板块，英化包不含） | 首关教程、横竖屏说明、引导拖动、暂停恢复 |
| 英文文案 | remake-copy（重塑包 remake-copy 板块，英化包不含） | 全英文覆盖、文案质量、换图中的文字、缺字字形 |
| 音频 | game-audio-library（重塑包 game-audio-library 板块，英化包不含） | 音乐音效素材、响度、开关、接入代码 |
| 启动与稳定 | [cocos-game-check/startup](../cocos-game-check/startup/README.md) | 启动进得去、加载页、加载失败重试、Native存档、性能 |

## 三、症状 → 找哪个板块

用户没点名 Skill 时，按症状进入对应板块；用户点名了就直接用点名的板块。

| 用户说的问题 | 板块 |
|---|---|
| 关太少/太多、难度节奏不对、太难过不去、太简单、限定关/奖励关不对、地图不显示总关数 | 关卡 |
| 难关提示没出现、提示给错步骤、看完广告没提示 | 广告（哪些关算难关看关卡） |
| 金币太多/太少、买不起、×2 发错数、礼盒倒计时不对、看广告领币数不对 | 经济 |
| 皮肤数量/价格/加成不对、皮肤页乱、试用弹窗不该弹 | 皮肤与道具 |
| 广告点了没反应、连点发两次奖、广告前后卡顿、复活不对、取消后状态错 | 广告 |
| 难看、太暗、按钮挤在一起、图片字糊、遮挡、布局不对 | 美术与UI |
| 新手不知道怎么玩、教程卡住、引导手指位置错 | 新手引导 |
| 有中文残留、英文不地道、字显示成方块 | 英文文案 |
| 没声音、声音太吵、开关无效 | 音频 |
| 进不去游戏、卡加载、首页按钮全没反应、重开后存档丢了、掉帧 | 启动与稳定 |
| 玩法逻辑错、胜负判定错、重开状态没清干净 | [测试与修复](../cocos-game-check/test/README.md) |
| 出包、ZIP 被拒、包太大 | [出包](../cocos-game-check/package/README.md) |

一个问题碰到两个板块时（比如"广告×2发错数"既是广告也是经济），**数值归经济、触发和回调归广告**；先在数值所属板块修，再按联动表回查另一个。

## 四、联动总表：改了 A，要回查谁

| 改了 | 必须回查 |
|---|---|
| 经济（B值、价格、礼盒、×2） | 皮肤价格表、关卡表 `coins`、广告奖励预览文字、结算页显示、存档迁移 |
| 关卡（关数、限定关、奖励关） | 经济的普通收入基准、皮肤限定款数量（`every_10`）、关卡地图与顶部栏、教程关 |
| 皮肤（数量、加成） | 经济购买预算、结算页"Skin bonus"、试用弹窗广告入口、美术皮肤页 |
| 广告（入口、回调） | 经济发奖、存档事务、页面恢复、启动/加载期间的广告会话 |
| 美术与UI（布局、按钮） | 按钮真实点击、文案是否放得下、教程手指坐标、广告按钮位置 |
| 新手引导 | 第 1–2 关（教学）难度、首关输入、暂停/恢复 |
| 英文文案 | 按钮和面板是否放得下（美术）、图片字重做（美术） |
| 启动与稳定 | 首次进入的教程、存档读写、广告 SDK 初始化顺序 |

只回查表里列出的相关链，不因为改了一个板块就重跑整套验收（[检查范围与停止条件](../cocos-game-check/test/references/testing-scope-and-stop.md)）。

## 五、共用的总规则（按需读）

| 什么时候 | 读 |
|---|---|
| 开工判断走英化还是重塑 | [两个制作入口](references/two-boards.md)、[融合边界与默认配置](references/fusion-policy.md) |
| 选阶段、按症状找正文 | [当前共同合同](references/current-contracts.md) |
| 四个阶段与确认点 | [阶段流程](references/stage-flow.md)、[检查分阶段](references/check-stages.md)、[全流程门禁](references/process-gates.md) |
| 先删的功能 | [内置板块总览与先删清单](references/game-modules.md)、[分享与排行榜禁用](references/no-social-features.md) |
| 累积问题与反馈登记 | [问题清单](references/known-issue-checklist.md)、[通用问题范围](references/feedback-regressions.md)、[人工问题变机器检查](references/executable-regression-retention.md) |
| 工程与平台 | [真实Cocos运行](references/cocos-runtime.md)、[工程与平台职责](references/architecture-and-platform.md)、[首页快捷方式与主页回访](references/tiktok-home-growth.md) |
| 交付与试玩 | [交付与验证](references/delivery-and-handoff.md)、[固定手机尺寸试玩](references/user-phone-preview.md) |
| 计划、用量与省 Token | [制作计划](references/production-plan.md)、[生产统计](references/production-accounting.md)、[执行节流](references/execution-budget.md)、[执行检查点](references/execution-checkpoints.md)、[省Token](references/token-economy.md) |
| 多应用/多聊天协作 | [执行分工与交接](references/session-relay.md)、[本地多应用](references/local-agent-dispatch.md)、[自动新聊天](references/auto-art-stage-chat.md)、[可选Grok](references/optional-grok.md)、[不压垮电脑](references/machine-load.md) |
| 新项目运行器 | [项目QA注册](references/project-qa-registration.md)、[工作流工具](references/workflow-tools.md)、[本机适配](references/host-adaptation.md) |

## 六、共享脚本与模块

所有板块共用一个脚本库，放在本 Skill 的 `scripts/`（互相调用，不拆散）；各板块 Skill 的"工具"一节列出它用哪些。共享模块：`assets/modules/AdRewards.ts`（经济数值与广告去重，原样复制进游戏）、`assets/known-issues.json`（门禁目录）、`assets/ad-simulator.js`。激励广告、加桌面和回访只用平台包 `assets/platform-kit/`（`RewardedService.js`、`TikTokMissionService.js`）；`assets/rewarded-service-cocos24.js` 是历史快照，只作失败对照，不许复制进游戏。命令里的路径写 `<remake-core>/scripts/...`，按本次实际加载的 skills 目录解析。

一键预检、总门禁：`scripts/preflight.py`、`scripts/check_known_issues.py`、`scripts/design_check.py`、`scripts/art_check.py`、`scripts/logic_check.py`。

## 七、改规则的约定

- 一条规则只写在它所属的板块 Skill；其他地方只放链接。改规则时只改那一处。
- 新增一类问题时，先判断属于哪个板块，写进那个板块的参考，再在本页症状表加一行。
- 跨板块的规则（阶段、证据、交付）才写在本 Skill。

## 八、用中文点名就行

每个 Skill 的说明里都写了中文触发词，直接说中文即可，比如：

| 你可以这样说 | 会用到 |
|---|---|
| "用关卡skill把难度调一下" / "加关到100" | remake-levels |
| "用经济skill改礼盒" / "金币给太多了" | remake-economy |
| "皮肤价格不对" / "用皮肤skill" | remake-skins |
| "广告点两下发了两次奖" / "加难关提示" | remake-ads |
| "按钮太挤了" / "用美术skill重做首页" | remake-art |
| "教程看不懂" / "用引导skill" | remake-onboarding |
| "还有中文" / "英文不地道" | remake-copy |
| "没声音" / "音效太吵" | game-audio-library |
| "卡在加载" / "进不去" | cocos-game-check/startup |
| "英化这个游戏" / "用这个启动包重塑" / "评审这个游戏" | 三个流程入口 |

AI 给你的回复也默认用中文。

