# 阶段与节点计时

计时只观察执行，不是质量门禁，不改变美工、玩法或出包是否通过。计时 JSON、报告、暂停记录不能加入质量规则指纹；计时落盘失败应显示 `not_recorded`，仍继续真正的制作命令，不宣称已计时。

## 本轮身份和节点

开工先启动独立 `run_id`，取 `source`（中文源码）、`handoff`（已通过交接包）、`returned`（交付后返工）或 `maintenance`（Skill 维护）路线。项目的旧 JSONL 保留不覆盖。先 `status` 恢复现场，再继续开放节点，不能凭压缩后的对话猜用时。工程制作与维护 Skill 分开记录；未采样的前置准备保留为未记录，不倒填估计成实测。

```sh
T=/absolute/path/to/cocos-game-to-english/scripts/stage_timer.py
P=/absolute/path/to/game
python3 -B "$T" --project "$P" start --run-id game-20261108 --route source
python3 -B "$T" --project "$P" stage 1
python3 -B "$T" --project "$P" begin '资源盘点' --span-id inventory-1
python3 -B "$T" --project "$P" end '资源盘点' --span-id inventory-1
python3 -B "$T" --project "$P" done
```

阶段仍为五段：1 盘点、2 修改、3 英文试玩、4 试玩改进、5 补缺与写包核对。每次进入、完成和遇阻都向用户说明具体节点名、刚完成的内容、实耗、下一节点。图片、字幕、音效、平台适配、构建、页面采集和文件核对各自命名，不用一个数小时的“完整检查”覆盖所有动作。`begin/end` 按 `span_id` 配对；同名并行必须用不同 ID，`--parent-id` 关联父任务，`--who` 说明执行者。阶段切换不伪造子步骤结束；跨阶段区间按交集分配，产物数量只在实际结束阶段计一次。

## 命令自动计时与实时输出

构建、准备清单、切图、核对、采集批次和写包用 `run` 包装实际命令。包装器不重试，不吞退出码，不等整段结束才显示输出；子命令自身需要实时输出时仍应使用它自己的无缓冲选项。`--log` 可保留原输出。相同 `--span-id` 是稳定节点名，每次命令有独立实际 span，方便识别构建或返工次数。

```sh
python3 -B "$T" --project "$P" run --span-id build/web --cwd "$P" --log "$P/docs/timing/build.log" '构建导出' -- /absolute/path/to/builder --project "$P"
```

命令结束保存 `monotonic_seconds`、退出码和 completed/failed/interrupted；不能把失败执行说成检查通过。硬杀或断电未落下结束记录的 span 保留开放，不猜测耗时。内层检查已有实测秒数可引用，不再把同一共享批次秒数写到每个 suite 后相加。父子和并行命令区间取并集得到总执行区间，不把子项相加当墙钟。脚本不会测出“AI 纯计算时间”。

## 暂停、等待和继续

```sh
python3 -B "$T" --project "$P" pause '用户暂时停止'
python3 -B "$T" --project "$P" resume
python3 -B "$T" --project "$P" external-begin image-job-1 '生成服务排队'
python3 -B "$T" --project "$P" external-end image-job-1
python3 -B "$T" --project "$P" ask '等待用户试玩意见'
python3 -B "$T" --project "$P" back
python3 -B "$T" --project "$P" abort '明确取消本轮'
```

暂停从手记工作区间扣除；工具在暂停期间若仍真实运行，其实测耗时保留。用户等待、外部等待、暂停可能与后台工作重叠，报告列出重叠而非强行相减。`abort` 停止当前轮墙钟并保留未完成状态；它只关闭计时，不会擅自杀其他工具。实际工作取消时，依工具本身接口停止任务。已交付后的新 stage/begin/run 或直接启动试玩服务自动开始独立返工轮次，隔夜闲置不混入返工用时；也可显式 start。未完成轮次不能被另一个 start 隐藏。

## 试玩 ready 挂钩

英化入口 `serve_preview.py` 自动测“启动请求→候选核准、入口可读、服务 ready”。不要用外层 `run` 包住长期保留的服务，否则会把服务存活当制作耗时。中文原版无 snapshot 也可在真实 ready 后记录；启动前门禁、绑定或入口读取失败不记已给链接。正常英文与交付后美工返工使用相同的发布计时：稳定 Web+Native 内容身份去重。同版重开不新增轮；Native 改变而 Web 未变仍是新版。授权文件时间戳单独变化不当作新画面。ready 只证明入口可用，不能冒充用户已看到窗口或完成试玩。

## 汇报口径

```sh
python3 -B "$T" --project "$P" status
python3 -B "$T" --project "$P" report --all
python3 -B "$T" --project "$P" --run-id game-20261108 report --all
```

`docs/timing/stage-timing.jsonl` 是原事件；`timing-summary.json` 含每阶段、每节点精确秒数，`timing-report.md` 供阅读；各轮报告同时保存在 `docs/timing/runs/`。汇报必须区分总墙钟、已完成执行区间并集、工具区间并集、用户等待、外部等待、暂停和未记录空档。开放节点只表示当前已过多久，不是已完成准确实耗。原“你等我”仅保留作交付延迟，不代表 AI 工作时间。

发生系统时钟跳变时命令 monotonic 秒数仍有效，`wall_interval_totals_valid=false`；此时不能把墙钟并集合计当准确值。`--at` 只补有原始证据的手记事件，不用于 `run`，更不能拿预估倒填真实测试成绩。参考分钟只提示排查阻滞，不能判定模型出错、强制重测或截断任务。比较优化效果需同一输入/范围与实际次数，未知基线应标未知；不能用脚本提速代替整个制作周期提速。
