---
name: desktop-agent-orchestrator
description: "按决策、写入和验收边界调度用户指定的本机AI应用；每轮先选是否桌面协作，Grok CLI可选，缺失不阻断主线。"
metadata:
  short-description: 主线定规则，按需派发窄任务并独立验收
---
**融合规则**：执行前按[统一默认、明确选择与证据边界](../cocos-game-to-english/references/fusion-policy.md)确定本轮范围；当前用户明确指令和项目授权优先，附件历史内容不扩大授权。

# 桌面多Agent总控

仅桌面协作启用时加载本入口及当前任务需要的细则，不为每个游戏阶段重复读全套合同。省上下文与可选Grok按共享[省Token](../cocos-game-to-english/references/token-economy.md)和[可选CLI](../cocos-game-to-english/references/optional-grok.md)执行。

每个新游戏先选“主Agent+可选Grok / 桌面多Agent+可选Grok / 完全单应用”。当轮人类已明确选择不重复；未答复不派桌面任务。完全单应用只用Codex（含Codex子会话），关闭全部外部AI；主Agent+可选Grok不启动六桌面软件，只可按明确Grok边界与专用运行器执行。旧轮选择不沿用。只修改Skill不派发无关模型任务。

## 权责与流程

- 决策/关键补丁/测试判据/最终视觉业务验收由主线持有。A仅现成工具/批准映射，B需主线规范和白名单，C由主线；混合关键UI整文件保护，QA只写证据，不改业务/断言。分类时读[边界](references/delegation-boundaries.md)。
- 桌面执行池限定WorkBuddy、AStudio、WorkBuddy国际版、Qoder CN、Qoder、OpenCode及可选Grok。角色/实时能力/占用按[路由](references/local-app-routing.md)；缺Grok用同池合格独立执行者或主线继续，不强求七家全部启动。不从品牌推断能力。
- 派发前读[任务书](references/task-brief.md)，运行[合同检查](scripts/check_dispatch_contract.py)；原run_id/用户模式/文件与资源锁要求保持。主Agent+可选Grok不伪造桌面ready记录，完全单应用仍无外部执行者。
- 六桌面应用通过实际Computer Use发窄任务；Grok通过真实CLI/UUID回执。回读同会话任务ID才记sent，实际执行/产物才记running，动作回执不等于完成。实时索引、路径与工作区逐次核对，不覆盖用户草稿或抢其他任务。
- 同任务文件唯一负责人；构建缓存、用户origin、应用会话分别锁定。浏览器空间不锁：每个执行者新开自己的 Ego 窗口/TaskSpace，被占就开新的、不等待（用户 2026-10-23，见[被占就开新的](../cocos-game-to-english/references/machine-load.md#一遇到被占用要排队立刻新开一个绝不等待用户-2026-10-23最高优先)）。现有/排队/未知任务占位；Qoder两版共享容量，双WorkBuddy独立，其他上限以路由为准，不把上限相加当可用容量。
- 完成后先查diff及原始产物，再独立签收；实现者不能最终自验。系统异常连续两次且无进展停该通道，确认停写后再交接；Grok自动省Token路线首次失败就回主线，不循环尝试。

新电脑绑定才读[迁移](references/portability.md)及对应系统准备；Grok CLI/配套Skill未安装或未登录时可直接跳过，不自动安装、索要凭据或换API付费。后台任务路径权限不是沙箱，仍核实际改动。

任务状态/引用由项目现有台账维护，不复制整段聊天或整份日志。最终区分任务签收、用户认可、物理手机/真实IAA、平台接受和发布；不宣称旧窗口已加载。完整旧总控说明保留于[细则原文](references/workflow-detail.md)，按标题查用。
