> 2026-10-24：本页仅供历史实现溯源；所有游戏排行榜均按[分享与排行榜前置禁用](no-social-features.md)移除，不按本页新建或保留。

# 排名系统（Weekly League）：只在重塑里加

> 此页仅用于用户明确启用/保留的兼容扩展，默认项目不加入、不主动询问。先读 [融合边界](fusion-policy.md)。下文设计建议不能代替授权。

用户 2026-10-21 定：**排名系统只在重塑游戏里考虑，英化游戏不增加任何排名系统**（原游戏自带且有实际功能及当前证据的排名才可保留，只英化、按[明令禁止的UI](cute-casual-style.md#九明令禁止的ui用户-2026-10-20)和[页面不能单调](page-richness.md)改页面，不改它的算法）。

做法：用固定的算法模拟一个"周联赛"。玩家每打一局名次都会上升，前期升得快、后期慢；别人的分数跟着同比例上涨；每局大约 5%～6% 的概率被反超、掉几名；永远到不了第 1 名。每周重置、分段位。周奖励先发 10 款排名专属皮肤，10 款发完后只发金币。

**算法写死在 `assets/league/LeagueSim.ts`，游戏里原样复制，AI 只改 `league-config.json` 的数值**，`audit_league.py` 会比对文件指纹并模拟几万局来检查。

## 一、哪些游戏加：开工时回答四个问题

| 问题 | 字段 | 说明 |
|---|---|---|
| 每局有没有明确的输赢或得分？ | `win_lose_or_score` | 过关/失败、分数、用时都算 |
| 有没有一个能一直涨的数？ | `ever_growing_number` | 已通关数、星星、经验/等级、战力、最高分 |
| 内容撑得住吗？ | `enough_content` | **至少 30 关**，或者是无尽/计分模式 |
| 这个数在玩家之间比较有意义吗？ | `comparable` | 大家玩的是同一套关卡/规则 |

四个问题仅检查用户已明确选择排名后的适用性；不是自动启用条件。默认 none/skip。明确启用时记录 decision=add 和实际授权依据，技术不适用时说明冲突。

| 游戏类型 `game_type` | 一般结论 | 用什么排 |
|---|---|---|
| `level_progression` 闯关类、关卡多（三消、停车、螺丝、方块、解谜≥30关） | 加 | 通关得分（过关＋星星） |
| `xp_level` 有经验值/等级 | 加 | 每局获得的经验 |
| `power_growth` 有战力（养成、合成、放置） | 加 | 每局增长的战力/产出 |
| `endless_score` 无尽、跑酷、计分 | 加 | 每局分数 |
| `time_attack` 计时挑战（越快越好） | 加 | 用时（越短得分越多） |
| `few_levels` 关卡少于 30 关 | 不加 | 几天就打完，排名停住反而显得假 |
| `relaxing_no_fail` 纯休闲无输赢（涂色、装扮、沙画） | 不加 | 没有能比的数 |
| `one_off_content` 一次性内容（找不同、脑筋急转弯） | 关卡≥30 才加 | 通关数 |
| `other` 其他 | 按四个问题 | |

判断写进 `docs/league/decision.json`（重塑开工、写规格时就写；启动包里写了就照抄核对）：

```json
{
  "schema": "league_decision.v1",
  "decision": "add",
  "game_type": "level_progression",
  "metric": "levels",
  "answers": {"win_lose_or_score": true, "ever_growing_number": true, "enough_content": true, "comparable": true},
  "evidence": {
    "win_lose_or_score": "GAME_DESIGN.md: clear the board to win, 1-3 stars",
    "ever_growing_number": "levels cleared and stars",
    "enough_content": "levels/ has 120 levels",
    "comparable": "everyone plays the same levels"
  }
}
```

英化的项目也写这个文件，只能写 `"decision": "none"`（不加），或者 `"keep_original"`（原游戏自带排名，写 `notes` 说明在哪、没改算法）。

## 二、怎么做（固定做法）

1. **复制算法**：把本 Skill 的 `assets/league/LeagueSim.ts` 原样复制到游戏的 `assets/scripts/league/`（一个字都不改；Cocos 2.4 和 3.x 都能用）。
2. **写配置**：复制 `assets/league/league-config.json` 到 `assets/resources/config/`，按第三节调数值。
3. **写接入代码**（另写一个文件，比如 `LeagueService.ts`）：
   - 第一次打开时生成一个随机种子存进存档：`createState(cfg, seed, Date.now())`；
   - 游戏启动和每次回到前台：`openLeague(state, cfg, now)`，保存返回的 state；`pending` 不为空就弹上周结算；
   - 每局结束（赢或输都调）：`recordRound(state, cfg, {win, stars, score}, now)`，保存；把返回的 `result`（升了几名、超过了谁）显示在结算页；
   - 排名页：`leaderboard(state, cfg, now)` 给出要显示的行、倒计时、离上一名差几分、下一款排名皮肤；
   - 领奖按钮：`claimSettlement(state)`，把返回的金币和皮肤加进钱包和皮肤系统，**钱包和排名状态一起存**（同一次保存，避免重复发或丢奖励）。
4. **计分方式**（`gain.mode`）：
   - 闯关类用 `level`：过关得 `win` 分，每颗星加 `stars_bonus`；
   - 经验、战力、无尽计分用 `score`：`score_ref` 填普通一局的典型值（中等关的经验/战力增长/中位数分数），得分按比例算，限制在 `score_min`～`score_max` 倍之间；
   - 计时挑战用 `time`：用时越短得分越多；
   - 输了也有一点分（`lose_factor`），所以每一局都会动。
5. **排名专属皮肤 10 款**：写进 `unlock_table.json`，`"unlock": "league"`，`ads`、`coins` 都是 0；只能从周结算获得，不在商店卖，不参加"看广告试用"。稀有度从低到高（例如 1–3 Rare、4–7 Epic、8–10 Legendary），按发放顺序排；美术和其他皮肤一样，按启动包美术方向做（重塑用明亮Q版）。卡片上标"League reward"和奖杯角标，未获得时写"Finish Top 1,000 in the Weekly League"。

## 三、参数（`league-config.json`，只改数值，算法不改）

| 参数 | 默认 | 允许范围 | 作用 |
|---|---|---|---|
| `pool_size` | 10000 | 1000–1000万 | 联赛总人数（模拟的） |
| `start_rank` | 9200 | 总人数的一半到总人数 | 每周开始时的名次（每周略有浮动 ±3%） |
| `best_rank` | 2 | 2–10 | **最好能到第几名；永远不是第 1** |
| `curve.half_points` / `curve.power` | 165 / 2.0 | >0 / 0.8–3 | 名次曲线：分数越多名次越前，**先快后慢**。half_points 越大越难升 |
| `min_step_above_rank` | 30 | ≥ best_rank | 名次在它后面时，每局（没被反超时）至少升 1 名 |
| `gain` | level，过关 10 分，每星 +2，输了 ×0.3 | 见第二节 | 一局得多少分 |
| `drop.chance` | 0.055 | **0.05–0.06** | 每局被反超、掉名次的概率（用户定 5%～6%）；前 `grace_rounds` 局不掉 |
| `drop.min_pct`/`max_pct`/`min`/`max` | 0.4%–1.5%，1–150 名 | ≤5% | 掉多少名（按当前名次的比例） |
| `others.beta` | 0.35 | 0–1，且 beta×power<0.8 | 别人的分数跟着你涨的比例；前几名一直在涨 |
| `others.jitter` | 0.06 | 0–0.2 | 每个对手分数的小差异，看起来更真 |
| `absence` | 离开 6 小时以上，每小时掉 0.2%，最多 5% | max_pct≤20% | 离开一段时间回来名次略降，想回来追 |
| `week.reset_weekday` / `reset_hour` | 1（周一）/ 0 点 | | 每周重置时间（玩家本地时间） |
| `tiers` | Bronze→Silver→Gold→Diamond→Champion，难度 1.0/1.4/2.0/2.8/3.8 | ≥3 档，难度不降 | 段位越高越难升（长期也是先快后慢） |
| `promote_top_rank` / `demote_from_rank` | 前 1000 升段，8000 名以后降段 | | 周结算时升降段位；没玩的那周不变 |
| `rewards` | 前10名 600、前100名 400、前1000名 200（都带皮肤），前5000名 80，其余 30 金币 | 名次越好金币不少 | 周奖励 |
| `league_skins` | 10 个 id | **正好 10 个** | 排名专属皮肤，按顺序发 |
| `skin_fallback_coins` | 300 | >0 | 10 款都有了，本该发皮肤时改发这么多金币 |
| `view` | 上面 6 名、下面 3 名、前 3 名 | | 排名页显示哪些行 |
| `avatars` | 12 | ≥6 | 对手头像图数量（Q版动物/角色头像，不用真人照片） |
| `calibration` | 一周 10 局 → 1000 名以后；40 局 → 100–2000 名；120 局 → 前 100 名 | | 检查用：不同玩家一周能到哪 |

默认值的实际效果（模拟）：第 1 局升 1500 名左右，10 局约 2,600 名，40 局约 500 名，120 局进前 100，几千局也只到第 2 名。一周玩 40 局左右能进前 1000 拿皮肤；段位升上去后要玩得更多。

调参只按用户的要求改（比如"再难一点"→加大 half_points 或 tiers 难度）；改完重跑 `audit_league.py`，模拟不过就不能用。

## 四、每周结算和奖励

- 每周一 0 点（玩家本地时间）开新一周：分数清零、名次回到 `start_rank` 附近、对手换一批。
- 新一周第一次打开游戏，弹**上周结算**：上周名次、段位升/降/不变、奖励（金币＋排名皮肤，带获得动画），按钮"Claim"。领一次就没有了；好几周没打开时，每一周的奖励都保留、分别发不同的皮肤。
- 奖励：上周名次落在哪一档就发哪档金币；档里带皮肤时发下一款还没拿到的排名皮肤；**10 款都拿到后只发金币**（多发 `skin_fallback_coins`）。
- 上周没玩：不发奖励、段位不变。
- 领奖不要求看广告。想加"看广告奖励翻倍"时按广告奖励规则单独做，不是必须。

## 五、页面（不能单调）

- **首页**：奖杯小图标（和其他功能一起排在下方那排，不占中间），角上显示当前名次或"!"（有待领奖励时）。
- **结算页**：在原有内容旁边加一个小的名次牌："#1,234 ▲56"，数字滚动动画；超过别人时一行小字"You passed SunnyFox27!"；被反超时"MochiPanda passed you!"（▼）。点名次牌进排名页。
- **排名页**（整页，不是小弹窗）：段位徽章和名称、标题"Weekly League"、倒计时"Ends in 2d 5h"、前三名领奖台（金银铜）、自己上面 6 名和下面 3 名的列表（头像、名字、分数，自己那行高亮并一直可见）、"离上一名还差 X 分"、底部下一款排名皮肤预览和"Top 1,000: League skin"、左上角 i 按钮打开规则弹窗。
- **规则弹窗**：几行说明怎么升名次、每周何时重置、奖励规则，**并写明"League rivals are computer players."**（检查会找这句话的意思）。
- 画风按明亮Q版：每行是彩色圆角条，前三名金银铜，段位徽章有配色。**禁止**大块白板/灰板、灰色细字、空白面板（你给的"Weekly Rankings"截图就是反面例子：大白头、一整块灰色空面板）。测试时 dump_ui 写 `"purpose": "league"`，`audit_page_richness.py` 要求至少 10 个名次/分数、页面用满 35% 以上。

## 六、诚实规则（防止误导玩家和平台审核）

榜单上的对手是模拟的，所以：

- 标题用中性的名字："Weekly League""Weekly Rankings""League"；**不写** National、Nationwide、Worldwide、Global ranking、"real players"、"players online"、"全国""真实玩家""在线人数"（检查会拦）。
- 不显示在线人数，不用真人照片，不用国旗。对手名字用算法生成的昵称（SunnyFox27 这类）。
- 规则弹窗写明对手是电脑玩家。
- 这条和用户的"模拟全国排名"要求并不冲突：玩法和感觉都一样，只是不冒充真人。是否符合 TikTok 当前审核规则以平台为准（本 Skill 不是平台规则的权威）。

## 七、检查

| 门禁 | 板块 | 查什么 |
|---|---|---|
| RANK-01 | 两个板块（英化只查"没加"） | `audit_league.py`：判断记录、算法未改、配置模拟（永远不是第1、5–6%掉名、每局都升、先快后慢、对手跟涨、排名页数据一致、重开一致、周结算10款皮肤后只发金币、只领一次、改时间、离开回来、多周未领、玩家档位校准）、10款皮肤在皮肤表里、文案不冒充真人、规则写明电脑对手 |
| RANK-02 | 只在重塑 | 浏览器实测七项：结算页名次变化、排名页、改到下周的结算弹窗只领一次、存档改成已有10款时只发金币、存档改到第2名附近打不到第1、关掉重开一致、规则弹窗；audit_league 判断为 add 时不能标不适用 |
| PAGE-01 | 两个板块 | 排名页不单调（见[页面不能单调](page-richness.md)） |

浏览器里改时间：`chrome_touch.py` 的 `init_js` 在页面加载前替换 `Date.now`（例如加 7 天）；改存档：`init_js` 里先写好 localStorage 里的排名存档（名次 3、已有 10 款皮肤等）再进游戏。

## 八、写进启动包

[启动包规范](../../cocos-game-from-starter/references/explicit-legacy-features.md#九weekly-league排名系统适合的游戏才加)第九节要求做启动包的 AI 在 `GAME_DESIGN.md` 写"Weekly League"一节：四个问题的答案和依据、结论 add/skip、用什么计分；`UI_PAGES.md` 列排名页、结算页名次牌、周结算弹窗、规则弹窗；`ECONOMY.json` 列 10 款 `unlock: league` 的皮肤。制作时照抄核对，和本页冲突以本页为准。
