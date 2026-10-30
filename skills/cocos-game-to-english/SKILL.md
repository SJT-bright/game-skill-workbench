---
name: cocos-game-to-english
description: "英化（触发词：英化、英化skill、中文源码、翻译成英文、英化这个游戏）。拿到能运行的中文Cocos完整游戏时，只把中文美工和文字改成英文，并补齐固定的几个入口：个人主页回访、添加桌面、音效/BGM音量、结算页看广告双倍与Retry、看广告复活，删除分享/更多游戏/排行榜（核心玩法里的分享奖励改看广告），修正操作问题。不改玩法、不加关卡、不加新系统。"
---

# 英化（独立流程）

修订：`2026-10-29.english-v7.7`（v7.7：平台标准件由出包脚本 `tiktok_finalize` 自动装上并核对；上一版 `2026-10-28.english-simple.1`，Saul 2026-10-28）。英化和重塑是两条独立的路：英化只用本包，不需要安装重塑包。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：英化一律加看广告复活，核心玩法里的分享奖励改激励视频、其他分享入口删掉，加桌面/回访奖励各 5B；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

拿到的是一个能运行的完整游戏。保留原工程、原玩法、原关卡、原画风、原声音和存档；不补关，不加经济、皮肤、礼盒、签到、教程等系统。用户之后对玩法提的改动是单独任务。

## 只做这几件事

逐项判断这个游戏要不要做；不需要做的写一句原因跳过。

| # | 做什么 | 说明 |
|---|---|---|
| 1 | 中文改英文 | 代码字符串、Label、平台文案改成自然英文；中文图片字按原画风重做英文版（尺寸、描边、颜色、位置跟原图一致），换字体并确认放得下。**句子（说明、教学、提示，两个以上单词）用真正的英文字体（TTF），不许用生成的字母图集拼句子**——那样小写会被画成大写，出现 HelP/TaP/Pond；图片字只用于固定短词和数字。改完全屏扫一遍，不许残留中文（含角落小字）。规则见 [英文界面重建](references/english-ui-rebuild.md)、[动态文字字形](references/dynamic-text-glyph-review.md) |
| 2 | 首页加两个功能键 | 个人主页回访（Revisit from Profile）、添加桌面（Add to Home Screen）。**原首页按钮全部不动**，只在原布局空位加这两个；所有环境都显示、不隐藏（本地试玩也显示）；平台不支持时点击提示 “Available in TikTok”，不发奖；真实成功才发奖，奖励各 5B（一次首页礼盒基础奖励，换算成原游戏货币），失败有反馈。|
| 3 | 设置里两个音量 | 音效（SFX）和背景音乐（BGM）分开调节、立即生效、重启后保留 |
| 4 | 删除三类功能 | 分享给朋友、更多游戏、排行榜：按钮、入口和相关代码调用全部删掉，删后页面不留空洞。**例外（v7.5，Saul 在细菌2048 的选择）**：原游戏核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频；其他分享入口连同触发它的礼物球、弹窗一起删干净。不许留“本平台不可用”的提示按钮；每个分享调用在 `docs/` 写明删掉还是改成广告。见 [固定入口](references/fixed-entries.md) |
| 5 | 修正操作 | 原来操作有问题的位置改好（点不到、点了没反应、改动后某处操作消失要补回）；不新增玩法 |
| 6 | 每关结算页 | 有 Retry；统一加 **Watch Ad x2** 入口，按钮比旁边的普通领取按钮更大、更显眼；普通领取（Claim）在它旁边，不如它显眼。见 [固定入口](references/fixed-entries.md) |
| 7 | 看广告复活 | 有失败/中断的一局都加“看广告复活”；**没有失败状态的游戏也加**（按 MusicSlice v30 的能量条做法）。单独一节，见 [固定入口·看广告复活](references/fixed-entries.md#看广告复活单独一节可整节删除) |

## 阶段

1. **盘点**：先跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py init --project <中文原工程> --board localize`（写新游戏标记 `.tiktok-kit/policy.json`），再跑 `tiktok_finalize.py inventory --project <中文原工程>`，它把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码逐项列到 `docs/english/platform-inventory.json`，第 2 阶段按它逐项改。和 `audit_new_english_images.py --make-list` 放在同一步做。然后列出全部中文（文字和图片字）、首页现有按钮、设置项、结算页、分享/更多游戏/排行榜入口、已知的操作问题。遗留名单上的旧英化游戏（射击高手、音乐消消乐等）继续做新版本时不跑 `init`，按旧游戏出包（拿不准就先跑 `tiktok_finalize.py decide --project <工程>` 看判定）；要改用标准件才跑 `tiktok_finalize.py adopt --project <工程>`。
2. **修改**：按上表 1–7 做。
   - **平台能力用平台包**：激励视频用平台包的 `RewardedService.js`，加桌面、主页回访用 `TikTokMissionService.js`（`remake-core/assets/platform-kit/`），不另写一份桥接。它们已经把 UI 回调包在 try/catch 里，提示抛错也不会把请求锁死（MusicSlice v29b 手写的 bridge 提示一抛错，看广告、加桌面、回访全部卡在 Checking）。触摸修正、存档层、启动件、适配层、App ID、图片格式和压缩由出包入口自动装上并核对，不要手写；手写的同类文件会被换掉（旧游戏除外）。新英化游戏一律装存档层 `storage-guard.js`（原版多键存储也走它）；旧英化游戏默认不装，只在 `adopt` 以后装（Q6）。原版的广告管理器改成调 `RewardedService`、原版里直接 `createRewardedVideoAd` 或直接调加桌面/回访接口的代码删掉：新游戏漏改出不了包（`A1_rewarded_outside_kit`、`G1k_growth_outside_kit`）。原版（2.4）自带和平台包模块同名的脚本（例如自己的 `TikTokMissionService.js`），`source` 段会把它移到 `.tiktok-kit/removed/`。`PlatformConfig.js` 要填本游戏的 `gameId` 和 `normalLevelCoins`，没填新游戏出不了包（`K_platform_config`）。
   - **原版的 `.webp` 图**：新英化游戏由 `source` 段换成 PNG/JPG；数据或脚本里写死的 `.webp`（例如 `"imageExt": ".webp"`）按文件和行号被拒（`IMG0_source_images`），要改成 `.png`/`.jpg`。原版是 Cocos 3.x 的没有 WebP 例外（`K_webp_exception_3x`），只能靠 PNG/JPG 和 `max_side` 缩到 30 MB 以内。
   - **新做的英文图**：按显示尺寸 2 倍导出再压缩。新图（哈希不在英化前的图片清单里）单张超过 800 KB，出包会被拒；宽/高超过显示尺寸 2.5 倍的会被列出来，要改小（`remake-core/scripts/audit_new_english_images.py`；开工时用 `--make-list <中文原工程>` 存英化前清单到 `docs/english/pre-english-images.json`，出包时缺这份清单也会被拒）。
   - **写 `qa/ad-regression.json`**：出包前的 10 个广告回归用例要它。`request` 走游戏自己真实的看广告方法，`grant` 挂在游戏真实的发奖函数上，`ready` 写首页已就绪的条件。示例：[examples/MusicSlice_ad-regression.json](examples/MusicSlice_ad-regression.json)（多渠道 AdsManager：`config.videoType=0` 后调 `config.AdsManager.ShowVideo()`，发奖统一走 `config.getReward`，示例把它换成计数）。同一个文件也给出包时必跑的运行时回归用（`cocos-game-check/package-check/references/runtime-regression.md`）：必须有 `home`（首页可用时返回 true），建议写 `enter_level`；缺 `home` 出包会被拒。
   - **图片复核记录 `docs/english/image-review.json`**：上传包里每张不同的图（按 SHA-256）一条：谁看的、有没有中文、换成了什么；图集按切片看（`"slices_reviewed": true`）。缺记录、还是 pending、写着有中文却还是同一张图，出包会被拒（`remake-core/scripts/audit_image_review_record.py`）。可以用 grok-image-review 转录图上的字，结论由主 Agent 定。
3. **检查**：用 [统一检查](../cocos-game-check/SKILL.md)，类型选“英化”。跑 `preflight.py` 之前先跑一次 `tiktok_finalize.py source --project <工程> --board localize`：英化工程的「平台包」一行查的是源码段记录是否新鲜，不查 `build-templates/bytedance/`。
4. **用户试玩确认**：给手机预览链接（`scripts/serve_preview.py`）；测试前问用户：“文字、图片和新入口都没问题了吗？”
5. **出包**：用户授权后，先跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <工程> --board localize` 再构建，再用写包入口出包（`make_tiktok_zip.py` 和 `build_checked_zip.py` 都要给 `--project`；游戏自己的打包步骤在写包入口之前做完），按统一检查里的出包与最终包检查。v7.6 写包入口出的收据在 v7.7 不再是官方入口，交付前用 v7.7 写包入口重新出。交付回复贴写包报告里的标准件小表，并写“标准件待真机复测”。

## 美工 Skill 只在点名时用

[美工 Skill](../remake-art/SKILL.md) 不在英化流程里自动调用。图片字换英文属于第 1 项，按原画风做，不重新设计。只有用户明确说“用美工 skill / 重做美术 / 这页太丑改一下”时才进入美工 Skill。原美工好的部分不碰。
