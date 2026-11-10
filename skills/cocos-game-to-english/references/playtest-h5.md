# 同版英文试玩与交包 H5

正式英文试玩和测试包交接随同版手机试玩链接附一份可勾选的 H5。复用已开的同版试玩服务和项目内的证据。首轮覆盖本轮实际改到的场景。后续只列反馈修复和新增内容的影响范围。交付后局部返工用单栏可选快查，只改一处就一条，最多五条。用户现有的试玩确认方式照常，H5 的点击记录供反馈和定位使用。

首次美工试玩主要请用户看原画风、英文可读性、按钮和文字布局、弹窗及转场观感。最终测试包 H5 供用户选几项实际改动快看。对运行时与平台检查，AI 在对应节点核对覆盖。两个时点按[试玩交接](preview-handoff.md)放行。

## 把检查排成试玩路线

先看本作的反馈、截图和已完成的复验。优先列用户报过且已复验的旧问题、用户严格要求的动作和本轮重要可见变化。同一路线能到的页面或状态合在一起。每页用实际入口名，写清怎么进入、点什么、什么画面算通过。旧现象只有本作有复现出处、当前已复验修好时才展示。通用画面项从[人工试玩画面清单](../../remake-core/references/manual-visual-review.md)挑适用的。

页面可选通过或标记异常后继续，自动统计通过、异常和待测。可在走完后复制异常，未操作的页保留待测。图片、配置、奖励去重和其他既有技术证据仍由原检查产出。生成 H5 只做已有证据和本版文件的读取核对。遇到 H5 自身问题就定点修 H5，用户的试玩确认和写包按原流程推进。

## 生成本版文件

把计划和 HTML 存在项目的 `docs/playtest/<版本>/`。计划内的证据优先用项目相对路径和文件指纹。HTML 单文件交付，放在 Web 导出、试玩快照、Native 构建和 ZIP 之外。用本包的 `build_playtest_h5.py` 生成。计划使用以下字段。

| 字段 | 填写方式 |
| --- | --- |
| `schema` | `english-playtest-plan.v1` |
| `game`、`version` | 游戏名和本轮实际版本 |
| `mode` | 本机单栏用 `trial`，正式双栏用 `package`，跨电脑转发用 `share` |
| `preview_url`、`web_tree_sha256` | 本机试玩用实际已启动的同版固定手机入口和 Web 指纹。转发模式只需 Web 指纹。从现有交付启动合同 `binding.web_tree_sha256` 取得，或用本包 `check_known_issues.tree_sha(当前 Web 导出目录)` 计算 |
| `require_ad_simulator` | 默认 false。有操作要实际点击模拟广告时写 true，由工具读取现行链接的模拟脚本 |
| `inventory` | 本轮待用户看的一组真实状态，每项填写 `id`、`page`、`state`、`control`、`evidence`。证据可用当前页面、用户反馈或报告位置 |
| `steps` | 按试玩顺序，每页填写 `id`、`page`、`enter`、`checks`。每条 check 填 `covers` 数组、`action`、`expected`、`basis`。依据选 `verified_fix`、`verified_behavior` 或 `strict_requirement`。已复验的旧问题再填 `problem` 和 `problem_evidence` |

```sh
PLAYTEST_H5="<英化包根目录>/cocos-game-to-english/scripts/build_playtest_h5.py"
python3 -B "$PLAYTEST_H5" --plan "$PLAN" --out "$HTML"
python3 -B "$PLAYTEST_H5" --plan "$PACKAGE_PLAN" --zip "$ZIP" --delivery-record "$DELIVERY_RECORD" --acceptance-report "$ACCEPTANCE_REPORT" --out "$HTML"
```

- 有本次实际 ZIP 和正式交付回执时，单栏也可以用 `--zip` 和 `--delivery-record` 标注包名与指纹。沿用既有交付证据，H5 核对实际文件与回执。
- 已有本版英化 `check_known_issues.py check --stage device` 通过报告，且与正式交付回执的 Web、Native 和实际 ZIP 匹配时，可生成正式双栏。左边同版可玩，右边独立滚动，换页保留左边的游戏状态。没有本版完整报告时按单栏交接，局部修复范围无需扩大。
- 同一份候选和同一套内容，在同一浏览器地址下重开会保留结果。构建或清单变化会用新的进度。发出前核对页面标题、版本和链接。需要确认交互时在 Ego Lite 点一项通过及一项异常，双栏再核窄窗口和左栏退出。已有当前交互证据可直接沿用。

## 换电脑接手

转发时将原计划的 `mode` 设为 `share`，用同一命令生成离线清单。另一台电脑能查看路线、勾选并复制异常。本地试玩地址绑定运行服务的电脑，收件人从同版 Web 构建启动自己的试玩服务，用实际 `preview_url` 再生成单栏。需要在新电脑正式交付时，用新电脑对实际 ZIP 的本次核对和同版试玩回执生成双栏。随项目转交旧检查时用相对路径和文件 SHA-256 证明对应关系，复用仍有效的检查结论。
