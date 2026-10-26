# 搜索关键词库（休闲 / 益智 / Q 版可爱风）

素材站基本都是英文检索，下面全部用英文。用法：**主题词 + 用途词**组合搜索，比只搜用途词结果更贴合游戏。
`needs.csv` 的 `keywords` 列用 `|` 分隔，脚本每个 ID 取前两个去搜。

## 1. 背景音乐（BGM）

**通用（先搜这些）**
`cute game music` · `casual game music loop` · `puzzle game music` · `happy loop` · `playful background music`
`cozy game music` · `light hearted` · `whimsical` · `bubbly` · `cheerful kids music` · `funny upbeat`

**按乐器（决定听感，最好用）**
`ukulele happy` · `marimba playful` · `xylophone cute` · `glockenspiel` · `pizzicato strings funny`
`music box` · `kalimba` · `whistle happy` · `toy piano` · `bells cheerful` · `acoustic guitar light`

**按游戏主题（主题词 + `music`）**

| 游戏主题 | 搜索词 |
|---|---|
| 糖果 / 甜品 | `candy`, `sweet`, `bakery`, `bubblegum pop` |
| 海洋 / 水 | `ocean`, `beach`, `tropical`, `island`, `steel drum` |
| 森林 / 动物 | `forest`, `animal`, `nature cute`, `woodland` |
| 农场 / 种植 | `farm`, `country cute`, `harvest`, `banjo happy` |
| 宠物 / 猫狗 | `pets`, `kitten`, `puppy`, `lovely` |
| 厨房 / 做饭 | `cooking`, `kitchen`, `cafe`, `jazzy light` |
| 太空 / 科幻（可爱） | `space cute`, `synth playful`, `retro future light` |
| 魔法 / 童话 | `fairy tale`, `magic cute`, `enchanted`, `celtic light` |
| 节日 | `christmas jingle bells`, `halloween cute`（不要 scary） |
| 像素 / 复古 | `chiptune happy`, `8 bit cheerful`, `retro arcade loop` |
| 解压 / 放松 | `relaxing lofi`, `calm piano`, `chill cozy` |

**胜利 / 失败短音乐（jingle）**
胜利：`level complete jingle` · `victory jingle` · `success fanfare short` · `win stinger` · `achievement`
失败：`game over jingle` · `fail jingle cartoon` · `lose trombone`（俏皮款）· `oops` · `sad trombone`（慎用，可能太夸张）

## 2. 音效（SFX）

| 用途 | 搜索词 |
|---|---|
| 按钮点击 | `ui click`, `button pop`, `soft click`, `tap`, `bubble click`, `wooden click` |
| 返回 / 关闭 | `ui back`, `cancel click`, `close pop` |
| 弹窗 | `popup`, `ui appear`, `whoosh pop`, `notification` |
| 选中 / 拿起 | `select pop`, `pick up`, `pop`, `blop` |
| 放下 / 放置 | `place`, `drop wood`, `tock`, `plop`, `thud soft` |
| 交换 / 滑动 | `swap`, `swish`, `slide`, `whoosh short` |
| 消除 / 匹配 | `match`, `clear`, `chime`, `pop sparkle`, `bubble burst`, `glass ting` |
| 连击 | `combo`, `ding`, `xylophone note`, `marimba note`, `bell hit` |
| 无效操作 | `error soft`, `wrong cartoon`, `boing`, `negative`, `bonk` |
| 提示 | `hint`, `sparkle`, `twinkle`, `magic shine` |
| 洗牌 | `shuffle cards`, `tiles shuffle`, `rattle` |
| 道具 | `power up`, `magic spell`, `booster`, `level up` |
| 大消除 | `bonus`, `sparkle burst`, `confetti`, `firework cute` |
| 金币 | `coin`, `collect`, `pickup`, `gem`, `cash register cute` |
| 结算星星 | `star`, `twinkle`, `bell ding`, `reward` |
| 奖励 / 开箱 | `reward`, `chest open`, `unlock`, `gift`, `treasure` |
| 倒计时 | `clock tick`, `timer tick`, `countdown beep` |
| 时间到 | `time up`, `alarm soft`, `bell end` |
| 关卡开始 | `ready go`, `level start`, `whoosh chime` |
| 扣生命 | `lose life`, `heart break cartoon`, `hurt cute` |
| 转盘 | `wheel spin`, `roulette tick`, `slot reel` |

**质感修饰词（加在前面）**：`cute` · `cartoon` · `soft` · `bubbly` · `light` · `squishy` · `jelly` · `toy` · `wooden` · `glass`

## 3. 要避开的词

`epic` · `dark` · `horror` · `scary` · `battle` · `war` · `cinematic trailer` · `heavy` · `metal` · `gore` · `aggressive` · `dubstep` · `distorted`

这些在索引里会被打上 `dark` 标签并大幅降分。

## 4. 提高命中率的技巧

- 先用**乐器词**找 BGM，比用心情词（happy）准得多。
- 同一个作者 / 同一个包里挑齐一整套音效，再搜下一个包补缺。`search_index.py` 会自动给“覆盖需求最多的包”加分。
- itch.io 搜 `music pack` / `sfx pack` 加主题词，常常一个包就够整个游戏用。
- Pixabay 搜索后按 “Most downloaded” 排序，热门曲质量更稳（但撞曲概率也更高）。
