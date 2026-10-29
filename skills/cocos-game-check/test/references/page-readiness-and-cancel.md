# 页面就绪、点击直达与取消后重进

2026-10-23 加入。适用于已有游戏维护、英化和重塑中真实存在的页面与资源链；不授权改玩法、美术主题、关卡、经济或存档。用户指定局部范围时，至少覆盖改动触及的依赖和页面，不把无关旧问题写成通过。

## 先定体验，再分包

玩家的普通导航不是资源管理器。首页、设置、帮助、暂停、已有奖励说明和已经到达过的页面，应当点击直接进入，不套统一“资源准备中”面板；游戏内不展示文件数量、bundle名称、UUID或内部stage。确有首次大资源下载，才显示符合游戏风格的下载说明、真实进度、可用退出与恢复；下载百分比不同于文件数量。不能靠假进度、延长超时或反复让用户返回来掩盖问题。

将页面分成实际需要的层次：

- 首屏和普通本地弹窗：随必需UI准备。打开设置/帮助不应依赖衣柜、商店、全部皮肤等包。
- 首局/下一局：在合适时机预取将要用的关卡与当前装备；核心玩法不依赖所有皮肤、全部地图和以后页面。首页就绪后可低优先预取首局；不得因预取抢占输入、拖慢当前首屏或播放音频解锁。
- 可延期的独占内容：仅请求目标页面所需。大量内容分组、按页/当前项加载。不能为了主包小，把所有剩余内容重新合成一个人人必等的大包。
- 已加载内容：明确复用内存/合法本地缓存；重开、返回、领取后重绘、进入下一关不重复下载同一组资源。

“点击直达”针对已就绪内容，不承诺尚未下载的任意远程内容零耗时。审查依赖图与实际网络轨迹，不按包名猜哪些内容是首局必需。计时遵守 startup-loading-timing.md，不发明最短等待时间。

## 资源任务和页面意图必须分离

取消等待通常只取消本次导航，不应自动使已完成/仍可复用的资源全部作废。一个资源组使用共享任务/缓存：

1. 目标页关闭后，结果不得强行切回旧页、发奖或改当前局。
2. 正在进行的安全资源下载可继续完成并写入正确资源缓存；玩家回首页也保留这份成果。若明确选择停止下载，必须真正中止/标记可恢复，下一次不能挂到被抛弃请求。
3. 再次打开附着到同一有效任务，或在确认失败后发起新请求；不得每点击一次就重置整组资源状态、清缓存、叠新任务。
4. 资源成功与导航成功分别结算，重复回调不重复提交。失败、超时和真实进度有各自状态；只有递增进度延后“前台无进展”截止，后台等待不消费该截止。
5. 无进展有提示、Retry/返回；只在用户显式操作时重试。Retry必须发新请求；旧结果不能替换新任务。资源部分成功尽量保留，不强行重置所有内容。

## 必须执行的矩阵

开工先从实际UI/路由/ClickEvent双向列页面入口、依赖组、首次需要的字节、就绪条件、第二次是否会再请求。实际运行确认路线，不能只搜索同名方法。写 `docs/page-readiness-plan.json`，每个入口为 `core`（普通本地/常用页面）或有具体理由的 `deferred`。所有实际待交付入口均在范围中；单次用户反馈维护明确列影响集合与未覆盖入口。

每条在范围内的路线，两种手机比例至少执行：

| 情形 | 故障或前置 | 必须观察 |
|---|---|---|
| 冷缓存首次打开 | 独立QA origin/受支持清理，不清用户存档 | core无资源等待遮罩，页面可操作；deferred只下载自己必需组，有合理说明 |
| 热缓存再次打开 | 成功到达后退出再打开 | 已就绪页面直达，不请求同组字节，不出现加载面板，实际按钮/触摸有效 |
| 慢加载三次取消再打开 | 后续包与其图片都可分别延迟；不是只延迟首页resources | 取消不跳旧页、不丢可复用成果、不叠任务；后台完成后下一次直达 |
| 页面关闭后任务完成 | 留在首页/另一页等下载完成 | 不抢导航；资源ready仍保留；重进可用 |
| 真实失败后重试 | 分包失败、包成功但某图片失败/不回调分别触发 | 看得到失败，Retry发新请求，已成功资源不全清，旧回调不影响新页 |
| 已缓存时断网重进 | 已完整到达的页面，断网后退出再入 | 本地内容可用，不把无关新下载变成硬依赖 |
| 普通控件独立性 | 后续独占大包挂起 | 设置、帮助、关闭、返回、音量/暂停操作仍有效 |

对玩法入口还要从首页PLAY、地图选关、下一关、免费重试进入后实际触摸产生一项业务变化。看到页面名字、loading消失、无报错、HTTP200或截图不是“可用”。

慢网络必须覆盖“下载仍在增长”和“完全无进展”；分包配置延迟是有效局部对照，但不能代替图片传输、目标Runtime或手机实测。Web、Native适配器边界、物理设备分开写。用户手机反馈不得先归因旧包/网络，也不把本地复现等同手机唯一根因。

## 证据与拦截

- `audit_page_readiness.py --project GAME --source-only --out REPORT` 只产生静态风险结果，用于preflight；不证明点击直达或已完成GUI矩阵。
- 最终 `--plan PLAN --runtime RUNS --binding REVIEW --out REPORT` 要求真实运行轨迹、每条路线各场景及两比例、当前binding和路径SHA。用工具记录的触摸时间/页面可用时间/资源组请求/等待遮罩，不手填pass替代轨迹；逐条人工审页面是否真可用。
- `LOAD-01` 要求此工具最终runtime报告，source_only报告不允许代替；缺报告/缺场景/失败/旧binding/无证据字节就拒绝。维护专用writer同样不得绕过新发现问题，用当前受影响路线证明修复。
- 首次出现保留同一判据的旧版失败、新版通过、正常对照；校准测试的判据不是“取消后ready应为false”，而是“旧导航失效，但资源成果保留、下一次真可用”。
- 汇报以业务链覆盖和剩余缺口为主。多少个局部断言、CRC/全SHA、页面截图数量不能替代未走完的业务链。不要保证未知的同类问题永不发生；给出当前能够提前拒绝的已知失效模式。

## 报告最小结构（给测试执行者）

计划的 `routes` 来自本版实际UI盘点；`inventory_evidence` 指向该盘点文件的相对路径和SHA。局部维护必须解释影响集合，不允许把全部入口缩成一个虚构route。`viewports` 填实际使用的两种比例。

```json
{"scope":"affected_routes_maintenance","inventory_evidence":[{"path":"route-inventory.json","sha256":"..."}],"viewports":[[375,667],[390,844]],"routes":[{"id":"settings","kind":"core","reach_steps":"首页 > 设置 > 调音量","dependency_groups":["core-ui"]}]}
```

`runtime` 必须含当前完整binding、`producer: "real_browser_touch_trace"`、`raw_evidence`（相对报告目录路径+SHA）和 `cases`。每个case写 `route / viewport / scenario / trusted_touch / target_interaction_effect / script_errors / player_internal_file_count / evidence_refs`；effect必须描述真实操作后的变化，refs是raw_evidence的索引。deferred route使用下表七种情形；local_independent route以额外的 `independent_interaction_under_unrelated_load` 情形替代其自身加载Retry矩阵。

- `cold`：记录 `wait_overlay_ms`，core必须为0；deferred保留实际下载与时序，不把真实下载藏成空白页。
- `warm / offline_warm`：`route_download_bytes: 0`、`wait_overlay_ms: 0`；网络字节只计算本route的依赖，无关后台下载另列。
- `slow_cancel_reopen / closed_completion`：`resource_ready_retained / latest_navigation_only / no_duplicate_inflight_task / reopen_usable`均须true；前者 `cancel_count >= 3`。
- `failure_retry`：`visible_failure / retry_new_request / recovered_usable / stale_result_ignored`均须true。
- `independent_interaction_under_unrelated_load`：`unrelated_bundle_pending: true`、真实目标交互effect、`interaction_completed_without_wait: true`、实际测得的 `observed_request_count` / `observed_network_bytes` 及 `wait_overlay_ms: 0`。同窗口可包含本地懒加载与后台流量，因此不得把观察流量冒称目标路由字节为0；原始请求URL、响应和字节须可读。

### 按实际依赖区分路线

计划中每条route必须增加 `loading_mode`，并由实际资源调用轨迹和双向路由清单支持：

- `deferred_resource`：该目标首次进入确实发起自己的延后资源请求。`Battle`、`Match` 等路线保留上表全部七个情形；`failure_retry` 必须观察目标错误、玩家实际点击 Retry、新的 HTTP 请求、成功进入并隔离迟到回调。不能用另一个路由的失败或网络面板代替。
- `local_independent`：无需等待独占资源才能进入并互动的路由。对本次维护的批量本地路由门禁，每条路由、每种手机比例至少在真实无关HTTP请求挂起期间触摸并完成一项目标交互，证明没有阻塞遮罩；同时记录请求窗口内全部真实网络请求、响应和字节，并确认交互无需等待懒加载完成。允许有非阻塞的延迟资源加载；不能把混合窗口流量错记成零，也不必虚构七类目标加载故障或页面Retry。此类路由不得伪造页面Retry、新HTTP或目标资源失败。

此差别只免除没有目标资源任务的本地路由 Retry 链；不免除逐路由两比例、真实触摸、原始轨迹、当前 binding 和后台资源独立性，也不改变 Battle/Match 的七情形要求。静态依赖声明不能单独证明 `local_independent`。

这些字段由原始触摸/网络/运行状态轨迹归纳，不能直接手填true当作运行证据。检查器只验证结构、覆盖、引用字节和显式失效；最终审查者仍须打开原始证据确认含义。后台完成、部分资源失败、持续进度/停滞分别在上述原始轨迹中标出；没有执行不写true。格式自测可以用合成输入，游戏验收不可用合成自测报告替代。
