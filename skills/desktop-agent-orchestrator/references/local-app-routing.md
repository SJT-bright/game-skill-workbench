# 指定七应用的路由与实际操作

本执行池仅有WorkBuddy、AStudio、WorkBuddy国际版、Qoder CN、Qoder、OpenCode、Grok；用户于2026-10-17明确指定。其他应用不自动补位。先选角色，再核工具/模型/限制和全局容量；下表不是模型能力排名。

| 应用/id | 默认职责 | 合格同角色备选 | 容量组/上限与macOS身份提示 |
|---|---|---|---|
| WorkBuddy / workbuddy | 原包校验、资源/中文候选清单 | AStudio/OpenCode | workbuddy/3；com.tencent.workbuddy.mac |
| AStudio / astudio | 已定短文案草案、英文/图片映射与资源接线 | WorkBuddy；UI绑定可由Qoder CN | astudio/1；cn.xfyun.acode |
| WorkBuddy国际版 / workbuddy_ai | 独立GUI/触屏操作与原始证据 | Qoder独立QA会话/AStudio，须确有对应工具 | workbuddy_ai/3；com.workbuddy.workbuddy-ai |
| Qoder CN / qoder_cn | 已定方案的独立UI和状态呈现 | AStudio/Qoder | qoder/两版合计3；com.qodercn.app |
| Qoder / qoder | 非关键已定补丁、既定断言用例；独立QA补位 | Qoder CN/AStudio | qoder/两版合计3；com.qoder.app |
| OpenCode / opencode | 构建、固定回归、HTTP/指纹、既定writer | Qoder/WorkBuddy | opencode/1；ai.opencode.desktop |
| Grok / grok | A16–A18独立包核验、原文/OCR | 国际版/OpenCode独立会话 | grok/桌面常规5最多6；后台单批默认3；com.grokapp.desktop或已核Grok CLI |

WorkBuddy国际版以应用身份与实际界面核对，不按语言猜。Qoder CN与Qoder是不同角色通道，但多份安装和两版共用的额度/容量不能重复计数。目标平台以实时应用库存定位；表中macOS标识只是匹配提示，不用于Windows/Linux伪造身份。

## 权限、工具与独立性

AStudio只能按主线已定用途/术语/映射实施，最终英文与奖励含义主线核。Qoder两版不接C域根因或关键补丁。国际版QA只采证、不改业务或断言。OpenCode产包后由不同会话独立读包；Grok在本工作流明确授权范围内仅运行既定核验命令/读回原始字段，不决定放行标准。所有C类判断由主线保留。

需要本地文件/终端/可信触摸的任务，必须核对应工具；普通文字回答不等价。独立核验用只读冻结输入、独立输出和断言。生产者不能同会话自验；会话身份按app+conversation，Grok CLI用实际UUID会话及回执，不用桌面进程数当运行数。

## Computer Use与后台入口

第一次CUA调用只做工具规定的初始化，例如getState；读取该环境返回的文档后再操作。macOS按完整app路径取应用；Windows/Linux按当前工具文档用实际windowId。遇同名/同bundle副本先确定实际路径，不能启动两份扩容。

先核准确工作区/会话/已有运行状态和输入框；已有草稿保留且不发送，换确认空白的新工作会话。每次动作后刷新AX树取新索引，不猜坐标或未公开后台接口。提交后读同会话任务ID/消息，再核工具活动或本版产物：输入不算送达，排队不算开工。

Grok的本工作流包核验读取已安装grok-background-maker，使用其后台CLI入口、独立UUID、现有登录通道和原始回执。执行路径从当前Skill目录定位，不沿用旧用户名。先dry-run核manifest/写冲突；缺CLI/登录记录不可用，不把修Skill/导出本身变成无关模型任务。OCR和原文分别用grok-image-review/grok-delegate；普通自动窄白名单不被扩大。

逐通道记录installed/UI或CLI可读/project_verified/tools_verified/dispatch_confirmed/output_verified，不能跳级。实际模型、限制、容量、观察时间/来源分别记，未知不记0/可用。不购买额度或无授权切付费模型。遇系统异常有依据重试一次，无新进展保留证据并选同池备选；旧写者未停仍占锁，只可隔离副本诊断。

## 派发前机械检查

在本Skill根目录运行以下命令；python3可替换为目标机的Python3解释器：

```sh
python3 scripts/check_dispatch_contract.py --task /绝对路径/task.json --ledger /绝对路径/ledger.json --report /绝对路径/preflight.json
```

任务/台账字段见[任务书](task-brief.md)。默认Grok为desktop记录；实际后台用transport=grok_cli、app_path=已核CLI可执行文件、cli_ready=true和UUID/回执，并保留项目/工具/模型/限制的真实核对字段。其他六家不能借此使用未验证后台通道。

ready只证明声明完整、没有已记录冲突且有合格候选，不证明语义分类/额度真实或已送达。只在当前Agent工作回合执行，不是常驻daemon；旧窗口需重读。迁移依赖与路径见[首次绑定](portability.md)。
