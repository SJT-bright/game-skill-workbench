---
name: cocos-game-from-starter
description: "接收游戏设计启动包、主题或策划，制作真实Cocos小游戏；先验证和导入设计数据，玩法确认后制作美术与声音。"
---

# 从设计启动包制作Cocos游戏

输入为START_HERE、GAME_DESIGN、UI_PAGES、ECONOMY和关卡数据等设计资料；附源码仍走本流程，只有中文源码转[英化](../cocos-game-to-english/SKILL.md)。用户原始文件只读保留。这里的设计启动包不指首屏下载负载。

按[当前共同合同](../cocos-game-to-english/references/current-contracts.md)选阶段，默认当前应用执行。分享、全部排行榜和广告跳关不作为可选玩法；局部维护遵循当前授权，不补模板系统。

| 阶段 | 行动与正文 |
|---|---|
| 接收与验证 | 先安全盘点，再运行 `scripts/validate_starter.py --input <目录或ZIP> --out <新报告.json>`；[完整规范](references/starter-pack-spec.md)、[读取与归属](references/starter-intake.md)、[最小示例](examples/minimal-starter/START_HERE.md) |
| Workshop v3 | 含workshop.json先按[工坊接收](references/workshop-handoff.md)，保留已接受的关序、seed、布局和BRIDGE数据；不套普通设计包重新生成 |
| 写项目规格 | [主题到规格](references/concept-to-spec.md)、[规格模板](assets/creation-spec-template.md)；设计表与实际布局、解法和依赖对齐，按原ID导入已验收表，不接收后重新抽奖励关 |
| 先做玩法 | [创建与工程](references/creation-gates.md)、[真实Cocos](../cocos-game-to-english/references/cocos-runtime.md)、[启动合同](../cocos-game-to-english/references/startup-contract.md)；最终尺寸占位图，无正式生图，短检启动/真实输入/基础结算存档后给用户玩法试玩 |
| 玩法通过后美术 | [UI样板](../cocos-game-to-english/references/ui-style-and-samples.md)、[全部适用美术](../cocos-game-to-english/references/art-before-trial.md)、[音频](../game-audio-library/SKILL.md)；沿用已确认玩法，不重复设计 |
| 稳定候选功能验收 | [范围与去重](../cocos-game-to-english/references/review-execution-plan.md)、[逻辑检查](../cocos-game-logic-check/SKILL.md)；关卡抽样，故障矩阵按实际机制执行，不乘到每关 |
| 试玩与交付 | [手机预览](../cocos-game-to-english/references/user-phone-preview.md)；已授权包进入[统一打包入口](../cocos-game-tiktok-package/SKILL.md)，不自动平台上传 |

普通包数量和奖励的单一合同由 `product_contract.py`、两份生成器和 `validate_starter.py`共同使用。限定关仅10的倍数；尾章不加限定。每关货币按已存reward_seed生成、重试不重抽；规则说明及字段完整见规范。求解器结果须在真实规则独立重放，校验器不替代玩法验收。

反馈写项目固定问题历史；未复验不出包，仅复测相关依赖。运行器、专款适配与账号配置留项目，按[项目QA登记](../cocos-game-to-english/references/project-qa-registration.md)，不改共享Skill。\n\n完工复盘需要更新共享规范时，按[完工知识整理、去重与通用化](../cocos-game-to-english/references/knowledge-consolidation.md)执行，先去重、替换和删除过时规则。\n
**统一手机触摸测试（用户 2026-10-27）**：玩法设计后的首个可玩确认及后续输入验收统一使用 Google Chrome DevTools/CDP 触摸模式：`chrome_touch.py --user-approved-chrome --channel chrome`，固定移动 viewport/DPR/UA/has_touch，记录 `playwright_cdp_touch` 和真实业务结果；鼠标只作辅助排错。见[Google Chrome 移动触摸运行模式](../cocos-game-to-english/references/google-touch-runtime.md)。

**玩法确认前的 Chrome 触摸预检（用户 2026-10-27）**：首个可玩候选交用户前，先用独立 Google Chrome iPhone CDP 触摸完成矩阵；Codex 内置浏览器只用于查看，不作为测试器。

**输出必须标明 Chrome 测试层（用户 2026-10-27）**：凡输出“测试通过”“手机触摸通过”“按钮已验证”或交付预览，必须注明 `Google Chrome iPhone touch`、设备尺寸/DPR、`input_transport=playwright_cdp_touch` 和业务结果。只在 Codex 内置浏览器查看或点击，必须写“仅查看，未作为手机触摸测试”，不得写成测试通过。
