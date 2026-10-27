# 当前共同约束与按需读取

修订：2026-10-27.economy-v4。用户当前要求和项目权威合同优先；模板默认值不改写已批准维护范围。规则正文在所属参考，本页只指定读入条件。每个实际问题登记项目历史并绑定原始反馈，不把一次事故自动扩成每个任务的全量检查。

| 当前工作/症状 | 需要读取的正文 |
|---|---|
| 新制作的默认模块、货币、皮肤、广告 | [融合边界](fusion-policy.md)、[模块](game-modules.md)、[关卡与顶部栏](top-bar-and-level-map.md) |
| 新制作/处理原有入口 | [分享与全部排行榜禁用](no-social-features.md)、[禁止广告跳关与教程](first-level-onboarding.md) |
| 设计确认前、玩法确认后、功能验收与增量维护 | [阶段与执行范围](review-execution-plan.md)、[停止条件](testing-scope-and-stop.md) |
| 美术制作或受影响页面 | [美术前移与锁定](art-before-trial.md)、[UI规范与样板](ui-style-and-samples.md)、[图片字与布局](page-richness.md)、[按钮分区](mobile-button-size-and-home-layout.md) |
| 遮字、灰格、列表首尾、关闭/返回压装饰 | [集合预览](../../cocos-game-art-redo/references/collection-preview-review.md)、[字底与字形](../../cocos-game-art-redo/references/text-backplate-review.md)、[局部UI契约](local-ui-contract.md) |
| 所有开发者控制的加载页 | [官方默认加载与重试样式](cocos-loading-screen.md) |
| 启动/加载失败、首页全按钮无响应、卡Loading | [启动真实业务判据](loading-scene-false-positive.md)、[启动合同](startup-contract.md)、[最终Native门禁](final-package-startup-gate.md)、[故障恢复](loading-recovery-regression.md) |
| 分包/场景路径、WebP、资源映射、构建Missing class | [场景路径](native-startup-path-casebook.md)、[最终包合同](../../cocos-tiktok-package-check/references/check-contract.md)、[资源/反馈拒包](../../cocos-tiktok-package-check/references/resource-and-reported-issues.md) |
| 广告效果/道具/奖励、存档异常 | [已知逻辑回归](../../cocos-game-logic-check/references/learned-regressions.md)、[Native存储](native-reward-storage-and-empty-features.md)、[检查点](execution-checkpoints.md) |
| 拖动落点、取消、实际声音 | [交互音频后置条件](../../cocos-tiktok-package-check/references/drag-audio-postconditions.md)、[输入与重开](replay-and-input-checks.md) |
| 角色方向/不可见轮廓、动画交接 | [角色写入者交接](actor-pose-handoffs.md) |
| 给用户试玩、浏览器身份/空间消失、结束测试 | [固定手机预览](user-phone-preview.md)、[资源与归属收尾](machine-load.md)；用户试玩由本地预览交接，Ego用于AI测试 |
| 多应用/多聊天协作且本轮有授权 | [执行分工](session-relay.md)、[可选委派](local-agent-dispatch.md)、[桌面工具](../../desktop-agent-orchestrator/SKILL.md) |
| 共享脚本需要新项目运行器/定点适配 | [项目QA注册](project-qa-registration.md) |

默认由当前执行者在当前应用继续；不每次询问是否多Agent。用户明确指定协作时才按对应环境和授权建立/续接。测试执行者可修授权范围内的代码bug并定点重测；需新图交有权生图的执行者，签收保持实际身份。总控可运行必要的只读检查、协调与验收命令，不将核心判断外包。

保留原始输入、历史交付、用户存档和其他聊天工作区。结束本次不用的测试页/服务并读回退出；保护仍供用户试玩的预览。执行结果按来源/静态、浏览器、Native候选、设备、真实广告、平台分别记录；不把本地通过写成已上传/发布。

## 同期规则的唯一归属

| 条件 | 正文与动作 |
|---|---|
| 玩家可见设置/制作说明 | [设置与玩家界面](common-game-components.md)：不展示Credits或同义About制作说明；许可证与素材出处保留项目，符合许可后处理，不直接抹掉义务 |
| 用户试玩有广告入口 | [可操作广告模拟](manual-ad-simulation.md)：本地服务经原奖励流程提供看完/取消/失败；上传Native/ZIP由既有拒包器排除模拟残留 |
| 完整功能测试或广告相关修复 | [AI逐入口广告模拟](automated-ad-simulation.md)：覆盖当前范围的原广告按钮、期望/实际奖励、保存、后续合法使用；写F11/R04，局部只测相关入口 |
| 制作记录、项目完结 | [生产统计](production-accounting.md)：增量记录步骤、时间、结果与证据；只用真实会话数据汇总token，不增加游戏CI或常驻任务 |
| 首页回访与快捷方式 | [共用任务流程](tiktok-home-growth.md)：实际Open、返回查询、单次持久领奖与Claimed，展示和入账使用同值 |
| 设计/改关、评价故障 | [关卡评价](top-bar-and-level-map.md)：普通与完美需有可操作差异、真实奖励和结算；不固定通关即满星 |
| 资源漏包与压缩恢复 | [定位与恢复](../../cocos-tiktok-package-check/references/resource-loss-recovery.md)：准确旧包命中、恢复资源引用、修复后原链；依赖变化只复验相关机制 |

每次游戏测试ZIP交付同时给同版本、已启动的固定手机预览链接；优先复用同版预览，缺少时只验证真实首页与一次玩法，不重跑全量。用户试玩结束或被替代后由Agent收尾。只核本轮实际范围，触摸、声音、模拟残留等必要拒包条件继续保留。

成品制作测试完成且当前范围已授权交付时，连续封装证据、正式出包并交同版试玩，按[完成后出包](check-fix-package-loop.md#成品测试通过后自动出包用户2026-10-26)执行；用户仅要求检测、评审、试玩或暂停时遵守当前边界。上传包的模拟窗口、Credits/制作说明入口，按[禁入窗口](../../cocos-tiktok-package-check/references/forbidden-player-windows.md)检查最终字节，修复后只复验受影响链。
