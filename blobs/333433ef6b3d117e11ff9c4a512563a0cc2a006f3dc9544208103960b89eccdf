# 英化第 2 阶段：原版平台代码改线（rewire-ads，生成时预防 P01 / P14 / P10）

**生成时必须用 `rewire-ads` 改原版广告和加桌面/回访奖励，别手写桥。** 以前第 2 阶段靠 AI 逐个文件把原版广告管理器改成调 RewardedService，漏一个分支或拷了旧版 RewardedService.js，广告关掉后就锁死、超时口径不对（普查：广告关后锁死 50 款、超时不对 32 款）；加桌面/回访奖励写死在原版里（切水果 `REWARD = 10` 钻）。

## 顺序（第 1 阶段盘点之后、改英文之前）

1. `python3 <skills>/remake-core/scripts/tiktok_finalize.py inventory --project <英化工程>`
   `docs/english/platform-inventory.json` 除了原来的 `categories`，多三张表：
   - `rewire_todo`：每个调用点一行（`kind`、`file`、`line`、`function`、`shape`、`auto`、`why`、`fix`）。
     - `ad`：建或放激励视频的函数。`auto: true` 的由 rewire-ads 改。
     - `growth`：`new MissionFlow({...})` 里写死的奖励（`auto: true`）；原版自己调 `addShortcut` / `startEntranceMission` 等（`auto: false`，删掉，换 `HomeGrowthEntries.js`）。
     - `save_best`：比最高分再写存档的函数，改用 `SaveStore.best(key, value)`。
     - `save_grant`：加奖励再写存档的函数，改用 `SaveStore.grant(delta, onDone)`。
   - `delete_list`：分享、互推（更多游戏、跳小游戏）、排行入口，第 2 阶段第一步照单删（规则见 [fixed-entries.md](../../cocos-game-to-english/references/fixed-entries.md)「删除：分享、更多游戏、排行榜」）。
   - `kit_copies`：平台包同名模块放在别处或是旧文本（拇指弹球 `assets/platform/RewardedService.js`），`sync` 会换回标准件。
2. `python3 <skills>/remake-core/scripts/tiktok_finalize.py rewire-ads --project <英化工程>`
   - 认得的广告函数保留原名和原参数，函数体换成调生成的 `assets/tiktok-platform/AdBridge.js`；桥里每个 `B['<文件>.<函数>']` 调 `RewardedService.request()`（15 秒前台、开播后不计时、看完才发奖、迟到不发奖、同时只一个）。认得的形状：回调式（成功/失败两个回调，或一个回调传 true/false）、Promise 式（resolve(true/false)，或 resolve()/reject()）、事件式（emit 成功/失败事件）。只建广告对象的函数换成 `AdBridge.inertAd`，游戏代码里就不再有 `createRewardedVideoAd`。
   - `new MissionFlow({...})` 里只加一种货币的写死数额换成 `AdBridge.growthAmount()`（= `PlatformConfig.growthReward()`，5B），`rewardText` 跟着换，没人用的常量删掉。
   - 改前的文件备份在 `.tiktok-kit/rewire-backup/`，记录在 `.tiktok-kit/rewire-ads.json`；跑完自动重写 inventory，剩下的 `rewire_todo` 就是要手改的。跑两次结果一样。
   - 接着跑 `tiktok_finalize.py sync`（装 RewardedService.js、PlatformConfig.js，挪走同名旧件）。
3. 手改 `rewire_todo` 里 `auto: false` 的每一行，改完再跑一次 inventory，直到只剩 `save_*`（等 SaveStore.grant/best 发版后照改）。

## 不自动改的（列在 rewire_todo，`why` 写原因）

- Cocos 3.x：`AdBridge.js` 是 2.4 写法；手改成 `globalThis.TikTokKit.RewardedService`、`TikTokKit.PlatformConfig.growthReward()`。
- 返回 `{promise, cancel}` 句柄的（埃及宝石 `HexPlatform.rewarded`）、Promise 返回结果对象的、回调参数不清楚的（数字码、多个回调）、成功回调带参数的、不在具名函数里的。
- 加桌面/回访奖励不是一种货币（BlockMaze 给三种道具），或数额不是一个常量。

`AdBridge.js` 是生成文件，别手改；改游戏代码或生成器后重跑 `rewire-ads`。出包门禁（A1、G1k、ad_regression）照旧拦，这一步只是让问题在第 2 阶段就消失。测试：`remake-core/scripts/test_tiktok_rewire.py`（夹具在 `scripts/fixtures_rewire/`，真实游戏文件原样）。
