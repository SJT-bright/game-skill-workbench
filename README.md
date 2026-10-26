# 游戏工作台

Mac / Windows 玻璃质感贴边浮窗，管理本机游戏、读取 Codex 对话、推送新版 Skill，并检查工作台自身更新。

## 使用

打开后以贴边小窗显示，点击展开。默认读取本机 Codex 的近期游戏对话，按“玩法制作、玩法结束、美工制作、待试玩、检查、已完成”整理。依据不明确时显示待识别，可右键修正。卡片显示对应对话的运行状态、任务时长和已记录 Token，右键“记录”查看阶段切换与统计范围。缺失记录显示未知，不将上下文窗口或账户额度当作单游戏用量、费用。没有 Codex CLI 时保留已有记录，仍可手动添加游戏和关联对话。

选择游戏和 Skill，点击“更新 Skill 到对话”；也可以右键 Skill 选择“推送新版 Skill”。发送内容包含完整 Skill 本机路径和文件树哈希，要求使用新版继续本对话后续制作。队列回执与 AI 完成分开。发送超时不自动重试。

游戏右键可打开对应对话、更新 Skill、检查或试玩。拖动浮窗靠近屏幕边缘会吸附，收起为 32×88 的侧边入口，展开 420×650。

## 更新

- **工作台软件**：读取本仓库 GitHub Release 的 `gamedesk-update.json`。发现新版时通知；点击“更新并重启”下载、校验并替换应用，保留个人数据。成功启动后移除本次更新的旧应用副本与下载缓存。
- **Skill 文件**：安装包内置 15 个允许分发的游戏 Skill，首次离线即可使用。`skills-feed` 分支提供完整文件与内容去重的版本记录，客户端按需获取变更文件，历史恢复仅下载所选版本。
- **仓库权限**：当前为私有仓库。使用者需有仓库访问权限，并在本机 GitHub CLI 登录。凭据留在本机，安装包不包含发布者登录信息。设置中提供 GitHub 登录入口。
- **可选独立服务**：保留局域网/HTTPS Skill Hub，发布者可选择目录自动发布；在线通过 SSE 推送，客户端每分钟补查。

默认数据目录：系统 Application Support / AppData 下 `GameDesk-Skill-Personal`，与原 Mac 总管工作台隔离。个人游戏、聊天、登录与连接密钥不进入源码或安装包。

## 维护与发布

```sh
npm ci
npm test
npm start
npm run build:mac
npm run build:win
```

在维护者电脑读取最新允许分发的 Skill：

```sh
npm run skills:sync
```

工作台中也可在“Skill 发布”选择本机维护目录并勾选自动发布：应用运行时检查文件变化，通过 GitHub API 提交变化文件，不克隆整个项目。

检查文件变更后提交 `skills/` 并推送到 `main`。`Publish Skill files` 工作流自动更新 `skills-feed`。本机专用 `cocos-game-finished-product-check` 不在分发 allowlist 中。

修改软件版本号后，在 GitHub Actions 手动运行 `Release desktop`：分别构建 Mac arm64 和 Windows x64，运行测试，发布安装包与绑定 SHA-256 的软件更新清单。工作台软件和 Skill 可以独立发布。

Windows 首次使用可下载完整便携包并运行 `GameDeskSkill.exe`；另有首次联网下载官方运行时的轻量启动包，不要求安装 Node.js。Mac 当前使用本地 ad-hoc 签名，未公证。Windows 自动化构建与物理设备视觉验收分开记录。

源码构建器使用 Node.js 标准库及系统解压、签名工具，运行时为官方 Electron 43.4.1，并核对上游 SHA-256。`ELECTRON_ARCHIVE` 可指定已下载的对应运行时 ZIP。Intel Mac 可设置 `ARCH=x64` 构建。

`npm run preview` 提供标记为演示的交互预览；不会读取真实聊天或发送消息。
