---
name: cocos-game-art-redo
description: "重做或局部修改Cocos游戏美术、按钮、图片字、图标和界面布局，并验证受影响页面与输入。"
---

# Cocos美术重做与局部修正

先确定本轮是完整重做还是已批准画面的局部修改。保留原始素材和用户存档；玩法和经济保持当前授权。分享、全部排行榜和广告跳关按[前置规则](../cocos-game-to-english/references/no-social-features.md)移除，其他业务不因美术任务擅自删除或新增。

| 工作 | 按需读取 |
|---|---|
| 主题、样板与同套资产 | [UI规范与样板](../cocos-game-to-english/references/ui-style-and-samples.md)、[明亮Q版](../cocos-game-to-english/references/cute-casual-style.md) |
| Logo、图片字、按钮连字、位图数字 | [页面丰富度与文字](../cocos-game-to-english/references/page-richness.md)、[字底与字形](references/text-backplate-review.md) |
| 双倍奖励主按钮、普通领取次按钮、首页分区和动态标题/主角 | [结算按钮层级](../cocos-game-to-english/references/mobile-button-size-and-home-layout.md#结算双倍主按钮层级用户-2026-10-27)、[按钮与首页](../cocos-game-to-english/references/mobile-button-size-and-home-layout.md) |
| 集合预览、首尾压框、装备对应 | [集合预览](references/collection-preview-review.md) |
| 拼装后的实际画面和输入 | [美术自审](../cocos-game-to-english/references/artwork-and-feedback.md)、[局部UI契约](../cocos-game-to-english/references/local-ui-contract.md) |
| 用户确认后的检查范围 | [美术前移与锁定](../cocos-game-to-english/references/art-before-trial.md)、[执行去重](../cocos-game-to-english/references/review-execution-plan.md) |

已知文字/按钮与其底图由内置image_gen整体生成，标题使用风格化logo，动态数字使用生成的位图字；不以程序字或空底叠字冒充。字图等比缩放，实际组合图核字芯/描边、装饰压字、关闭与父面板、最长数字串和字距；普通矩形边界通过不能代替实际画面。

**结算页主次（用户 2026-10-27）**：可领取广告双倍奖励时，“看广告 ×2”必须是最大、最醒目的收益操作主按钮，普通领取／免费继续做成较小的次按钮，降低视觉权重但保持清楚可读、容易触摸。美术样板、生图提示词、实际组装及手机画面验收均按上表的结算按钮层级执行；不能让 HOME/NEXT 抢走广告奖励入口的视觉主位。

完整首次重做覆盖实际全部页面、弹窗和条件状态、两种比例及两轮自审；局部修改查受影响整页、共享组件与真实点击，已通过且无新变化不再追加整轮。`art_check.py`按适用行运行，未测范围不写通过。用户确认画面后，最终出包只查运行故障，不重评审美。

共同症状按[当前合同](../cocos-game-to-english/references/current-contracts.md)进入所属参考。交用户[同版固定手机预览](../cocos-game-to-english/references/user-phone-preview.md)，结束自建QA页与无用服务。本任务不自动生成游戏包；已报告缺图/遮挡等问题记入项目，并定点修复复验。

反复出现的数字模糊、遮挡与漏检，按[成屏视觉缺陷回归](references/rendered-ui-regression-review.md)先在项目内用旧失败、修复、正常及缺采集对照模拟校准，再采用通用审查步骤；覆盖受影响的倒计时、价格、广告完成与教学等条件状态。

删除界面代码时按[相邻功能回归](../cocos-game-to-english/references/button-state-check.md#删除界面代码时保护相邻方法2026-10-27)检查完整方法边界及受影响入口。

## 通用规范与完工整理

适用性与故障修复按[通用问题规范](../cocos-game-to-english/references/feedback-regressions.md)；完工沉淀按[去重维护](../cocos-game-to-english/references/knowledge-consolidation.md)，入口只引用主规范。

受影响输入的执行器、预检和结果字段统一按[Chrome 触摸运行合同](../cocos-game-to-english/references/google-touch-runtime.md)与[触摸预检矩阵](../cocos-game-to-english/references/chrome-touch-preflight-matrix.md)执行。

**每轮修改主动交预览（用户2026-10-28）**：每轮游戏代码、美术、玩法、广告或打包相关修改完成后，主动在回复中给出当前同版本可点击的固定手机预览链接，无需等用户再次索取。按[用户本地试玩](../cocos-game-to-english/references/user-phone-preview.md)执行；交接前确认服务可访问且指向本轮完成的构建。
