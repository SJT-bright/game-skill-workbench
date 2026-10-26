# Ego Lite 操作与恢复

2026-10-15 用户指定以后默认用 Ego Lite；替代本页旧 Chrome/CUA 默认路线。用户本次明确选择优先于默认工具和历史任务路线。先读已安装 `ego-browser` Skill（本机 `<SKILLS_DIR>/ego-browser/SKILL.md`），以其当前 API 为准。

用 `ego-browser nodejs` 的 heredoc 执行。**每个会话、每次测试新建自己的 TaskSpace**（用户 2026-10-23：被占就开新的，绝不等待）：新建前先跑 `browser_slots.py sweep --close`（主 Skill 的 scripts）关掉空了的旧空间；新建后打印 `spaceId` 并 `browser_slots.py register --kind ego_space --space-id <ID> --name "<线名+做什么>"`；本次测试内 `taskSpace(同一数字ID)` 恢复；JS 变量不跨命令保存。用 `task.page("p1")`，复用 Page。空间被别的会话/测试占用、正在被用、排队或还没轮到时，**不等待、不接管，立刻新建一个**；同一个错误在自己的空间里复现时才按失败排查（换新空间不能把真失败说成通过）。不能操作其他任务的空间。

页面优先使用官方 `goto/reload/snapshot/screenshot/mouse/keyboard`。普通 DOM 用 snapshot 与语义选择器，Canvas 先 screenshot 再按 CSS 坐标。每组动作后读回真实状态；回执只证明派发。状态变化或尺寸变化后重新观察，不盲目连点。

## 启动与触控核验

必须在游戏脚本启动前配置手机环境。优先在同一 TaskSpace 的空白 Page 配置，再 `goto()` 目标；若已先载入游戏，在同一 Page 配好后完整 `reload()`，让引擎重新检测输入能力。仅改尺寸或在旧场景里打开 touch 模拟不够，也不需要清存档或新建空间。

使用官方 `page.cdp()`，按目标设备设置移动端 UA（`Emulation.setUserAgentOverride`）、`Emulation.setTouchEmulationEnabled` 的 enabled/maxTouchPoints、`Emulation.setEmitTouchEventsForMouse` 的 enabled/configuration="mobile"，以及 `Emulation.setDeviceMetricsOverride` 的 width/height/deviceScaleFactor/mobile。以上设置全部完成后才导航或完整刷新。记录实际调用、执行顺序及结果；某项不支持时保留失败，不能默认已生效。

启动后先只读核验三层，再测试按钮与拖动：

- DOM：实际 UA、innerWidth/innerHeight、devicePixelRatio、maxTouchPoints、`'ontouchstart' in window` 和 Canvas CSS rect。
- 引擎：实际运行中的触控与移动端判定。Cocos 2.x 读取 `cc.sys.isMobile`、`cc.sys.capabilities.touches`；其他引擎读取对应能力，不能填写无关的 Cocos 字段。
- 输入接收：实际 Canvas 或该引擎输入目标已注册 touchstart/touchmove/touchend 等所需触摸监听，并连接到引擎输入链。用工具允许的只读监听检查或实际引擎回调证据核对，不替换监听、不调用控制器。工具无法取得时标 unavailable，并将引擎触控门禁标 blocked；不能用 DOM 事件或节点业务监听存在来补填通过。

任一层显示引擎仍为鼠标模式、触摸监听缺失或证据冲突时，先修正同一 Page 的启动配置并完整刷新，再复测；此时不把拖动无效归为游戏业务故障。引擎启动时可能缓存能力；事后出现 maxTouchPoints 或 trusted touch 不会证明它已重新注册触控。

触摸点使用该 Page 的 `Input.dispatchTouchEvent` 的 touchStart/touchMove/touchEnd，坐标基于本页截图，记录 transport=ego_page_cdp。分别保留浏览器原始输入、引擎收到触摸和实际界面/玩法变化的证据。DOM trusted touch 不能单独证明引擎处理了触摸；兼容鼠标事件可能使短点按触发 Button，而拖动仍未进入引擎。`page.mouse` 按实际收到的事件分类，触摸点按通过也不能替代拖动或多指验收。

多指测试先以浏览器原始 `touches / changedTouches` 核对协议行为，不假定 `touchEnd` 的非空 `touchPoints` 数组代表仍按住的手指。逐指松开后分别核对实际结束的 identifier、剩余触点和业务状态；协议用错的尝试保留原始记录并排除，不把意外释放拥有者后的一次正常操作误判为串指。

切换过同一空间的其他 Page 后，先核对目标页的 `document.visibilityState` 与实际渲染；需要时通过该 Page 的 `Page.bringToFront` 恢复自己的页。焦点模拟与真实前后台分开记录；等待条件应匹配当前真实节点/场景，不把选择器写错造成的等待超时当成游戏加载失败。

`page.evaluate()` 仅用于只读观察、证据采集；不调用按钮回调、游戏控制器、改余额或进度（唯一例外：主Skill"关卡抽测"规定的测试专用跳关，只用来到达要测的关）。禁止 DOM dispatchEvent 伪造输入，直接 Page API 流程不接外部 Playwright/独立 CDP；需要 `chrome-mobile-testing` 已声明的计划、录屏或加载计时能力时按该 Skill 的受限适配器流程执行，并区分实际输入路径。系统 cancel 与多指即使通过CDP产生，也只能称浏览器合成模拟，不能称物理系统事件。

自己绑定的测试空间失活或未分配时，先停止旧 ID 的操作并核实它从空间列表消失，再自动新建、登记独立空间继续，不询问用户、不接管旧 ID。用户明确接管、要求停止或浏览器工具安全 hard stop 时立即停止对应操作，不换空间、接口或发系统信号绕过。普通并发占用也新建自己的独立空间。**测试用完马上自己关（用户 2026-10-23，所有环节）**：只是自己测试的空间，测完立刻 `browser_slots.py close --name "<线名>"`（拥有者先用已绑定的官方 API 调用一次 `finish({keep:[]})`，脚本只核读回并注销；退出码 2 时先核归属和控制权，用已有绑定结束自有空间，再核列表并重跑 close），汇报前 `browser_slots.py check --name "<线名>"` 通过；**不为用户保留任何 Ego 空间**（`--keep` 只给 Codex 本地预览服务，Ego 空间登记 `--keep` 会被拒绝）；用户试玩结束或新版替代后 Agent 也关闭对应预览并核实端口退出，不让用户手动清理。不关闭用户创建或未知来源标签页，不清浏览器数据。

## 用户试玩交接

**用户 2026-10-23：Ego 只给 Agent 自己测试，用户试玩一律在 Codex 本地预览；禁止一切在 Ego 里让用户试玩的行为。**（取代以前"在 Ego 里配置手机模拟页、置前 handOff 给用户"的做法。）

1. Agent 自己的手机模拟检查照常在本会话新建的 Ego 空间里做（上方启动与触控核验），测完马上 `browser_slots.py close --name "<线名>"`。
2. 给用户试玩：主 Skill 的 `serve_preview.py --directory <准确版本的 Web 导出> --keep --name "<线名> 用户试玩"` 起本地服务，把打印的本地预览链接写在 Codex 回复里，用户在 Codex 里打开；写清"这是竖屏/横屏游戏"、建议窗口尺寸和操作方法。已有进行中的用户预览不刷新、不清存档。
3. 不开"等用户试玩"的 Ego 空间或窗口，不置前、不 `handOff()`，不写"试玩页已在 Ego Lite 中打开并交给你"。
4. Ego 里出现"需要你处理"、等用户试玩或等用户操作的空间（旧会话留下的），先用 `browser_slots.py ego-list` 找到；核实当前归属和用途后由拥有者用已有绑定结束，再 `ego-finish --space-id <ID>` 确认消失；不盲接管、不触及用户在用或未知归属空间；别的会话正在跑的测试空间不动。
