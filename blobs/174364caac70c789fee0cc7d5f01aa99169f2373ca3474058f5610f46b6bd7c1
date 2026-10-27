---
name: mobile-touch-computer-use
description: 用户要求游戏本地预览、试玩、游玩或打开游戏时，先用固定手机尺寸外壳轻量交接，不启动全量验收；需要代测时默认用 Google Chrome DevTools/CDP 触摸模式自动验收游戏或网页的手机触控模拟、长屏布局、按钮和手势；Ego Lite 仅在用户明确指定时使用。适用于“替我测试手机端”“电脑模拟手机点击”“按钮手机点不动”等请求；通过 Ego Lite 官方 CLI 操作页面、手机视口和触摸输入，必要时操作已安装的系统模拟器，记录实际输入与界面变化，区分模拟结果与平台真机结果。
---

# 手机触控模拟验收

**用户亲自试玩先走轻量入口**：预览/试玩/游玩/打开游戏/恢复链接，以及美化、重塑交接前，必读[固定手机尺寸试玩](../cocos-game-to-english/references/user-phone-preview.md)。共享预览脚本默认390×844同源手机框、只缩小不放大，真实确认首页/开始后才发链接；仅试玩不执行下面的完整代测流程。

让 Agent 直接操作界面完成测试。**Google Chrome DevTools/CDP 触摸默认（用户 2026-10-27）**：自动测试在独立 Google Chrome 触摸模式里做，使用 `chrome_touch.py --user-approved-chrome --channel chrome`；固定移动 viewport、DPR、UA、`has_touch`，通过 `Input.dispatchTouchEvent` 或 `page.touchscreen` 发送触摸。`input_transport` 必须是 `playwright_cdp_touch`，普通鼠标不计作手机通过。用户试玩仍使用 Codex 本地预览链接，手机框只负责展示。Ego Lite 只有用户明确指定时才启用。完整合同见[Google Chrome 移动触摸运行模式](../cocos-game-to-english/references/google-touch-runtime.md)。

**禁止在 Ego 里让用户试玩（用户 2026-10-23，取代旧的"在 Ego 置前交接手机模拟页"）**：Agent 在 Ego 里完成设备/触摸配置和实际交互检查，测完关掉自己的空间；给用户试玩时，用主 Skill 的 `serve_preview.py --keep` 起本地服务，把本地预览链接写在 Codex 回复里，用户在 Codex 里打开，并写清横/竖屏、建议尺寸和操作。不开给用户的 Ego 窗口，不置前、不 `handOff()`，不说"已在 Ego 里打开交给你"；Ego 里显示"需要你处理"/等用户的空间，先用 `browser_slots.py ego-list` 只读列出；核实归属和用途后由拥有者结束已有绑定，再用 `ego-finish --space-id <ID>` 确认消失。细节见[用户试玩交接](references/computer-use.md#用户试玩交接)。

文档命令中的 `<SKILLS_DIR>` 取本次实际加载的 skills 目录，先解析再执行，不沿用其他电脑的用户名或盘符。Windows使用已安装的 `py -3 -X utf8 -B`，macOS使用实际 `python3 -B`；不为示例路径重新安装解释器。

## 确定目标

从请求和项目事实取得准确 URL、版本、构建入口及反馈的按钮与场景。已知信息不重复询问。只有不能唯一确定目标，或确有工具/权限阻挡时才请求缺少的信息；继续独立可做的工作。

保护已有标签页、登录、存档和服务。会消费道具、改变进度或领取奖励时，优先使用同字节构建的新本地 origin 或测试账户。记录隔离方式，不清浏览器数据、不改用户进度、不调用游戏函数造场景。

## Google Chrome 默认路线

先读取[Google Chrome 移动触摸运行模式](../cocos-game-to-english/references/google-touch-runtime.md)和 `chrome-mobile-testing` Skill。用户本次明确选择的执行器优先于默认路线和旧任务继承的 Chrome/CUA 流程。指定 Ego Lite 时先执行真实 `ego-browser nodejs` 命令，失败后才诊断。**被占就开新的，绝不等待（用户 2026-10-23）**：每个会话、每次测试用**自己新建的** TaskSpace，记录数字 spaceId 并登记（`<SKILLS_DIR>/cocos-game-to-english/scripts/browser_slots.py register --kind ego_space --space-id <ID> --name "<线名+做什么>"`），本次测试内以同一 ID 恢复、复用 Page；遇到空间被别的会话/别的测试占用、正在被用、排队、还没轮到，**不等待、不接管别人的空间，立刻新建一个**。每次新建前先跑 `browser_slots.py sweep --close`，退役已不存在的拥有者记录，只关闭已完成且当前身份匹配的自有进程；旧 Ego 空间和仅心跳超时的活资源先核当前归属与用途，别人还在用的不动；**测试用完马上自己关（用户 2026-10-23，所有环节）**：`browser_slots.py close --name "<线名>"`（Ego 先由拥有者用已绑定的官方 API 结束，再核空间消失并注销；退出码 2 保留待处理记录），汇报前 `browser_slots.py check --name "<线名>"` 通过。不选择或检查用户未指定的 profile。

全部页面导航、截图、点击、拖动和键盘输入优先走 Google Chrome touch runner 的 CDP 触摸通道；普通鼠标只作辅助排错。Canvas 用当前截图确定 CSS 坐标。手机 UA、触摸模拟、移动端鼠标转触摸配置和设备尺寸必须在游戏脚本启动前设置；已经加载过游戏时，在同一 Page 配好后完整 reload，再核对 DOM、实际引擎触控能力和 Canvas 触摸监听，详见 [启动与触控核验](references/computer-use.md)。需要触摸阶段时用 Chrome CDP `Input.dispatchTouchEvent`，记录 `input_transport=playwright_cdp_touch`；普通 `page.mouse` 不自动算触摸。

直接使用 Page API 的流程不引入外部 Playwright 或独立 CDP；需要声明过的 `chrome-mobile-testing` 计划、录屏或加载计时能力时，先读该 Skill，允许它连接当前 Ego 的 CDP 并创建自有隔离 context，报告实际输入路径，不把 helper 回执写成 Page API 证据。不用 AppleScript、系统鼠标脚本或 DOM `dispatchEvent` 代替操作。`page.evaluate()` 可只读观察 DOM/引擎公开状态和被动事件，不能调用游戏控制器、按钮回调、改余额、强制通关或造点击。文件工具可准备隔离副本、服务、日志和报告。

按 [Google Chrome 触摸模式](../cocos-game-to-english/references/google-touch-runtime.md) 和本 Skill 证据格式留存动作与结果。Chrome 启动失败时说明具体故障，继续可做的离线检查；用户明确指定 Ego Lite 时才改走 Ego，不静默回退到鼠标或普通浏览器点击。已有系统模拟器仅在目标需要时使用。自己绑定的测试空间从列表消失时，停止对旧 ID 的操作，核实它已不存在，自动新建并登记独立测试空间继续，不再询问用户，也不接管旧 ID。用户明确接管、要求停止或浏览器安全 hard stop 时立即停止对应操作。Agent 从不主动把 Ego 空间交给用户（用户 2026-10-23）。

使用直接全屏游戏入口；固定比例 iframe 可用于体验，但另测填满长屏的真实 Canvas。通常选两种不同长屏比例，尺寸按用户机型或项目风险决定。记录浏览器、模式、视口、DPR、Canvas CSS 范围与日期，机型名称不能当真实设备证据。

## 实际验收

从运行界面建立入口清单，覆盖本次范围内的首页、玩法、失败/胜利、重玩、返回、设置、弹窗和广告入口。只有实际出现的控件可标已测；没到达的条件入口保留未测。局部检查不能称全量验收。

每个案例先确定可见预期，然后真实操作并读回：

- 点按：松开后是否执行一次预期操作；clicked 回执不是通过。
- 拖出：按钮内按下、移动到外面松开是否取消；一次性 drag 不能称单独观察按下反馈。
- 重复：适度连点是否多次开局、重复奖励或卡住；不盲点消费入口。
- 状态：失败、暂停、返回或关闭弹窗后，重玩/主页/关闭是否仍有效。
- 遮罩：弹窗是否阻挡底层玩法，关闭可否重开、是否被同次松手穿透。
- 平台缺失：Web 广告不可用/失败/取消能否退出；本地提示或 Mock 不是真实广告成功。

奖励入口还要读回金币、道具、解锁和领取状态，不能只看广告窗口能打开。检查有无平台判断在广告请求之前直接发奖、仅show成功就奖、免费预览按钮或取消后仍奖。按实际规则区分需要广告的额外奖励、正常通关基础奖励和已存道具消费；不要为修广告无意删除后两类。

领取成功后必须回看原入口：按钮是否即时隐藏或灰CLAIMED，红点是否关闭，关闭奖励展示/等待动画后是否恢复成旧Watch；重开、刷新及重复点击分别核验。一次/每日/每局/可重复/导航入口按真实规则区别，不能统一隐藏或恢复。本环境的游戏Skill提供 [累积故障清单](../cocos-game-to-english/references/known-issue-checklist.md)，先加载本项目已知问题ID和每入口状态矩阵；本Skill负责真实操作与证据，不以截图或余额单项替代完整后置条件。

广告完整提示、原生关闭、游戏回调、保存和效果要逐阶段读回。等待期间跨两个可达入口/页面检查互斥；业务超时不等于原生会话关闭，SDK已终止后再显式请求仍须可用。已完成但保存失败时，重试同一奖励不得再播广告；具体存储故障由隔离source/Native回归注入，手机实际遇到时保留原始反馈。异步切场须覆盖旧组件被真实引擎销毁后回调，不只用永不清字段的节点替身。恢复凭证仅内存时如实标范围。

初次启动先按 [最小启动回归](references/cold-start-regression.md) 运行本项目的离线检查，覆盖平台缺键/对象返回、不完整或损坏旧记录、有效余额/进度和合法已领取状态；源码与本次实际编译包分别验证，失败阻止打包。出现新故障时保留最小失败样例，先证明旧版失败、修复版通过，再接入现有构建入口。离线检查在独立进程和内存中调用实际业务方法，不操作用户正在玩的游戏，也不代替 Chrome 触摸界面操作。默认金币异常、误显示已领取、重复模板标题、返回按钮缺失可能来自初始化中断；平台实际返回值未捕获时不能据替身确定唯一手机根因。

多指、真实 `touchcancel`、长按、按下中截图只有工具明确支持且实际证据存在时才标已测。touchmove/end 不证明多指或系统取消。工具无法分离 down/up 时记录边界，继续可测项。

Canvas 游戏用当前截图定位，尺寸/场景变化后重新取状态。AX 索引只用最近状态；每组确定性动作后读状态，不能沿用旧坐标。简单截图文字识别遵守当前环境的 OCR 分流规则，整体空间/布局由主 Agent 判断。

Cocos/TikTok任务同时读取 [通用问题适用范围与重点](../cocos-game-to-english/references/feedback-regressions.md)。优先逐实际广告/奖励入口检查完成、发奖、保存、按钮状态、失败恢复和重复/迟到结果；再检查加载、排版及实际存在的输入、动画和暂停机制。个性化玩法与设计改动只留项目。执行项目已有回归后以 Google Chrome CDP 触摸实际输入验证界面；源码/Native检查不能补写touch或真实IAA。用户指定Chrome或禁止模拟器时遵守其路线。

## 被动证据

本地 Web 导出可用 [隔离副本与输入证据](references/evidence.md) 的 helper，在独立 HTML 加只读事件观察器，其余游戏文件逐字节核对。观察器只监听事件、测 DOM/Canvas 和记录错误，不改布局、不吞事件、不调游戏代码；普通交付包不加观察器。

远程页面不能安全加观察器时，保留设备模式 UI 和实际操作证据，原始事件字段标 unavailable；不伪造日志。有工具真实原始触摸回执时优先保留。

失败先核对版本、启动时的手机环境、引擎触控能力、Canvas 监听、事件类型和最后实际界面，区分输入未到、命中错误、拦截、松手丢失与业务失败。DOM 的 trusted touch 只证明浏览器收到输入；引擎仍按鼠标模式启动时，兼容鼠标事件也可能让短点按有效，不能据此宣布引擎触屏或拖动通过。仅凭截图、代码里有 pause 或旧模拟通过不能宣布根因。

## 完成

按证据参考保存版本绑定、案例、截图、原始事件和未测项。区分 browser_touch_simulation、os_simulator、platform_remote_debug、physical_device；只有实际物理设备记录允许 physical_device=true。

清楚报告通过、失败、受限、未测范围。修复在授权范围内时另建候选、重建并用 Google Chrome CDP 触摸复测，不只改报告。现有 Cocos 手机门禁仍按它自己的绑定和真机要求，本 Skill 不自动放行。

结束只清理本轮 QA 服务；按 `ego-browser` 规则调用一次 `task.finish({keep:[]})`（不为用户保留页面：用户试玩在 Codex 本地预览），用 `browser_slots.py close --name "<线名>"` 一并结束并注销本次空间。保护原标签页和服务。给用户结论、证据和可打开的报告，不要求重做已完成的操作。

## 资源争用与关闭回执

普通并发占用时新建独立空间，不抢其他会话资源。自己绑定的测试空间失活或未分配时，先停止旧 ID 的操作并读列表核实原 ID 消失，再自动新建、登记独立空间继续；无法核实消失时先排查，不能盲接管。用户明确接管、要求停止或浏览器安全 hard stop 时立即停止对应操作，不换空间、接口或系统信号绕过。测试结束后由当前拥有者用已绑定的官方 API `finish({keep:[]})`，`close` / `ego-finish` 读列表确认消失；预览服务核对原进程及端口退出，不能要求用户手动关闭。无法确认时退出码 2，记录保留，`check` 不放行。历史空间的名称或“需要你处理”标签不能单独证明可以关闭；先核当前归属与用途。详见主 Skill 的 `references/machine-load.md`。

**禁止把 Codex 内置浏览器当作测试器（用户 2026-10-27）**：Codex 内置页面只能用于用户查看/试玩，不能用于 Agent 的手机触摸测试、按钮通过结论或触摸证据。Agent 必须在交链接前使用独立 Google Chrome iPhone CDP 触摸模式，并读取[Chrome iPhone 触摸预检矩阵](../cocos-game-to-english/references/chrome-touch-preflight-matrix.md)。

**输出必须标明 Chrome 测试层（用户 2026-10-27）**：凡输出“测试通过”“手机触摸通过”“按钮已验证”或交付预览，必须注明 `Google Chrome iPhone touch`、设备尺寸/DPR、`input_transport=playwright_cdp_touch` 和业务结果。只在 Codex 内置浏览器查看或点击，必须写“仅查看，未作为手机触摸测试”，不得写成测试通过。
