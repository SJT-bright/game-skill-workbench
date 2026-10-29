---
name: cocos-game-check
description: "统一检查（触发词：检查、测试、验收、找bug、修bug、启动、进不去、白屏、卡加载、按钮没反应、音量、出包、打包、ZIP、检查包、包太大、评审）。所有Cocos小游戏共用的检查Skill：英化游戏和重塑游戏都用同一份。启动与稳定、功能测试与修复、出包、最终包检查、评审（只检测不修改）、美术检查，以及全部检查脚本。"
---

# 统一检查（英化与重塑共用）

修订：`2026-10-28.check-unified.4`。英化包和重塑包内这个 Skill 字节相同。检查规则以重塑包 v7.1 的检查板块为准（`startup/`、`test/`、`package/`、`package-check/`），评审沿用原评审入口（`review/`）。检查脚本与规则库用同包的共享库 [remake-core](../remake-core/SKILL.md)，美术检查用同包的 [remake-art](../remake-art/SKILL.md)；本 Skill 不再自带它们的副本（v7.3.2 去重）。

## 先定是哪一类游戏

| 类型 | 判断 | 适用 |
|---|---|---|
| 英化 | 拿到的是能运行的中文完整游戏，只改中文美工/文字，加少量固定入口 | 下表“英化”列；不查关数、经济数值、皮肤、签到、教程等重塑专属项 |
| 重塑 | 用启动包做的新游戏 | 全部检查 |

工程里写 `docs/board.txt`（`localize` 或 `remake`）；没写时按 [两个制作入口](../remake-core/references/two-boards.md) 判断。

## 三道关：哪一关在什么时候跑（用户 2026-10-28）

本 Skill 把所有检查放在一处，但**不是做完游戏才一次查完**。按制作阶段分三道关，前一关通过才进下一阶段，后面的关不重复前面已经查过的内容（详见 [检查分阶段](../remake-core/references/check-stages.md)）：

| 关 | 什么时候跑 | 查什么 | 不查什么 |
|---|---|---|---|
| 1. 设计关 | 玩法（占位图）做完、交用户确认玩法之前 | 玩法、关卡、经济、皮肤、模块，以及所有广告节点的位置与流程（复活、结算×2、局内道具/增益、礼包、看广告解锁）；`remake-core/scripts/design_check.py` | 美术 |
| 2. 美术关 | 美术做完、交用户试玩之前；之后改图只复查受影响的整页 | 画面、按钮、图片字、穿模、暗区、清晰度；`remake-core/scripts/art_check.py`、[art](../remake-art/SKILL.md) | 设计数值 |
| 3. 最终总检测 | 用户确认玩法和美术、锁定之后，出包之前 | 只查功能：能进、不卡加载、按钮有反应（含 TikTok 触摸坐标探针）、广告完成/取消/失败、存档、包体；`remake-core/scripts/check_known_issues.py`、`preflight.py`、`logic_check.py`，再出包与最终包检查 | **不再查美术和设计**，也不重评审美 |

用户试玩确认后美术锁定；出包前如需改美术，只按受影响页面复查美术关，不重跑整套。英化没有设计关（不改玩法），美术关只查改过的页面。

## 检查项与入口

| 检查 | 英化 | 重塑 | 入口 |
|---|---|---|---|
| 启动与稳定：进得去、加载页、Retry、存档 | 必查 | 必查 | [startup](startup/README.md) |
| 功能测试与修复：按钮、输入、胜负、重开、异步广告 | 必查 | 必查 | [test](test/README.md) |
| 无中文残留、英文文案 | 必查 | 必查 | `remake-core/scripts/audit_english_coverage.py`、`audit_copy_quality.py` |
| 位图字只用于数字和符号；句子用真字体；字母大小写不串（禁止 HelP/TaP 这类） | 必查 | 必查 | `remake-core/scripts/audit_bitmap_letter_fonts.py`（美术关 `art_check.py` 已接入） |
| TikTok 触摸坐标：Cocos 2.x 包装好平台包 `touch-coordinates.js`，只给 screenX/screenY 也能点（浏览器模拟测不出） | 必查 | 必查 | `remake-core/scripts/audit_upload_startup.py`（触摸坐标探针）、平台包 `remake-core/assets/platform-kit/build-templates/bytedance/` |
| 设置里音效/BGM 两个音量分开可调且保存 | 必查 | 必查 | `package-check/scripts/audit_sound_settings.py` |
| 删除分享、更多游戏、排行榜 | 必查 | 必查 | `remake-core/scripts/audit_no_social_features.py`、[前置规则](../remake-core/references/no-social-features.md) |
| 个人主页回访、添加桌面入口 | 必查 | 必查 | `remake-core/scripts/audit_platform_markers.py` |
| 结算页 Watch Ad x2 与 Retry；广告取消/失败不发奖、只用激励视频、无广告跳关 | 必查 | 必查 | `remake-core/scripts/audit_ad_binding.py`、`audit_no_ad_skip.py`、`audit_no_ad_simulator.py` |
| 美术检查（穿模、暗区、按钮覆盖、图片清晰度） | 只查改过的页面 | 必查 | [art](../remake-art/SKILL.md)、`remake-core/scripts/art_check.py` |
| 关卡、经济、皮肤、签到、教程、模块 | 不查 | 必查 | `remake-core/scripts/audit_level_plan.py`、`audit_game_modules.py`、`audit_acquisition_progression.py` 等 |
| 出包与最终包检查 | 必查 | 必查 | [package](package/README.md)、[package-check](package-check/README.md) |
| 评审别人的游戏（只检测不修改） | 可用 | 可用 | [review](review/README.md) |

引擎：重塑固定 Cocos Creator 2.4.15 与平台包；英化保持原游戏的引擎版本，平台包相关项只在原版为 2.4.15 时适用。

## 规则

- **TikTok 与 Cocos 的触摸差别（用户 2026-10-28，最严重的一类“点不动”）**：Cocos Creator 2.4 的触摸转换（`getTouchesByEvent`）读触点的 `clientX/clientY`，TikTok 运行环境给的触点只有 `screenX/screenY`，算出的坐标是无效值，扫码后按钮点不动、常卡在首页。浏览器手机模拟会给 `clientX`，**测不出这个问题**。所以每个 Cocos 2.x 的 TikTok 包都必须：用平台包 `build-templates/bytedance/` 原样的 `main.js` 与 `touch-coordinates.js`（不要自写 patch_build 替代），并通过 `remake-core/scripts/audit_upload_startup.py` 里的触摸坐标探针（`probe_cocos2_touch_coordinates.cjs`，对打包产物真实执行，只给 screenX/screenY 也要得到有效坐标）。探针不过不出包。

- 本 Skill 只检查和修检查出的 bug；美术、玩法、经济的设计改动交给对应制作 Skill，英化美工只在用户点名时才做。
- 结果写在工程 `docs/`；失败如实保留，不改阈值、不改检查器替游戏过检。
- 共用功能（广告、存档、Retry）只测一次，不乘到每关。
- 浏览器与触屏测试用同包的 `chrome-mobile-testing`、`mobile-touch-computer-use`、`ego-browser`。
