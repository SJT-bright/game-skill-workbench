# 音频素材来源清单

只收录**免费、可商用**的来源。授权以下载当时网页上写的为准；脚本会逐个记录授权，不合格的自动跳过。

图例：🟢 免署名　🟡 可商用但必须署名　⚠️ 每个文件授权不同，脚本逐个筛选

---

## A. 有 API，AI 直接调用（最快、最稳）

| 来源 | 链接 | 授权 | 适合 | 脚本 |
|---|---|---|---|---|
| **Openverse** | https://openverse.org/ （接口 https://api.openverse.org/v1/audio/ ） | ⚠️ 只取 CC0 / PDM / CC-BY | 音乐 + 音效，聚合 Freesound、Jamendo、Wikimedia 等 | `fetch_openverse.py`，**不用注册** |
| **Freesound** | https://freesound.org/ （申请 key：https://freesound.org/apiv2/apply/ ） | ⚠️ 脚本只取 CC0 | 补充特定音效，按评分排序 | `fetch_freesound.py`，需要免费 API key |
| **OpenGameArt** | https://opengameart.org/ | ⚠️ 只取 CC0 / OGA-BY / CC-BY | 专门给游戏的音乐、音效 | `fetch_oga.py`（基于 `pip install oga`） |

## B. 不用登录，网页直接下载

| 来源 | 链接 | 授权 | 适合 | 脚本 |
|---|---|---|---|---|
| **Kenney** | https://kenney.nl/assets/category:Audio | 🟢 CC0 | UI、金币、放置、胜负短音乐，**风格统一，首选** | `fetch_page.py --pack kenney_*` |
| **Mixkit 音效** | https://mixkit.co/free-sound-effects/ | 🟢 Mixkit 免费授权 | 游戏、点击、提示、胜利 | `fetch_page.py --pack mixkit_*` |
| **Mixkit 音乐** | https://mixkit.co/free-stock-music/ | 🟢 Mixkit 音乐免费授权（与音效授权分开，首次用看一眼） | 欢快 BGM | `fetch_page.py --pack mixkit_music_happy` |
| **Juhani Junkala（OpenGameArt）** | https://opengameart.org/content/jrpg-pack-4-calm 等 | 🟢 CC0 | 成套游戏循环 BGM | `fetch_page.py --pack oga_*` |
| **BigSoundBank** | https://bigsoundbank.com/ | 🟢 CC0 | 写实录音补充 | `fetch_page.py --url <单个音效页> --license CC0` |
| **incompetech（Kevin MacLeod）** | https://incompetech.com/music/royalty-free/music.html | 🟡 CC BY 4.0 | 2000+ 首 BGM，可按心情筛选 | `fetch_page.py --url <单曲页> --license "CC BY 4.0"` |
| **soundimage.org（Eric Matyas）** | https://soundimage.org/ | 🟡 需署名 | 大量 puzzle / funny 风格循环曲 | `fetch_page.py --url <分类页> --license "soundimage attribution"` |
| **Sonniss GameAudioGDC** | https://sonniss.com/gameaudiogdc | 🟢 免版税，**禁止用于 AI 训练** | 专业音效，一包几 GB | qBittorrent 只勾选需要的文件夹 → `add_credit.py` 登记 |
| **99Sounds** | https://99sounds.org/free-sound-effects/ | 🟢 免版税 | 偏电影/写实，少量可用 | 下载页在 Gumroad，用浏览器 → `add_credit.py` |

## C. 需要登录（你的账号，Playwright 保持登录）

| 来源 | 链接 | 授权 | 适合 | 脚本 |
|---|---|---|---|---|
| **Pixabay 音乐** | https://pixabay.com/music/ | 🟢 Pixabay 授权（不能单独转卖文件，放进游戏没问题） | **BGM 首选来源**，量大、免署名 | `browser_fetch.py search pixabay-music` → `download` |
| **Pixabay 音效** | https://pixabay.com/sound-effects/ | 🟢 同上 | 音效补充 | `browser_fetch.py search pixabay-sfx` |
| **itch.io 免费音频** | https://itch.io/game-assets/free/tag-audio | ⚠️ 每个包自定，脚本读页面授权 | 成套游戏音乐包、音效包，质量高 | `browser_fetch.py search itch` / `itch-free-music` / `itch-free-sfx` |
| **Tallbeard Studios 免费循环包** | https://tallbeard.itch.io/music-loop-bundle | ⚠️ 读页面 | 150+ 首循环曲 | `browser_fetch.py download <链接> --site itch` |
| **ZapSplat** | https://www.zapsplat.com/ | 🟡 免费版必须署名；上架前看一眼官网授权页 | 10 万+ 音效 | `browser_fetch.py login zapsplat` |
| **Freesound 原始文件** | https://freesound.org/ | ⚠️ 只要 CC0 | 需要 WAV 原文件时 | `browser_fetch.py login freesound` |

## D. 不要用

| 来源 | 原因 |
|---|---|
| BBC Sound Effects | 只允许非商业用途 |
| 任何标 NC / Non-Commercial / Personal use only / Editorial 的文件 | 不能商用 |
| CC-BY-ND | 不允许改动（我们会裁剪、调响度） |
| CC-BY-SA | 默认不用（改过的音频要按同样授权公开，麻烦）；确需时加 `--allow-sa` |
| Jamendo 免费曲库 | 大多是 NC，商用要另买授权（Openverse 会自动筛掉 NC 的） |
| Uppbeat 免费版 | 每月下载次数少，需署名，商用受限 |
| YouTube 音频库 | 授权针对视频，用在游戏里不明确 |
| 爱给网等授权不清的站 | 很多只限个人学习，无法确认 |
| 来源不明、授权不明的文件 | 一律不用 |

## 署名格式

需要署名的素材，`process_audio.py` 会自动写进游戏工程的 `docs/audio/CREDITS.txt`，该文件保留在交接文档，不生成 Credits/关于/制作人员界面；确有强制玩家可见署名义务时按许可另选展示位置或更换素材。常见固定写法：

- incompetech：`Music by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0`
- ZapSplat：`Sound effects obtained from https://www.zapsplat.com`
- CC BY：`"曲名" by 作者 (链接) — CC BY 4.0`
