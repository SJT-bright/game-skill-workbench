---
name: remake-art
description: "美工（只在用户点名时使用；触发词：用美工skill、重做美术、美术skill、这页太丑、重新设计界面）。重做或局部修改Cocos游戏美术、按钮、图标和界面布局。英化流程不自动调用：英化里的中文图片字换英文按原画风做，属于英化入口第1项。"
---

> **英化包说明（Saul 2026-10-28）**：只在用户点名时使用；英化没有启动包，**保持原游戏画风**，只改用户点名的页面或元素，原美工好的部分不碰；下文“画风跟随启动包”只适用于重塑。


# Cocos美术重做与局部修正（美术与UI板块）

修订：`2026-10-27.modules-v6`。**管什么**：画风禁止项（只写负向约束；画风本身跟启动包走，用户 2026-10-27/28）、页面布局与分区、按钮、图片字与 Logo、图标、动效、首页与设置页、加载页画面。**不管什么**：文字内容是否地道（文案（重塑包 remake-copy 板块，英化包不含））、数值（经济（重塑包 remake-economy 板块，英化包不含））、关卡数据（关卡（重塑包 remake-levels 板块，英化包不含））。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：美术只出 PNG/JPG，右上角留给胶囊，首页底排只放两个平台入口，不做 Credits；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

**画风跟随启动包（用户 2026-10-28）**：本板块不规定任何正向画风（不要求明亮、Q版、糖果色、光泽、胶囊按钮、固定颜色含义、亮度下限或华丽感），只写[禁止项清单](references/style-limits.md#〇画风禁止项清单只查负向用户-2026-10-28)。有启动包时，`ART_DIRECTION.md`（以及 UI_PAGES、EXPERIENCE 的页面与素材需求）就是本作的美术规格：题材、主角与角色造型、场景、配色、页面清单、按钮与图标需求、生图提示词都按它做，不另起一套画风，也不按 AI 自己的偏好改。只有它和下面的禁止项冲突时才调整，并在项目记录里写明哪一条、怎么改；启动包没写到的部分按同一风格补齐。没有启动包时才按游戏题材自定风格。精简启动包（`supply: light`）的 `ART_DIRECTION.md` 带色板 HEX、逐页背景、UI kit、字体和生图提示词，照它执行，见[精简启动包的详细画风](references/ui-style-and-samples.md#精简启动包的详细画风)。

先确定本轮是完整重做还是已批准画面的局部修改。保留原始素材和用户存档；玩法和经济保持当前授权。分享、全部排行榜和广告跳关按[前置规则](../remake-core/references/no-social-features.md)移除，其他业务不因美术任务擅自删除或新增。

**图片格式与出包处理（v7.7）**：
- 只交 PNG（有透明）或 JPG（不透明），不交 WebP 美术。新游戏工程里的 `.webp` 出包前由 `tiktok_finalize.py source` 自动换成 PNG/JPG（uuid 不变），构建产物里还有 `.webp` 就拒绝出包（`K_S_webp`）。图换成 PNG/JPG 后，数据和脚本里写死的 `.webp`（例如美术清单里的 `"imageExt": ".webp"`）会让图加载失败，源码段按文件和行号拒绝（`IMG0_source_images`），要自己改成 `.png`/`.jpg`。只有缩完图仍超 30 MB 才能走 WebP 例外，见 [TikTok 固定适配·第 6 条](../cocos-game-check/references/tiktok-fixed-adaptation.md#6-图片只出-pngjpg按显示尺寸缩压缩webp-9-款大图和首屏过多-24-款)。
- 素材只用 CC0（不需要署名，也就不需要 Credits）。这一条只是文档规则，没有门禁会查，选素材时自己核对授权并记在 `docs/` 里。
- 不用按显示尺寸手动缩图：出包时宽和高都超过显示尺寸 2 倍的图会自动缩到 2 倍，但只限场景或预制体里静态 Sprite 用的、单帧、没有裁边、不在 `resources/` 或 bundle 里的图。**代码按路径加载的图、带裁边（trim）的图不会自动缩**，要在 `<工程>/.tiktok-kit/image-overrides.json` 里逐张写 `max_side`（例如 `{"images": {"assets/resources/art/*.png": {"max_side": 900}}}`，键可以用通配；位图字的字形图不要缩）。
- 出包时所有 PNG 压成 256 色（pngquant）。渐变背景出现色带时，按张在同一个 `image-overrides.json` 里改：`{"quantize": false}` 不压缩，或 `{"format": "jpg", "jpg_quality": 95}`（带透明的图不能转 JPG）。前后对比用 `python3 <skills>/remake-core/scripts/finalize_images_compare.py --project <工程> [--native <构建目录>]`，它出成对图和 `index.html`，把可能有色带的图标成 `check` 排在最前面，并给出建议的 `suggested-overrides.json`。

| 工作 | 按需读取 |
|---|---|
| 主题、样板与同套资产 | [UI规范与样板](references/ui-style-and-samples.md)、[画风只守禁止项](references/style-limits.md) |
| Logo、图片字、按钮连字、位图数字 | [页面不单调与文字](references/page-richness.md)、[字底与字形](references/text-backplate-review.md) |
| 双倍按钮、首页分区和动态标题/主角 | [按钮与首页](references/mobile-button-size-and-home-layout.md)；结算页 ×2 大按钮＋下方一行 Claim 文字见结算页设计（重塑包 remake-ads 板块，英化包不含） |
| 首页按玩法设计、会动的背景、可互动的首页物件 | [首页按玩法设计](references/home-by-gameplay.md)（用户 2026-10-28） |
| 集合预览、首尾压框、装备对应 | [集合预览](references/collection-preview-review.md) |
| 拼装后的实际画面和输入 | [美术自审](references/artwork-and-feedback.md)、[局部UI契约](references/local-ui-contract.md) |
| 用户确认后的检查范围 | [美术前移与锁定](references/art-before-trial.md)、[执行去重](../cocos-game-check/test/references/review-execution-plan.md) |

已知文字/按钮与其底图由内置image_gen整体生成，标题使用风格化logo，动态数字使用生成的位图字；不以程序字或空底叠字冒充。字图等比缩放，实际组合图核字芯/描边、装饰压字、关闭与父面板、最长数字串和字距；普通矩形边界通过不能代替实际画面。

完整首次重做覆盖实际全部页面、弹窗和条件状态、两种比例及两轮自审；局部修改查受影响整页、共享组件与真实点击，已通过且无新变化不再追加整轮。`art_check.py`按适用行运行，未测范围不写通过。用户确认画面后，最终出包只查运行故障，不重评审美。

共同症状按[当前合同](../remake-core/references/current-contracts.md)进入所属参考。交用户[同版固定手机预览](../remake-core/references/user-phone-preview.md)，结束自建QA页与无用服务。本任务不自动生成游戏包；已报告缺图/遮挡等问题记入项目，并定点修复复验。

## 更多正文（本板块）

[原画风与反馈](references/artwork-and-feedback.md)、[生图后全量巡检](references/full-visual-review.md)、[动态画面](references/dynamic-visual-review.md)、[题材与可读性](references/theme-readability.md)、[图集切片](references/atlas-slice-integrity.md)、[角色姿态交接](references/actor-pose-handoffs.md)、[首页与设置页](references/common-game-components.md)。

## 联动表：改了美术与UI，要回查

| 改了 | 回查 |
|---|---|
| 页面布局、按钮位置 | 按钮真实点击与触控区域（测试与修复）；教程手指坐标（新手引导）；广告按钮层级（广告） |
| 图片字、按钮字 | 英文是否准确（文案） |
| 皮肤页、商店页 | 价格/加成显示与表一致（皮肤、经济） |
| 地图、资源栏 | 总关数和数字实时更新（关卡） |

## 验收清单

- [ ] 画风照启动包、不混用几套；没有[禁止项](references/style-limits.md#〇画风禁止项清单只查负向用户-2026-10-28)：深色/过密/过细的字、大面积深色/纯黑纯色底、大白板、单色图标、刺眼整屏高亮、无层次平涂、字压复杂底图、遮挡穿模、模糊；玩区 ≥80%
- [ ] 功能按上/左/右/下分区，次要功能用小图标
- [ ] `art_check.py` 按适用行运行通过，两种比例截图看过
- [ ] 改动页面的按钮真实点击有效
- [ ] 只交 PNG/JPG、素材都是 CC0；代码加载或带裁边的大图已在 `image-overrides.json` 写 `max_side`；有色带的图已按张处理
