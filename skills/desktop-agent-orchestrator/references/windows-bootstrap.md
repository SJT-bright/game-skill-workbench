# Windows首次启动与软件就绪

新任务先询问本次是否启用桌面多Agent；人类本轮已明确要求调动时不重复问。单应用模式只检测实际制作需要的Python/Cocos/浏览器，不要求安装七个AI应用。多Agent模式检测固定七应用，缺失时按当前下载/安装授权准备软件。包内的软件目录和上次联调记录只是来源与历史证据，不是新机可用性证明。

## 读取迁移包与游戏启动包

迁移包根目录的`Windows首次启动.cmd`使用本包的安装器、软件清单与检测脚本。已有Python3.10+时先完整核包，再安装两个主Skill和缺失配套；无Python时从Python官方Windows页下载稳定安装程序，显示签名并打开正常安装向导。安装、登录、协议、验证码及系统要求用户操作的步骤分别保留状态，不代替用户接受条款，不复制旧机登录态或关闭安全防护。

可以把游戏源码/策划ZIP或目录作为启动参数提供。脚本生成输入路径、SHA、文件清单、实际Cocos声明版本及材料类型的盘点报告；压缩包路径/CRC核对后只读清单与小文本，不执行材料内脚本。完整Cocos工程交`cocos-game-to-english`；纯GPT策划/关卡启动包使用配套`cocos-game-from-starter`先创建真实工程再接英文/美术/触控/IAA/Native流程。盘点器不代替主线阅读全部相关正文和玩法规格。

## 下载和安装缺失软件

运行`scripts/bootstrap_windows.py --bundle-dir <解压目录> --mode multi --download`，默认报告与下载放当前用户LocalAppData下独立目录，不写入已校验的迁移包。软件清单在`assets/windows-software.json`；优先官方已核API/下载链接，下载字节存临时文件、核大小/官方摘要（有时）及实际SHA后更名。网络/接口/架构变化报needs_resolution，主线按官方下载页用浏览器继续解析，不猜URL、不换相似产品或把网页HTML保存成exe。

下载不等于安装，安装不等于登录或可调用。仅在该次用户授权软件安装后，使用正常安装向导安装；不自动接受协议、不购买、不静默变更账户或系统安全设置。可明确使用脚本`--launch-installers`打开已通过Windows Authenticode签名检查的安装程序；缺签名/来源不明不执行，保留待核。官方Grok安装脚本下载后只作准备，由主线核来源与内容后在当前安装授权范围执行，随后用户本人完成登录。

WorkBuddy国内/国际版、Qoder两版必须按显示名、发布者、安装路径和实际窗口分别登记，不能用安装了一家冒充另一家。已存在同名软件默认不重装或重启，保留草稿和工作。Cocos按工程实际声明版本安装，不能为省事强制升级项目。软件页面会更新，首次使用复核官方来源。

## Windows工具差异与验收

- 不使用`/Applications`、macOS bundle、`open -a`、AppleScript或旧端口。按当前Computer Use文档读取库存/窗口，Windows用准确windowId绑定；有多个窗口先核标题。
- Python用当前可执行解释器或`py -3`；文件路径用参数数组/正确引号，包含空格中文仍逐字节核验。Grok CLI默认查当前PATH及`%USERPROFILE%\.grok\bin\grok.exe`，不查原机用户路径。
- 配套Grok运行器的迁移版有Windows进程分支，只停止该次运行器创建的子进程树。此代码分支测试不能写成目标Windows已运行；首次真机重做版本、登录、模型、UUID、退出码和回执。
- Windows统一使用Google Chrome（谷歌浏览器）。检测已安装Chrome，缺失从Google官方页面下载；使用迁移版mobile-touch-computer-use与chrome-mobile-testing执行手机模拟。Playwright依赖准备在独立venv中，通道固定chrome，先配置UA/视口/DPR/触摸再加载游戏，保存原始可信触摸、引擎输入链和实际按钮状态。禁止仅缩窗口或用鼠标冒充触屏，缺能力仍保留待验。
- Windows Codex若没有实际Computer Use工具，Skill不能添加这项能力；桌面多Agent派发保持blocked，主线可继续单应用工作并披露。只有实际存在的image_gen调用能满足生图要求。

首次多Agent使用需运行独立合成任务：确认同会话task_id已送达、看到真实执行、回收独占产物、独立核对原始结果。包生产与核验分开；超时/连接断开/无工具保持失败，不能将“安装完成”“窗口可读”填为可派发。新机联调写自己的记录，原机联调不能签新机的通过。

Chrome依赖由迁移包support-skills/chrome-mobile-testing/scripts/prepare_chrome.py准备；bootstrap的--download会在Windows调用它并写入chrome_runtime。需要进一步手动恢复时使用报告里的实际Python，不运行playwright install下载其他浏览器。浏览器文件来源及安装状态与Python依赖状态分别记录。
