# 明确选择的兼容玩法

仅在当前用户或项目权威规格明确选择后读取；附件历史内容不自动启用。默认统一模板见[融合政策](../../cocos-game-to-english/references/fusion-policy.md)。不得让默认模板和兼容模式同时约束同一经济字段；在模块决策中记录选用方式、依据、适用门禁和旧存档迁移。

- **收集与皮肤系统**（共用）一律按[收集与皮肤系统设计](../../cocos-game-to-english/references/rarity-unlock-design.md)：Common→Rare→Epic→Legendary 从低到高；五种解锁；广告最多 8 次；1 个广告＝中等难度一关的金币；没有完美通关送皮肤，旧项目已明确采用每 15/20 关限定关时，送皮肤的只有这些限定关（送只能在这关拿到的限定皮肤，或大量金币），并解锁新地图；下一关前弹"看广告试用"（前 2 关不弹）。数值写 `unlock_table.json`（门禁 ECON-01/02）。
- **排名系统 Weekly League**（只属于重塑，英化不加；用户 2026-10-21）：已明确选择且适合的游戏（闯关多、经验值、战力、计分）按[排名系统](../../cocos-game-to-english/references/ranking-league.md)做：算法 `LeagueSim.ts` 原样复制、只调 `league-config.json`；每局都升、先快后慢、别人同比例上涨、每局约 5%～6% 掉名次、永远到不了第 1；每周重置、分段位；周奖励先发 10 款排名专属皮肤，发完只发金币；标题不写 National/Worldwide/"真实玩家"，规则弹窗写明对手是电脑玩家。`audit_league.py`（RANK-01）＋浏览器实测（RANK-02）。
- **可选玩法**（共用，FEAT-00/01/02，用户 2026-10-22）：皮肤增益（不同皮肤不同加成，越稀有越高，最多 +50%）和七日签到（每天领一次，第 7 天是最大的大礼包，含金币、皮肤、星星/体力），用户要了才做；签到逻辑 `DailyCheckin.ts` 原样复制、只调配置；`audit_optional_features.py` 查。见[可选玩法](../../cocos-game-to-english/references/skin-bonus-and-checkin.md)。

## 兼容启动包字段

下列旧版规格只服务已经明确选择的兼容模式；不把它作为默认新项目数量或购买方式。价格、模式与迁移写入项目决策后，使用对应审计，不与默认模板双重校验。

## 六、ECONOMY.json：金币与收集（按这个格式）

```json
{
  "coins_per_level": 50,
  "coins_per_ad": 50,
  "items": [
    {"id": "skin_01", "group": "skin", "order": 1, "rarity": "common", "unlock": "free", "ads": 0, "coins": 0},
    {"id": "skin_02", "group": "skin", "order": 2, "rarity": "common", "unlock": "ads", "ads": 1, "coins": 0},
    {"id": "skin_lv20", "group": "skin", "order": 40, "rarity": "legendary", "unlock": "level", "level": 20, "condition": "clear", "ads": 0, "coins": 0},
    {"id": "map_02", "group": "map", "order": 2, "rarity": "rare", "unlock": "level", "level": 20, "condition": "clear", "ads": 0, "coins": 0}
  ]
}
```

**硬规则**：稀有度 common → rare → epic → legendary 从低到高；每组都要有 `ads`（只看广告）、`coins`（只用金币）、`ads_coins`（先看广告再付金币）、`ads_or_coins`（二选一）四种；**广告最多 8 次**；`coins_per_ad`（R）= 中等难度一关给的金币；价格按"广告单位"换算：common 1–2、rare 3–4、epic 5–6、legendary 7–8 个广告的价值，金币价 = 广告单位 × R；只有初始物品免费。**没有完美通关送皮肤**。**限定关的限定皮肤**写 `"unlock": "level", "level": 20, "condition": "clear"`，`ads` 和 `coins` 都是 0（买不到），稀有度 rare/epic/legendary，并写在关卡表那一关的 `reward` 里。新地图在限定关解锁（`map` 组 `"unlock": "level", "condition": "clear"`）。货币名按题材（`"currency": "Pearls"` 写在最上面）。

**要皮肤增益时**：每个皮肤写 `"bonus": {"type": "coins", "pct": 18}`，越稀有越高（common 5–10、rare 11–20、epic 21–32、legendary 33–50），最多 50。**要七日签到时**：签到送的皮肤写 `"unlock": "checkin"`，并在 `GAME_DESIGN.md` 列 7 天奖励（第 7 天最大，含金币、皮肤和星星/体力）。

**加排名时**（第九节结论是 add）：再列 10 款排名专属皮肤，`"unlock": "league"`、`ads` 和 `coins` 都是 0，稀有度从低到高（例如 1–3 rare、4–7 epic、8–10 legendary），id 用 `league_skin_01`…`league_skin_10`。它们只能从每周排名奖励获得，不在商店卖。

**由你决定**：有哪些皮肤/收集物、各几件、名字和稀有度分配（含 10 款排名皮肤的造型）。


## 九、Weekly League：排名系统（适合的游戏才加）

在 `GAME_DESIGN.md` 写一节"Weekly League"，回答四个问题并写依据：

| 问题 | 例 |
|---|---|
| 每局有没有明确的输赢或得分？ | 消完棋盘过关，1–3 星 |
| 有没有一个能一直涨的数？ | 已通关数和星星 / 经验 / 战力 / 最高分 |
| 内容撑得住吗？（至少 30 关，或无尽模式） | 120 关 |
| 这个数在玩家之间比较有意义吗？ | 大家玩同一套关卡 |

**四个都是"是"才加**（结论写 `add`），否则写 `skip`。适合的一般是：闯关类关卡多、有经验值/等级、有战力、无尽计分、计时挑战；不适合：关卡少于 30 关、纯休闲无输赢（涂色、装扮）。

结论是 add 时还要写：游戏类型（`level_progression`/`xp_level`/`power_growth`/`endless_score`/`time_attack`）、每局怎么计分（过关＋星星，或者经验/战力/分数，并写普通一局的典型数值）、排名页和结算页名次牌放哪（`UI_PAGES.md`）、10 款排名皮肤（`ECONOMY.json`）。

**硬规则**（启动包不能改，制作方的 Skill 会按固定算法做）：每局都会升一点、前期升得快后期慢、别人的分数同比例上涨、每局约 5%～6% 的概率被反超、永远到不了第 1 名；每周重置、分段位（Bronze→Silver→Gold→Diamond→Champion）；周奖励先发 10 款排名皮肤，发完只发金币；标题用"Weekly League"这类中性名字，**不写** National、Worldwide、"real players"、在线人数；规则弹窗写明对手是电脑玩家。**不要**自己设计排名算法或公式。

