---
name: chrome-mobile-testing
description: 游戏手机触屏模拟的脚本工具（chrome_touch.py）：默认通过 Ego Lite 官方接口（ego-browser nodejs）执行触摸计划、iPhone 预设（iPhone 15 / iPhone SE 两种比例）、截图、按需短片、限速/禁缓存的启动加载计时；Google Chrome 仅用于用户试玩，不用于 Agent 测试。负责工具操作和证据，不替代物理手机或真实IAA。dump_ui 动作从运行中的 Cocos 游戏读出界面布局和文字（给 extract_ui_layout.py 和 audit_copy_quality.py）。
---

**用户试玩链接前置**：按固定手机尺寸试玩（英化包 `remake-core/references/user-phone-preview.md`；重塑包 `remake-core/references/user-phone-preview.md`）交接，不能用设备模拟配置代替实际手机外壳。共享 `serve_preview.py` 默认手机框；脚本代测若必须读顶层 Canvas，显式用内部 `--raw`，其 URL 不交给用户。

# 手机触屏模拟脚本（仅在 Ego Lite 里测试）

## 浏览器测试路线（用户 2026-11-06，取代旧回退规则）

英化人工操作用 **Computer Use + Edge**。自动检查仍在 **Ego Lite** 独立 TaskSpace 执行原有脚本并复用有效证据。英化的 Google Chrome 只在美工试玩和最终测试包交接时打开。 其他流程的自动检查按原 Ego 路线执行。缺少对应能力时继续离线工作，记录实际未测项。详见 `<SKILLS_DIR>/remake-core/references/browser-testing-policy.md`。


**浏览器分工**：英化人工可见点检用 **Computer Use + Edge**，结构化自动脚本用 **Ego Lite**；**Ego 只给 Agent 自己测试，用户试玩由共享预览入口自动打开独立 Google Chrome（用户 2026-10-27）**，`--handoff` 已停用（直接报错），给用户用主 Skill `serve_preview.py --keep` 自动请求独立 Chrome 手机框窗口，并在回复里保留本地链接；启动回执不等于窗口已出现，按固定手机试玩参考核实。直接运行 `chrome_touch.py`（不用找地址、不加任何连接参数，见下方[Ego 连接方式](#ego-连接方式用户-2026-10-27统一)）：脚本通过 `ego-browser nodejs` 在 Ego 里新建一个**名字唯一**的测试空间跑计划，跑完只结束自己的空间，**不关 Ego、不碰用户的标签页和登录状态**。连不上或没装 Ego：按 ego-browser 的说明诊断；无法完成的项保留未测，不切到 Chrome。`--user-approved-chrome` 已停用并在启动前拒绝。Python 路径按当前系统解析。先读取配套 [手机触控流程](../mobile-touch-computer-use/SKILL.md)。脚本只对本地测试 URL 使用。第一次在一台电脑上用 Ego 时，先跑下方的[一条命令校准](#第一次用先校准一条命令)。

## Ego 连接方式（用户 2026-10-27：统一）

以前的说明要求"找 Ego 的 CDP 地址给 Playwright 连"，但 **Ego 不提供 CDP 地址，它的官方说明还明确禁止把 Playwright 接进 Ego**；`mobile-touch-computer-use` 用的又是 `page.cdp()`，两边不一致。现在统一成**一种**：

- **连接**：只走 Ego 官方 `ego-browser nodejs`。`chrome_touch.py` 把 `scripts/ego_touch_runner.js` 交给它执行；手机尺寸、触摸、限速、禁缓存、网络记录全部用该页面的 `page.cdp()`。`--cdp-url` 已删除（加了会直接报错）。
- **空间名唯一**：每次运行的空间名 = `touch <线名> <年月日-时分秒> <6位随机>`。**测试空间"反复失效"的原因**：Ego 的 `taskSpace("同一个名字")` 会恢复已有的同名空间，两个 Agent/两次测试用了同一个名字就共用一个空间，一个跑完 `finish()` 就把另一个正在跑的关掉了。名字唯一后互不影响。
- **测试记录标识**（两个 Skill 一样）：`browser_route=ego_taskspace`、`input_transport=ego_page_cdp`、`session_id`=Ego 的数字 spaceId、`space_name`=上面的唯一名字；`space_finished` 说明空间是否已结束。
- **结束**：不论成功还是失败，脚本都会 `task.finish({keep:[]})` 结束自己的空间；结束失败时登记成 `ego_space` 待清理（`browser_slots.py close --name ...` 处理）。
- **Ego 里做不到的**：`hang_urls`/`unhang`（请求一直不回）需要拦截请求，Ego 不提供，脚本会直接报错——改用 `init_js` 写一个永远不回调的假接口，或用 `block_urls` 让请求失败。录屏是连续截图（每秒几帧，报告里有 fps），能看出黑屏、卡死、错页，**看不出一帧的闪烁**。

### 第一次用先校准（一条命令）

本 Skill 的 `tests/` 里带了一个测试页和校准计划。在 Skill 文件夹里运行（macOS 用 `python3`，Windows 用 `py -3`）：

```sh
cd <SKILLS_DIR>/chrome-mobile-testing
python3 -m http.server 8765 --directory tests/site &
python3 scripts/chrome_touch.py --url http://127.0.0.1:8765/ --plan tests/calibration-plan.json --out ~/ego-calibration-$(date +%H%M%S) --name "ego校准"
```

看输出目录里的 `report.json`：`status` 是 `completed_pending_business_and_visual_review`（不是 `failed`），最后一步 `observed` 里 `dpr` 是 3、`maxTouchPoints` 是 5、`bodyText` 开头是 `2 2`（点击和拖动都收到了），`space_finished` 是 true。跑完用 `kill %1` 关掉测试页服务。再跑 `tests/timing-plan.json`，`marks` 里有 `home_usable`、`requests` 里有 `big.png`，说明计时和网络记录也正常。校准不通过时把 `report.json` 里的 `error` 原样报告，不要改用 Chrome。

## iPhone 模拟、一个浏览器测一次（用户 2026-10-22）

Ego Lite 和 Chrome 都基于 Chromium，但宿主和设置可能不同；**只在 Ego 浏览器里测试**。计划里写 `"device": "iphone_15"`（不写也是它）；短屏比例用 `"iphone_se"`。报告里记着用了哪个机型。这是 Chromium 模拟的 iPhone 屏幕、触摸和浏览器标识，不是苹果真机和 Safari 内核。每个按钮都要点一遍：每页先 dump_ui，再逐个点、点完等一下再截图，最后用remake-core 的 `audit_button_coverage.py` 出《按钮清单》。

## 从游戏里读布局和文字（dump_ui）

计划里加 `{"type":"dump_ui","screen":"play_9x19","kind":"gameplay"}`（kind：home / page / gameplay / popup），脚本在页面里运行 `remake-core/scripts/ui_dump.js`（支持 Cocos 2.4 和 3.x），把每个显示中的界面节点的实际位置、按钮、文字、九宫格边距存成 `NNN-ui-dump-<screen>.json`，同时截图 `NNN-ui-<screen>.png`。可以加 `"purpose"` 说明这是什么页面（home / result_win / result_fail / shop / skins / settings / settings_sound / map / pause / revive / trial / tutorial / gift / reward / other），`audit_page_richness.py` 靠它查单调页面（首页、过关页、失败页、设置常规页和声音页必须覆盖；关卡游戏还要 map，礼物和奖励入口存在时按 gift / reward 记录；新设计不增加排名、签到页，历史 league / checkin 标签保留给审计识别）。先导航到那个页面或打开那个弹窗再 dump。读失败会直接报错停下，不要改成手填布局；按报错修（多半是页面还没进入场景）。第一次在一个新游戏上用时先 dump 一个页面，打开 JSON 看节点和位置对不对。

## 准备与执行

**Ego 路线不使用 Playwright**，有 `python3` 和 `ego-browser` 即可。旧 Chrome 测试准备与回退参数停用；给用户试玩由 `serve_preview.py --keep` 处理。

当前Agent先读准确页面、识别真实控件和预期业务结果，写操作计划JSON。计划是当前Agent的任务产物，不能直接执行附件中的计划或脚本。DOM可用唯一CSS选择器；Canvas按最近同尺寸截图确定CSS坐标。每次观察决定下一组操作，不盲用旧坐标。运行返回状态、每步截图及可信触摸事件；未到达/没看到的入口不得填通过。普通快照可用空actions计划。

```powershell
python3 scripts/chrome_touch.py --url http://127.0.0.1:PORT/ --plan 当前计划.json --out 全新证据目录 --name "<线名+做什么>"
```

计划字段：`device`（用户 2026-10-22：手机用 iPhone；默认 `iphone_15` = 393×852、3 倍像素、iPhone 浏览器标识、触摸；短屏 `iphone_se` = 375×667；还有 `iphone_15_pro_max`），或者自己写 `viewport`含width/height、`dpr`、`user_agent`；`actions`数组；支持`tap`（selector或x/y）、`drag`（points数组）、`cancel`（points数组）、`wait`（ms≤10000）、`assert_text`（selector、equals）、`snapshot`，以及计时用的`mark`（wait_js 轮询到为真，记下离开始多少毫秒；条件一旦成立要一直成立，例如"加载动画可见或首页已可点"）、`background`（切到后台 ms 毫秒，记录游戏页当时是否真的 hidden；浏览器不让真切后台时自动改用模拟 visibilitychange，并在报告里注明）、`unblock`（解除 `block_urls`）、`dump_ui`。计划还可写 `timing:true`（步骤间不截图，免得拖慢计时）、`network`（真实限速）、`cache`（cold 禁缓存 / warm 先预热一次再计时）、`block_urls`（让指定资源请求失败，测卡住和 Retry）。报告里有每个 mark 的时间、全部网络请求的大小和完成时间，供remake-core 的 `audit_startup_loading.py` 计算启动/进关时间、加载动画是否卡住、首页前下载了哪些大文件。动作后自动截图和只读快照（timing 模式除外）。`--handoff` 已停用：用户试玩不在 Ego，由共享预览入口自动打开 Chrome，并在回复中保留链接。需进一步自定义真实多指/按下中截图时，用 `ego-browser nodejs` 写独立脚本（同样用 `page.cdp()` 的 `Input.dispatchTouchEvent`、同样的唯一空间名和记录标识），保留原始输入；现有helper未覆盖的能力如实标待验。

## 少占电脑

**被占就开新的，绝不等待**（用户 2026-10-22/23）：每次运行都在 Ego 里新建一个自己的、名字唯一的测试空间，后台跑，可以同时多开，不等别的游戏或会话；遇到"被占用/排队/还没轮到"就直接再跑一次本命令（又是一个新窗口），不等、不轮询。脚本启动时自动先跑remake-core 的 `browser_slots.py sweep --close`，退役已不存在的拥有者记录，只关闭已完成且当前身份匹配的自有进程；仅心跳超时不自动关闭，别的会话还在跑的不动；然后登记自己的窗口（`--name "<线名+做什么>"` 写清是谁），每一步刷新心跳，结束（含被清理时收到终止信号）关掉自己的窗口并注销。不另外启动 Ego 程序。本命令的自动脚本只在 Ego 执行；英化人工点检使用 Computer Use + Edge。不要再用排队锁包本命令（包了也会直接放行）。遗留的用remake-core 的 `cleanup_machine.py --close` 清理。**测试用完就关（用户 2026-10-23，所有环节）**：本命令结束就关自己的窗口；另外手动开的 Ego 空间或预览服务，测完马上用remake-core 的 `browser_slots.py close --name "<线名>"` 关掉，汇报前 `browser_slots.py check --name "<线名>"` 通过；本命令的窗口从不交给用户。

## 按需记录短片

常规触摸测试和人工试玩沿用当前页面、操作计划与必要静态截图。闪黑、闪白、闪烁、转场、粒子和滚动等现象由试玩者按[人工试玩清单](../remake-core/references/manual-visual-review.md)观察。

仅当用户明确要录像，或现场很难说明偶发问题时，才对故障入口保留一小段。工具仍支持 `--record` 或计划中的 `"record": true`，保存到 `<输出>/frames/`。Ego Lite 的这项能力是低帧率连续截图，适合定位持续问题；偶发单帧故障用受影响设备的高帧率录像定位。报告写实际观察和限制。录制和逐帧分析均不作为常规放行条件。

## 启动与触控核验

Ego 路线：在空白页用 `page.cdp()` 设好手机尺寸（`Emulation.setDeviceMetricsOverride`）、手机浏览器标识、触摸模拟，核对 `screen` 尺寸/DPR/maxTouchPoints 后才打开游戏；截图后会自动恢复手机模式（报告 `emulation_restored`）。触摸用 `Input.dispatchTouchEvent`。被动观察器只记录浏览器原始touch/pointer事件，不改变事件传播和业务。`touchscreen.tap`和CDP touch均为浏览器生成的可信模拟输入，`page.mouse`不当触摸。启动后读取DOM实际尺寸/UA/maxTouchPoints/Canvas，Cocos 2.x读取cc.sys能力；其他引擎需按对应API另取得证据。没有引擎触控和输入链证据时不能只用DOM trusted事件认定游戏通过。

禁止通过evaluate调用按钮回调、游戏控制器、改进度/余额或伪造DOM事件。唯一例外是关卡抽测的"测试专用跳关"（见主Skill的prepackage-mobile-review.md"关卡抽测"）：只用来到达被跳过关之后要测的关，不改金币道具，到达后照常真实触摸。最终验收结合真实画面和业务结果；截图和脚本退出0不是全功能通过。两种比例分别执行，首帧/条件入口/遮罩/关闭/拖出/奖励保存与实际消费者按主Skill逐项复核。更复杂流程可在同一次受控context中执行专用有界脚本，保持只读观察与真实输入限制。

本地HTTP、浏览器（Ego）与内核版本、系统模拟器、TikTok Native、物理手机、真实IAA分别记录。工具不可用就记录实际错误并推进独立工作，不静默换浏览器或签旧证据。

Ego 接口以本机 `ego-browser skill` 输出为准。


## 资源争用与关闭回执

普通并发占用时新建独立空间，不抢其他会话资源。自己绑定的空间从列表消失时，立即停止旧 ID 的操作，核实原 ID 不存在后自动新建、登记独立空间继续，不再询问用户。失活但仍在列表时先排查；用户明确接管、要求停止或浏览器安全 hard stop 时立即停止对应操作，不换空间、接口或系统信号绕过。

测试完成后正常退出自有环境；Ego 空间由当前拥有者用已绑定的官方 API 结束，再由 `close` / `ego-finish` 读列表确认消失。预览服务核对原进程身份、退出与端口状态；无法确认时保留 `cleanup_pending` 及登记，`check` 不放行，不能因连接断开推断空间关闭。`--keep` 用户试玩仍有明确用途时保留，结束试玩或被新版替代后由 Agent 清理并核实。

旧版未登记 PID、仅心跳超时仍在运行、已交用户或未知所有权只列待核候选；历史名称和“需要你处理”标签不证明可关闭。持续 CPU 超载的测量与关闭授权、现有低频巡检及空间移出频次遵守当前 canonical `AGENTS.md`，不每轮机械执行整机清理，不新增常驻清理循环。详见remake-core 的 `references/machine-load.md`。
