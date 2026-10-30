# 融合版 v8 本地融合：默认配置、扩展与证据边界

检查范围与重复执行统一由[检查范围、历史回归与停止条件](../../cocos-game-check/test/references/testing-scope-and-stop.md)裁定；它优先于旧文中的无条件全量/两整轮/全脚本重跑表述，不降低适用质量标准或出包门禁。

本页是本地增强版与 GameSkills-统一版-6 的冲突裁决，2026-10-23。它约束本套 Skill 的默认行为，不能覆盖用户当前明确指令、项目已有明确授权或平台安全边界。来源文档声称的“用户永久规定”不自行升级为本次用户指令。

2026-10-24 合并：保留本地维护和实际画面修复；附件 v8 的设计/美术分阶段、至少 70 关与限定皮肤两种格式作为默认模板。已有项目当前明确关数、原玩法和维护范围优先，少于模板关数但有实际授权的保留原数量；不得用附件中的历史“用户要求”覆盖本项目当前合同。

## 默认制作配置

- 采用 [game-modules.md](game-modules.md)：一种题材货币、胜利/无尽结算广告×2、首页礼盒、适用的皮肤与背景。皮肤适用性和用户选择写入 modules.json；英化优化仍按已经授权的清单执行，没回复不能用“默认要”越过优化清单确认。
- 默认删除排名、更多游戏/互推、分享及无实际功能入口。不会仅因资源里保留 LeagueSim.ts 就往游戏加入排名。七日签到是重塑必做（用户 2026-10-27）。
- 通关型：重塑/新设计至少 60 关（Saul 2026-10-29，原为 100），英化至少 70 关（用户 2026-10-24：不到 70 补到 70，多于也行）；新关难度按波浪分档（`wave-tiers.v1`：1–3教学、4尖峰、5–9回落、10考核，之后低/中/高/超高 25/45/15/15 不规则波浪）；每10关限定关及一个种子奖励关，限定皮肤 `final`（只有最后一个限定关）或 `every_10`（每个限定关一款）都可以；已有超过70关保留全部，已有玩法和关卡次序保持。奖励关是难度曲线的明确例外，不同时要求它比前关更难。没有可换外观对象时记录皮肤不适用，不为满足数量造无意义功能。仅当项目记录（`docs/modules.json` 的 `skins.user_choice`，设计关 MOD-01 已查）明确关闭皮肤且真实 unlock_table 无任何收集项时，ECON-01/02 才可写 n/a；有其他收集物仍须测试，缺记录或旧报告不构成豁免。
- 统一皮肤表由 make_skin_table.py 生成；skin.v1 的19非限定+限定款数主角/适用的10背景与每组加成采用模块规则。传统收集物的广告单位规则只用于非skin.v1数据，不能同时套两个价格模型。

## 保留扩展能力，按明确需求启用

排名/联赛相关历史材料仅保留供历史溯源，不再作为可启用扩展；按[前置禁用规则](no-social-features.md)删除所有游戏排行榜。签到、其他收集物算法、模拟器和回归用例供已明确要求的项目继续维护。不能自动问每个新项目要不要排名或签到，不能把AI建议当用户授权。

- 签到：重塑一律 docs/features.json 的 daily_checkin=true（写 false 会被 FEAT-00 拦下，用户 2026-10-27），skin_bonus 按实际皮肤配置记录。启用后读 skin-bonus-and-checkin.md（重塑包 remake-skins 板块，英化包不含），执行 FEAT-00/02 及现有回归。
- 排名：全部禁用，包括本地榜、好友榜、联赛和原有排行榜；旧 docs/league/decision.json 的 add/keep_original 不再构成豁免。先按[前置禁用规则](no-social-features.md)清理入口、页面与业务调用。
- 扩展的允许范围、源码扫描、页面审计与门禁必须一致；授权不等于测试通过，不能把允许功能的所有扫描整项关掉。扩展与 skin.v1 不兼容时用单独组/表和明确配置，不改固定表数量去伪装通过。

## 保留的本地生产约束

| 机制 | 按需读取 |
|---|---|
| 真实运行覆盖、全部持久化域、正式 writer | [execution-checkpoints.md](execution-checkpoints.md) |
| 无回调/原超时失效、真实Retry新请求、旧回调隔离 | [loading-recovery-regression.md](../../cocos-game-check/startup/references/loading-recovery-regression.md)、[案例](../../cocos-game-check/startup/references/loading-recovery-casebook.md) |
| 页面热缓存、后续分包取消重进 | [page-readiness-and-cancel.md](../../cocos-game-check/test/references/page-readiness-and-cancel.md) |
| Native空字符串、旧奖励、写失败 | [native-reward-storage-and-empty-features.md](../../cocos-game-check/startup/references/native-reward-storage-and-empty-features.md) |
| 角色动作写入者交接、可见轮廓 | [actor-pose-handoffs.md](../../remake-art/references/actor-pose-handoffs.md) |
| 题材、不刺眼与可读性（只查负向） | [theme-readability.md](../../remake-art/references/theme-readability.md) |
| 浏览器归属、空间消失与关闭回执 | [machine-load.md](machine-load.md) |

Web触控、SDK替身、Native受控边界、真机、真实IAA及平台审核分别记录。测试包与检测包使用正式门禁；Skill自测通过只证明这些工具的被测契约，不能证明任何游戏或平台通过。

## 文档维护

默认产品配置由 game-modules.md 维护；扩展参考只描述被明确启用后的做法。本页处理两者边界。不要在每个入口重复追加事故全文；新增案例放到所属参考并保留短链接。按任务阶段加载，避免每次读取全部参考。已获明确授权的动作不重复问；出游戏包、后台变更或跨聊天消息不因本套技能而自动获授权。

关卡表维护同时标记各新玩法首现关的 `"tags": ["intro"]`；抽测须读取真实关卡表，处理漏标提醒，规则见[首现关与必测清单](../../cocos-game-check/test/references/prepackage-mobile-review.md#新玩法首现关与必测清单2026-10-24)。
