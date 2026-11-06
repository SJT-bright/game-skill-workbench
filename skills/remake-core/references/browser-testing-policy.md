# 浏览器测试统一使用 Ego（用户 2026-11-06）

所有由 Agent 执行的浏览器测试一律通过 Ego Lite 官方 `ego-browser nodejs` 和独立 TaskSpace：包括首次进首页、试玩链接冒烟、截图、dump_ui、触摸、多指、布局、美术、声音、存档、广告、启动故障、回归及出包前验收。离线文件、源码与单元测试仍使用对应本地工具。

Google Chrome 仅用于把手机尺寸的本地试玩链接交给用户亲自玩。Agent 不在这个 Chrome 窗口中执行验收、回归、声音采样或自动测试；交付链接的自动冒烟与首页截图也在 Ego 完成。用户试玩窗口与测试空间分别登记、分别收尾。

删除旧的“英化优先自动换 Chrome”“没装 Ego 就用 Chrome/Edge”“经本轮同意可回退 Chrome”等路线。以前任务里的单轮 Chrome 授权不延续到此规则之后的测试。不使用 Playwright、普通 Chrome/Edge/Chromium、伪装成 `ego-browser` 的启动器或 `EGO_BROWSER` 覆盖来代替 Ego。`--browser chrome` 和 `--user-approved-chrome` 在测试入口必须拒绝，且拒绝发生在启动任何浏览器之前。

Ego 连接、尺寸或实际布局异常时，先核对当前官方 API、真实 CDP 视口与截图尺寸；修复 Ego 配置后继续。自己的空间消失时按空间归属规则核实并新建，用户接管或安全 hard stop 立即停止。Ego 做不到的项目保留实际错误及“未测/受限”，继续可独立推进的本地工作，不替换浏览器，不把历史 Chrome 记录改写为 Ego 通过。

浏览器证据记录 `browser_route=ego_taskspace`、`input_transport=ego_page_cdp`、数字 `session_id`、唯一 `space_name`，并核实测试结束后空间已消失。只读文件检查、哈希与受控宿主结果仍不代表物理手机、真实广告或平台上传通过。
