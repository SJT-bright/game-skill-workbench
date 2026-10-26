# 换电脑后的首次绑定

本Skill和cocos-game-to-english为两个主Skill，按同一skills根目录安装。定位从当前实际加载的SKILL.md开始，用相对路径寻找scripts、references和兄弟Skill；不要沿用原电脑用户名、项目路径、端口、应用副本、会话ID或容量台账。

先按[Windows首次启动与依赖就绪](windows-bootstrap.md)读取包、检测软件、选择本轮执行模式。

## 安装与依赖

迁移包提供两个完整主Skill，及其所需的mobile-touch-computer-use、ego-browser、grok-background-maker、grok-image-review、grok-delegate配套定义/脚本；不包含任何账号、缓存、历史验收回执、游戏或AI应用二进制。

在迁移包根目录运行提供的install_skills.py。默认安装到当前CODEX_HOME/skills，未设置CODEX_HOME时使用当前用户主目录下.codex/skills；已有两个主Skill会先备份，已有配套依赖默认保留。安装后重开/新建Codex会话，确认两个主Skill已发现；旧对话不保证刷新。

脚本需要Python 3.10+，按目标机用python3或python调用；外部运行时需要Cocos Creator、Ego Lite/ego-browser、用户指定的七个AI应用，以及Grok CLI与用户本人的有效登录。支持Skill定义不等于运行时已安装。Codex会话须有实际Computer Use和内置image_gen能力；普通文本聊天窗口不能因此获得这些工具。已有支持Skill版本不符时先核差异再决定是否替换，不能改全局规则或账号来强行运行。

## 七应用现场登记

先读取当前Computer Use工具文档和应用/窗口库存，按真实平台定位WorkBuddy、AStudio、WorkBuddy国际版、Qoder CN、Qoder、OpenCode、Grok。macOS按名称/实际路径/bundle核对，Windows/Linux按工具文档的windowId；找不到或有多个副本时进一步核对，不能照抄原电脑路径。

依[路由](local-app-routing.md)分角色。逐通道核工作区、现有任务/草稿、模型、工具、限制与全局占用；默认角色不是“已可用”。Grok后台另核当前CLI路径、现有登录和UUID回执，不能从导出包导入原电脑凭据。缺一个通道，在指定七个内按同角色备选推进；没有合格候选时保留待派，主线继续关键判断或直接运行A类确定性工具。

第一次实际制作时，新建本游戏的独立工作副本、保护文件、任务台账和资源锁；输入/规范/输出都绑定新路径与SHA。重新建立本版GUI/触屏/包证据；历史通过和原电脑截图不带到新版本签收。

## 原则保持

主线保留C类判断和关键补丁、内置生图及最终视觉/业务验收，执行者只做A/B有界工作；QA不改业务/断言，生产者不自验。Qoder两版共享容量、两个WorkBuddy独立；7应用是执行池，不要求同时运行。外部发送/付费/发布仍按该次任务实际授权，迁移不增加权限。
