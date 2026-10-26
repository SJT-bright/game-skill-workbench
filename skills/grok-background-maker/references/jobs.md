# 后台任务格式

运行器使用 Python 3.9+ 标准库。本机 CLI 从实际PATH及用户目录查找：Windows候选为 `.grok/bin/grok.exe`，macOS为 `.grok/bin/grok`，也可通过 `--cli` 指定。先用 `--dry-run` 检查格式和并行写入冲突；正式运行再查询已登录账户的可用模型。不会自动登录、修改全局模型或落到 API key 通道。

```json
{
  "model": "grok-4.7-build-fast",
  "max_parallel": 3,
  "timeout_seconds": 1800,
  "max_turns": 30,
  "jobs": [
    {
      "id": "content",
      "cwd": "/absolute/project",
      "prompt_file": "/absolute/task-input/content.txt",
      "write_paths": ["/absolute/project/content.md"],
      "expected_files": ["/absolute/project/content.md"]
    },
    {
      "id": "module",
      "cwd": "/absolute/project",
      "prompt_file": "/absolute/task-input/module.txt",
      "write_paths": ["/absolute/project/src/new-module"],
      "expected_files": ["/absolute/project/src/new-module/index.py"]
    }
  ]
}
```

路径均为绝对路径。`cwd` 是已存在的工作目录，`prompt_file` 是非空 UTF-8 文件。`write_paths` 声明该进程可修改的文件或目录；不同任务的这些路径不能相同或互相包含。文件任务的 `expected_files` 至少列出一个制作/修改后的文件，须属于该任务的 `write_paths`；运行器记录前后哈希，存在不等于内容合格。

分析、摘要、翻译、文案、资料查询等只需要返回文字的任务，使用结果模式：省略 `write_paths` 和 `expected_files` 或均设为 `[]`。文字保存到该任务回执目录的 `result.txt`，主 Agent 核对后向用户交付。用户没有指定项目时可将 `cwd` 设为本次任务的独立工作目录，不必要求用户提供文件名。需要联网查询时在任务中设置 `"enable_web": true`；默认 `false`，仅影响该 Grok 进程，不修改全局配置。查询结果仍需核对原始来源与链接。

`max_parallel`、`timeout_seconds`、`max_turns` 均须为正整数，可按实际任务调整。运行器不让 Grok 再启动模型子代理，避免在既有并行任务之外自行增加模型调用。脚本和渲染进程可按任务正常使用。

```sh
python3 "<SKILLS_DIR>/grok-background-maker/scripts/run_jobs.py" \
  --manifest /absolute/task-input/jobs.json --dry-run

python3 "<SKILLS_DIR>/grok-background-maker/scripts/run_jobs.py" \
  --manifest /absolute/task-input/jobs.json \
  --out-dir /absolute/task-receipts/new-run
```

输出目录必须是新目录，避免覆盖回执。运行器每次启动及完成任务都会刷新 `summary.json`，并输出简短 JSON 进度。每个任务目录保存 `request.txt`、`raw.json`、`stderr.txt`、`result.txt` 和 `receipt.json`；回执记录 PID、UUID、指定模型、实际模型用量、退出码、时间、预期文件哈希与变更情况。只有正常结束、模型用量得到确认，且文件任务有预期文件或结果任务有非空文字时，才标为 `completed_pending_review`，仍需主 Agent 验收。费用没有报告时为 `null`。

默认通过 CLI 的非交互 `always-approve` 模式（`--permission-mode bypassPermissions`）执行已授权本地工作，避免脚本调用停在无人应答的权限询问上；已配置的 deny 规则、hooks 和管理限制仍生效。内置联网工具默认关闭，可按任务需求用 `enable_web` 启用；MCP 调用仍拒绝。**声明路径不是沙箱**，主 Agent 必须按任务授权安排工作、检查实际改动。通过 Bash 联网获取材料若确有必要，应在任务 prompt 中明确范围；外部发送与发布按具体任务的既有授权执行，不因指定 Grok 而增加权限。

监控时读取摘要和必要日志，避免向对话打印整份原始输出、材料或环境变量。正常执行使用 `exec_command` 返回的 session ID 跟进。取消可向该 session 发送 Ctrl-C，或向运行器自身 PID 发送 SIGTERM；运行器收到信号后停止队列并清理其 Grok 进程组。不得按软件名批量杀掉其他 Grok 会话。超时同样清理对应进程组并报告失败；不自动回滚文件、不自动重试。

文档命令中的 `<SKILLS_DIR>` 取本次实际加载的 skills 目录，先解析再执行，不沿用其他电脑的用户名或盘符。Windows使用已安装的 `py -3 -X utf8 -B`，macOS使用实际 `python3 -B`；不为示例路径重新安装解释器。

