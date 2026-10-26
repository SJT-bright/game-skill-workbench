# 一手来源与证据边界

类型：来源页集合，每条对应独立材料。检索：2026-09-22。原文通过链接保留，本页是摘要。阅读范围主要为论文摘要与相关官方工程正文，不声称对所有论文全文完成复现或系统综述。共保留 17 项核心来源；本轮重点增补 S7–S17。

## 路由背景：不能直接推出本地任务可降级

| 来源 | 一手材料与观察 | 对当前规则的作用与边界 |
|---|---|---|
| S1 | [Anthropic · Building effective agents，2024](https://www.anthropic.com/engineering/building-effective-agents)：介绍流程分解、任务路由与评估。 | 支持按任务分工；哪些工作可分配受本次用户更严格的授权约束。 |
| S2 | [RouteLLM，2024/2025](https://arxiv.org/abs/2406.18665)：用偏好数据学习模型路由、评估质量与成本。 | 本技能没有训练路由器；论文基准成绩不能代替本机 Grok 验收。 |
| S3 | [NVIDIA · Small Language Models are the Future of Agentic AI，2025](https://arxiv.org/abs/2506.02153)：立场论文讨论重复、专门任务与异构系统。 | 立场论证不等于“重复任务都不需要推理”，Grok 也不等于小模型。 |
| S4 | [FrugalGPT，2023](https://arxiv.org/abs/2305.05176)：研究提示适配、近似和模型级联的质量/费用取舍。 | 当前优先保留质量，不把收益数字或“先用低成本模型”作为强制策略。 |
| S5 | [Anthropic 多 Agent 研究系统，2025](https://www.anthropic.com/engineering/multi-agent-research-system)：明确子任务边界，讨论共享状态与协调成本。 | 不委派需要项目全局状态的工作；主 Agent 保留证据控制权。 |
| S6 | [Anthropic Contextual Retrieval，2024](https://www.anthropic.com/engineering/contextual-retrieval)：分块可能丢失实体、时间等上下文。 | 不盲目切段；本版不再把相关性筛选、片段摘要交给 Grok。 |

## 质量风险：本轮新增

| 来源 | 一手材料与观察 | 当前采取的工程规则 |
|---|---|---|
| S7 | [Lost in the Middle，2023/2024](https://arxiv.org/abs/2307.03172)：所测模型的长上下文检索受信息位置影响。 | 不因材料能装入上下文就认定完整；建立覆盖清单，避免整包长文盲目提取。不是所有新模型的统一错误率。 |
| S8 | [RULER，2024](https://arxiv.org/abs/2404.06654)：简单单针检索不能代表多目标、聚合与多跳任务能力。 | 成功读到一条不代表能读全；单次简单样例不扩大权限。 |
| S9 | [FRANK，NAACL 2021](https://arxiv.org/abs/2104.13346)：摘要可能流畅但事实不可靠，研究错误类型与评估指标。 | 摘要/归纳由主 Agent 完成；历史模型结果用于识别风险，不用于当前 Grok 排名。 |
| S10 | [FIB，ACL Findings 2023](https://aclanthology.org/2023.findings-acl.322/)：评测模型对事实一致摘要的偏好，文本中出现干扰摘要会影响判断。 | 出现过的句子未必是正确结论；原文子串验证不能替代事实关系核验。 |
| S11 | [OCRBench v2，2024/2025](https://arxiv.org/abs/2501.00321)：评测定位、手写、布局、复杂解析和推理等多种 OCR 场景。 | 只把清晰、局部印刷文字列为候选；复杂表格、手写和推理排除。历史分数不迁移到现用模型。 |
| S12 | [OmniDocBench，CVPR 2025](https://arxiv.org/abs/2412.07626)：文档提取涉及不同版式、文本、表格、公式等模块，表现依材料而变。 | 先找源文字层/专用解析器，避免把完整复杂文档解析等同于抄字。 |
| S13 | [ChartQA，ACL Findings 2022](https://aclanthology.org/2022.findings-acl.177/)：图表问答涉及视觉与逻辑推理。 | 读出标签和解释趋势是两种工作；后者不委派。 |
| S14 | [Large Language Models Cannot Self-Correct Reasoning Yet，ICLR 2024](https://arxiv.org/abs/2310.01798)：研究没有外部反馈的内在自纠错，所测推理任务未稳定改善。 | “再检查一遍”不能作独立验收；不声称现代所有模型均无法自纠错。 |
| S15 | [LLMs Get Lost In Multi-Turn Conversation，2025](https://arxiv.org/abs/2505.06120)：模拟实验中逐步给出信息可能引发早期假设与不可靠性。 | 给搬取步骤完整、局部且清晰的输入；任务解释与共享状态留主 Agent。 |
| S16 | [Reasoning about Uncertainty，2025](https://arxiv.org/abs/2506.18183)：研究推理模型自报置信度与校准，存在过度自信和模型差异。 | 不用自报置信度阈值批准输出，也不因其表达肯定就缩小核验。 |
| S17 | [Generalizing Verifiable Instruction Following / IFBench，NeurIPS 2025](https://arxiv.org/abs/2507.02833)；[Ai2 官方说明，2026-05-11](https://allenai.org/blog/ifbench-artificial-analysis)：即使约束可检查，模型仍可能违反格式/数量等要求。 | 程序检查条目、字段和逐字证据；JSON 合法不能代表任务内容正确。 |

以上材料支持“需要辨别任务难度与验证方法”，不能单独证明本地 Grok 会或不会完成某任务。本版更窄白名单直接来自用户的质量优先要求，具体路由属于本地工程策略。

## 本地证据与历史替代关系

- 早期文本调用（旧机历史验证回执未随包迁移）：仅证明该次调用及提取样例。
- 旧分类批次（旧机历史验证回执未随包迁移）：历史样例，已被当前授权收紧，不再用于证明分类可自动委派。
- 当前最窄范围、检查方法与实例见 [质量边界调研](quality-boundaries.md) 和 [矩阵](task-matrix.md)。

当前收紧版验证：6 条记录、24 个字段的逐项核对（旧机历史验证回执未随包迁移），以及 8 类错误拦截检查（旧机历史验证回执未随包迁移）。这是合成协议样例，不是所有场景能力认证；未再次进行图片 OCR 实测。
