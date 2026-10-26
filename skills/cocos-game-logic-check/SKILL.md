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
