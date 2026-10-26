# 方法来源与融合范围

2026-10-17，按用户要求将xskills的cocos-mini-game中可复用方法蒸馏进现有两个Skill；目标统一为国际TikTok，不安装/调用第三个制作Skill。各入口沿用原依赖关系：已有完整源码的维护无需加载创建Skill；创建阶段继续依赖本Skill。来源网址与原件不属于执行依赖。

来源：[xiongxianzhu/xskills](https://github.com/xiongxianzhu/xskills/tree/58e46cc51b40a360973e2c67466b6a8be727c5b4/skills/cocos-mini-game)，提交 `58e46cc51b40a360973e2c67466b6a8be727c5b4`，MIT许可。原作者版权及许可全文见[MIT许可](licenses/xskills-MIT.txt)。重写后的规则、示例与模板服从本机现行游戏流程和用户授权。

| 原方法 | 本地承载 |
| --- | --- |
| 趋势/玩法提案、PRD、范围与技术选型 | 创建Skill的[主题到规格](../../cocos-game-from-starter/references/concept-to-spec.md)、[规格模板](../../cocos-game-from-starter/assets/creation-spec-template.md) |
| 进度/任务、精确路径、依赖与验证回写、按需资产规格 | [任务与证据](production-plan.md)、[任务模板](../assets/production-task-template.md) |
| 工程目录职责、平台接口、生命周期与后端按需 | [工程与平台职责](architecture-and-platform.md)，技术范围写入既有规格与任务 |
| 性能维度、弱网/资源与可测产品指标 | [性能与迭代](performance-and-iteration.md) |

没有采纳国内微信/抖音实现、默认双端、固定3.8+2D、全项目只准一个任务进行中、音频只交提示词或自动增加后端。国际TikTokSDK与公开配置、原玩法/关卡、严格账本/消费者、原免费流程、全UI生图/声音、触屏、60稳定ID及产包门禁继续原规则。新内容是方法融合，不证明任何游戏或平台验收已完成。
