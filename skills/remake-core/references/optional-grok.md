# Mac可选Grok CLI

Grok是可选加速项，不是游戏制作、验收或分享此Skill的必装依赖。`grok_mode=auto`按本次模式检测现有CLI；`off`完全不调用，用户说不用Grok/完全单应用时优先关闭。用户本人Mac可用时实际CLI执行白名单；分享给没有Grok的人，由主Agent按相同标准完成。只修改Skill/导出时不为证明调用而浪费模型请求。

## 有界分流

- 工具能准确完成的解析/扫描/映射/哈希/构建/回归，直接工具优先，不为用Grok增加一次模型调用。
- 未明确指定更广任务时，自动Grok仍只有[原文/字段搬取](../../grok-delegate/SKILL.md)及[清晰图片读字](../../grok-image-review/SKILL.md)。主Agent保留完整原件和对应关系。无Grok/失败时主Agent或解析器接手；读字任务不可用需简短说明接手。
- 在用户明确启用Grok协作且主线已给定命令/输入/断言的本工作流，可执行固定独立回解/CRC/全SHA/根文件核验。通常现成脚本主线直接跑更省，不机械包一层模型。
- 不自动把规则设计、摘要筛证据、技术根因、关键补丁、美术/最终验收交给Grok。用户明确指定某个Grok任务时读取后台Skill按该范围执行，不因auto扩大权限或改模型/账户。

## 调用，不只写名字

从实际skills根定位`grok-background-maker`；不写死作者用户名。执行前只有当前原文/图片任务需读对应专用Skill，固定命令任务才读后台格式（重塑包 grok-background-maker 板块，英化包不含）。原文/OCR继续使用各专用生产入口，不用普通聊天回答假冒图片识别。

固定命令任务可以使用本Skill的降级包装器（路径按实际目录）：

```sh
python3 scripts/run_optional_grok.py --mode auto --manifest /绝对路径/jobs.json --out-dir /绝对路径/新回执目录 --dry-run
python3 scripts/run_optional_grok.py --mode auto --manifest /绝对路径/jobs.json --out-dir /绝对路径/另一新回执目录
```

包装器检测`PATH/grok`及当前用户`.grok/bin/grok`，需要时可用`--cli`指定。Grok存在仍不代表已登录，正式执行由既有运行器核原登录/模型；不自动登录、不换API key、不购买额度、不改全局hooks/权限。后台执行而不打开桌面窗口。

manifest仅包含一项窄任务（并行用户明确需要时按独立任务安排），示例结构：

```json
{"model":"grok-4.7-build-fast","max_parallel":1,"timeout_seconds":120,"max_turns":4,"jobs":[{"id":"fixed-package-check","cwd":"/隔离目录","prompt_file":"/输入/任务.txt","write_paths":["/输出/核验.json"],"expected_files":["/输出/核验.json"],"enable_web":false}]}
```

prompt给出主线既定的唯一命令、冻结输入、只读文件、唯一输出、实际退出码和核验字段，要求不得转派/修改断言。不得粘贴全部项目规则/历史。`cwd`选干净隔离目录，避免CLI自动读取项目巨型历史；确需项目规则提供与该任务有关的原文及出处。未知模型需按专用Skill先核可用性，不静默替换。

## 回执与降级

`--dry-run`只校验任务格式/冲突，不发模型请求，也不证明登录。正式任务保留既有UUID、原始输出、退出码和文件SHA；包装器只返回简短摘要及回执路径。`completed_pending_review`仍由主线核验。无CLI/缺配套、未登录、网络/额度/超时或格式问题返回`skipped`或`fallback_required`，没有Grok产物时不写通过。

默认省Token路线一次失败就回主线，不自动重试。先确认运行器停止该任务的进程组、核实际差异，文件租约释放后才能接手；保留失败回执而不降低功能/奖励/包门禁。工具本身报错不让整个游戏流程退出。即使写路径列出，也不是操作系统沙箱。
