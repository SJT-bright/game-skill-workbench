# 与共享流程衔接

`cocos-game-to-english` 的 SKILL.md 只管英化；它的 references、scripts、assets 是两个板块共用的工具库。重塑从这里读取共享规则，但**顺序按本 Skill 的 SKILL.md：先玩法（占位图）→ 用户玩法通过 → 再做全部美术和声音**，不按英化的阶段表走。规则的适用范围见[两个板块](../../cocos-game-to-english/references/two-boards.md#五哪些规则共用哪些只属于一个板块)。

按本次安装版逐步加载 `cocos-game-to-english/references/` 里的必要参考，不复制流程后假称自动继承。记录目录、入口SHA、实际使用文件SHA及`assets/known-issues.json`当前revision，以实际读取为准。

安装位置不同则从技能注册路径/本机目录定位，并记录本项目依赖。盘点器支持`--base-skill /绝对路径/cocos-game-to-english`。找不到依赖时保留已授权独立创建成果并说明完整流水线缺失，不静默下载或降低验收。

| 原流程 | 启动包模式的映射 | 依赖 |
| --- | --- | --- |
| 选型/规格 | 主题未定才补提案，统一国际TikTok；已有PRD/规则复用，需求ID追到任务与证据 | [主题到规格](concept-to-spec.md)、[任务证据](../../cocos-game-to-english/references/production-plan.md) |
| 工程/性能 | 实际目录职责与平台边界，按本作设备/场景记基线；不强迁引擎或新增平台 | [工程职责](../../cocos-game-to-english/references/architecture-and-platform.md)、[性能迭代](../../cocos-game-to-english/references/performance-and-iteration.md) |
| 原工程/原版 | 原档是策划；无工程写不适用，新建Cocos并保留首个可玩基线 | [构建](../../cocos-game-to-english/references/cocos-runtime.md)、`scripts/audit_project.py` |
| 功能总表 | 开始建立，加入待创建模块；Web/反馈后/包前更新 | [流程门禁](../../cocos-game-to-english/references/process-gates.md) |
| 英文覆盖 | 创建时用英文：开工脚本扫一次判定源码语言，英文源码不做中文逐项审查（复用了中文代码/素材时按中文源码处理）；只核新图英文拼写与实际页面 | [英文/全UI](../../cocos-game-to-english/references/english-ui-rebuild.md)、`scripts/audit_english_coverage.py` |
| UI规范/样板 | 每款按主题定色板和按钮体系；内置image_gen先做代表样板并在真实Cocos自审选定，再以其作图像参考生成整套，主线自主推进 | [主题规范与样板](../../cocos-game-to-english/references/ui-style-and-samples.md) |
| 原创美术/声音 | 策划定本作主题，创建角色/场景/玩法素材/完整UI；无旧图不能只交文字按钮 | [美术](../../cocos-game-to-english/references/artwork-and-feedback.md)、[首页/声音](../../cocos-game-to-english/references/common-game-components.md) |
| 视觉自审 | 原件及Cocos显示/动画/条件状态，两比例修复复查 | [全量视觉](../../cocos-game-to-english/references/full-visual-review.md) |
| 教程/复活 | 依本作规则，真实首关/机制教学、继续与免费新局，不抄别款数值；今后制作、换皮遵循 [不提供广告跳关](../../cocos-game-to-english/references/first-level-onboarding.md#不提供广告跳关)，新输入原源码自带也一律清理入口及完整业务路径；不回改其他已结项成品，无关局部维护不扩改 | [教程](../../cocos-game-to-english/references/first-level-onboarding.md)、[复活/帮助](../../cocos-game-to-english/references/rewarded-revive-and-help-layout.md) |
| 多应用 | 主线定规则/断言/保护文件，独立实施/构建/QA按合同 | [本地分工](../../cocos-game-to-english/references/local-agent-dispatch.md) |
| 输入/试玩 | 真Web/Ego Lite/触摸链/普通入口，模拟与手机分开 | [包前检查](../../cocos-game-to-english/references/prepackage-mobile-review.md)、[输入门禁](../../cocos-game-to-english/references/mobile-input-gates.md)、`scripts/audit_mobile_input.py` |
| IAA/配置 | 已授权整组公开配置，不用Secret/默认不登录；普通Web预览不发奖；显式本地广告模拟走原奖励业务 | [Native/IAA](../../cocos-game-to-english/references/tiktok-native-iaa.md)、[配置/预览](../../cocos-game-to-english/references/local-review-and-test-ids.md)、[配置复用](../../cocos-game-to-english/references/ad-configuration-reuse.md) |
| 主页两能力 | 真SDK/资格/持久奖励及本作消费者 | [主页能力](../../cocos-game-to-english/references/tiktok-home-growth.md)、`scripts/audit_platform_markers.py` |
| 累积问题 | 原catalog固定ID/原checker，本作实际入口和证据 | [问题清单](../../cocos-game-to-english/references/known-issue-checklist.md)、`assets/known-issues.json`、`scripts/check_known_issues.py` |
| Native ZIP | 真Native导出、实际writer重跑本作回归和原门禁、独立解压/字节核对 | [交付](../../cocos-game-to-english/references/delivery-and-handoff.md)、`scripts/verify_native_zip.py` |

上表是索引，不替代原文；脚本参数使用前读`--help`。会变的平台包体/SDK要求在实际构建时核官方文档及工具版本，不把样例策划4MB/20MB或别款记录当平台当前保证。

用户说以后上传TikTok，默认做本地候选所需工程/公开配置接线/构建/核验，不等于现在登录、创建应用、上传、送审或发布。只修改Skill时不调用游戏制作/浏览器/平台流程，不改变已有游戏/服务/存档/包。

已授权测试候选继续原Skill允许的本地范围，真机/真实广告待验单列，不改catalog/移除检查/伪填通过/复制别款特批。创建规格、验收和求解记录留项目核验目录，不进Native。收尾区分游戏实际制作状态和Skill安装状态。
