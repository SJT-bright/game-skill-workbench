---
name: cocos-game-logic-check
description: "检查和修复Cocos游戏玩法、按钮、异步广告、奖励、存档、加载与输入；按改动关联确定回归范围。"
---

# Cocos逻辑检查与修复

先按当前候选、授权改动、现有证据和历史故障确定范围。已批准成品维护不自动升级全量制作验收。按[当前合同](../cocos-game-to-english/references/current-contracts.md)读取实际症状，先修阻断再继续受影响链。

| 检查对象 | 参考 |
|---|---|
| 操作、胜败、重开、取消、多指与暂停 | [重开与输入](../cocos-game-to-english/references/replay-and-input-checks.md)、[移动输入](../cocos-game-to-english/references/mobile-input-gates.md) |
| 关卡覆盖与共用矩阵去重 | [执行计划](../cocos-game-to-english/references/review-execution-plan.md)；`plan_level_tests.py`按完整基线或changed范围生成清单 |
| 奖励、广告效果、道具消费者、晚回调 | [已知逻辑回归](references/learned-regressions.md)、[实际模块](../cocos-game-to-english/references/game-modules.md) |
| 启动、Retry新请求与恢复 | [启动合同](../cocos-game-to-english/references/startup-contract.md)、[加载恢复](../cocos-game-to-english/references/loading-recovery-regression.md) |
| 原生存储、坏档、重复奖励、写失败 | [Native存储](../cocos-game-to-english/references/native-reward-storage-and-empty-features.md)、[执行检查点](../cocos-game-to-english/references/execution-checkpoints.md) |
| 拖动和声音 | [实际交互后置条件](../cocos-tiktok-package-check/references/drag-audio-postconditions.md) |

先便宜数据/依赖/体积核对和一次关键真实操作，再进入适用故障矩阵。抽中关卡验证该关规则与正常完成；共用广告/存档/Retry不在每关重复。第二比例查布局、触摸和视口相关风险，不重复全部通关清单。只有依赖不明、基础机制广泛变化、多个独立机制失败或明确完整验收要求时扩大范围，并记录原因。

测试执行者可以在授权范围修代码bug并自己定点重测；设计变化依当前合同处理，需要新图交有权生图的执行者。相同一轮截图/dump/操作可支持多个实际断言，保留原始证据和准确执行身份，不能靠手填pass或旧报告哈希续用。

收到反馈立即登记固定问题历史与实际生产依赖。按[可执行问题门禁](../cocos-tiktok-package-check/references/resource-and-reported-issues.md)保存故障、修复与正常对照；缺复验或失效不得出包，相关文件未变只核证据不重跑运行器。结束无用QA页面/服务，给用户准确结果；未授权不打包。

已有游戏适配后若反馈跳跃、移动或落地手感改变，按[帧率与原版运动对照](../cocos-game-to-english/references/mobile-motion-state-review.md)先核实际时间步与轨迹，再决定修复；不要直接改原版物理数值。试玩点不动时同时按[电脑试玩输入](../cocos-game-to-english/references/user-phone-preview.md)区分鼠标桥接、真实触摸和业务按钮故障。

## 激励广告入口与点击失效

广告必须由玩家主动点击触发、且失败页仍可免费退出的完整规则只维护在 [Cocos 游戏广告设计](../cocos-game-ad-design/SKILL.md#激励广告必须由玩家主动点击触发2026-10-27)。本 Skill 只负责按本轮实际入口路由到该规范和问题账本，不复制广告触发与回调正文。

## 通用规范与完工整理

适用性与故障修复按[通用问题规范](../cocos-game-to-english/references/feedback-regressions.md)；完工沉淀按[去重维护](../cocos-game-to-english/references/knowledge-consolidation.md)，入口只引用主规范。

## 点击闪烁的跨游戏回归

点击过渡中的空帧、旧图叠加、字体回退和尺寸跳变统一按 [按钮状态轻量核对](../cocos-game-to-english/references/button-state-check.md#click-transition-flash-regression-cross-game-rule-2026-10-27) 执行；这里不复制第二套帧证据协议。


## Native 广告前置存储合同（2026-10-27）

任何新增、修改或排查激励广告时，必须把“点击广告前的 Native 存储读取”作为广告链的一部分。浏览器模拟广告通过不代表 Native 通过；测试执行者必须在实际 Native 宿主或同等可信 adapter 边界注入存储返回形状：缺省 `null`、空字符串、字符串/数字 `0/1`、桥接 `false/true`、损坏对象/数组、坏字符串、负数和越界值。依据实际平台契约及键语义处理 Boolean 和缺省值；无法区分读取失败与缺键时不得假定成功。损坏值继续拒绝并可重试，不能静默发奖。

每个广告入口按同一合同验证：真实按钮触摸→库存/奖励读取→pending 恢复→SDK create/show→close/error/timeout→奖励写入→读回→原消费者可使用。必须保留旧故障、修复版和正常对照，并记录广告是否实际进入 SDK；若在 SDK 前失败，不能把它写成“广告无填充”。没有 `storage_boolean` Native 原始证据时，广告测试不完整。

实现者负责接入公共存储归一化入口；测试者负责执行 `storage_boolean` 及损坏值矩阵；出包者负责检查合同回执和当前 Native 字节。三者任何一个缺失都不能把广告入口标为通过。



**2026-10-27 审查纠偏**：先依据目标平台存储 API 的实际契约和键的业务语义区分缺失、合法 Boolean、读取失败与损坏值；不能跨游戏一律把 `false` 当缺失、`true` 当 1。测试注入须说明替身位置并通过真实用户入口验证业务结果；本地替身和日志不证明平台真机行为。逐形状留可复核断言，缺失旧版反例、完整广告链或平台证据时分别标未验证。

受影响输入的执行器、预检和结果字段统一按[Chrome 触摸运行合同](../cocos-game-to-english/references/google-touch-runtime.md)与[触摸预检矩阵](../cocos-game-to-english/references/chrome-touch-preflight-matrix.md)执行。

**真实广告不是本地交付门槛（用户2026-10-27）**：电脑本地不要求真实 TikTok 广告填充或播放；用独立SDK边界模拟验证实际触摸、奖励与恢复，不得因缺少真实广告而停工、拒包或等待用户。适用检查通过即完成授权交付，日常不重复免责声明。统一规则见[电脑本地广告验收边界](../cocos-game-to-english/references/tiktok-device-stage.md#电脑本地广告验收边界用户2026-10-27明确)。
