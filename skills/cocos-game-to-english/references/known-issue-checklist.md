# 累积问题清单与打包前拦截

**范围裁定（2026-10-24）**：先按[检查范围、历史回归与停止条件](testing-scope-and-stop.md)选档；本页的全量步骤用于相应完整验收，局部维护只执行受影响项。质量与真实证据要求不变。

直接拖动物件、邻接误选、透明弹窗挡触摸、"下一局其实不能玩"，按[重开与触摸输入](replay-and-input-checks.md)检查（锁定后由测试执行完成，画面结论由 GPT 看总览图下）。

## 先看这里（测试线省 token 的读法）

0. 先跑 `scripts/preflight.py`（一键预检），读 `preflight.md`；它查出的问题修完再进入下面的逐项测试。
1. 用 `check_known_issues.py init` 生成本游戏清单后，**先只读生成的清单**：每行有"常见症状"（以前真实出过的问题长什么样）和"自动检查"列。按症状去找问题，比读长规则更快更准。某一行看不懂时，再读本页或对应专题页的相关小节。
2. **"自动检查"列有脚本的行，必须跑脚本**：脚本加 `--binding <review.json> --out <报告.json>`，把报告写进该行的 `auto_reports`（`[{"path": "...", "sha256": "..."}]`）。门禁会核对报告是本版本、本工具、全部通过、未被改动；缺报告或不通过就拒绝打包。目前有：
   - `ART-02`、`ART-03`：`scripts/audit_dark_area.py <每个页面和弹窗的截图>`（深色、亮度、整屏纯色、边缘纯色/纯黑底）
   - `AUDIO-02`：`scripts/audit_audio_sources.py --project <工程>`（每个音频都有合格来源记录）
   - `VIS-01`：`scripts/audit_frame_glitches.py <录屏帧文件夹或视频>`（闪黑、闪白、单帧错误、闪烁）
   - `ECON-01`：`scripts/audit_acquisition_progression.py --table <unlock_table.json>`；`NOSKIP-01`：`scripts/audit_no_ad_skip.py --project <工程>`
   - `STORAGE-01`：`scripts/audit_native_storage_contract.py --trace <trace.json> --native <最终Native目录> --binding <review.json>`；旧版空字符串失败、现版 23 场景通过，真实主页/地图/关卡详情触控恢复，最终 Native 字节与报告一致；缺一项就拒绝测试 ZIP
3. 修完问题、改代码或换图后，核实际证据绑定和受影响范围；只补失效检查及相关回归。现有工具使用全树绑定时按其要求真实重跑，不把旧报告换哈希当新证据；也不在同版有效时固定重开全部人工操作。
4. **每条检查写自己看到的内容**：同一段话复制到多条检查，或一条检查的几个观察字段写成一样，门禁会直接拒绝。


接收游戏、用户反馈修复后、锁定后测试和打包前读取（本 Skill 不做上传后的手机测试）。本文件维护执行方法；固定编号、已遇到问题和具体检查动作统一保存在 [known-issues.json](../assets/known-issues.json)，不再另外复制一份不同步的总表。每款游戏的具体入口、奖励、实际结果与来源留在其项目。

## 从通用机制生成本游戏清单

先执行 [全英文覆盖与全 UI 重构](english-ui-rebuild.md)，将中文候选处置（中文源码）或"入场扫描：英文源码"记录（英文源码）/全部文字图片与帧/实际页面状态放入 `UI-01`，全 UI 控件清单/image_gen 输出与绑定/动态字段/实际组合放入 `ART-01`。两项均需要本版 GUI 观察；静态扫描可定位候选，不能替代读图或真实运行。新制作默认全量 UI，局部维护按当前授权范围记录；不把原游戏主题/关卡也纳入无授权改版。

先读 [通用问题适用范围与重点](feedback-regressions.md)。通用表检查功能机制，不保存单款游戏的对象、设计改动、具体胜败条件或固定数值。广告与奖励优先逐入口检查；运动/物理、拖动、周期等项只在该游戏实际存在或明确授权时适用。广告复活先按 [通用复活要求](rewarded-revive-and-help-layout.md) 按当前授权范围审查/补齐缺少的机制，完整制作/换皮不能以原版没有复活直接免验；无关局部维护记录范围与缺失，不擅自扩项，也不伪报已实现。按 [不提供广告跳关](first-level-onboarding.md#不提供广告跳关) 执行：今后制作、换皮产出不提供广告跳关，新输入原源码自带也一律删除入口和完整业务路径；不追溯其他已结项成品，无关局部维护不扩改。跳关不作为必备奖励入口，生成器/checker 不得要求为通过清单新增它。保留全部统一编号供适用性审查，不适用写依据，不为通过清单新增功能。原反馈、历史案例和个性化改动留项目。无对应功能的行只完成适用性说明，无需运行该用例，更不能据此要求新增玩法。

1. 读取项目原始反馈与已有故障记录，核对当前版本。保留“已复现/已证实缺陷/用户报告待定位”的区别；不要预设旧包、缓存、网络或唯一根因。
2. 双向盘点实际入口：scene/prefab ClickEvent → 当前运行节点 → 业务方法 → SDK/奖励消费者，同时从广告/领取方法回查有没有遗漏的按钮。包含条件入口、首页礼盒和结算×2；备用、当前配置不存在的入口写明依据。只测试同名方法会漏掉错误事件绑定。
3. 逐奖励入口填写 `id`、`reach_steps`、实际 `binding`、`policy`、`trigger` 和 `persistence`。领取规则为 `once / daily / per_run / repeatable / navigation_reward`；触发为 `rewarded_video / platform_mission / direct`；持久范围为 `durable / session`。一次/每日/每局奖励按当前资格显示已领或离页；可重复入口按真实下一次资格恢复。导航动作与领取状态分别验，不能强制所有导航按钮改成同一种文案或统一隐藏。
4. 通过脚本生成当前历史问题的本游戏待测表和每入口状态矩阵。每项有固定编号、复现动作、可观察预期、结果、证据。实际不适用时保留编号、写具体原因与源码/用户范围依据，不直接删行。

```sh
python3 /path/to/skill/scripts/check_known_issues.py init \
  --project /path/to/current-source --native /path/to/current-Native \
  --web /path/to/current-Web --build-tag CurrentBuild \
  --inventory /path/to/project/reward-entry-inventory.json \
  --review /path/to/project/known-issue-review.json \
  --markdown /path/to/project/累积检查清单.md \
  --board localize   # 英化写 localize，重塑写 remake（和 docs/board.txt 一致）
```

`--board` 写进检查表，`check` 时按它检查：英化不检查只属于重塑的 ART-02、ART-03、AUDIO-01、AUDIO-02、ECON-01、ECON-02（清单里 `boards: ["remake"]`，检查表里可以不填），ART-05 只要求 `audit_dev_text` 报告，UI-03 不要求 `audit_ui_coverage` 报告（见[两个板块](two-boards.md)）。不写 `--board` 时按重塑（最严）生成。

inventory输入是实际入口数组，例如：

```json
[{"id":"actual-entry","reach_steps":"实际到达步骤","binding":"真实节点/ClickEvent/方法","policy":"repeatable","trigger":"rewarded_video","persistence":"durable"}]
```

工具保存同版本的独立入口快照及哈希；不能删掉未测入口，或把持久奖励改成session来略过保存检查。同页分别领取、彼此独立的奖励写相同`independent_group`，生成A→B、B→A交叉检查，逐方向确认另一奖励仍可领、模型未被改变。具体坐标、奖励数值、应用/广告ID不要写回本通用清单。

## 实际试玩入口和玩家错误提示

用户报告版本号、SDK错误码或旧画面时，先读其实际访问入口与HTTP业务模块，核默认启动器、旧链接、iframe及实际脚本/资源对应哪一构建。不能只核首页HTML或配置中的版本字符串，不能先归因旧包、缓存或要求用户重新上传。保留实际旧模块反例；当前源码、Web、Native与可运行普通入口分别验，冻结的历史构建与用户存档保留。

本轮修复后，默认启动器和仍可访问的旧普通入口必须到同一份已验证当前构建。需要兼容转发时覆盖页面及同prefix资源，避免新壳混载旧JS；实际导航后读回最终URL和业务模块身份，旧页面内存不会因服务器更新自动替换。旧入口不能静默回落到历史版，缺当前文件时显式停止。该项连同真实启动动作作为现有`TEST-04 / BUILD-01`的入口身份依据，不以HTTP200代替实际内容比较。

玩家错误窗口只显示可理解的结果及可用动作；版本标签、SDK探针和内部stage/code留在诊断日志。最小检查执行真实提示写入方法，分别观察玩家UI与日志，不因源码含console版本标记就判失败，也不能只删文字掩盖不可用状态。无SDK、部分SDK、create/show错误或超时不得发奖；窗口可关闭，已完成视频的保存失败仍按同目标重试且不重看。将旧模块的实际UI泄漏反例与修复后的source/实际Native检查接入本项目原打包门禁，不新建庞大通用框架，也不把本地边界替身当真实广告可用证明。

## 领取不能只验广告和余额

每个实际入口展开catalog的状态矩阵，包括`save_failure_retry`和`apply_or_consume`。免费同步领取的广告等待/取消分支、仅局内即时效果的持久保存分支可按事实标不适用并留证；声明为持久奖励的保存重试、每个入口的实际效果不能免验。每日/每局/重复奖励按真实周期或下一局条件检查恢复时机。

领取成功至少同时检查：

- 奖励只应用一次且数额/解锁/效果准确；领取模型或次数记录已经更新。
- 原领取Button及红点按当前资格更新；一次性入口不能继续伪装成可领。可重复入口允许按真实规则再次可领；导航可保留动作并另显已领状态，或确认真实离页，不强制统一按钮文案。
- 关闭奖励展示后、入场/进度动画结束后、原页面重新置顶后，再看一次。缓存重用、滚动离屏后回来和刷新后的状态分别检查。
- 当前资格已耗尽时再点原位置不再发奖/请求；同一领取的重复完整回调不再发奖，跨页面迟到回调不影响新目标。可重复入口的新明确请求与新凭证仍须可用。

取消、错误和超时采用另一组后置条件：不发奖、保留原可领资格、反馈清楚、能重试或退出。广告SDK确认终止后还必须能响应下一次显式请求；旧会话终态不明时只释放业务UI不能再次show。依当前SDK契约判断终态，不调用未支持的强制关闭接口。独立的免费/广告奖励、基础/额外奖励分别核对。

状态的`postconditions`增加以下可校验字段；填写为true仍须对应原始运行或界面证据，不能靠手填造通过：

| 状态 | 必须检查并填写 |
| --- | --- |
| 视频的取消/错误/超时 | `no_automatic_replay`；error另需`terminal_failure_retry_available`，timeout另需`unconfirmed_session_not_reopened` |
| `save_failure_retry` | `same_transaction_retried`、`no_additional_ad_request`、`reward_applied_once`、`commit_readback_ambiguity_checked`、`no_premature_success_ui`；`recovery_scope`填`process_only`或`durable_restart` |
| `apply_or_consume` | `actual_effect_verified`、`correct_target`、`quantity_and_effect_consistent`；按真实功能验证库存使用或即时效果，不为即时奖励虚构库存 |

保存故障覆盖“写前失败”和“写成但读回失败”；仅验证配额报错不够。相同凭证重试只处理同一笔奖励，新凭证及合法下一次领取仍应正常。扣减与加载/效果交付的失败由`STATE-06`检查，不能只测发奖入账。无法故障注入的手机分支保留受限，Agent先在隔离进程对实际source/Native做最小回归，不要求用户制造真实存档损坏。

`recovery_scope`是实际能力说明：仅内存凭证不得声称重启可恢复；可跨重启须另有中断/重启证据。会话诊断按玩家动作、请求标识、show/close/保存/消费阶段区分素材继续显示、重复show、另一次合法请求和保存重试，不根据一段循环画面直接断言根因。

源码测试必须执行实际状态与外观方法，例如 `showButton`、`restoreResultControls`、实际事件绑定与保存逻辑。不得把被检查方法替成空函数，再仅断言余额或`interactable=false`。Graphics/SDK/节点可作为明确边界替身，但仍需实际渲染与点击检查。一次性领取“看起来还是Watch但不能点”不满足完成后的可见状态要求。

## 领取结果一致性检查

### 最小执行法：先打通，再扩展

首个奖励机制可运行就做，别等整套UI和最终打包。每种实际机制先选一个代表入口，复用现有隔离SDK/存储夹具，完成：

- **一条真实链**：实际按钮绑定/触屏→本次同一奖励完成→模型与语义保存→当前按钮/提示→原使用路径生效→已有缓存页重开→真实刷新。普通UI不放调试工具；即时效果按效果核，无持久库存或独立使用页的不虚构，刷新也不强加局内效果永久保留。
- **两类反例**：未完成（取消/展示失败/关闭后迟到）不奖且能退出；已完成后提交/效果失败，保留同目标重试、不二播/重复发奖。持久奖励至少包含“写成读回失败→关闭→正常保存操作→缓存页重开”；周期/目标变化只在实际存在时加一个最小序列。早期代表反例不替代最终原状态矩阵。
- **一次身份核对**：早期核本轮触屏实际页面与业务JS；最终出包时再核同版source/Web/Native/ZIP，不为早期预防提前产包。查默认启动器/旧链接，不能只看HTML、文件名或HTTP200。手机模式在引擎启动前配置，核引擎接收和实际按住/拖动，不能只用DOM触摸或直接调用方法代替。

在原功能表/observed记录“入口与目标→模型/保存→UI/实际使用→重开/刷新”和当前输入身份即可，链接现有原始证据；不另增固定ID、报告或通用脚本。原最小回归接实际writer，缺工具、失败或旧输入仍拒绝出包。

同一奖励的当前动作要清楚；没有业务用途时不叠第二层确认，必需选择/导航按原规则保留。独立金币、解锁和装备分别显示；不把某游戏的“只留一个入口”、天数、物品或坐标强加给其他游戏。以下详细后置条件继续逐入口执行。

遇到“看完仍显示没领取”“已领但不能用”时，先核原版规则和用户已授权的变更，写清每个入口实际奖励、资格周期、目标与使用路径。同屏金币、解锁和登录赠礼不自动成为一笔奖励；领取次数与登录日期计数、当前奖励与下一次预告、拥有与已使用/装备分别解释。不得靠自动补奖或自动穿戴改变原规则来消除表面差异。

对受影响入口按最短链执行，原始数据和实际画面对应同一领取目标：

1. 领取前记录余额/库存/拥有、选择/实际效果、本次金额或数量及资格；有相关页面缓存时先打开一次再返回。
2. 完整结果后分别读模型与语义保存结果，核本次类型/数量/目标及一次入账。已确认成功不能继续报未领取、失败或要求再看视频；写入尚待确认时明确保存重试，不能提前显示成功。
3. 等奖励展示/过渡结束，再看原按钮、文字和红点。合法离页时确认原页确实关闭，返回后仍核本次结果；按钮隐藏或禁用本身不证明成功，不能只看余额。
4. 通过原使用路径真实使用/装备或触发一次即时效果，核实际角色/技能/关卡状态。当前页所有关联项和已缓存页面须同步余额、拥有、选择及使用标记；单选规则下标记只能对应当前模型，不能只刷新被点卡片。随后离页重开核缓存状态；没有选择/缓存机制时不虚构。
5. 重开与真实刷新分别读回；周期奖励另测相邻合法资格和周期边界，核已领页没有错用下一次奖励金额。新合法周期按原规则恢复，不能把正常下一次资格误报成重复领取。

奖励配置变更或出现“说明与到账不符”时，比较当前承诺的类型、数量、目标与实际消费者使用的同一资格配置；不要从文案反推期望。优先由共享业务数据生成说明，修复仅更新已授权的规则和关联视图，不自动补奖或装备。用同一文案/模型不一致判据验证旧失败、修复与正常对照；观察接原领取矩阵或项目 `package_issue_gate.py` runner，绑定实际配置、编译模块和UI依赖。静态配置或 Label 替身只证明对应层，最终可读性及真实使用仍需当前界面证据。

保存故障还要与正常操作组合：完成视频→写成但读回失败→关闭→另一个正常设置/背包操作同步模型→重开已缓存的领取/使用页面；另测待保存事务遇到日期/局/奖励目标变化。恢复旧事务只能确认旧目标，不能把新目标的已完成凭证当旧事务结清而清掉；也不能未看新视频就自动发新周期奖励。正常同目标重试、无故障跨周期及下一次合法领取都保留为对照。

以下字段接入原状态矩阵；pass必须引用实际方法/存储/GUI证据，不能统一填true，不能把show/refresh/实际消费者替成空函数后只断言余额：

| 状态 | 增补的必查后置条件 |
| --- | --- |
| `completed` | `reward_identity_verified`（本次类型/数量/物品及周期/局目标）、`current_reward_display_consistent`（本次结果与下一次预告区分）、`success_feedback_consistent`（提交结果与成功/待保存/失败反馈一致） |
| `reopen` / `reload` | `model_and_presentation_consistent`（当前合法资格下，模型与重绘后的文字、按钮及数量/拥有一致） |
| `save_failure_retry` | `proof_target_preserved`（完成凭证与原日期/局/物品匹配，恢复历史事务不消耗另一目标的新凭证） |
| `apply_or_consume` | `ownership_and_usage_distinguished`（拥有与选中/装备/实际生效明确）、`related_views_consistent`（已有相关页面含缓存再次显示时与同一模型一致） |

只有余额或即时效果的游戏，按真实余额/实际效果解释这些字段，不新增皮肤、装备、第二页或持久库存；无独立使用阶段时在observed说明同一即时效果已验证。无相关缓存页也说明实际界面范围。具体金额、日期、对象和最小用例留项目。

旧记录缺现代凭证不等于未发奖。对照旧成功与旧中断样例；证据不足时保留原数据、明确状态未知/已记录，不无据自动补发、重置日期或清存档。内存待保存凭证不能宣称永久恢复。确认同目标保存重试不重看、入账不重复及实际反馈一致后，才记录对应范围通过。

## 每次修复都增加可检出的失败样例

为新故障建立最小复现，先用同一检查证明原问题版本失败，再证明修复版本的源码和本次实际Native通过。能用现有样例扩展就不另造庞大测试框架；纯图片排版不写复述实现的测试，用真实页面和图片/构建绑定核验。把最小回归命令接入实际构建/打包入口，不能仅留说明或读以前的pass JSON。

失败样例也要覆盖测试自己的盲区：去掉已领取显隐更新、把Button事件绑定到旧方法、混入旧Native或旧报告，应使真实打包入口停止且不产新ZIP。测试次数、截图数量或HTTP200都不能代替对应后置条件。

## 加载和排版必须观察实际界面

检测前先完成 [共通首页与声音设计](common-game-components.md)，并在当前功能表逐项记录；新制作每游戏的 MUSIC/SFX 独立全局开关、十格/10%音量及首页两个语义图标不能漏项。沿用现有 `AUDIO-01` 检查实际声音、全档/边界、开关互不影响、持久化及暂停/广告/前后台恢复；沿用 `UI-01/03`、`UI-05/06`、`ART-01` 核英文、玩家页无试听/调试列表、主题背景、动态状态与真实 GUI；主页接口/资格/奖励仍用原检查。只扩充这些检查的实际覆盖说明与证据，不新增强制字段或改变现有稳定ID（数量以当前 catalog 为准）；局部维护不扩大用户范围。

生图导入后先独立完成 [全部可见图像与实际组合的视觉巡检](full-visual-review.md)，不只检查本轮新图或主页。`ART-01`另填写`image_inventory_coverage / resource_visual_review / page_state_visual_review / defects_and_rechecks`，说明全部可见图像/显示位置的已审、未审范围、逐素材及实际状态证据、缺陷优化和复查。`UI-05`增加`source_and_imported_images / alpha_atlas_crop / actual_background_composition`，`UI-06`增加`render_order_and_mask / text_visibility / open_close_states`；两项pass也须真实GUI。不可查看/不可达/问题未闭环时保留待验，不用一句“视觉正常”覆盖未检查内容。

`UI-01`、`ART-01`、`LOAD-02`和`UI-03`的pass至少有本轮`gui_mouse / gui_touch / device`层；`mixed`须另列`layers`。源码/HTTP只作补充。`observations`在生成表中留空：英文覆盖填写`text_scan_and_dispositions / image_and_frame_text_review / runtime_page_states`，全UI填写`ui_scope_and_inventory / imagegen_assets_and_bindings / dynamic_fields / rendered_states_and_hit_results`，加载填写`loading_stage / failure_recovery / ready_target / usable_state`，排版填写`viewports / conditional_states / stable_layout / hit_results`。记录实际读取和运行、失败→恢复→可操作的真实过程及动画稳定画面/命中结果；受限或没到达的条件页保留待验。

启动相关修复沿用 `LOAD-01/02`、`TEST-01/04`、`BUILD-01`，按[Native 首页到首关](cocos-runtime.md#先验证-native-启动到首关)核对实际业务初始化、首页可操作与首关完成，不新增固定ID。把“主场景已挂载，但业务初始化抛错/首页未建立”的旧失败保留为负例；外层 finished 或夹具计数器不能将它判成通过。

## 检查完成与版本对应

**画面结论只能由 GPT 写**：带 `visual_verdict` 标记的检查（ART-01–05、UI-02/03/05/06、VIEW-01、VIS-01）标了通过时，review 顶层必须有 `visual_verdict`：GPT 看过本版 `make_contact_sheet.py --binding` 生成的总览图，`reviewer` 填 `gpt`，`images_reviewed` 等于总览图上的截图数，`verdict` 为 `pass`，`open_issues` 为空，`observed` 写看了什么。测试执行 Agent 可以填其他行，但不能写这一项（见[测试分工](session-relay.md#锁定后的测试分工)）。

`review`使用schema 3，保存源/Native/Web指纹、build tag、catalog摘要、全部编号、入口矩阵及证据路径/哈希。证据行使用真实`layer`与`observed`；不适用需`reason`与当前绑定的依据；入口已声明的视频或持久奖励不能把相关AD/CLAIM/STATE总项免验。`completed`的`postconditions`填写奖励、模型及按钮结果；取消/失败填写零奖励与恢复；重开/刷新/迟到回调填写不额外奖励/请求。

### 换其他 AI 测试时的 GPT 抽查（gpt_spot_check）

检查表顶层 `test_executor` 写着其他 AI（不是 gpt/codex）时，门禁要求顶层 `gpt_spot_check`：`reviewer` 为 `gpt`；`locked_commit` 写锁定时的提交号、`code_changes_reviewed` 为 true（Codex 读过测试阶段的 AI 从锁定到现在改过的全部代码：`git diff <锁定提交>..HEAD`）；`rerun_auto_checks` 为 true（GPT 自己重跑了全部自动检查脚本）；`flows` 至少 3 条 GPT 亲自重做的流程，每条有 `check_id`、自己的 `observed` 和当前版本证据；有看广告入口时必须含一条 AD-*/CLAIM-*，有平台任务时必须含 GROW-01/ASYNC-01/LIFE-02 之一；`disagreements` 必须为空（发现对不上就把那一类全部重测后再清空）。这样便宜模型漏测或乱填"通过"时，GPT 在抽查里就能发现，包出不来。

### 改坏版本的失败记录（negative_control）

带 `requires_negative_control` 的检查（ASYNC-01、GROW-01）标通过时，同一行证据里必须同时有：

- 一个 `current_result`：当前版本用这个检查脚本跑出的通过结果（`execution.tool` 记脚本路径和 SHA）；
- 一个 `negative_control`：**同一个脚本**（SHA 相同）在故意改坏的版本上跑出的失败结果，格式：

```json
{"schema": "known_issue_negative_control.v1", "mutant": "去掉 Promise 成功处理", "status": "fail", "failed": 8,
 "tool": {"path": "tests/test_return_contracts.py", "sha256": "<和 current_result 的 tool 相同>"}}
```

至少覆盖"去掉 Promise 处理""去掉截止恢复""允许旧请求回写"三种改坏方式（可以存三个文件）。从没在坏版本上失败过的检查，证明不了它能抓住这个问题（Monkey Dash 2026-10-21）。

### 奖励入口必须写 `api`，返回方式要逐条测

看广告和平台任务入口在 inventory 里写 `api`（例如 `createRewardedVideoAd`、`getShortcutMissionReward`、`getEntranceMissionReward`）。`audit_async_contracts.py` 报告里列出的每个奖励接口都必须有入口，否则门禁拒绝：代码里有的机制，一定会产生它的检查。

这些入口要填 `return_contracts` 状态：`channels_tested` 写测过的返回方式。平台任务至少要有 `callback`、`promise`、`both`、`void_or_incomplete`、`reject_or_throw`；看广告至少要有 `event`（onClose/onError）、`promise`（show 的 Promise）、`reject_or_throw`。另外四项都为 true：`each_channel_settles_once`、`non_eligible_results_no_reward`、`every_result_visible_end_state`、`test_double_supports_each_channel`。`pending` 状态另填 `sdk_and_timer_held_recovers`（SDK 结果和原超时回调都扣住，画面仍结束等待）和 `retry_after_recovery_works`（之后真实触摸重试成功）。

### 内置板块和单调页面（MOD-01/02、PAGE-01，用户 2026-10-21／2026-10-23）

- **MOD-01 内置板块**（两个板块，不能标不适用；**设计关**用 `design_check.py` 查，最终总检测不重查，用户 2026-10-24）：`audit_game_modules.py --project <工程> --binding <review.json> --out <报告>` 的报告放进 `auto_reports`（`docs/modules.json`：问过用户、英化按钮审查表、没有排名/签到/更多游戏/分享、有货币、`AdRewards.ts` 和技能里一模一样且模拟通过、皮肤表 skin.v1；礼盒 10 帧只在美术关 `art_check.py` 查）。**MOD-02** 五个观察项都要浏览器实测（`result_double_every_end`、`ad_button_single_fire`、`ad_cancel_no_reward`、`no_stutter_around_ads`、`same_after_reload`）。见[内置板块](game-modules.md)。
- **PAGE-01**（两个板块，不能标不适用；**美术关**用 `art_check.py` 查，最终总检测不重查）：`audit_page_richness.py --binding` 的报告；dump_ui 要带 `purpose`（首页 home、过关 result_win、失败 result_fail、设置功能页 settings、设置声音页 settings_sound，有关卡时地图 map），它同时量每张截图的纯色背景和花哨背景（`busy_background`，游戏中也量）。**交用户看美术之前就要跑过一次**，不是等到打包。观察 `no_dark_bold_text_any_hue`：没有任何深色粗字（用户 2026-10-23 永久禁止，不分颜色，游戏中 HUD 和图片字也算；`dark_bold_text`、`dark_picture_text`、状态字 `dev_text` 都为零）。观察 `buttons_and_title_one_piece_generated`（用户 2026-10-23，两个板块，重点）：所有字都是生成的图片字、和画面一体——按钮连字一次成整张图（`spliced_button` 为零）、首页标题是一张生成的 logo（`typed_title` 为零）、数字是按画风生成的数字位图字（`font_number` 为零）；只有公告、玩法说明这类大段文字可用细一点的字体；`art_check.py` 的"文字一次成图（标题logo、整张按钮、图片数字）"一行通过。观察 `no_squashed_picture_text`（用户 2026-10-23）：字图等比缩放、没有压扁拉长（`squashed_text`、`squashed_picture` 为零；反例 DETAILS 压扁 2.89 倍），没有 Canvas 画的字（`canvas_text`、`canvas_font_code` 为零）。观察 `text_colours_varied`：一页上标题、按钮字、数字、标签颜色不全一样（`uniform_text_colour` 为零；反例全青色 Hazel's Shelf Scramble 首页、全橙黄 Your Progress 弹窗）。观察 `all_screens_restyled_together`：`docs/art/screens.json` 列出所有能点开的页面和弹窗，每个都 dump 过、风格一致，`art_check.py` 的"字不压扁拉伸、字色有变化""全部页面和弹窗（docs/art/screens.json）"两行通过；只改美工时走 `cocos-game-art-redo`。观察 `no_overlap_clipping`（用户 2026-10-23）：没有穿模——字不压图标（反例体力"20"压在闪电上）、图不伸出按钮/胶囊（反例 WATCH AD 左边金币）、按钮和字不重叠（`overlap_text_picture`、`overlap_text`、`overlap_buttons`、`clip_out`、`text_outside` 为零），`art_check.py` 的"位置穿模"一行通过、Codex 看过 `overlap/` 穿模审查图。观察 `action_words_on_buttons`：WATCH AD、PLAY 这类主要功能字在生成的按钮上（`action_caption` 为零），按钮下的小字只做解释；道具/体力/金币/关卡的胶囊、按钮、收集键是生成的图，会变的数字单独生成位图字。
- **ART-05 首页两个主页键、不要分享**（两个板块，英化重点，用户 2026-10-23）：观察 `home_shortcut_revisit_keys_no_share`——`audit_ui_coverage.py` 报告里每个首页都有桌面快捷方式和个人主页回访两个键、没有任何分享入口；`audit_platform_markers.py <工程>` 不是 `share_feature_present_remove_it`。英化时这两个键直接加、不问用户；原游戏的分享按钮、弹窗、奖励和调用都删掉。
- **HUD-01 顶部资源栏**（两个板块，不能标不适用，用户 2026-10-22；最终测试只看数字实时变化 `counts_update_live`，位置和图标在美术关查）：`audit_top_bar.py --binding` 的报告（`docs/top-bar.json`＋dump_ui）；测试时按"首页/地图 → 过一关 → 回首页/地图"dump，货币和关卡数要当场变大。观察 `currency_never_in_the_middle`（用户 2026-10-23：每个页面货币只在最上方，报告 `currency_only_at_top` 通过）。ART-05 观察 `home_currency_top_buttons_bottom_compact`（设置在上角、功能按钮按中部两侧和PLAY下方最多五个分区，按钮合计≤40%）；PAGE-01 观察 `popups_have_generated_illustration`（`plain_popup` 没有）。
- **LEVEL-01 关卡板块**（两个板块，不能标不适用）：`audit_level_plan.py --binding` 的报告（**设计关**用 `design_check.py` 查，最终总检测不重查；`level_plan.json`：通关型至少 70 关（`levels_at_least_70`，多于 70 也行）、每 10 关一个限定关（第 10、20、30…关，华丽边框节点）、每 10 关一个按种子随机的奖励关（3 倍货币、看广告 6 倍、货币图标节点）、难度逐关递增、限定皮肤格式 `limited_skin_mode` 是 `final`（只有最后一个限定关送）或 `every_10`（每个限定关各送一款）、地图显示总关数；无尽型没有地图）。`level_plan.json` 是通关型（mode levels）时 **LEVEL-02** 不能标不适用，观察项都要实玩填。
- **FEAT-01 皮肤板块**：`docs/modules.json` 里 `skins.user_choice` 是 yes（默认）时不能标不适用，四个观察项都要浏览器实测（结算金币只加一次、试用也有加成、换完立刻生效、重开一致）；限定皮肤排最前变暗、卡片加成、越稀有越精致属于设计和美术，在设计关、美术关查（用户 2026-10-24）。
- **ART-06 美术自检**（两个板块，**美术关**查，最终总检测不重查，用户 2026-10-24）：每轮美术后 `art_check.py` 的通过报告（含首页礼盒 10 帧动画一行）；观察里写明每轮美术做完都跑过（`art_check_after_each_art_round`）、按意见修改时整页复查过、Codex 按看图清单看过总览图；`two_full_self_review_rounds`：交用户前至少两整轮自审、第二轮零"需处理"（用户 2026-10-23：美术是重中之重）。
- **ART-04 清晰度**（两个板块，用户 2026-10-23；**美术关**查，最终总检测不重查）：`art_check.py` 的报告（清晰度行＝dump 里运行时的图 `low_res`＋`audit_image_clarity.py`）；观察 `runtime_frames_2x_background_1_5x`（代码里动态设置的图集格、角色帧有效像素≥节点 2 倍，背景≥1.5 倍）、`same_check_every_art_round`（每轮美术自检就过了这一行；反例 RobotSpaDay 用户确认美术后最终验收才查出 22 张不到 2 倍，所以 2026-10-24 起只在美术关查）。英化未改的原图写 `docs/art/clarity-exempt.json`（每条 why）。
- **LOGIC-01 逻辑检查**（两个板块，不能标不适用，用户 2026-10-23）：`logic_check.py --mode build --binding` 的通过报告（`cocos-game-logic-check`）：重塑第一轮玩法做完、玩法确认节点 1 之前跑过（`logic_check_after_gameplay_round`），英化在优化和广告接入之后、美术之前；`docs/logic/inventory.md` 的按钮去向表里每页有出路——关卡内能回首页、设置能返回、失败页 Home＋Retry（复活广告单独在下面）、胜利页 Home＋Next、按钮位置固定（`every_page_has_exit_and_standard_buttons`）；暂停停住物理和计时、离开一局清干净（`pause_stops_physics_and_leaving_cleans_up`）；广告/加载回调带局次、超时安全恢复且不能叠奖励（`async_round_tokens_and_ad_timeout_recovery`）；刷新后进度和声音设置都在（`progress_and_sound_restored_after_refresh`）；F01–F20 用真实触摸走过、两种比例、每个 pass 有证据文件（`flows_walked_with_real_touch`）。review 模式的报告不能用来过门禁。
- **LOAD-02/LOAD-03 加载（最终检查重点，用户 2026-10-23）**：LOAD-03 报告必须是最终构建上的新报告，不写死结束时间（按 `*_allowed_ms`/`*_waste_ms` 判白等，计划不能放宽"不卡住"的三个数），观察 `no_fake_loading_wait`（下完就进，不超过 max(2 秒, 首页时间 25%)）、`every_level_entry_timed`（PLAY、地图选关、Next、Retry 进关都计时）、`final_build_loading_retest`；LOAD-02 观察 `every_entry_route_enters`（每条进关路线都真实进到能玩）。
- **PAGE-01 数字不叠印、没有假透明格子**（两个板块，用户 2026-10-23）：观察 `no_glyph_overlap_fixed_numbers_one_picture`（报告里没有 `glyph_overlap`/`double_number`/`negative_spacing`/`font_advance`；固定数字和金币图标/底板一起生成成一张图，会变的数字是一个位图字体 Label，三位数和最大值都放大看过；卡片里的奖励图不伸出卡片）、`no_checkerboard_fake_transparency`（没有 `checker_fill`，生成图是真透明）。反例：Daily Rewards 弹窗 100/150/200/300 像"10"叠在"100"上、第 7 天的车伸出卡片、卡片里是绿色棋盘格。见[数字不叠印](page-richness.md#数字和字不能叠在一起固定数字和底图一起生成用户-2026-10-23两个板块)。
- **英化选了"按重塑画风重做"**：`docs/art-style.txt` 写 `remake`，`init` 加 `--art-style remake`，ART-02、ART-03 对这个英化游戏也要通过；检查表和 art-style.txt 不一致时门禁会拦。

### 只有一种包：可直接上传的 TikTok 平台包（BUILD-04）

用户 2026-10-23（SquareRush UPLOADFIX）：旧包因 `assets/resources` 留在主包、未压缩主包 8,754,975 字节＞4,000,000 被 TikTok 拒绝。以后打包、出包、上传测试包、检测包、压缩包**都只出这一种包**，用 [`cocos-game-tiktok-package`](../../cocos-game-tiktok-package/SKILL.md) 的 `make_tiktok_zip.py` 出：

```sh
python3 /path/to/skill/scripts/make_tiktok_zip.py --native <Native构建> --app-id <App ID> --out <新ZIP> --resource-manifest <当前业务资源清单.json> \
  --project <工程> --web <Web构建> --build-tag <版本> --review <known-issue-review.json> \
  --startup-contract <当前启动报告.json> --loading-recovery-runtime <当前恢复runtime.json>
```

它先跑 `pre_scan` 门禁，再查形式和体积（外层文件夹、Web 构建、源码、ZIP 套 ZIP、Mac/Windows 垃圾、非 ASCII 路径、测试跳关、App ID、主包≤4,000,000、总包≤30,000,000、独立分包各≤4,000,000），不合格**不写 ZIP**；写完回读核对、独立解压再比，才放到 `--out`。报告 `<ZIP名>.report.json`（tool `make_tiktok_zip`，带 review 的 binding）放进 BUILD-04 的 `auto_reports`（`--stage post_package` 检查）。观察：`made_by_make_tiktok_zip`、`big_resources_in_normal_subpackage`（resources 等大 bundle 在 `subpackages/`，启动时带进度加载、有 Retry）、`main_total_independent_within_limits`、`root_entry_no_outer_folder`、`no_web_source_nested_zip_or_junk`。形式和改法见[包的形式](../../cocos-game-tiktok-package/references/package-forms.md)。

### 打包脚本必须真的拒绝（BUILD-03）

本游戏的打包脚本在生成 ZIP 前自己运行 `check_known_issues.py check --stage pre_scan`，非零就停止、不留 ZIP。出包时用下面的命令实际跑一遍打包脚本，证明缺检查表、有失败项、指纹过期、缺 `STORAGE-01` Native 自动报告时都出不了包，正常时能出包：

```sh
python3 /path/to/skill/scripts/test_writer_refusal.py \
  --review /path/to/project/known-issue-review.json --zip-dir /path/to/zip-output \
  --out /path/to/evidence/writer-refusal.json -- <本游戏的打包命令>
```

报告放进 BUILD-03 的 `auto_reports`（`--stage post_package` 检查）。只证明共用门禁会拒绝不算数，必须是本游戏实际的打包脚本。用 `make_tiktok_zip.py` 出包时，它就是打包脚本：`-- python3 make_tiktok_zip.py ... --out <单独的检查用 ZIP>`（已有的 ZIP 不覆盖；跑完删掉检查用的 ZIP）。

每条证据标`role`：`current_result`是本轮现场运行的JSON结果包装，要求`schema=known_issue_current_result.v1`、完整`binding`等于本轮、`status=pass`、整数`failed=0`；`execution`必须含命令数组`command`、整数`exit_code=0`、`tool`与`raw_report`的`path/sha256`；路径相对包装所在目录或为绝对路径。脚本核原报告的明确通过状态与无失败案例；无可识别结果保留待审，不拿手写包装代替执行。`current_artifact`用于本轮原截图、实际资源或绑定盘点，证据引用也带本轮`binding`，主线审阅原件。历史说明为`historical_reference`，预期失败的旧版报告为`negative_control`；后二者不能单独支撑当前pass。哈希能发现文件变化，不能证明从未被盘点的入口不存在、截图真实或人工声明准确。

```sh
python3 /path/to/skill/scripts/check_known_issues.py check \
  --project /path/to/current-source --native /path/to/current-Native \
  --web /path/to/current-Web --build-tag CurrentBuild \
  --review /path/to/project/known-issue-review.json --stage pre_scan \
  --report /path/to/project/known-issue-gate.json
```

缺项、pending、fail、limited、证据缺失/改变、旧源码/Native/Web、未补新catalog条目均返回2。`pre_scan`检查产包前能完成的项目，暂不要求最终ZIP回解结果和尚未扫码的真实手机结果；ZIP生成后以`--stage post_package`补验最终包与源、Web、Native的对应，真实设备项（`--stage device`）不在本 Skill 范围，不跑、不问；最终以 `post_package` 通过为准。后两阶段不得倒填为产包前已完成。现有手机输入六门禁、真实IAA、后台接受/发布保持独立，不能被本脚本替代。脚本只校验清单覆盖、字段、后置条件和证据完整性，不能判断截图是真是假、是否实际操作或未知缺陷；主线必须审查原始证据，不编造pass。

原执行报告自身也须有`binding`：至少含`source_sha256`和`native_tree_sha256 / web_tree_sha256`之一；所有记录的本轮绑定字段必须相符。旧成功报告缺少输入指纹时重跑项目回归，由现场运行记录输入，不能仅套本轮包装续用。

先准备当前实际Web及适配后的Native目录，供版本绑定和界面检查；项目提供prepare-only时只准备目录、不创建ZIP、不表示已验收。诊断坏基线可导出，但进入产ZIP入口仍须经过同一门禁。

实际打包器在写ZIP之前现场运行本游戏源/实际Native最小回归，再运行本清单校验。失败不生成新ZIP，不覆盖旧包。build-only导出仍可执行以供诊断。用户明确只要某阶段时按其范围工作，但未完成的检查保留待验，不把中间候选称最终验收。

## 持续维护

**项目里记 bug（每个游戏都要）**：每发现并修好一个问题，在本游戏 `docs/bugs.md` 记一行：`日期｜症状（玩家看到什么）｜原因｜怎么修的｜对应编号或"新"`。用户之后要整理经验时，直接看这个文件；交接包也带上它。

**沉淀进 Skill 的方法**：标"新"的问题，按通用化判据去掉游戏名后写成新编号，**必须带一句 `symptom`（玩家看到的现象）**；如果能用脚本从截图、工程文件或包里查出来，就写或扩展一个检查脚本并在该编号写 `auto_check`，让门禁强制运行，不能只加一句"以后注意"。

每次新增反馈，先搜索已有ID；同类问题补复现和边界，不重复建一批同义规则。新故障家族追加稳定ID，修正旧规则时保留替代说明并更新catalog revision，旧review因摘要变化重新核对。通用机制进入本Skill，游戏具体失败样例、原图/视频、命令和已验证版本留项目。已有规则漏执行与规则本身缺项分别记录，不能每次只加一句“以后注意”。

修改catalog或校验器后，运行 `python3 scripts/test_known_issue_gate.py --report /项目核验/known-issue-gate-selftest.json`，核对缺项、旧输入、假包装、错误不适用、加载/布局缺GUI及保存重看均被拒绝，并保留即时/持久、重复/导航的有效对照。该脚本只测试清单校验契约，不能据合成夹具声称游戏已通过。


## 页面就绪与后续资源取消重进（2026-10-23）

导航/分包/加载维护及最终出包前，按[页面就绪与取消重进](page-readiness-and-cancel.md)执行。首页resources故障不能覆盖后续包；取消旧导航同时保留资源成果，热缓存页面点击直达；LOAD-01新增audit_page_readiness的最终runtime报告，source_only静态报告不合格。实际输入改变后复验受影响业务链；不要用断言数或ZIP完整性替代漏测路线。

### 加载恢复组合故障补充（2026-10-23）

LOAD-03 强制执行[加载恢复回归](loading-recovery-regression.md)，新增自动报告 audit_loading_recovery 和三项观察。缺 SDK＋定时器组合、第二次真实请求、旧成功/失败隔离、Native 边界、正常对照任一项均不能标通过；原计时和逐路线测试继续保留。报告字段与脚本命令见该页。


### 提供测试包前的简要问题清单（2026-10-23）

以下清单适用于交给用户的测试包，不能以“只是测试包”跳过。完整复现见[案例](loading-recovery-casebook.md)。

| 已发现的问题 | 出包前必须看见的证据 | 对应门禁 |
|---|---|---|
| 字体失败/不回调卡首页，晚到重建UI | fail、hang仍首页→Play→真实操作；晚到不重启页面；没有外部字体则记录实际未调用及正常操作 | LOAD-03 optional_font |
| SDK回调和原超时都不执行 | 两者同时扣住，仍有失败出口，Retry后真正可玩 | LOAD-03 sdk_and_watchdog_held |
| Retry复用旧图片在途任务 | 真实传输挂起→触摸Retry→同资源第二次底层请求→ready→实际操作 | LOAD-03 image_inflight_retry |
| 新请求继承启动旧计时 | 守卫先安装、延后创建请求不早超时；真实进度先于帧也不误判 | LOAD-03 request_local_clock |
| 慢下载/后台被误判、旧成功或失败拉走页面 | 持续进度、后台完成/未完成、旧成功/失败逐项验证；当前目标和输入正确 | LOAD-03对应恢复场景 |
| 菜单被无关资源卡住、取消重进丢缓存 | 核心菜单独立；慢下载三次取消重进、旧完成隔离、热缓存断网可用 | LOAD-01 audit_page_readiness |
| 只到首页截图，下一关/失败重试/地图实际进不去 | Play、Next、Retry、地图各自进入并真实操作；教程及存档reload恢复 | LOAD-02/03、LOGIC-01 |
| 包入口或绑定错误、旧报告冒充当前版 | 当前source/native/web绑定；ZIP根game.js及配置；独立解压核对和实际加载复验 | BUILD-03/04 |

LOAD-03观察补充`optional_font_nonblocking`、`request_local_clock_verified`，恢复自动报告现为12场景。缺项、未测、只有静态/入口替身或旧10场景报告均不通过。出包交付必须带当前review执行pre_scan，完成后执行post_package；结构诊断只用 verify_native_zip.py 读取现有包；make_tiktok_zip.py 已拒绝无 review 出包。手机Runtime、真实广告和平台接受另记，不补填通过。

最终出包另需 [实际运行覆盖表](execution-checkpoints.md)：正式 writer 扫描并核对源码/Web/Native 存储调用归属、实际测试目标与证据哈希；未归属、缺用例、过期一律拒绝。此表补充原检查表，不能代替 LOGIC/AD 等门禁。
