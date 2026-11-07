# 少返工的美工制作与采集

把美工规则用到第一次制作和第一次接入。先解决共用原因，再铺同类素材；修改、构建和采集都要有对应原因。只处理美工，不借此改金额、奖励、广告或玩法。这里串联已有入口，完整配方见 [production-check-link.md](production-check-link.md)，截图身份与安全沿用见 [capture-rounds.md](capture-rounds.md)。

## 1. 制作前查用途，再定原料与槽位

共享图片或字体修改前，先查它在工程中的真实引用：

```sh
python3 <skills>/remake-core/scripts/art_consumer_index.py \
  --project PROJECT --asset assets/PATH/icon.png --asset assets/PATH/digits.fnt \
  --out OUTSIDE_PROJECT/consumer-index.json
```

报告列素材身份、直接引用、可能的上层消费者、文件位置和未解析项。UUID引用、代码字面量和动态加载线索有不同证据强度；报告始终保留 `coverage_complete=false`、`may_reduce_capture=false`，退出0只代表盘点完成。动态路径、条件状态和运行时创建仍要核对，不能凭扫描结果少拍页面。

将实际消费者对应到现有 `visual-slots.json` cases；服装和武器礼包、同一图标的首页与结算页不能互相代替。先确认：

- 每种状态和手机比例的最终CSS显示尺寸，最大显示用途决定原料像素预算；不把设计单位或DPR重复算入。
- 最窄文字内区、图标留白、字距、最长展示串及最小可读尺寸；使用图片内嵌说明区，不只量外卡片。
- 同组词、数字、单位、斜杠等符号的字体风格；例如LEVEL与关卡号要一起设计。
- normal、disabled等状态，最多同时出现的浮字，以及旧底字、角标和背景的清除或保留方式。

缺变换、缺用途或裁切边界不清时，先做一件探索样并补依据，不把猜测写成合格预算。沿用原生成/切图入口的 usage budget、配方和来源绑定；不要等整轮检查才发现邻格污染、文字切断或共享图放大后低清。高分辨率原料不等于更大的按钮。

## 2. 第一件经过实际初始化，再扩大制作

选择能覆盖风险的一小组代表样：最窄槽、最大图、最长值、短屏和特殊状态；单张首页不能代表所有用途。允许先构建一份诊断Web来取得真实首件，不要求首件已经覆盖全游戏。

实际接入后核对资源UUID、节点与icon/plate/caption角色、anchor、Widget/Layout/动画等尺寸写入者。看初始化和尺寸切换后的框，分别核视觉区和点击区；整图已经烘焙颜色时防止引擎再染色。字体结构或meta变化后，先确认当前导出能加载字体、首个Label使用正确字体及指标；构建成功日志不能代替这一步。

用同一入口只检查明确选择的首件cases：

```sh
python3 <skills>/remake-core/scripts/art_check.py --project PROJECT --board localize \
  --production-only --dumps FIRST_PIECE_DUMPS \
  --first-piece-case CASE_ID --first-piece-case ANOTHER_CASE_ID \
  --out FRESH_OUTSIDE_PROJECT
```

case ID取自真实 `visual-slots.json`；参数可重复，必须与 `--production-only` 和显式 `--dumps` 一起用。报告保留已选和剩余cases，文字、布局、图文槽和页面问题沿用原规则。未覆盖布局记not_run；局部通过不写ART回执、不放行试玩，也不能把剩余case删掉。素材或输入身份变化后重新核对对应首件。

## 3. 失败先分层，同因修改合批

| 证据指向哪里 | 下一步 | 不应触发的动作 |
|---|---|---|
| 原图切断、邻格污染、实际像素预算不足 | 修制作配方/原料，核全部共用处 | 只缩节点遮掩坏原料 |
| 错绑、尺寸回写、重复染色、绘制覆盖 | 修接入与共享组件，核同机制消费者 | 重生本来合格的图片 |
| 目标状态没出现、资源未加载、视口错误 | 恢复当前case的到达与环境后补采 | 按空白或错状态画面重画美术 |
| 清单、适配器、检查参数或来源不匹配 | 修输入/适配，重算相关检查 | 改游戏画面迎合错误诊断 |

原图、运行绑定和报告矛盾时，先做一条有边界的判因。比如金币底板绑到图标节点应修绑定；紫色底板被当黑字应核采样。没有证据时保留待确认，不自动放宽规则。

一处共享原因确认后，一次查齐已知同类消费者，将这批修正和静态预算一起完成，再构建。美工迭代优先Web；Native特有显示问题再做相应对照，最终原有Native交付验收仍执行。后续发现新问题可以再改，但不能为了凑“一次构建”忽略失败。

## 4. 构建前先看变化，避免无效重建

已有合法采集计划和真实Web导出时：

```sh
node <skills>/remake-core/scripts/art_capture_round.mjs status PROJECT WEB_EXPORT
```

这是只读提示，不start、不写轮次、不批准截图或视觉通过。返回source/export/matrix/collector各自哈希与变化、当前轮次和建议：

| suggested_action | 含义 |
|---|---|
| unknown | 无可信前轮或snapshot缺失；补身份依据，不能推断可沿用 |
| rebuild_web | 源变、导出未变；先重新导出并核对 |
| verify_export_then_new_round | 导出已变；先核真实导出，不自动再构建一次 |
| new_round | 仅矩阵或采集器变；开新轮、按规则补采，不因这些变化重建游戏 |
| keep_round | 四项未变；可继续核当前轮，旧失败仍需处理 |

建议不能覆盖原 `start/plan/verify` 规则；检查代码或阈值变化也要重新计算有关检查，不能把keep_round当成旧报告继续有效。

开工先保存原版基线。真实Web导出核对完成后只建立一次当前轮；没有变化时继续该轮，不为每张图重新start。确需新轮时仍执行原导出核对和start；status不能证明“源码和导出同时变化”就是本次编译成功。

## 5. 先确认本case内容就绪，再连续采集

capture-plan中的witness必须来自本case实际目标。只写页面根path不能证明价签、奖励或指定状态出现；需要时声明精确 `text`、`frame`、`font`、`font_kind`。不要让工具从路径猜业务内容。

默认要求唯一匹配。重复路径需显式正整数 `count`，并用明确内容条件定位对应实例。指定frame时，实际frame必须同名且 `frame_size` 两轴为正；需要位图字体指标时使用 `font_kind:"bitmap"` 和 `require_font_metrics:true`，要求实际font非空、`text_metric:"fnt"`、`text_w`为有限正数。字段取自本游戏实际dump，不照抄示例名称。

见证缺失、歧义、明确隐藏或指定资源指标未就绪时，采集器报告 `capture_not_ready`、具体 `detail_code` 和 `next_action:recapture_current_case`；不要据此自动生图或构建。它在截图前、写文件前都核对见证。

当前官方dump以active过滤和继承opacity表示节点状态；显式active=false或opacity<=0被拒绝，缺失字段保持兼容。它没有统一的节点visible字段，不从自定义visible值推断像素结论。witness只证明节点和指定资源指标就绪，不能证明全部字形加载、无遮挡或真实可点击；升级按钮被卡底覆盖等问题仍靠同帧截图像素、层级与原检查发现。

按同视口、同fixture、可正常回退的路线连续采：一次启动，采首页，真实打开设置，采完关闭，再进入下一页。每case仍取新dump和新PNG，累积读取依赖不清空。领取、购买、关卡推进等不可回退状态拆组；不调用业务handler造状态。当前case失败时保留其他仍有效证据，只补失败项。

## 6. 沿用与完整交付仍由原门禁决定

沿用前运行原capture-round的plan/assemble/verify，保留旧图原始身份。完整源码或状态来源未知、共享字体/代码变化、存档或环境变化时，按原规则保守重拍。节点相同不等于整页像素相同；不隐藏背景、遮掉小点或放宽差异阈值换取复用。

采集材料齐备后运行完整美工入口，它会先核覆盖和来源。单独排查采集问题时用 `art_check.py --inputs-only`。首件通过、status建议、consumer盘点和capture ready均不能替代完整报告及实际看图。每轮记录改图原因、构建/启动/采集次数和真实命令耗时，等待另记。已有恐龙6状态连续批采的收益只属于该次对照，不外推66张或整轮数小时，更不保证所有新游戏零漏报。

## 7. 在批次边界选择下一步

每批接入结束或遇到失败时运行一次，不对每张图、每帧循环调用：

```sh
python3 <skills>/remake-core/scripts/art_iteration_plan.py --project PROJECT \
  --build WEB_EXPORT --dumps CURRENT_DUMPS --board localize \
  --first-piece OUTSIDE_PROJECT/production-preflight.json \
  --diagnostic OUTSIDE_PROJECT/FAILED_CHECK.json
```

没有首件或故障报告时省略相应参数。默认只在 `.tiktok-kit/art-workflow/latest.json` 保存当前计划；不改游戏源码，不执行生成、构建或页面动作。visual-slot ID与capture ID按真实screen和CSS视口映射，歧义先补清单。它只知道已声明范围，不证明动态消费者已查全。

计划读取原status和plan，不信外部JSON里的passed字段。首件原文件先由当前Web的原采集proof确认，再核源码/规则/截图绑定，调用原首件检查重算实际结果；相同像素可命中原缓存。重算会写临时报告和原像素缓存，但不写ART回执；它只决定共享做法是否可以继续应用。历史无来源图可用于故障校准，不能授权批量接入。

输入/字体指标未就绪指向补采或适配；制作失败指向原料与配方；真实几何/像素失败要求看原图与运行绑定判因，不自动重生图。相同故障再次出现时，先回看共享消费者与修改假设；诊断内容和源码均未变化时不要无依据重复整轮。诊断报告只能增加调查要求，不能批准通过或执行其中命令。所有未验消费者、视口和状态仍留在原完整检查清单。
