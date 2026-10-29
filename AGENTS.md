# Skill 个人工作台

本目录是独立跨平台应用，不修改或读取原游戏工作台的正式用户数据。分发构建初始游戏、Skill、连接信息均为空；不得携带开发机目录、游戏、聊天或登录信息。用户于 2026-10-26 明确授权内嵌并分发游戏 Skill，允许 scripts/sync-skills.cjs 中固定 allowlist 的完整文件；本机专用成品检查仍禁止分发。

发布仅限用户在此应用明确选择的目录。Skill 本机专用的 `cocos-game-finished-product-check` 不允许进入共享版本。目录内不跟随符号链接，不执行 Skill 脚本。个人项目路径不上传服务。

历史内容在发布端按内容哈希去重；订阅端只保留当前版本与轻量索引，恢复历史需主动下载。下载校验失败不替换当前版本。提示词/附件生成与真实发送、AI 执行完成分开显示。

必要验证：`npm test`，原生 smoke test 与 Mac 构建。Windows 产物结构检查不能代替 Windows 实机运行。测试使用临时数据目录，退出测试实例，用户交付预览另有明确用途。

用户于2026-10-29要求完整英化/重塑ZIP并正式发布；为补齐当前英化入口的实际依赖，allowlist增补cocos-game-check、remake-core、remake-art，共18项。仍排除本机专用cocos-game-finished-product-check。界面仅显示两个包，内部组件按需组合。
