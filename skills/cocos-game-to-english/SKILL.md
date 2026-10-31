---
name: cocos-game-to-english
description: "英化（触发词：英化、英化skill、中文源码、翻译成英文、英化这个游戏）。拿到能运行的中文Cocos完整游戏时，开工先给中文原版的手机试玩链接（不等回复），再只把中文美工和文字改成英文，并补齐固定的几个入口：个人主页回访、添加桌面、音效/BGM音量、结算页看广告双倍与Retry、看广告复活，删除分享/更多游戏/联网排行榜（核心玩法里的分享奖励改看广告；局内和电脑对手比的本地名次可以留），修正操作问题；看广告的几项（结算双倍、复活、领奖窗看广告双倍勾选框、广告计时和广告回归）自动按包里的广告板块 remake-ads 做，数额按 remake-economy。默认不改玩法、不加关卡、不加新系统（创新玩法要 Saul 点名）。"
---

# 英化（独立流程）

修订：`2026-10-31.english-simple.10.2.2`（10.2.2：Saul 说广告太少时用单独安装的 ad-boost，选了哪个板块就加哪个，原首页按钮不动；要求重新设计英化游戏也照原游戏画风，Saul 2026-10-31；10.2.1：结算页 Claim 统一成 x2 正下方一行可点的小字，Saul 2026-10-31；10.2：广告 remake-ads、货币 remake-economy 两个板块放进本包，结算 x2、看广告复活、领奖窗勾选框、广告计时和广告回归自动按广告板块做；10.1：开工先给中文原版试玩链接、局内本地名次可以留、领奖窗看广告双倍勾选框；v7.7：平台标准件由出包脚本 `tiktok_finalize` 自动装上并核对；上一版 `2026-10-28.english-simple.1`，Saul 2026-10-28）。英化和重塑是两条独立的路：英化默认只用本包（本包带广告 remake-ads、货币 remake-economy 两个板块）；Saul 要求创新玩法时，新加的部分用这两个板块和重塑包里的关卡、皮肤、引导板块（见下面「创新玩法」）。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：英化一律加看广告复活，核心玩法里的分享奖励改激励视频、其他分享入口删掉，加桌面/回访奖励各 5B；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

拿到的是一个能运行的完整游戏。默认保留原工程、原玩法、原关卡、原画风、原声音和存档；不补关，不加经济、皮肤、礼盒、签到、教程等系统。关卡、皮肤、引导板块不主动调用；广告板块只用在下面「看广告的几项按广告板块做」写的几处（不用 Saul 点名），货币板块只用来算这几处的数额，原游戏的价格和其他数值不改。

**创新玩法（Saul 2026-10-30）**：Saul 要求给英化游戏加新玩法时，算单独任务。新加的部分用现成的板块做：广告 remake-ads、货币 remake-economy（本包自带）；关卡 remake-levels、皮肤 remake-skins、引导 remake-onboarding（在重塑包里，本机已装；只装了英化包的机器要先装重塑包）。不另写一套，这样不容易出新 bug，做过的也能复用。只做 Saul 点名的部分，原有玩法照旧不动；加关在关卡表写 `explicit_total`，新加的部分照对应板块的检查查。

**看广告的几项按广告板块做（Saul 2026-10-31）**：英化自己要做的广告的事，自动按本包的[广告板块 remake-ads](../remake-ads/SKILL.md)做，数额按[货币板块 remake-economy](../remake-economy/SKILL.md)，不用 Saul 点名：

- 第 6 项结算 Watch Ad x2：x2 是结算页上最大的按钮，Claim 是它正下方一行可点的小字，样子和位置按[结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)表里「看广告 ×2 按钮」「直接领取」两行（Saul 2026-10-31）；看完到账、取消/失败/超时停在结算页且 Claim 仍可点、只发一次，按[共用的广告设计](../remake-ads/SKILL.md#共用的广告设计)的结算一行；数额按[经济规则·货币和结算×2](../remake-economy/references/economy-rules.md#二货币和结算2)（基础已发只补差额；没有货币的游戏翻倍本局捡到的道具）。
- 第 7 项看广告复活：按[复活审查](../remake-ads/references/rewarded-revive-and-help-layout.md)的实施和检查做（英化一律加，不用再审要不要加；页尾的小型教程英化不做）；复活页 → 结算页的顺序按[一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)。
- 原游戏自带签到、转盘、礼包领奖窗时的看广告双倍勾选框：按广告板块共用表那一行和验收清单；数额按[经济规则·第四节](../remake-economy/references/economy-rules.md#四七日签到的数值用户-2026-10-27)末尾（有数量的项 ×2，皮肤不翻倍）。
- 原游戏已有的看广告入口改接平台包、广告计时、`qa/ad-regression.json`：按[广告机制](../remake-ads/references/ad-mechanism.md)和[超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)。

其他页面和按钮仍按本页和[固定入口](references/fixed-entries.md)（原游戏的保留，结算页上原有的按钮不能比 x2 大）。其他看广告入口（首页礼盒、独立领币、皮肤试用、体力 +3、难关提示、局内道具、看广告解锁）英化不主动加，Saul 要求创新玩法时才按广告板块做。

**Saul 说广告太少时用 ad-boost（Saul 2026-10-31）**：Saul 说「这款广告太少」「加点广告」「加转盘」「加礼包」「加签到」这类话时，读 `~/.kiro/crew/skills/ad-boost/SKILL.md`（Codex：`~/.codex/skills/ad-boost/SKILL.md`），照它做：先跑诊断，用大白话说现在有几个看广告的地方，再用一道可多选的选择题问加哪几个板块，只加他选的。
- 授权：英化本来不加新系统；**Saul 在 ad-boost 的选择题里选了哪个板块，就是授权这款加这个板块**，不用再问第二次；没选的不加。道具补给、皮肤看广告、体力 +3 只在原游戏本来就有这个系统时才加。
- 首页：**原首页按钮一个都不动**（不挪、不缩放、不重排），新入口只放空位，不压原按钮和 Logo；没有空位时问 Saul 放哪。接线前后各截一张同一手机尺寸的首页（`docs/adboost/home_before.png`、`home_after.png`）对比，原按钮有变化就退回改。
- 画风和数值：新板块的面板和图标跟原游戏画风走，优先沿用原游戏的图案和配色；广告行为和回归仍按上面的广告板块，数额按货币板块；原游戏已有的数值不改。
- 交付记录写一行：「XX、YY 板块按 Saul <日期> 在选择题里的选择加入；英化默认不加新系统，本次是他授权的例外。」

## 只做这几件事

逐项判断这个游戏要不要做；不需要做的写一句原因跳过。

| # | 做什么 | 说明 |
|---|---|---|
| 1 | 中文改英文 | 代码字符串、Label、平台文案改成自然英文；中文图片字按原画风重做英文版（尺寸、描边、颜色、位置跟原图一致），换字体并确认放得下。**句子（说明、教学、提示，两个以上单词）用真正的英文字体（TTF），不许用生成的字母图集拼句子**——那样小写会被画成大写，出现 HelP/TaP/Pond；图片字只用于固定短词和数字。**等级、关卡号、分数、货币、奖励数（Saul 2026-10-30："这种是所有游戏都需要进行的"）**：原版不管是图片字还是普通字，英化后一律按原画风做成"图片字的词（LEVEL、货币名）＋生成的 0-9 位图数字＋货币图标"，不能是一整行英文普通字（反例："LEVEL 1 • +10 PEARLS" 白字压在半透明色条上）；数字后面也不铺纯色色条。`art_check.py` 的 `font_number`、`font_value_label`、`flat_value_plate` 在英化游戏同样拦，登记成运行时文字也不豁免。设置页不显示版本号和 Credits（`dev_info_text`）。**品牌车名、动漫角色名不直译**（v7.8 E8：「法拉利458」不写 Ferrari 458，写 Supercar 这类通用叫法），`audit_copy_quality.py` 按 `remake-core/assets/trademark-words.json` 拦，并写出命中的词。改完全屏扫一遍，不许残留中文（含角落小字）。规则见 [英文界面重建](references/english-ui-rebuild.md)、[动态文字字形](references/dynamic-text-glyph-review.md) |
| 2 | 首页加两个功能键 | 个人主页回访（Revisit from Profile）、添加桌面（Add to Home Screen）。**原首页按钮全部不动**，只在原布局空位加这两个；所有环境都显示、不隐藏（本地试玩也显示）；平台不支持时点击提示 “Available in TikTok”，不发奖；真实成功才发奖，奖励各 5B（一次首页礼盒基础奖励，换算成原游戏货币），失败有反馈。|
| 3 | 设置里两个音量 | 音效（SFX）和背景音乐（BGM）分开调节、立即生效、重启后保留 |
| 4 | 删除三类功能 | 分享给朋友、更多游戏、排行榜：按钮、入口和相关代码调用全部删掉，删后页面不留空洞。**例外（v7.5，Saul 在细菌2048 的选择）**：原游戏核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频；其他分享入口连同触发它的礼物球、弹窗一起删干净。不许留“本平台不可用”的提示按钮；每个分享调用在 `docs/` 写明删掉还是改成广告。**局内本地名次可以留（Saul 2026-10-31，照 68 小熊拳击）**：一局里玩家和电脑对手的名次（局内分数牌、结算名次）、按名次给的本地奖杯和段位、个人星级和最高分都不算排行榜；数据只存本机、不联网，匹配页写 Finding opponents，电脑对手不用真人风格的名字，段位叫 Tier 不叫 League。要删的是联网的世界/好友/地区/周榜（含开放数据域）、本地编出来的全服名次（如 “You are #3,512”、“Top 5%”）和假联赛；`remake-core/scripts/audit_no_social_features.py` 按这个口径查。见 [固定入口](references/fixed-entries.md) |
| 5 | 修正操作 | 原来操作有问题的位置改好（点不到、点了没反应、改动后某处操作消失要补回）；不新增玩法 |
| 6 | 每关结算页 | 有 Retry；统一加 **Watch Ad x2** 入口，是结算页上最大、最显眼的按钮；普通领取（Claim）是它正下方一行可点的小字，不做成第二个按钮（Saul 2026-10-31）。见 [固定入口](references/fixed-entries.md)；样子按[广告板块·结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)，广告行为和 x2 数额按广告、货币板块（见上面「看广告的几项按广告板块做」） |
| 7 | 看广告复活 | 有失败/中断的一局都加“看广告复活”；**没有失败状态的游戏也加**（按 MusicSlice v30 的能量条做法）。单独一节，见 [固定入口·看广告复活](references/fixed-entries.md#看广告复活单独一节可整节删除)；实施和检查按广告板块（见上面「看广告的几项按广告板块做」） |

## 阶段

1. **盘点**：**开工先给 Saul 中文原版的手机试玩链接，不等回复，接着往下做**（Saul 2026-10-31）。在中文原工程的一份副本上导出 Web（复制到工程外再导出，原工程一个文件都不动；用原游戏对应版本的 Creator 命令行，写法见[真实 Cocos 运行](../remake-core/references/cocos-runtime.md)：2.4 是 `--path <副本> --build "platform=web-mobile"`，3.x 是 `--project <副本> --build "platform=web-mobile"`；macOS 命令行卡在导入资源时加 `--no-sandbox --disable-gpu-sandbox --disable-gpu`；原工程里已经有没改过的 `build/web-mobile` 也可以直接用），把导出的 `web-mobile` 整个复制到游戏文件夹的 `本地试玩_中文原版（不用上传）/`，再在后台起链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory "<游戏文件夹>/本地试玩_中文原版（不用上传）" --snapshot --open --idle-minutes 0 --name "<游戏> 中文原版"`。原版不用 `--keep`：原版没有美术回执，广告也还没接平台包，看广告冒烟对它没有意义。自己先打开链接，确认能进首页、能开始玩一局，再把链接发给 Saul。导不出 Web 时（引擎版本不对、构建报错、只有小游戏包没有源码），把原因写给 Saul，同样接着做。这份导出后面截中英对照图（`docs/baseline/`）也用。然后跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py init --project <中文原工程> --board localize`（写新游戏标记 `.tiktok-kit/policy.json`），再跑 `tiktok_finalize.py inventory --project <中文原工程>`，它把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码逐项列到 `docs/english/platform-inventory.json`，第 2 阶段按它逐项改。和 `audit_new_english_images.py --make-list` 放在同一步做。然后列出全部中文（文字和图片字）、首页现有按钮、设置项、结算页、分享/更多游戏/排行榜入口、已知的操作问题。遗留名单上的旧英化游戏（射击高手、音乐消消乐等）继续做新版本时不跑 `init`，按旧游戏出包（拿不准就先跑 `tiktok_finalize.py decide --project <工程>` 看判定）；要改用标准件才跑 `tiktok_finalize.py adopt --project <工程>`。
2. **修改**：按上表 1–7 做。
   - **平台能力用平台包**：激励视频用平台包的 `RewardedService.js`，加桌面、主页回访用 `TikTokMissionService.js`（`remake-core/assets/platform-kit/`），不另写一份桥接。它们已经把 UI 回调包在 try/catch 里，提示抛错也不会把请求锁死（MusicSlice v29b 手写的 bridge 提示一抛错，看广告、加桌面、回访全部卡在 Checking）。触摸修正、存档层、启动件、适配层、App ID、图片格式和压缩由出包入口自动装上并核对，不要手写；手写的同类文件会被换掉（旧游戏除外）。新英化游戏一律装存档层 `storage-guard.js`（原版多键存储也走它）；旧英化游戏默认不装，只在 `adopt` 以后装（Q6）。原版的广告管理器改成调 `RewardedService`、原版里直接 `createRewardedVideoAd` 或直接调加桌面/回访接口的代码删掉：新游戏漏改出不了包（`A1_rewarded_outside_kit`、`G1k_growth_outside_kit`）。原版（2.4）自带和平台包模块同名的脚本（例如自己的 `TikTokMissionService.js`），`source` 段会把它移到 `.tiktok-kit/removed/`。`PlatformConfig.js` 要填本游戏的 `gameId` 和 `normalLevelCoins`，没填新游戏出不了包（`K_platform_config`）。
   - **原版的 `.webp` 图**：新英化游戏由 `source` 段换成 PNG/JPG；数据或脚本里写死的 `.webp`（例如 `"imageExt": ".webp"`）按文件和行号被拒（`IMG0_source_images`），要改成 `.png`/`.jpg`。原版是 Cocos 3.x 的没有 WebP 例外（`K_webp_exception_3x`），只能靠 PNG/JPG 和 `max_side` 缩到 30 MB 以内。
   - **新做的英文图**：按显示尺寸 2 倍导出再压缩。新图（哈希不在英化前的图片清单里）单张超过 800 KB，出包会被拒；宽/高超过显示尺寸 2.5 倍的会被列出来，要改小（`remake-core/scripts/audit_new_english_images.py`；开工时用 `--make-list <中文原工程>` 存英化前清单到 `docs/english/pre-english-images.json`，出包时缺这份清单也会被拒）。
   - **写 `qa/ad-regression.json`**：出包前的 10 个广告回归用例要它。`request` 走游戏自己真实的看广告方法，`grant` 挂在游戏真实的发奖函数上，`ready` 写首页已就绪的条件。示例：[examples/MusicSlice_ad-regression.json](examples/MusicSlice_ad-regression.json)（多渠道 AdsManager：`config.videoType=0` 后调 `config.AdsManager.ShowVideo()`，发奖统一走 `config.getReward`，示例把它换成计数）。同一个文件也给出包时必跑的运行时回归用（`cocos-game-check/package-check/references/runtime-regression.md`）：必须有 `home`（首页可用时返回 true），建议写 `enter_level`；缺 `home` 出包会被拒。
   - **广告规则去哪看**：按上面「看广告的几项按广告板块做」：广告计时和广告回归看 [超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)，复活页和结算 x2 两屏看 [一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)，领奖窗看广告双倍勾选框看 [广告板块共用表](../remake-ads/SKILL.md#共用的广告设计)，数额看 [经济规则](../remake-economy/references/economy-rules.md)；和 [TikTok 固定适配·已定口径](../cocos-game-check/references/tiktok-fixed-adaptation.md) 有出入时以已定口径为准。
   - **图片复核记录 `docs/english/image-review.json`**：上传包里每张不同的图（按 SHA-256）一条：谁看的、有没有中文、换成了什么；图集按切片看（`"slices_reviewed": true`）。缺记录、还是 pending、写着有中文却还是同一张图，出包会被拒（`remake-core/scripts/audit_image_review_record.py`）。可以用 grok-image-review 转录图上的字，结论由主 Agent 定。
3. **检查**：用 [统一检查](../cocos-game-check/SKILL.md)，类型选“英化”。跑 `preflight.py` 之前先跑一次 `tiktok_finalize.py source --project <工程> --board localize`：英化工程的「平台包」一行查的是源码段记录是否新鲜，不查 `build-templates/bytedance/`。
4. **用户试玩确认**：给手机预览链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory <同版 Web 导出> --snapshot --keep --project <工程>`（转到同包 `remake-core/scripts/serve_preview.py`；`--keep` 要给 `--project`，英化游戏没有美术回执只出警告；用法见[固定手机尺寸试玩](../remake-core/references/user-phone-preview.md)）；测试前问用户：“文字、图片和新入口都没问题了吗？”
5. **出包**：用户授权后，先跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <工程> --board localize` 再构建，再用写包入口出包（`make_tiktok_zip.py` 和 `build_checked_zip.py` 都要给 `--project`；游戏自己的打包步骤在写包入口之前做完），按统一检查里的出包与最终包检查。v7.6 写包入口出的收据在 v7.7 不再是官方入口，交付前用 v7.7 写包入口重新出。交付回复贴写包报告里的标准件小表，并写“标准件待真机复测”。

## 美工 Skill 只在点名时用

[美工 Skill](../remake-art/SKILL.md) 不在英化流程里自动调用。图片字换英文属于第 1 项，按原画风做，不重新设计。只有用户明确说“用美工 skill / 重做美术 / 这页太丑改一下”时才进入美工 Skill。原美工好的部分不碰。例外是第 1 项里写的等级、关卡号、分数、货币美化，以及不显示版本号和 Credits：这两条英化必做，不用等点名（Saul 2026-10-30，见 [Saul 的美术禁区与必做项](../remake-art/references/saul-art-rules.md)）。

**Saul 要求“重新设计”英化游戏时，画风也照原游戏**（Saul 2026-10-31，香肠太难了 Redesign v2：他说“结合广告skill和美工skill重新设计游戏”，结果原版亮橙色、薄荷绿的圆角按钮和木色金边的六边形图标钮全被换成同一种深红方块；Saul：“要按照原游戏的风格去设计美工”）：原图能用就用，要新生成就把原图放进参考图照着画；按钮底色不用深色（深红、砖红、深棕、藏青、深灰、黑这类），金币、爱心、礼盒这些物品图标后面不另加底板；原游戏本来带底座、奶油色边或高光的照原游戏。只有他明说换画风（例如“按重塑画风重做”）才换。用 ad-boost 加的新板块也一样，面板和图标跟原游戏走。
