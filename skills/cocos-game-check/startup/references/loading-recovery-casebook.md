# 加载与重试：Mosslight v20 复盘与可复用检查

来源：2026-10-23 用户要求把完整修复过程及漏测位置写入 Skill。适用：Cocos 页面/场景/资源加载维护、完整逻辑检查、Native 测试出包。历史游戏为60关；不把60关、它的资源名、App ID或画风变成其他游戏的要求。当前用户范围优先，本文不扩大外部操作授权。

配套：[恢复矩阵与证据格式](loading-recovery-regression.md)、[加载时序](startup-loading-timing.md)、[页面取消重进](../../test/references/page-readiness-and-cancel.md)、[启动契约](startup-contract.md)。先读当前阶段相关部分，不通读所有游戏历史。

## 1. 为什么以前会漏测

以前的测试证明了“按钮 Retry 再调一次 loadBundle”，却没有证明 Cocos downloader/parser 内部也创建了新任务。替身与实现使用同一层假设，双方一起漏掉底层合并队列。只看成功回调、Home截图、HTTP200、ZIP结构，也证明不了失败后能恢复并真正操作。

其他遗漏包括：SDK回调与原超时定时器同时不执行；可选字体阻塞启动；守卫安装到实际请求之间的空白时间被错误累计；后台时间与有效下载进度被当成停滞；取消导航丢掉已完成资源；教程虽保存但启动未读回。修复不能只增加测试条数，必须改变故障注入边界和观测对象。

## 2. 先固定对象与原始证据

1. 确定当前项目、准确输入、当前候选、独占写入路径、原包及存档。另建候选，不改用户原包或清空用户存档。
2. 画出实际链：HTML/Native入口→引擎适配→SDK分包→Cocos bundle→文件下载→图片/字体/音频解码→页面就绪→真实输入生效。列每个等待点、callback/Promise返回路、可见反馈、取消及退出。
3. 测前写不可变计划，记录版本、两种比例、冷热缓存、网络参数、故障边界、计时点、动画ROI；每轮保存完整计划原字节及SHA。真实首次冷启动完成且输入生效后，才可记warmup_done。
4. 旧版失败、新版恢复、无注入正常对照使用同一判据。保留原日志、请求身份、时间原点、截图/帧、实际输入及结果。第一次复现数据遗失应明确标缺，不能后来生成一份冒充原记录。

## 3. 故障、根因、修法和观察对象

| 实际故障 | 根因 | 修复原则 | 必须看见的结果 |
|---|---|---|---|
| 外部字体回调不回，加载页面没有操作出口 | 把可选字体当作首页启动前提 | 首屏必需美术与字体并行；字体成功后只更新实际文字，不重启页面；字体fail/throw/hang都有正常主流程 | 字体一直不回仍Home可点、Play可进入、实际操作有效；晚到成功不重复建UI |
| SDK回调与旧setTimeout都扣住，永远无失败出口 | 回调和定时器成为共同单点 | 当前帧或可靠生命周期恢复路径检查每个请求的无进展时间；成功/失败只结算一次 | 实际无进展后可见Retry；恢复后新请求和实际移动；原超时定时器继续被扣住 |
| Retry点击了两次但服务器同一图片请求始终只有一次 | Cocos内部同ID在途队列仍等待旧原始回调 | 让原始downloader/parser回调以失败结算一次，释放等待和并发；可中止就中止，否则隔离晚到结果；保留已完成缓存 | 首次真实HTTP/原生图片解码挂起→失败→真实Retry→同一资源第二次底层请求→ready→真实操作 |
| 新请求刚创建就超时 | 继承守卫安装时钟；首帧累计了此前启动耗时 | 每请求自有last_progress/idle；从创建或最后真实进度计时 | 守卫安装后等60秒再创建请求，1ms更新不失败；无帧间隔先到进度再到帧不误判 |
| 下载仍推进或后台等待时误报失败 | 固定总截止或重复进度错误续命 | 只计算前台连续无有效进展；有效字节/百分比增长才更新；后台暂停计时、恢复后核实际完成态 | 持续真实进度超过旧总截止仍成功；重复同数值不续命；后台完成及未完成都能正确恢复 |
| 返回首页后旧成功/失败把页面拉走 | 缺导航代次和请求身份 | 取消导航失效代次，晚到资源成果可缓存，晚到导航提交必须拒绝 | 三次取消重进无旧页面闪回；旧成功和旧失败均不影响新目标 |
| Help/Settings/Pause也等地图或全量美术 | 共享大批加载屏障绑在所有按钮 | 按页面最小资源就绪；核心控件可用内置风格回退；不要为打开设置下载地图 | 扣住extra/game包时核心菜单真实点开；热缓存不重复工作；暖缓存断网仍可到已就绪页面 |
| 教程每次重来 | 保存了tutorials但构造时重置为空 | 启动恢复有效记录，校验坏存档；不改变新玩家首次指引 | 完成教程→Home→reload记录保留；独立新存档仍显示指引 |

### Native适配边界

Native分包守卫必须在适配器捕获函数前安装。图片守卫包裹适配器实际注册的downloader/parser，保留原生文件、缓存和解码处理器。不要把Web Image/XHR替换成Native实际实现。callback-only、Promise-only、二者同时、无可选progress API、throw/reject/error、重复与迟到结果均覆盖。

参考实现位于 `../assets/loading-recovery-examples/runtime-load-guard.js` 和 `asset-load-guard.js`，来自本次Creator2.4.15候选。它们是**版本相关示例**，保留原游戏命名空间以便溯源；移植前核实际引擎/适配器接口和注册顺序，不能把示例原样复制就判通过。由当前游戏每帧驱动update、生命周期驱动setBackground并接入实际加载链。下载与解码可有不同阶段，按真实可观测进度判断，不凭假百分比刷新计时。

## 4. 真实HTTP复现方法

在独立测试端口挂起一个首屏实际图片响应，其他文件正常服务。保持旧响应挂起，仅放行未来请求；记录同一URL的服务器请求序号。等可见失败，真实触摸Retry；底层请求数必须恰好增加一次，ready属于新请求，随后真实触摸产生业务变化。旧响应随后成功或失败不得改变新状态。最后关闭自有故障服务并读回端口消失。

不能只在loadBundle入口伪造返回值，也不能用临时改变产品超时、控制器调用、强制通关或写余额代替真实输入。外部SDK/生命周期测试替身只放隔离QA入口，不进交付Native或普通用户预览。浏览器生命周期事件模拟只能称模拟，不能写物理手机后台通过。

## 5. 动画和计时采集本身也要校准

- 引擎前CSS动画和Canvas内加载标志位置不同，用各阶段完整标志ROI；大联合ROI含太多空白，缩小后会稀释真实微动画。不能靠背景流水运动算加载标志在动。
- 保存逐帧原图、阶段、时间和CDP成功回执。不要凭采集器有一行setNetwork就写已生效。实际网络量使用ResourceTiming.transferSize，encodedBodySize单列；缓存命中不能算再次下载。
- 截图文件名按毫秒取整，performance.now保留小数。已观察ready且距离对应ready标记≤1ms的终点帧可排除加载ROI统计；任意较早ready或无阶段标签仍失败。短于1秒的完整等待不会超过1秒冻结，但长等待必须有充分原始帧。
- 计划/采集器改变后保留旧失败并重测受影响集合，不把后来的计划SHA贴到以前的报告。检查器失败先判断是产品、采集还是判定问题，再做对应修复；不能放宽1秒动画冻结、10秒无进展、之后2秒可见Retry来消除失败。
- 慢网完成时间按真实下载量、带宽及延迟评估，不要求任何体积的游戏都在固定几秒结束。不允许假的最短加载时间、进度条拖延或串行等待无关资源。

## 6. 加载修复后不能漏掉的业务回归

加载影响所有入口。按当前项目机制测试：首页/Play、Next、结果Retry、失败Retry、地图选关、Pause/Resume/Home、Settings/Help、资源失败BackHome、加载取消重进、reload存档、教程、触摸取消和第二指。确认遮罩/暂停时不能误操作、恢复后输入真实生效。

Mosslight具体机制还覆盖：60关/末关无Next、每关一次免费提示跨重开不刷新、提示券只在有实际提示效果时消耗、广告完成一次发奖、cancel/error/reject/throw/timeout/late/duplicate不重奖，结算翻倍与续玩分别验证；每日两种奖励各三次及次日恢复。其他游戏按自己入口清单验证，不强加这些经济规则。次日测试使用持续流动的时间偏移，不冻结Date导致加载计时失真。

如果全量通关发生在最终加载修复前，必须证明后续差异只涉及加载，最终编译Rules重放全关并真实复测受影响加载链；否则重新执行受影响的玩法回归。不得把旧版本全量记录直接写成最终版本全量触屏记录。

## 7. 门禁、出包与结果边界

保留 `audit_startup_contract`、`audit_startup_loading`、`audit_loading_recovery`、`audit_page_readiness` 各自职责；静态source-only不算runtime。恢复报告按最新矩阵12场景执行（新增字体与请求时钟）；真实请求序列/原始证据哈希要求见恢复矩阵。将绑定到当前source/native/web/build_tag的最终报告放入对应known-issue项；缺原始证据、版本漂移、负例逃逸都不能通过。

用canonical `make_tiktok_zip.py`生成真实Native平台ZIP，根目录直接game.js/game.json/project.config.json，写前核体积和App ID，写后CRC、逐文件比对、独立解压，再对解压实际编译模块/入口复验；Web成功不能等同Native SDK启动通过。测试包若没有正式总门禁应明确写明，不能以一个自建包装器的passed代替总门禁。

历史上传两种错误分开记录：`game.js must exist in the main package`明确指向主包入口，应检查ZIP根目录和导出类型；`invalid character 'a' after top-level value`只说明平台打包结果JSON解析失败，单凭此句不能断言项目某个JSON坏了，应结合原包、平台完整日志、结构与官方工具核验。最终是否被TikTok接受，只能以实际上传结果为证。

## 8. 可运行的防回退自测

从本Skill根目录使用已有Python（Pillow；全美术检查另需NumPy）和Node：

```bash
python3 scripts/test_loading_recovery_gate.py
python3 scripts/test_startup_animation_phases.py
node scripts/test_image_inflight_example.cjs
node scripts/test_native_load_guard_example.cjs
python3 scripts/test_known_issue_gate.py --report known-issue-selftest-report.json
```

恢复门禁负例覆盖缺场景、错误请求身份、缺真实图片重试、时序/哈希/绑定错误。图片示例覆盖引擎风格同ID队列释放、旧结果隔离、60秒启动空档、24秒真实进度、进度先于首帧、后台与解码结算一次。动画自测包含静止拒绝、运动接受、缺标签拒绝、终点取整接受和中途ready拒绝。**这些是检查器/示例自测，不是任何当前游戏通过证明。** 修改相应逻辑后跑相关负例，避免产品与测试共同遗漏同一条返回路。

## 9. 这次实际成果及证据保存方式

Mosslight v20最终：27次加载审计（18个正常网络/缓存/比例运行＋9故障），10项恢复场景；60关自然触控序列＋加载差异证明＋最终编译Rules重放；44项按钮/广告、28项结算广告检查；最终ZIP独立解压，官方离线18项。真实HTTP确实出现同URL第二次请求。没有实际手机Runtime/真实IAA/后台上传接受证明，不能推导这些层已通过。

项目事实和完整原始记录留在项目Wiki/游戏docs；Skill只保留通用方法和最小可运行示例。证据名可检索：`browser-real-http.json`、`image-inflight-contracts.json`、`font-startup-contracts.json`、`native-guard-channels.json`、`startup-loading-v3-final.json`、`loading-recovery-final.json`、`post-image-change-proof.json`、`zip-independent-final.json`。迁移到别的电脑不依赖原电脑绝对路径。

融合时同时保留本地并发新增的logic_check实例回归R01–R08：循环列表、坏存档、真实挂起重试、资源消费者、失败暂停出口、按钮实际反馈、触点归属、当前运行数据绑定。它与LOAD恢复矩阵互补；旧的F01–F20通过不自动填满新行，新行缺观察、哈希或当前源绑定仍失败。
