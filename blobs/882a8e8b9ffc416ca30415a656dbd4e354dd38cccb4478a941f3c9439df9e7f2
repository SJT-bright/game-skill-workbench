# Cocos逻辑检查与修复（测试与修复）

修订：`2026-10-27.modules-v6`。收尾层：玩法做完后的功能验收和代码 bug 修复。发现的问题属于哪个板块，就按那个板块 Skill 的规则修（症状表见 [remake-core](../../remake-core/SKILL.md)）；本 Skill 管检查范围、证据和回归。

先按当前候选、授权改动、现有证据和历史故障确定范围。已批准成品维护不自动升级全量制作验收。按[当前合同](../../remake-core/references/current-contracts.md)读取实际症状，先修阻断再继续受影响链。

| 检查对象 | 参考 |
|---|---|
| 操作、胜败、重开、取消、多指与暂停 | [重开与输入](references/replay-and-input-checks.md)、[移动输入](references/mobile-input-gates.md) |
| 关卡覆盖与共用矩阵去重 | [执行计划](references/review-execution-plan.md)；`plan_level_tests.py`按完整基线或changed范围生成清单 |
| 奖励、广告效果、道具消费者、晚回调 | [已知逻辑回归](references/learned-regressions.md)、[实际模块](../../remake-core/references/game-modules.md) |
| 启动、Retry新请求与恢复 | [启动合同](../startup/references/startup-contract.md)、[加载恢复](../startup/references/loading-recovery-regression.md) |
| 原生存储、坏档、重复奖励、写失败 | [Native存储](../startup/references/native-reward-storage-and-empty-features.md)、[执行检查点](../../remake-core/references/execution-checkpoints.md) |
| 拖动和声音 | [实际交互后置条件](../package-check/references/drag-audio-postconditions.md) |

先便宜数据/依赖/体积核对和一次关键真实操作，再进入适用故障矩阵。抽中关卡验证该关规则与正常完成；共用广告/存档/Retry不在每关重复。第二比例查布局、触摸和视口相关风险，不重复全部通关清单。只有依赖不明、基础机制广泛变化、多个独立机制失败或明确完整验收要求时扩大范围，并记录原因。

测试执行者可以在授权范围修代码bug并自己定点重测；设计变化依当前合同处理，需要新图交有权生图的执行者。相同一轮截图/dump/操作可支持多个实际断言，保留原始证据和准确执行身份，不能靠手填pass或旧报告哈希续用。

收到反馈立即登记固定问题历史与实际生产依赖。按[可执行问题门禁](../package-check/references/resource-and-reported-issues.md)保存故障、修复与正常对照；缺复验或失效不得出包，相关文件未变只核证据不重跑运行器。结束无用QA页面/服务，给用户准确结果；未授权不打包。

## 更多正文（本板块）

[页面就绪与取消重进](references/page-readiness-and-cancel.md)、[按钮状态核对](references/button-state-check.md)、[手机连续状态与帧率](references/mobile-motion-state-review.md)、[打包前Ego检查](references/prepackage-mobile-review.md)、[检查范围与停止条件](references/testing-scope-and-stop.md)。
