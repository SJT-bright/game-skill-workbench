# 英化固定入口（Saul 2026-10-28）

**必须遵循（Saul 2026-10-29）**：下面每个入口都在 [TikTok 固定适配](../../cocos-game-check/references/tiktok-fixed-adaptation.md) 的口径内做（广告计时 v7.4、每屏一个看广告按钮、加桌面/回访奖励各 5B、平台能力只用平台包）。看广告的入口（结算 Watch Ad x2、看广告复活、领奖窗勾选框）的广告行为和检查自动按本包的 [广告板块](../../remake-ads/SKILL.md) 做，数额按 [货币板块](../../remake-economy/SKILL.md)，不用 Saul 点名（Saul 2026-10-31）；页面和按钮按本页。

## 首页：个人主页回访与添加桌面

- 原首页所有按钮的位置、大小、图片保持不动。新加的两个按钮放在原布局的空位，用原游戏同风格的小图标按钮，不遮挡开始按钮和玩法区，避开右上角平台胶囊区域。
- Revisit from Profile：调用平台“从个人主页回访”能力；Add to Home Screen：调用平台“添加到桌面”能力。
- **永不隐藏（用户 2026-10-28）**：本地浏览器试玩、手机预览、正式包都显示这两个按钮；平台不支持时点击给出简短英文提示（如 “Available in TikTok”），不模拟成功、不发奖；调用失败或取消也要有提示，不发奖。
- **奖励固定 5B（Saul 2026-10-29，所有游戏统一）**：加桌面、主页回访各发一次，每项等于一次首页礼盒的基础奖励 5B，换算成原游戏的货币（B = 原游戏一个普通关的基础收入；原游戏没有首页礼盒也按 5B 算）。不再按单款自定（以前 20～150 各不相同）。只在平台真实返回可领后发一次，“已领取”和加币一次写入并持久记录，重复点击不重复发。用平台包时在 `PlatformConfig.js` 填 `normalLevelCoins`，`reward` 写 `draft.coins += config.growthReward()`。
- 两个入口直接接平台包 `TikTokMissionService.js` / `MissionFlow.js`，不另写桥接；固定规则和验收见 [TikTok 固定适配·加桌面与回访](../../cocos-game-check/references/tiktok-fixed-adaptation.md#7-加桌面主页回访以及-sdk-去哪里找19-款sdk-命名空间-6-款)。

## 设置：音效与 BGM 音量

- 两个独立控件（滑块或分档按钮）：Sound Effects、Music。拖动立即生效，存本地，重启后保持。
- 音量为 0 时等同静音；原有的单个“声音开关”可保留，但不能替代这两个控件。
- 用原游戏已有的声音管理代码接这两个控件；原游戏没有合格的，就写一个最小的：两路音量各自存本地、启动时读回、广告前后暂停和恢复。`GameAudioManager` 模板在重塑包的 game-audio-library 里，英化包不带（本机装了重塑包时可以照它写）。检查按 AUDIO-01。

## 删除：分享、更多游戏、排行榜

- 删除按钮、入口、弹窗和调用平台分享/跳转/排行榜接口的代码；删后重新排好所在页面，不留空位、不留无效点击区。
- **局内本地名次可以留（Saul 2026-10-31，照 68 小熊拳击）**：一局里玩家和电脑对手的名次（局内分数牌、结算名次）、按名次给的本地奖杯和段位、个人星级和最高分都不算排行榜；数据只存本机、不联网，匹配页写 Finding opponents，电脑对手不用真人风格的名字，段位叫 Tier 不叫 League。要删的是联网的世界/好友/地区/周榜（含开放数据域）、本地编出来的全服名次（如 “You are #3,512”、“Top 5%”）和假联赛；`remake-core/scripts/audit_no_social_features.py` 按这个口径查。
- **分享换奖励（v7.5 默认，取自 Saul 对细菌2048 的选择；取代旧的“一并删除、不改成广告”）**：
  - 原游戏核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频：完整看完才发奖，取消、失败、超时不发奖，弹窗保留可重试，旁边有不看广告的退出（如 No Thanks）。
  - 其他分享入口（成就分享、升级分享、邀请好友等）连同触发它的礼物球、弹窗一起删干净。
  - 不许把分享换成一句固定提示留着入口：玩家看得到的 “unavailable on this platform”、“Sharing / Leaderboard unavailable”、“Coming soon” 这类字都是死按钮（细菌2048 原件 `WeChatCom.ts:10`、`MainUISc.ts:344`）。
  - 每个调用分享封装（`Share()`、`shareAppMessage` 等）的位置都在 `docs/` 写明：删掉了，还是改成了看广告（写脚本名即可，如 `ReviveUISc`）。检查：`remake-core/scripts/audit_share_entries.py`（一键预检“分享换奖励”一行）。

## 结算页：Watch Ad x2、Claim、Retry

- 每关结束（通关获得货币时）都显示 **Watch Ad x2**：页面上最大、最显眼的按钮（更大的尺寸、更亮的颜色或动效），文案如 `Watch Ad x2`；节点名 `BtnDouble`、图片帧 `btn_x2_*`（美术检查的 `result_double`、`result_double_main` 靠名字认出它）。
- 普通领取 **Claim** 是 x2 正下方的一行可点小字（如 `Claim 50`，数字随本关金额；Claim 用图片字、数字用位图数字，和英化入口第 1 项一样），不做成第二个按钮、没有底板；节点名 `LinkClaim`、图片帧 `link_claim*`，面积不超过 x2 按钮的一半，点击区高至少 44px（可以用透明点击区扩大）。美术检查 `audit_page_richness.py` 的 `result_claim_link` 按这个查（Saul 2026-10-31，和[广告板块·结算页设计](../../remake-ads/SKILL.md#结算页设计用户-2026-10-27)一样）。
- 点 Claim 只拿本关原额；看完广告拿两倍（基础已发时只补差额）。广告取消、失败或超时不发奖，按钮恢复可点，可以再选 Claim。
- 防连点：广告进行中按钮锁定，回调只结算一次；退出、重进或迟到的回调不补发。
- 这些广告行为按 [广告机制](../../remake-ads/references/ad-mechanism.md) 和 [超时规则与广告回归](../../remake-ads/references/ad-timeout-and-regression.md) 查；x2 数额按 [经济规则·货币和结算×2](../../remake-economy/references/economy-rules.md#二货币和结算2)：没有货币的游戏 x2 翻倍本局捡到的道具，本局没捡到东西时不放 x2、改一行文字。
- 结算页有 **Retry**（重玩本关），以及原游戏已有的 Home/Next 等按钮保持原样，只是不能比 x2 大。
- 只用激励视频；不加插屏、横幅，不做看广告跳关。

## 签到、转盘结果、礼包领奖窗：看广告双倍勾选框（Saul 2026-10-31）

原游戏自带签到、转盘或礼包领奖窗的，领奖窗上放一个「Watch Ad x2」勾选框，**默认勾上**（照 64 音乐消消乐签到页的样子）。原版没有这些窗的不加。

- 勾着点 CLAIM：播激励视频，完整看完（`onClose` 的 `res.isEnded === true`）才发 2 倍。
- 取消勾选点 CLAIM：不播广告，免费发 1 倍。
- 广告没看完：不发 2 倍，也不吞掉 1 倍；弹窗留着，玩家可以取消勾选再领。
- 每个领奖窗只有这一个看广告入口；「必须看广告才能领」不许做。首页礼盒不加勾选框；一局结束的复活页 → 结算 x2 两屏不变。
- 数额：本次奖励里有数量的项（金币、道具、体力）×2，皮肤不翻倍，见 [经济规则·第四节](../../remake-economy/references/economy-rules.md#四七日签到的数值用户-2026-10-27) 末尾；勾选框的规则见 [广告板块共用表](../../remake-ads/SKILL.md#共用的广告设计)。
- 检查：美术关的 `remake-core/scripts/audit_claim_double.py`（读 dump_ui，领奖窗的 purpose 写 `checkin`、`wheel_result`、`spin_result` 或 `gift_pack`）；广告回归在 `qa/ad-regression.json` 写了 `double_claim` 才跑 `double_watch`、`double_quit`、`double_free` 三条（写法见 `cocos-game-check/package-check/scripts/ad_regression.py` 文件头）。

## 看广告复活（单独一节，可整节删除）

Saul 2026-10-28 在 MusicSlice 上要求加；**2026-10-29 已定：英化游戏一律加看广告复活，没有失败状态的游戏也加**（以前按单款决定的做法作废，如气球快跑 v56 去掉复活）。复活和结算 x2 分两屏：一局结束先出复活页（只有 **Watch Ad to Revive** 和免费 **No Thanks**），玩家放弃或已用过复活后再进结算页（只有 Watch Ad x2，Retry/Home 在下面）；**同一屏只放一个看广告按钮**。必须遵循 [TikTok 固定适配·复活与 x2](../../cocos-game-check/references/tiktok-fixed-adaptation.md#2-看广告复活结算-x214-款)。

- 有失败/一局中断的游戏：失败时弹出复活，主按钮 **Watch Ad to Revive**（激励视频），旁边是不看广告的退出（显示结算或回首页）。看完才复活，取消、失败、超时不复活、可再选退出；原游戏已有的付费复活保留原样。
- **没有失败状态的游戏也加**（按 MusicSlice v30 的做法）：加一条能量条，失误扣能量（v30：漏切扣 8，切到炸弹扣 12，切中回 3），能量耗尽时暂停并弹出复活；复活后从暂停处继续。不改关卡、曲目和计分规则。
- 复活和结算 x2 走同一个平台包 `RewardedService.js`；复活弹窗打开时局内物理、计时、生成都停（`L-MODAL-PAUSE`）。
- 实施和检查按 [复活审查](../../remake-ads/references/rewarded-revive-and-help-layout.md)（英化一律加，不再审要不要加；页尾的小型教程英化不做）和 [一局结束：每屏一个视频按钮](../../remake-ads/references/end-flow-one-video.md)。
- 复活弹窗有 Home（回首页，清理和结算页一样），看广告加载中不能点。

