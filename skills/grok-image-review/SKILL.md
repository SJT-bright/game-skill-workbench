---
name: grok-image-review
description: 已停用。所有图片由 Codex 自己读取，不调用 Grok 图片识别。
---

# Grok 图片识别已停用

用户于 2026-11-01 明确要求：以后所有读图都由 Codex 自己完成。

不要运行本目录的 Grok 图片识别脚本，也不要将图片转交 Grok。包括截图文字、姓名/学号/日期、封面字段、报错文字、图表和排版验收，均由 Codex 直接查看实际图片并核对。

此规则取代本技能此前的自动分流、独立转录和读图前先调用 Grok 的要求。历史脚本与资料仅保留，不作为执行入口。

## 万一有旧流程还在调脚本（生成时预防 #39）

`scripts/review.py` 读到本页「已停用」就不调 Grok：只在回执目录写 `receipt.json` 和 `fallback.json`（`status: fallback_required`，`next: main_agent_reads_image`），退出码 3，不写 `result.json`。看到退出码 3 或 `fallback.json`，就自己打开图片核对，不能写成「已用 Grok 读取」或「已通过」。

用户以后重新启用 Grok 时才加 `--force-grok`。那时脚本每次最多再试 `--retries` 次（默认 1，最多 2），只在超时或进程失败时重试；回复不合格不重试。每次尝试的原始输出都留在 `raw.<n>.json` 和 `stderr.<n>.txt`，最后一次另存为 `raw.json` 和 `stderr.txt`；全部失败同样写 `fallback.json`、退出码 3。
