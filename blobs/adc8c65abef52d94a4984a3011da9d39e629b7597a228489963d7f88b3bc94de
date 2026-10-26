---
name: game-audio-library
description: 休闲/益智小游戏的音乐与音效：从正规免费可商用素材库下载到本机共用音效库、自动质检打分、自动选择、统一响度加工、生成配置和授权记录，并提供 Cocos 2.4 / 3.x 播放代码。音频线做新游戏音频、替换不合格音频时使用；Windows 与 macOS 通用。
---

**默认输出验收（R09）**：按[实际互动与音频输出](../cocos-tiktok-package-check/references/drag-audio-postconditions.md)在声音接入后交试玩前主动测音乐/音效的实际输出与音量、开关及音频失败恢复，不等用户报错；单个可选片段失败不得阻断整套音频。素材响度和播放参数不等于游戏有声音。


# 游戏音频模块（休闲 / 益智小游戏）

适用：TikTok 国际版小游戏 · Cocos Creator 2.4 和 3.x · Windows 与 macOS。
负责：**获取素材 → 质检 → 自动选择 → 加工 → 接入代码 → 授权记录**。门禁 `AUDIO-01`（开关与音量）、`AUDIO-02`（来源与授权）直接用这里的产物检查。

## 0. 给 AI 的执行规则（先读）

- **所有步骤用 `scripts/` 里的现成脚本，不要自己重写。** 脚本出错就改脚本本身，改完继续。
- **默认自动选择**（用户决定）：直接跑一条命令，不等用户试听。汇报里写一句"音频为自动选择，建议有空时试听确认"。用户明确说要自己挑时才加 `--listen`。
- **不用 AI 或代码合成音乐/音效**，只用第 2 节的正规素材库。只下载可商用素材；授权由脚本判断和记录，不合格自动跳过。
- 命令写法：macOS 用 `python3`，Windows 用 `py -3`（下文统一写 `python`）。
- **英化＋优化**：不下载、不换声音文件；只用本模块的播放管理代码（`GameAudioManager`）给原声音文件接上两类开关和十格音量（见主 Skill 的 two-boards.md）。
- **重塑附了源码、原来已有音频时**：先跑主 Skill 的 `audit_audio_sources.py` 看现有音频；合格的保留，在 `docs/audio/sources.md` 写"原游戏自带"（启动包给的写"启动包提供"）；只为缺的、不合格的 ID 跑本模块（`needs.csv` 只留这些 ID）。工程已有能用的音频管理代码且满足 AUDIO-01 时，加 `--no-code`，只换音频文件和配置。

## 1. 总体原则

- 风格和画面一致：**明亮、可爱、轻快、Q 弹**。不要沉重、阴暗、史诗、恐怖。
- 整个游戏的音效**尽量来自同一个素材包**，BGM 尽量同一作者——听感统一比单个音效好听更重要（脚本会自动给覆盖最多的素材包加分）。
- BGM 比音效小声；所有音效响度统一；不能刺耳（玩家会听几百遍）。
- 音乐和音效**两个独立开关 + 两个独立音量（0–10 共 11 档，每档 10%）**，设置自动保存。
- 包体：音效 ≤ 50KB，BGM ≤ 1.6MB，音频合计 ≤ 5MB（以 TikTok 小游戏当前官方限制为准）。

## 2. 一次性准备（每台电脑只做一次，所有游戏共用）

```
python scripts/setup.py
```

它会按系统装好 ffmpeg（macOS 用 Homebrew，Windows 用系统自带的 winget；**Windows 装完要关掉终端再开一个**）和 Python 依赖，并建立素材库目录。优先安装随本 Skill 单独提供的离线音效库 ZIP，方法见 [离线库安装与分享](references/portable-library.md)。安装器会校验素材并登记当前电脑的本地路径；以后更新 Skill 保留该库，不必重复下载。没有离线库时，第一次跑流水线发现库为空，会按原流程下载免登录的 1 级素材包，之后所有游戏共用。

可选（不做也能用）：
- Freesound 免费 API key（https://freesound.org/apiv2/apply/）设成环境变量 `FREESOUND_API_KEY`（Windows：`setx FREESOUND_API_KEY 你的key`；macOS：写进 `~/.zshrc`），候选不够时多一个来源。
- 需要登录的站（Pixabay、itch.io 等）：`python scripts/setup.py --browser`，再 `python scripts/browser_fetch.py login pixabay`，**由用户本人在弹出的浏览器里登录一次**。自动模式不依赖它们。
- Sonniss 大合集：用 qBittorrent 只勾 UI / Cartoon / Magic / Interface 文件夹，放到素材库 `raw/sonniss/<包名>/`，再用 `add_credit.py` 登记授权。
- 任何手动下载的素材都要用 `add_credit.py` 登记授权，否则标为 unknown，不会被选用。

素材库选择顺序：`GAME_AUDIO_LIB` 环境变量 → 安装器登记的 `~/.game-audio-library/library.json` → `用户目录/GameAudioLibrary`。配置只记录当前电脑的安装目录，不随 Skill 写死作者路径。

```
GameAudioLibrary/
├── raw/<来源>/<素材包>/...   原始文件
├── auth/<网站>/             浏览器登录状态
├── index.csv                索引：标签、时长、响度、质量分、授权
├── credits_master.csv       每个文件的来源和授权
└── skipped.csv              被跳过的素材和原因
```

## 3. 每个新游戏：一条命令

**先改需求表**：第一次运行会把 `templates/needs_casual_puzzle.csv` 复制到 `<工程>/audio_work/needs.csv`。AI 按这个游戏的玩法：删掉用不到的 ID（没有倒计时就删 `sfx_timer_tick`、`sfx_time_up`），加上特有的 ID（命名见第 7 节），按主题改 `keywords`（参考 `references/keywords.md` 的"主题词 + 乐器词"）。

```
python scripts/audio_pipeline.py --project <游戏工程> --theme <实际题材> --no-fetch
```

自动完成：素材库为空时下载 1 级素材包 → 建索引打分 → 找候选 → 候选不够自动上网补（Openverse 免 key；有 key 时加 Freesound）→ **自动选择** → 加工 → 生成配置和授权记录 → 按工程的 Cocos 版本复制播放代码（已有同名文件不覆盖）。

已安装离线库时优先使用 `--no-fetch`：全流程仅用本机素材，空库或缺工具会明确停止，不偷偷下载或安装。确需补库时按下面原站下载方式另补，再重建索引。

常用参数：`--theme` 实际题材；`--redo` 重新选；`--no-fetch` 不上网；`--style retro` 像素/复古风；`--engine 2.4|3.x` 认不出版本时手动指定；`--no-code` 不复制播放代码；`--listen` 用户要自己试听时生成试听页（导出 `selection.csv` 后再跑一次不带 `--listen` 的命令）。

重活排队：在游戏制作中运行时，用主Skill的 `scripts/heavy_lock.py run --project <工程> --name "音频流水线" -- python scripts/audio_pipeline.py --project <工程>`，避免和同一个游戏的构建同时写文件（不同游戏互不等待）。素材库索引默认只用一半CPU核心。

产物：

| 文件 | 说明 |
|---|---|
| `assets/resources/audio/sfx/*.mp3`、`bgm/*.mp3` | 加工好的音频 |
| `assets/scripts/audio/GameAudioConfig.ts`（3.x）/ `.js`（2.4） | 自动生成，不要手改 |
| `assets/scripts/audio/GameAudioManager`、`GameAudioButton` | 播放代码（2.4 是 .js，3.x 是 .ts） |
| `docs/audio/credits.csv` | 每个游戏内音频文件的来源与授权（门禁 AUDIO-02 读它） |
| `docs/audio/CREDITS.txt` | 需要署名的素材；保留为项目授权记录，不生成 Credits 界面；强制玩家可见署名按许可另选展示位置或更换素材 |

候选还不够时的补充方式：

```
python scripts/fetch_openverse.py "ukulele" --category music --n 10
python scripts/fetch_freesound.py "bubble pop" --n 10
python scripts/fetch_oga.py --type music --tag happy --tag cute --n 8
python scripts/browser_fetch.py search pixabay-music "playful marimba"   # 需要先登录
python scripts/build_index.py          # 补完必须重建索引
```

下载规则（已内置）：登录站点每次间隔 5 秒、单次最多 30 个；下过的链接不重复下；不可商用的跳过并记进 `skipped.csv`。遇到人机验证或要登录：**自动模式下直接跳过这个网站**，改用免登录的来源，不停下、不问用户，在最后汇报里提一句；只有用户说"我要试听"或主动要求用这个网站时，才请用户在弹出的浏览器里手动过一次，不要尝试绕过。

## 4. needs.csv 字段

| 列 | 含义 |
|---|---|
| `id` | 代码里用的名字，如 `sfx_match` |
| `type` | `bgm` / `jingle` / `sfx` |
| `required` | `yes` 必须有；`no` 可选（代码里有自动替代，见第 8 节） |
| `variants` | 需要几个版本 |
| `gen` | `pitch_var`：1 个素材生成 N 个微变调版本随机播放；`pitch_steps`：生成 N 级逐级升半音（连击、星星）；`loop`：BGM 无缝循环处理 |
| `tags` | 本地匹配用的标签（`click`、`pop`、`coin`、`win`、`lose`、`invalid`、`whoosh`、`sparkle`、`place`、`swap`、`match`、`star`、`tick`、`unlock`、`popup`、`close`、`jingle`、`music`） |
| `keywords` | 上网搜索用的英文词，`|` 分隔 |
| `max_sec` | 音效最长秒数；BGM 截取长度 |
| `volume` | 这个声音的音量系数（写进配置） |
| `notes` | 说明 |

## 5. 背景音乐（BGM）

| ID | 场景 | 必需 | 说明 |
|---|---|---|---|
| `bgm_menu` | 主界面 / 选关 | 是 | 轻松、欢迎感，60–120 秒循环 |
| `bgm_game` | 游戏中 | 是 | 轻快但不抢注意力，长时间听不烦 |
| `bgm_game_2` | 游戏中轮换 | 否 | 奇偶关交替，减少听腻 |
| `jingle_win` | 过关 | 是 | 欢快上扬，2–5 秒 |
| `jingle_lose` | 失败 | 是 | 俏皮柔和，2–4 秒，不要沮丧 |

风格：90–125 BPM；木琴、马林巴、尤克里里、拨弦、钟琴、口哨、玩具钢琴、轻电子；纯音乐不要人声；不要重低音、强鼓点。

## 6. 音效（SFX）

标准清单在 `templates/needs_casual_puzzle.csv`：界面（点击、返回、弹窗、开关、锁定）、玩法（选中、放置、交换、消除、连击、无效、提示、洗牌、道具、大消除）、奖励（金币、星星、奖励、解锁、转盘）、状态（倒计时、时间到、关卡开始、扣生命）。

- 按下立刻出声（脚本切掉开头静音）。
- 高频音效做 3 个微变调版本随机播放，不连续重复。
- 连击 5 级逐级升调；结算星星 3 级升调。
- 无效操作用柔和的 boing / bonk 类卡通音，不用刺耳的 buzzer。
- 防刷屏：同一音效间隔 ≥ 50ms，同时最多 6 个；多个金币间隔 60ms 依次播放。

## 7. 命名规则

全小写、下划线。BGM 以 `bgm_` 开头，短音乐 `jingle_`，音效 `sfx_`。多版本自动命名 `_1 _2 _3`。代码里**只用 ID，不写文件路径**。

## 8. 质量与授权标准（脚本自动执行）

**质检打分**（`build_index.py`，0–100）：几乎没声音、偏小声、削波爆音、峰值顶满、采样率 < 32k、码率 < 96k、开头静音 > 0.3 秒、超长文件、风格偏暗、无授权记录——各自扣分。

**授权**（`common.py` 的 `classify_license`，主 Skill 的 `audit_audio_sources.py` 用同一套规则）：允许 CC0 / 公有领域 / Pixabay / Mixkit / Kenney / Sonniss 等免署名授权，以及 CC-BY / OGA-BY / incompetech / soundimage / ZapSplat 等需署名授权；**拒绝** NC、ND、仅个人使用、Editorial、CC-BY-SA（确需时加 `--allow-sa`）、来源不明。不确定的一律不用。来源清单见 `references/sources.md`。

**加工**（`process_audio.py`）：

| 类型 | 处理 | 响度 | 格式 | 目标大小 |
|---|---|---|---|---|
| 音效 | 去首尾静音、去 60Hz 以下隆隆声、2ms 淡入 / 12ms 淡出、限幅 | -16 LUFS | mp3 单声道 96k | ≤ 50KB |
| 短音乐 | 同上，60ms 淡出 | -16 LUFS | mp3 立体声 128k | ≤ 150KB |
| BGM | 截取 → 尾部交叉淡入开头（无缝循环）→ 限幅 | -20 LUFS | mp3 立体声 128k | ≤ 1.6MB |

音频超预算时：减少 BGM 数量或缩短 `max_sec`；确需远程加载时按主 Skill 的分包/远程资源规则处理并实测。

## 9. 接入代码

`audio_pipeline.py` 已把代码放进 `assets/scripts/audio/`。启动场景调用一次：

- **3.x**：`GameAudioManager.init(); GameAudioManager.instance.preload(); GameAudioManager.instance.playBGM('bgm_menu');`
- **2.4**：`var GameAudio = require('GameAudioManager'); GameAudio.init(); GameAudio.instance.preload(); GameAudio.instance.playBGM('bgm_menu');`

| 位置 | 调用（`am` = `GameAudioManager.instance`） |
|---|---|
| 每个界面打开时 | `GameAudioButton.attachAll(this.node)`（自动给所有按钮加点击音；back/close 用返回音） |
| 弹窗基类 | 打开 `am.playSFX('sfx_ui_popup_open')`，关闭 `am.playSFX('sfx_ui_popup_close')` |
| 进入关卡 | `am.playLevelBGM(level)`，`am.playSFX('sfx_level_start')` |
| 选中/放置/交换/消除 | `am.playSFX('sfx_select' / 'sfx_place' / 'sfx_swap' / 'sfx_match')` |
| 连击 | `am.playCombo(comboCount)` |
| 无效操作 | `am.playSFX('sfx_invalid')` |
| 获得金币 | `am.playCoins(n)` |
| 胜利 / 失败 | `am.playJingle('jingle_win' / 'jingle_lose')`；结算界面出现后 `am.playBGM('bgm_menu')` |
| 结算星星 | 每颗星动画时 `am.playStar(1/2/3)` |
| 激励视频 | 请求展示前 `am.pause('ad')`；广告关闭（完成、取消、出错都算）后 `am.resume('ad')`；发奖时 `am.playSFX('sfx_reward_ad')` |
| 暂停菜单 | 打开 `am.pause('menu')`，关闭 `am.resume('menu')`（是否暂停音乐按游戏设计） |
| 设置面板 | `setMusic(on)`、`setSFX(on)`；点格用绝对档位 `setMusicLevel(0–10)`、`setSFXLevel(0–10)`；减/加用 `decreaseMusicLevel()` / `increaseMusicLevel()`、`decreaseSFXLevel()` / `increaseSFXLevel()`。显示读 3.x 的 `musicOn / sfxOn / musicLevel / sfxLevel`，2.4 的 `isMusicOn() / isSFXOn() / getMusicLevel() / getSFXLevel()`；均为当前有效状态，OFF/0档为0，非零记忆另存，ON恢复，按[声音状态交叉检查](../cocos-game-to-english/references/common-game-components.md)验收 |

切后台/回前台由代码自动处理。暂停按"原因"记录：看广告时切后台再回来，广告没关之前不会响。可选 ID 没做时自动用相近音效代替（如 `sfx_ui_back` → `sfx_ui_click`），代码可以放心调用标准 ID。

保存是否成功读 3.x 的 `settingsSaved` 或 2.4 的 `isSettingsSaved()`；失败时当前设置仍立即生效，界面应说明仅本次运行有效并提供 `retrySaveSettings()` 重试，不能显示已永久保存。流水线仍只复制不存在的管理代码；已有工程须在当前授权内对照接口合并修复，不覆盖已有适配或声音配置。模板合同用 `node scripts/test_audio_manager_contracts.cjs --typescript <本机已安装的typescript/lib/typescript.js>` 验证；这是管理模块边界验证，游戏实际入口与听感仍走原验收。

`docs/audio/CREDITS.txt` 保留署名及许可记录，不生成 Credits/关于/制作人员界面。优先选择无需游戏内署名的素材；确有强制玩家可见署名义务时，按许可另选展示位置，无法满足时更换素材。

## 10. 验收清单（对应 AUDIO-01 / AUDIO-02）

- [ ] 第一次点击后 BGM 开始；切场景淡入淡出，没有两首 BGM 叠在一起
- [ ] BGM 循环处听不出接缝
- [ ] 所有按钮有点击音，按下立刻出声
- [ ] BGM 明显比音效小，没有刺耳或特别响的音效
- [ ] 快速连点不爆音；高频音效不机械重复
- [ ] 连击越连音越高；星星逐个升调
- [ ] 胜利/失败 jingle 正常，结算后 BGM 恢复
- [ ] 音乐、音效开关独立；两个 11 档音量独立；关掉开关不丢音量档位；重启后都保持
- [ ] 切后台、看激励视频时静音，回来恢复；看广告时切后台再回来不会提前出声
- [ ] 音频总大小在预算内（看 `process_audio.py` 输出）
- [ ] 主 Skill `scripts/audit_audio_sources.py --project <工程>` 通过；`CREDITS.txt` 已保留，许可署名义务已满足，玩家端无 Credits 页面或入口

## 11. 常见问题

| 情况 | 处理 |
|---|---|
| 提示缺 ffmpeg | `python scripts/setup.py`；Windows 装完要重开终端 |
| 认不出 Cocos 版本 | 加 `--engine 2.4` 或 `--engine 3.x` |
| 第一次运行很慢 | 正在下载 1 级素材包和建索引，只有第一次这样 |
| 公司网络/代理打不开素材网站 | 换网络重跑；或让用户手动下载素材包放进 `raw/<来源>/<包名>/`，再用 `add_credit.py` 登记 |
| 浏览器下载找不到按钮 | 看素材库 `auth/debug/` 截图，改 `browser_fetch.py` 里的 `PRE_CLICK` / `DL_TEXT` |
| Pixabay 人机验证 | 自动模式跳过 Pixabay，用其他来源；用户主动要求时才请他在弹出的浏览器里手动过一次，不要尝试绕过 |
| 接口返回 429 | 脚本会等 60 秒重试；仍失败就隔一会儿再跑 |
| 某个 ID 一直没有候选 | 换 `references/keywords.md` 的乐器词/主题词，或放宽 `max_sec` |
| 索引里很多 unknown | 手动下载的素材没登记，用 `add_credit.py` 补登 |
| 网站改版、链接失效 | 更新 `templates/packs.csv` 的 `page_url` |
| 工程里已有同名 GameAudioManager | 脚本不会覆盖；确认是旧版本时由组装线手动替换 |


## 跨游戏声音区分（用户2026-10-25）

先按玩法题材填写实际 needs.csv，不能所有游戏原样使用同一套关键词。BGM按题材和配器筛选；SFX先符合实际动作与材质，不能仅凭题材相同拿激光音代替按钮点击。候选分层保留原质量至少70分、许可、类型和时长过滤；只有题材不足时明确标记回退，不把泛用音称为题材专属。

索引保留源字节 SHA256、标准化解码音频ID和来源曲目/录音族。不同格式、循环版及已知同曲版本按族去重；同名但实际不同的素材保留。使用历史同时兼容旧路径和新ID，搬动素材库后仍能减少跨游戏重复；同一游戏的多个BGM尽量选不同家族，确实不足则如实记录，不靠微变调凑数量。这是确定性内容/来源族去重，不宣称能识别所有旋律或听感相似。

加工子程序失败就停止使用旧产物冒充成功；只有本次输入与实际输出SHA核验成功才记录使用历史，失败的可选片段不计入已使用来源。现有 selection 不自动替换；已有项目只有当前任务授权换声音时才加 --redo。保持同一游戏材质和配器一致、原响度/包体和实际输出验收要求。

## 题材素材扩充与其他电脑复用（2026-10-25）

新游戏选音前先读取已安装本机库；题材仍缺时读取 [题材库下载与复用](references/theme-library.md) 和 `templates/theme-packs.json`。需要新增素材时按游戏实际题材运行 `python3 scripts/sync_theme_library.py --theme <题材>`，或主动补齐时一次下载 `--theme all`；库和已审回执均无变化时不重复下载。原站音频存当前用户共用库，升级 Skill 不删除素材库；清单和校验回执控制增量下载。题材标签直接进入索引，needs.csv 同时写 music/动作标签与题材，继续执行跨项目重复降权。不要把题材配乐覆盖误称为该题材全部拟音覆盖；缺的动作声音仍需另补。不得为更新本库替换已经通过的游戏 selection。
