---
name: cocos-game-check
description: "统一检查（触发词：检查、测试、验收、找bug、修bug、启动、进不去、白屏、卡加载、按钮没反应、音量、出包、打包、ZIP、检查包、包太大、评审）。所有Cocos小游戏共用的检查Skill：英化游戏和重塑游戏都用同一份。启动与稳定、功能测试与修复、出包、最终包检查、评审（只检测不修改）、美术检查，以及全部检查脚本。"
---

# 统一检查（英化与重塑共用）

修订：`2026-10-28.check-unified.4`。英化包和重塑包内这个 Skill 字节相同。检查规则以重塑包 v7.1 的检查板块为准（`startup/`、`test/`、`package/`、`package-check/`），评审沿用原评审入口（`review/`）。检查脚本与规则库用同包的共享库 [remake-core](../remake-core/SKILL.md)，美术检查用同包的 [remake-art](../remake-art/SKILL.md)；本 Skill 不再自带它们的副本（v7.3.2 去重）。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](references/tiktok-fixed-adaptation.md) 做（英化和重塑都适用，本页每条写了现在由哪个门禁拦、哪些仍是文档规则）；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

## 先定是哪一类游戏

| 类型 | 判断 | 适用 |
|---|---|---|
| 英化 | 拿到的是能运行的中文完整游戏，只改中文美工/文字，加少量固定入口 | 下表“英化”列；默认不查关数、经济数值、皮肤、签到、教程等重塑专属项（Saul 要求创新玩法时，新加的部分要查） |
| 重塑 | 用启动包做的新游戏 | 全部检查 |

工程里写 `docs/board.txt`（`localize` 或 `remake`）；没写时按 [两个制作入口](../remake-core/references/two-boards.md) 判断。

## 三道关：哪一关在什么时候跑（用户 2026-10-28）

本 Skill 把所有检查放在一处，但**不是做完游戏才一次查完**。按制作阶段分三道关，前一关通过才进下一阶段，后面的关不重复前面已经查过的内容（详见 [检查分阶段](../remake-core/references/check-stages.md)）：

| 关 | 什么时候跑 | 查什么 | 不查什么 |
|---|---|---|---|
| 1. 设计关 | 玩法（占位图）做完、交用户确认玩法之前 | 玩法、关卡、经济、皮肤、模块，以及所有广告节点的位置与流程（复活、结算×2、局内道具/增益、礼包、看广告解锁）；`remake-core/scripts/design_check.py` | 美术 |
| 2. 美术关 | 美术做完、交用户试玩之前；之后改图只复查受影响的整页 | 画面、按钮、图片字、穿模、暗区、清晰度；`remake-core/scripts/art_check.py`、[art](../remake-art/SKILL.md) | 设计数值 |
| 3. 最终总检测 | 用户确认玩法和美术、锁定之后，出包之前 | 只查功能：能进、不卡加载、按钮有反应（含 TikTok 触摸坐标探针）、广告完成/取消/失败、存档、包体；`remake-core/scripts/check_known_issues.py`、`preflight.py`、`logic_check.py`，再出包与最终包检查 | **不再查美术和设计**，也不重评审美 |

用户试玩确认后美术锁定；出包前如需改美术，只按受影响页面复查美术关，不重跑整套。英化默认没有设计关（不改玩法），美术关只查改过的页面；Saul 要求创新玩法时，新加的部分照对应板块查。

## 检查项与入口

| 检查 | 英化 | 重塑 | 入口 |
|---|---|---|---|
| 启动与稳定：进得去、加载页、Retry、存档 | 必查 | 必查 | [startup](startup/README.md) |
| 功能测试与修复：按钮、输入、胜负、重开、异步广告 | 必查 | 必查 | [test](test/README.md)；存档/领奖/签到日期等静态规则 `remake-core/scripts/logic_check.py`（`preflight.py` 的「逻辑检查」行） |
| 无中文残留、英文文案 | 必查 | 必查 | `remake-core/scripts/audit_english_coverage.py`、`audit_copy_quality.py` |
| 位图字只用于数字和符号；句子用真字体；字母大小写不串（禁止 HelP/TaP 这类） | 必查 | 必查 | `remake-core/scripts/audit_bitmap_letter_fonts.py`（美术关 `art_check.py` 已接入） |
| TikTok 触摸坐标：Cocos 2.x 包装好平台包 `touch-coordinates.js`，Cocos 3.x 包在引擎加载前给 `tt.onTouch*` 装好坐标修正，只给 screenX/screenY 也能点到原位（浏览器模拟测不出）；探针结果为空即失败 | 必查 | 必查 | `remake-core/scripts/audit_upload_startup.py`（触摸坐标探针：2.x `probe_cocos2_touch_coordinates.cjs`，3.x `probe_cocos3_touch_coordinates.cjs`）、平台包 `remake-core/assets/platform-kit/build-templates/bytedance/` |
| 设置里音效/BGM 两个音量分开可调且保存 | 必查 | 必查 | `package-check/scripts/audit_sound_settings.py`；源码阶段 `remake-core/scripts/audit_sound_settings_static.py`（`preflight.py` 的「声音设置」行） |
| 删除分享、更多游戏、排行榜。把 `WxGameBox` 这类旧类换成空实现时，空实现的 `init(nodes)` 要把传进来的节点设成 `active = false`，不能什么都不做（v7.8，Holly's Hay Hop v1：旧类原本负责隐藏挂件，换成空类后局内一直显示「Try It」框） | 必查 | 必查 | `remake-core/scripts/audit_no_social_features.py`、[前置规则](../remake-core/references/no-social-features.md)；`preflight.py` 的「分享/排行榜」「互推」「分享换奖励」（`audit_share_entries.py`）行，`--stage final` 时「跳过」也算需处理；还显示着的退役槽位由写包入口必跑的运行时套件 `dead_shell`（VIS_DEAD_SHELL，[运行时回归](package-check/references/runtime-regression.md)）拦 |
| 个人主页回访、添加桌面入口 | 必查 | 必查 | `remake-core/scripts/audit_platform_markers.py` |
| 结算页 Watch Ad x2 与 Retry；广告取消/失败不发奖、只用激励视频、无广告跳关 | 必查 | 必查 | `remake-core/scripts/audit_ad_binding.py`、`audit_no_ad_skip.py`、`audit_no_ad_simulator.py` |
| 美术检查（穿模、暗区、按钮覆盖、图片清晰度） | 只查改过的页面 | 必查 | [art](../remake-art/SKILL.md)、`remake-core/scripts/art_check.py` |
| 关卡、经济、皮肤、签到、教程、模块 | 默认不查；创新玩法新加的部分要查 | 必查 | `remake-core/scripts/audit_level_plan.py`、`audit_game_modules.py`、`audit_acquisition_progression.py` 等 |
| 出包与最终包检查 | 必查 | 必查 | [package](package/README.md)、[package-check](package-check/README.md) |
| 出包时的布局状态、按钮普查（v7.8，总表 B30，Saul 10-30 定必跑）：iPhone 14 和 SE、胶囊按点 / 按像素，查按钮伸出屏幕、压胶囊、压底部横条、被 3D 盖住、胶囊单位一变就移位、开局下载超过 10 MiB 或带声音；首页每个按钮和一层弹窗按钮真点一次，没反应就拦。首页规则：重塑查设置在左上、最下面一排只放主页回访和加桌面；英化原按钮不动，只查两个入口在首页、能点、不压原按钮。新游戏拦、老游戏只警告；3.x 只有开局下载会拦 | 必查 | 必查 | 写包入口自动跑（运行时套件 `layout_state`、`button_sweep`，[运行时回归](package-check/references/runtime-regression.md)），每款多 6～10 分钟；要测「展台上有车」这类首页一层点不到的状态，在 adapter 写 `layout_states`。顶栏、设置钮贴着胶囊放的，用平台包 `parts/CapsuleLayout.js` 读胶囊位置 |
| 物理和推力不许跟着屏幕帧率走（v7.8，总表 P16）：同一段操作在 60 Hz 和 120 Hz 的显示时钟下各跑一次，按真实时间比位置，差超过 5% 就拦（这一条是最终裁判，logic_check 的 L-FPS 只是提示）。新游戏拦、老游戏只警告；3.x 只警告「未覆盖」 | 必查 | 必查 | 写包入口自动跑（运行时套件 `frame_rate`）；adapter 要写 `frame_rate` 块（跟踪的节点、那段操作），没有物理、没有自己会动的东西写 `{"n/a": "原因"}`。用了 2.4 物理的新游戏，`tiktok_finalize.py source` 自动装平台包 `parts/PhysicsClock.js`（打开 enabledAccumulator），推力自己乘 dt（`Clock.force(v, dt)`） |
| 出包流程（v7.8，总表 B32）：出包后同款旧包连同回执挪进「旧包/」，交付文件夹只留这一个包和「最新.txt」（上传用哪个包、sha256、时间）；检查用的工具不是安装版（自己复制改过的）报「改过的工具」并写反馈草稿到 ！Skill更新/；Saul 改了设计、旧问题的用例不再适用时，按新设计登记新问题再用 `package_issue_gate.py supersede` 作废旧的（要 Saul 原话、日期、新问题编号）；旧笔记里的 `cocos-game-check/core/scripts/<脚本>.py` 转到 `remake-core/scripts/` | 自动 | 自动 | 两个写包入口自动挪包、写 最新.txt（不想挪加 `--keep-old-packages`）；`check_package` 报告的 `modified_tools`；作废见 [已报告问题](package-check/references/resource-and-reported-issues.md)「按新设计作废旧问题」 |
| 障碍不许在屏幕里凭空出现、消失、瞬移（v7.8，总表 P2 补）：四种屏幕（390×844、375×667、768×1024、1115×791）上主角无敌飞 18 秒再复活一次，带碰撞体的障碍在看得见的地方新出现、消失、一帧跳 40 以上就拦。新游戏拦、老游戏只警告；3.x 只警告「未覆盖」 | 必查 | 必查 | 写包入口自动跑（运行时套件 `popin`）；adapter 要写 `popin` 块（主角、无敌、复活、游戏节点），没有滚动障碍的写 `{"n/a": "原因"}`。跑酷、飞行类用平台包 `parts/CourseLane.js` 算出生、回收和复活清障 |
| 看广告入口真点（5 个入口加复活）、试玩链接点看广告 | 有 adapter `ad_entries` 时必查；给 Saul 试玩链接前必查 | 同左 | 运行时套件 `ad_entries`（复活等主角自己失败，不要开局强制失败）；`serve_preview.py --keep` 给链接前自动跑 `trial_link`（模拟广告窗要在最上层、点「看完」游戏要变），不过就不给链接，也能 `runtime_regression.py trial --url <链接>` 手动跑 |
| 评审别人的游戏（只检测不修改） | 可用 | 可用 | [review](review/README.md) |

引擎：重塑固定 Cocos Creator 2.4.15 与平台包；英化保持原游戏的引擎版本。v7.7 起出包时由 `tiktok_finalize` 把平台包标准件装进英化工程（2.4.x 和 3.x 都装，见 [TikTok 固定适配·出包时怎么装](references/tiktok-fixed-adaptation.md#出包时怎么装v77tiktok_finalize)）；换成平台包 `main.js` 只在清单 `startup24` 列出的引擎版本上做（2.4.4、2.4.6、2.4.13、2.4.15；其他 2.4 版本保留自己的 `main.js`，触摸和存档两行插进 `game.js`）。平台包工程检查（`remake-core/scripts/audit_platform_kit_required.py`，内含 `check_kit_project.py`）按实际构建用的 Creator 版本判断：2.x 重塑工程用本机 2.4.15 构建，要求 `build-templates/bytedance/` 带平台包 `main.js` 和 `touch-coordinates.js`；英化工程（`.tiktok-kit/policy.json` 的 board 是 `localize`，或有 `docs/english/`）不查构建模板，改查源码段记录是否新鲜（和写包入口的 K5 同一个检查），所以跑 `preflight.py` 前先跑 `tiktok_finalize.py source`。

## 规则

- **TikTok 与 Cocos 的触摸差别（用户 2026-10-28，最严重的一类“点不动”）**：Cocos Creator 2.4 的触摸转换（`getTouchesByEvent`）读触点的 `clientX/clientY`，TikTok 运行环境给的触点只有 `screenX/screenY`，算出的坐标是无效值，扫码后按钮点不动、常卡在首页。浏览器手机模拟会给 `clientX`，**测不出这个问题**。所以每个 Cocos 2.x 的 TikTok 包都必须带平台包的 `touch-coordinates.js`（v7.7 起由写包入口里的 `tiktok_finalize` 自动装上：产物 `main.js` 是平台包 `main.js` 时由它加载，否则在 `game.js` 里插一行；不要自写 patch_build 替代，见 [TikTok 固定适配·出包时怎么装](references/tiktok-fixed-adaptation.md#出包时怎么装v77tiktok_finalize)），并通过 `remake-core/scripts/audit_upload_startup.py` 里的触摸坐标探针（`probe_cocos2_touch_coordinates.cjs`，对打包产物真实执行，只给 screenX/screenY 也要得到有效坐标）。探针不过不出包。**Cocos 3.x 包同样必查（v7.4，Marlows r4 漏过）**：3.x 的小游戏触摸输入同样读 `clientX/clientY`，缺字段时引擎的 Vec2 把 NaN 变成 0，点哪里都落在左下角 (0,0)。`audit_upload_startup.py` 对 `web-adapter.js` + `cocos-js/` 的包运行 `probe_cocos3_touch_coordinates.cjs`：真实执行包里的 `game.js` → `web-adapter.js`（以及引擎加载前 require 的修正模块，如 `marlow-touch.js`、`grotto-touch.js`），触点只带 `identifier/screenX/screenY/force`，再走引擎自己的 SDK 拷贝和触摸回调；引擎收到的坐标必须是有限值、在屏幕内、并且落在点按的位置上才算通过。修正要在引擎加载（`System.warmup`/`System.import`）之前装到 `tt.onTouch*` 上。**探针结果为空（`touch_coordinates: null`）不算通过**：TikTok 的 Cocos 2.x/3.x 包认不出引擎触摸转换时直接失败，并写明原因。

- 本 Skill 只检查和修检查出的 bug；美术、玩法、经济的设计改动交给对应制作 Skill，英化美工只在用户点名时才做。
- 结果写在工程 `docs/`；失败如实保留，不改阈值、不改检查器替游戏过检。
- 共用功能（广告、存档、Retry）只测一次，不乘到每关。
- 浏览器与触屏测试用同包的 `chrome-mobile-testing`、`mobile-touch-computer-use`、`ego-browser`。
