# 游戏工作台

Mac / Windows 玻璃质感贴边浮窗，管理本机游戏、读取 Codex 对话、推送新版 Skill，并检查工作台自身更新。

[下载 Mac / Windows](https://github.com/SJT-bright/game-skill-workbench/releases/latest) · [MIT 许可证](LICENSE)

## 使用

打开后以贴边小窗显示，鼠标划入自动展开（也可点击）。鼠标移开或窗口失焦保持打开；点击收起按钮才回到贴边入口。手动收起后需移出再划入，避免立即弹回。默认读取本机 Codex 的近期游戏对话，按“玩法制作、玩法结束、美工制作、待试玩、检查、已完成”整理。依据不明确时显示待识别，可右键修正。卡片显示对应对话的运行状态、任务时长和以万／百万／亿表示的 Token，右键“记录”查看阶段切换与统计范围。缺失记录显示未知，不将上下文窗口或账户额度当作单游戏用量、费用。没有 Codex CLI 时保留已有记录，仍可手动添加游戏和关联对话。

选择游戏和 Skill，点击“更新 Skill 到对话”；也可以右键 Skill 选择“推送新版 Skill”。发送内容包含完整 Skill 本机路径和文件树哈希，要求使用新版继续本对话后续制作。队列回执与 AI 完成分开。发送超时不自动重试。

游戏右键可打开对应对话、更新 Skill、检查或试玩。拖动浮窗靠近屏幕边缘会吸附，收起为 32×88 的侧边入口，展开 420×650。

## 更新

- **工作台软件**：读取本仓库 GitHub Release 的 `gamedesk-update.json`。启动及每5分钟自动检查，休眠恢复后补查。发现新版时通知；点击“更新并重启”下载、校验并替换应用，保留个人数据。成功启动后移除本次更新的旧应用副本与下载缓存。
- **Skill 文件**：安装包内置 15 个允许分发的游戏 Skill，首次离线即可使用。`skills-feed` 分支提供完整文件与内容去重的版本记录，工作台后台每分钟检查并自动下载变更文件，随后提示更新摘要并保留未读标记；无需打开仓库或手动获取。断网后恢复连接会在后续检查补齐。应用需要保持运行（收起浮窗即可）；退出期间的更新在下次启动补齐。历史恢复仅下载所选版本，主动恢复的版本保持锁定，避免被自动更新覆盖。
- **公开更新**：源码、Release 安装包和 Skill 文件公开可读，无需申请仓库访问权限。发布变更仍需要维护者 GitHub 写入权限；凭据留在本机，安装包不包含发布者登录信息。匿名 GitHub API 访问受平台限流影响。
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

## 开源许可

项目原创代码和文档采用 [MIT](LICENSE)，允许使用、修改和再分发。第三方组件保留原许可，见 [第三方声明](THIRD_PARTY_NOTICES.md)。个人游戏、Codex 对话及本机统计不作为公开仓库内容上传。

## 维护者无窗口发布

`npm run skills:publish` 只同步 allowlist 中的本地 Skill 源目录到发布仓库，不读取游戏或对话。可由系统后台任务每分钟执行；无变更时只检查本地哈希，失败在下轮重试。状态保存在维护者电脑的 `GameDesk-Publisher` 目录，与使用者工作台独立；GitHub 发布仍需要维护者自己的写权限。macOS 后台任务无需打开悬浮窗口。
