# 输入快照、阶段交接与用量工具

只在跨阶段接续、变更后选择复测或阶段用量复盘时读本页。工具使用Python 3.10+标准库，无需安装新依赖；Windows使用`py -3 -X utf8 -B`，其他环境使用实际Python 3。`<SKILL>`、`<GAME>`、`<LOG_DAY>`、`<ROOT_ID>`替换为实际路径/ID，命令不是未经替换的可运行值。

## 检查输入快照

沿用既有检查ID，在项目现有证据目录维护一个小JSON，不重复创建另一套验收表。例如：

```json
{
  "schema_version": 1,
  "checks": [{
    "id": "UI-CORE-INPUT",
    "scope": "Web-actual-engine",
    "dependencies": ["src/CoreControls.js", "art/buttons", "art/manifest.json"],
    "tool_files": ["tools/test-core-input.py"],
    "context": {
      "browser_version": "actual-installed-version",
      "engine": "actual-project-version",
      "viewport": [390, 844],
      "dpr": 2,
      "protocol": "trusted-touch-v1"
    },
    "evidence": ["evidence/core-input-result.json"]
  }]
}
```

路径依实际工程修改，不能照抄不存在的文件。dependencies可为项目内文件或目录，目录内新增/删除文件都会改变指纹；源目录不能指向工程外。tool_files可显式引用项目内工具或外部已安装工具文件；工具版本、环境、参数/种子、目标Runtime、比例/DPR写入context，必要时把配置文件纳入dependencies。不同证据层使用不同scope/ID。不得省略实际消费者、图集/meta或引用清单造成虚假的“未变化”。

```text
python "<SKILL>/scripts/check_input_snapshot.py" snapshot --project "<GAME>" --checks "<GAME>/docs/check-inputs.json" --out "<GAME>/evidence/inputs-before.json"
python "<SKILL>/scripts/check_input_snapshot.py" snapshot --project "<GAME>" --checks "<GAME>/docs/check-inputs.json" --out "<GAME>/evidence/inputs-after.json"
python "<SKILL>/scripts/check_input_snapshot.py" compare --before "<GAME>/evidence/inputs-before.json" --after "<GAME>/evidence/inputs-after.json" --out "<GAME>/evidence/recheck-plan.json"
```

基线必须对应上次实际执行的输入/工具/环境与原始证据；由真实测试记录绑定其指纹，不能在改动后把旧结果补挂到新快照。第一次还没有有效旧证据时，先执行所需检查再记录基线，不凭工具生成通过。快照输出放在被声明输入目录之外，避免把工具自己的结果纳入下次指纹；不要将整个project/evidence目录作为所有检查的依赖。

compare只输出：

- `needs_run`：新增检查或输入/工具/上下文/项目位置变化。
- `cannot_reuse`：缺失输入、缺失/变化/未绑定的证据，应恢复缺件或定位证据。
- `review_existing_evidence`：声明输入与证据相同。仍需确认旧结果确实通过、覆盖范围完整、绑定真实、没有未纳入的依赖。
- `removed_checks`：配置中被删除的检查，必须说明是否仍适用，不能借删ID减少验收。

两工具都只独占新建输出文件，已存在的路径（含硬链接/符号链接别名）直接拒绝；快照/比较输出也不能放进声明的输入、工具或证据目录。重跑使用新文件名保留旧基线，不覆盖源码或原始证据。

所有结果`is_acceptance_result=false`，快照命令exit0只代表工具执行完成；检查缺件在counts.incomplete列出。工具不运行测试、不读取截图判审美、不决定样本量，也不解锁writer、60ID或手机门禁。完整证据留文件，主线只读摘要和具体变化项。

## 阶段交接

沿用现有progress/handoff路径，不新增重复状态。阶段结束或上下文提醒时只保留：目标与当前授权、实际路径/输入和候选指纹、已做与待做、活跃问题及负责人、原始证据链接、恢复命令与条件。旧版本/待决/下一步移入日志并标替代关系。没有新输入不重复盘点。

能继续或工具可续接时自主推进；确有客户端限制才说明用户需要做什么。新会话会增加首次非缓存输入，不以固定频率换会话冒充节省。共享规格和进度由一个写者维护，独立任务才并行。

## 用量复盘

用量脚本只读取明确指定日志目录中的元数据，再解析选中根会话及能找到的后代；不要为了找用量扫描整个账号历史。ROOT_ID从当前会话的session_meta或实际协调工具取得，不从文本提及猜测。子会话日志在别的日期目录时显式加该目录；缺少日志或cwd超出workspace的后代无法自动证明齐全，范围要声明。写入未完成的末尾半行会被忽略，快照不能证明截止时点所有响应都已落盘。

```text
python "<SKILL>/scripts/audit_model_usage.py" --log-dir "<LOG_DAY>" --workspace "<WORKSPACE>" --root-id "<ROOT_ID>" --until "2026-10-19T04:29:32Z" --out "<GAME>/evidence/usage-stage.json"
```

多个日期目录或独立根重复传`--log-dir`、`--root-id`；不能同时选祖先和后代做根。阶段窗口可加`--since`，时间必须带时区；按用量事件时间切窗，跨边界开始的响应可能归入后一个窗口。until固定取本次实际截止，不照抄示例日期。输出到新的JSON保留基线，禁止覆盖JSONL日志。

脚本排除继承的创建前事件、先去重完全未变化的累计计数、核对采计增量、处理since之前的基线。被忽略的重复状态载荷如有异常单列ignored_duplicate_payload_anomalies，不计调用或用量；真正参与统计的事件校验累计量、本次量和增量的非负整数、缓存子集、推理子集及加总关系；异常不会被后续正常累计值掩盖。遇到计数回退/增量矛盾/无效字段时落盘并exit2，`reliable_counters=false`，不能当精确成本结论；错误根或目录直接失败。没有调用时平均输入0、P90为空，不能除零。

只读stdout的调用数、平均/P90输入、缓存/非缓存输入与可靠性；完整逐会话计数留文件，不导出聊天或凭据。调用是观测用量记录，不等于账单请求；缓存已包含在输入，推理已包含在输出。等待数包含合理等待，不算可删除比例。无实际计价、生图用量和可比质量/范围时不承诺现金、额度、时间或节省百分比。

## 一键预检

`python scripts/preflight.py --project <工程> --board localize|remake [--native-zip <测试包.zip>] [--screens <截图文件夹>] [--levels <总关数>] [--expected-app-id <ID>] [--maintenance-scope <scope.json> --binding <current-review.json>] [--maintenance-visual-policy <policy.json>] [--copy-table <copy-table.csv>] [--glossary <glossary.json>]`

在任何触摸/视觉测试之前运行。`--board` 不写时读工程的 `docs/board.txt`；英化（localize，英化＋优化）照查截图亮度、UI 占比与排版、皮肤表，清晰度和音频来源只作提示（见[两个板块](two-boards.md)）。依次调用清晰度、音频来源、中文残留、英文文案（`audit_copy_quality.py`，并写审查单 copy-review.md）、广告接入标记、异步返回方式（`audit_async_contracts.py`：奖励查询的回调和 Promise 都接住了吗）、触屏写法、上传包结构、广告位绑定、截图亮度与背景、关卡抽测清单、内置模块（`audit_game_modules.py`：货币、礼盒、广告门、skin.v1），排名始终禁止，已明确授权的签到等非社交扩展按feature_policy.py及对应审计校验、单调页面（`audit_page_richness.py`：读 docs/test 里带 purpose 的 dump_ui）、顶部资源栏（`audit_top_bar.py`：`docs/top-bar.json`、在最上方、货币贴合题材、过关后变大）、关卡地图（`audit_level_plan.py`：关卡表的限定关和奖励关、地图显示总关数、无尽没有地图；骨架用 `make_level_plan.py` 生成）这些已有脚本，缺输入的项自动跳过；结果写到工程外的 `<工程名>-preflight/<时间>/`：`preflight.md` 一页摘要、`preflight.json`、`logs/` 每项完整输出。退出码 0 全部通过，1 有"需处理"。只读 `preflight.md`，需要细节再打开对应 JSON。它只做静态检查和截图测量，不代替真实触摸、真机和真实广告验收。

用户选择保留已有玩法并只修复时，必须把当前 `--maintenance-scope` 和 `--binding` 一起传入。preflight 会将它们传给已有维护分支的模块、收集、签到和页面审计：检查当前源码/Web/Native、实际按钮与保留功能，不要求新增 `modules.json`、`DailyCheckin.ts` 或通用玩法模板。`audit_level_plan.py` 会收到所选 `--board` 和当前 binding；`endless` 继续按无地图处理。文案表或词表在工程外时，显式传 `--copy-table`、`--glossary`，避免只读工程内默认路径。若使用视觉维护映射，还要传同一 scope/binding 的 `--maintenance-visual-policy`；没有它时，页面通用规则仍会报告缺项。维护范围不替代当前运行证据或最终包验收。

单独的清晰度检查：`python scripts/audit_image_clarity.py --project <工程>`，对比场景/预制体里每个 Sprite 的显示尺寸和原图尺寸；九宫格与平铺跳过，代码里动态换的图要看截图。代码里动态换的图由 `audit_page_richness.py` 按 dump 的 `frame_size`/`display_size` 量（`low_res`）。

## 逻辑检查

`python scripts/logic_check.py --project <工程> --init` 生成 `docs/logic/flows.json`（F01–F20）；`python scripts/logic_check.py --project <工程> --mode build|review [--binding review.json]`：静态扫描疑点（触摸取消当抬起、`while(true)`、加载失败只打日志、按钮随机换位、存了不读的键、声音开关不保存、关卡配置空槽、Daily 不读日期、暂停不停物理）＋读 `docs/logic/triage.json` 判定＋核对 flows 的真实触摸结果和证据文件。build 模式（自己的游戏）有待处理就退出码 1；review 模式（别人的游戏）只列出、退出码 0，报告不能用于门禁。用法见 `cocos-game-logic-check` Skill（门禁 LOGIC-01）。


## 打包（TikTok 平台包）

`python scripts/make_tiktok_zip.py --native <Native构建> --app-id <App ID> --out <新ZIP> --project <工程> --web <Web构建> --build-tag <版本> --review <review.json> --resource-manifest <当前业务资源清单.json> --startup-contract <当前启动报告.json> --loading-recovery-runtime <当前恢复runtime.json>`（[`cocos-game-tiktok-package`](../../cocos-game-tiktok-package/SKILL.md)，BUILD-04，用户 2026-10-23）：所有叫法（打包、出包、上传测试包、检测包、压缩包）都只出这一种包。先跑门禁，再查形式（外层文件夹、Web 构建、源码、ZIP 套 ZIP、垃圾文件、非 ASCII、测试跳关、App ID）和体积（未压缩主包≤4,000,000、总包≤30,000,000、独立分包各≤4,000,000），不合格不写 ZIP；写完回读、和 Native 逐字节比、独立解压再比，才放到 `--out`，旁边写 `<ZIP名>.report.json`。检查现成的包：`python scripts/verify_native_zip.py <包.zip>`（限额内置，只能更严）。

## 设计关自检

`python scripts/design_check.py --project <工程> [--board localize|remake]`（用户 2026-10-24）：英化 1.5 优化做完、进美术前，重塑第一轮、节点 1 前跑。一次跑完 `audit_level_plan.py`（≥70 关 `levels_at_least_70`、限定关、奖励关、限定皮肤格式 `final`/`every_10`；地图页没 dump 时只作提示）、`audit_game_modules.py`（MOD-01）、`audit_acquisition_progression.py`（ECON-01）、`audit_league.py`（RANK-01）、`audit_optional_features.py`（FEAT-00）。结果在工程外 `<工程名>-designcheck/<时间>/design-check.md/json`，退出码 0 全部通过、1 有需处理。最终总检测不再查这些（[检查分阶段](check-stages.md)）。

## 美术自检

`python scripts/art_check.py --project <工程> --dumps docs/test/art-round-N`：每轮美术做完立刻跑（ART-06），把画面相关的检查一次跑完：页面内容与背景（`audit_page_richness.py`，含空白卡片、占位方块、深色粗字、字超出按钮、大片空白、按钮≤40%、单调弹窗、首页大标题和封面、选关≥6关）、截图颜色（`audit_dark_area.py`）、布局（`extract_ui_layout.py`＋`audit_ui_coverage.py`）、文字放得下（`audit_copy_quality.py --require-runtime`）、开发用字和占位图（`audit_dev_text.py --final`）、清晰度（ART-04：dump 里运行时的图≥节点 2 倍、背景≥1.5 倍的 `low_res`＋`audit_image_clarity.py`，两个板块第一轮起就拦；英化未改的原图写 `docs/art/clarity-exempt.json`），首页礼盒 10 帧动画（`docs/modules.json` 的 `gift_box.frames_dir`），再生成总览图和看图清单。美术只在这里查，最终总检测不再查美术（用户 2026-10-24，[检查分阶段](check-stages.md)）。结果在工程外 `<工程名>-artcheck/<时间>/art-check.md`。缺页面、缺截图都是"需处理"。见[美术自检](page-richness.md#五美术自检每轮美术做完立刻做两个板块art-06page-01)。

## 动态画面录屏分析

`chrome_touch.py --user-approved-chrome --channel chrome --record`（配套 chrome-mobile-testing，跑在独立 Google Chrome iPhone 触摸模式）把每一帧存到 `<输出>/frames/`；然后 `python scripts/audit_frame_glitches.py <frames文件夹或视频> --report <报告.json>`。视频（手机录屏、系统录屏）需要 ffmpeg，帧文件夹需要 Pillow。每个问题自动存 之前/当时/之后 三张图，只看这些图即可。详见 `references/dynamic-visual-review.md`。

## UI 不挡玩法

`python scripts/audit_ui_coverage.py docs/ui-layout.json --binding <review.json> --out <报告.json>`：按组装线写的布局文件，量游戏中常驻 UI 占屏比例（≤20%，即玩法区≥80%）、常驻元素是否重叠、提示气泡大小和是否压在屏幕中间、游戏中弹窗面板占屏比例（≤60%）；每个弹窗和带边框的面板（`boxes`），里面的标题牌、状态牌、文字、展示区、按钮是否都在内框里（留 8 像素）、有没有压到角花等装饰、彼此有没有重叠。一键预检会自动找 `docs/ui-layout.json` 跑它。截图里的大块白色/纯色由 `audit_dark_area.py` 量。

## 启动加载计时

`python scripts/audit_startup_loading.py --plan docs/test/startup-plan.json --runs <chrome_touch 输出文件夹...> --binding <review.json> --out <报告.json>`：读计时运行的报告（Ego Lite 里跑，`timing`/`record`/`network`/`cache`），逐次核预算、加载动画是否卡住、首页前的大文件、覆盖次数和四种加载故障。规则见 `references/startup-loading-timing.md`，计划模板 `assets/startup-plan-template.json`。

## 截图总览图（给 GPT 一次看完）

`python scripts/make_contact_sheet.py <截图文件夹或文件...> --out <总览图文件夹> --binding <review.json>`：把一轮测试的截图拼成编号总览图（默认每张 8 个、4 列、缩略图宽 300 像素），并写 `contact-sheets.json`（编号→原图路径和 SHA）。测试执行做完截图后跑一次，录屏证据图另拼一组；GPT 一次看完总览图，只打开可疑编号的原图，然后在 review 里写 `visual_verdict`。输出文件夹必须是空的；需要 Pillow。

## 重活排队与清理（不压垮电脑）

- **被占就开新的，绝不等待**（用户 2026-10-23）：浏览器测试（`chrome_touch.py`）、录屏、批量跑关、预览服务都不排队；每次在 Google Chrome 里新开独立测试窗口，后台运行，可以多开；包在锁里也会直接放行。
- `python scripts/browser_slots.py sweep [--close]`：新开窗口前查以前开的测试窗口、Ego 空间、预览服务，退役已不存在的拥有者记录，只关闭已完成且当前身份匹配的自有进程；旧空间与心跳超时先核用途，别人还在用的不动（`chrome_touch.py`、`serve_preview.py` 启动时自动跑）；`register --kind ego_space --space-id <ID> --name ...` 登记手动新建的 TaskSpace，测试用完马上 `close --name "<线名>"`（或 `--id <slot>`；`release` 同义）：核进程退出；Ego 由拥有者先结束已绑定任务，脚本读回空间消失后才注销，退出码 2 时由拥有者核当前控制权并结束已绑定的自有空间，读回消失后重跑 close；不盲用历史 ID；`check --name "<线名>"` 退出码 1 表示这条线还有没关的，汇报"测试完成"前必须是 0（用户 2026-10-23，所有环节）；`ego-list` 列出 Ego 全部空间、`ego-finish --space-id <ID> ...` 只核对已由当前拥有者结束的空间消失，不凭"需要你处理"标签关闭空间（Ego 只给 AI 测试；`--keep` 只允许给用户的本地预览，Ego 空间登记 `--keep` 会被拒绝）；`snapshot --from <Web 导出>` 复制一份私有构建副本。
- `python scripts/heavy_lock.py run --project <工程> --name "<线名+做什么>" -- <命令>`：只给同一个游戏写文件的活（构建、音频流水线），放后台跑；`--no-wait` 被占就立刻返回 75；`status --project <工程>` 看谁在占用。不写 `--project` 不排队。
- `python scripts/cleanup_machine.py [--close]`：先跑一次 sweep；登记已完成且当前进程身份匹配的自有资源自动清理，未登记的历史/孤儿进程只列待核候选；父进程已不在不是独立关闭依据，别的会话还在跑的不关；不碰用户自己的 Chrome、Cocos 编辑器、Codex 和正在锁里运行的任务。
- `serve_preview.py` 默认 20 分钟没人访问自动关闭（`--idle-minutes`）；每条测试线自己开（默认新端口），`--snapshot` 用私有副本，构建同时进行也不影响测试；给用户的试玩链接加 `--keep`，链接要求用户在独立 Google Chrome 中打开；Codex 内置浏览器只可查看，不能作为手机测试。详见 `references/machine-load.md`。


融合后的清理边界：独立窗口/端口和私有快照继续使用；完成的自有QA正常退出并注销，核实空间/页面/端口已消失。`--keep`保留的用户试玩不因固定小时数到期关闭；用户玩完或新版替代后 Agent 关闭并核实。自动清理只处理登记中已完成且进程启动身份匹配的资源，或退役已不存在的拥有者记录；仅心跳超时仍在运行、旧版未登记PID、未知所有权只列待核候选，经支持的界面确认确实无用后再处理。自己绑定的 Ego 测试空间失活/未分配，核实旧 ID 已消失后自动新建登记独立空间继续，不问用户、不接管旧 ID；用户明确接管、要求停止或工具安全 hard stop 立即停止，不换空间、接口或系统信号绕过。

新玩法首次出现的关卡必须标 `"tags": ["intro"]`，推荐配稳定 `mechanics` 标识；生成必测清单时给 `plan_level_tests.py` 传 `--level-plan`。所有首现关强制纳入，漏标提醒的处理及示例见[新玩法首现关与必测清单](prepackage-mobile-review.md#新玩法首现关与必测清单2026-10-24)。
