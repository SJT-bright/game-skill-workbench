# 启动契约：游戏必须进得去（所有游戏强制，用户 2026-10-21）

来源：《躲雨小鸭》等多款游戏首页一直转圈、进不去游戏。查出来的原因不是运气，是写法问题：

- 把**可选的提示接口**（showModal/showLoading 等）当成启动必需条件：缺了这个接口就直接不启动，而测试替身恰好提供了它，所以没测出来；
- 只保护了部分加载阶段：分包之后的资源、场景、入口出错时，有的只打印日志，没有恢复入口；
- "重试"其实还挂在同一个旧请求上；只"忽略旧回调"挡不住引擎真的切进旧场景；
- 首页前把以后才用的美术和声音全塞进启动包（26.7 MB），改成按需加载后降到 10.35 MB。

以后**每个游戏**（新做、英化、重塑、维护）都按下面写和测。英化/维护拿到的旧源码，第一步就按本页检查启动链，不合格先修，再做别的。英化时只改启动、加载和分包的代码与配置，不改美术、玩法和声音内容（声音挪到单独分包不算改声音）。

## 一、写法（组装线必须遵守）

1. **只有真正需要的才是硬依赖**：引擎、入口文件、Canvas、分包加载能力、首页必需的资源。提示弹窗、toast、加载提示、统计、震动、分享、广告 SDK 初始化都是**可选**的：不存在、canIUse 说不支持、调用抛错、返回 false、异步失败、Promise 拒绝、**一直不回调**，都只走降级，绝不拦住启动。
2. **原生弹窗一直不回调**：5 秒后游戏自己显示一个提示和明确的按钮（需要玩家点一下才继续），不自动无限重试；旧的、重复的确认只算一次。
3. **入口最先建立保护**：在加载适配器和引擎之前就建立启动保护，入口里的同步异常也能进入"出错→Retry"，不能被提前写好的"成功"标志吞掉。
4. **分阶段、有代次**：分包、引擎初始化、场景、首屏图片各自是一个阶段，每次尝试有自己的代次，只接受当前代次的结果。
   - **场景**：先加载场景资源（3.x 用 `bundle.loadScene` 拿到 SceneAsset，2.4 用 `preloadScene`），确认还是当前代次，再切场景（`runSceneImmediate`/`runScene`）。不能直接 `director.loadScene` 然后靠"忽略旧回调"挡旧场景。
   - **引擎初始化**还没回调时，重试不能再调一次 `game.run`；迟到的初始化结果只给当前代次。
5. **超时按"前台连续无进展"算**（默认 15 秒）：真实进度增加就重新计时，重复或倒退的进度不算，切后台暂停计时。不能用固定总截止、不能无限等待、不能自动反复重载。
   - 进度覆盖当前阶段的全部硬依赖，prefab 数量不能代替纹理/场景就绪；只有目标页面可操作才结束等待。引擎前加载反馈不再依赖待加载的大图或字体。共享在途请求可复用，但失败/超时须清除拒绝或悬挂的 Promise；重试须能接收真实新进度和终态，旧 owner 不切场。
6. **404/503/一直不回调都要有恢复入口**（Retry），**Retry 必须真的发出新请求**（例如图片重试新建一个 Image/新请求，并解绑旧结果），恢复后要能真正进关、操作，不是只回到首页画面。
7. **首页 ready = 首屏必需图片真的加载完**，不是"场景建好了""接口调用发出去了"。ready 之前按钮不执行业务（显示等待）。
8. **启动包只放首页和第一关要用的东西**，启动下载量默认不超过 10 MB：
   - 启动包：首页、第一关、字体；
   - 后续包：其他地图、皮肤、商店、声音面板等页面的美术，用到时再加载；当前装备的资源可以提前预取；
   - **声音单独一个包**：声音加载失败不能挡首页和 PLAY，之后再试；不清音量设置和存档。
   - 不靠删声音、降画质、丢存档来"变快"。
   - 核实际 Native 的分包下载边界：延后读取纹理不等于延后下载整个所属分包。记录首页必需依赖与后续页面依赖，按实际导出包归属核下载量；不把 Web 请求减量当手机耗时改善。
9. **后续页面加载失败**：只影响那个页面，给出提示，重新打开时再试；不影响正常玩。

## 二、怎么测（在独立 Google Chrome iPhone touch 模式里用当前生产代码，不改写被测的加载器）

[启动加载计时](startup-loading-timing.md)的故障测试里，下面这些每个游戏都要跑（`audit_startup_loading.py` 会检查一个都不能少）：

| fault | 怎么构造（chrome_touch 计划） | 必须看到 |
|---|---|---|
| `optional_api_missing` | `init_js` 放一个没有 showModal/showLoading 的平台对象 | 照常进首页、进关、操作有效 |
| `native_modal_no_callback` | `init_js` 让 showModal 永远不回调 | 约 5 秒内出现游戏自己的提示（mark `fallback_prompt_shown`），点一下后能继续玩 |
| `image_no_callback` | `hang_urls` 让一张首屏图片一直不回；出现 Retry 后 `unhang` 再点 Retry | Retry 发出新请求，最后真的进关操作 |
| `audio_fail` | `block_urls` 让声音文件/声音包失败 | 首页和 PLAY 照常，能玩 |
| `deferred_bundle_fail`（有后续包时） | `block_urls` 让一个后续包失败，打开对应页面 | 该页面有提示（mark `deferred_failure_message`），正常玩不受影响 |
| 原有四种 | 慢但有进度、切后台、卡住后 Retry、旧结果迟到 | 见计时页 |

测试替身不能"什么都提供"：那正是上次漏检的原因。每种故障先在旧版上确认会失败（第一次发现时保留旧版失败、新版通过、正常对照）。

## 三、静态检查（便宜，每次预检都跑）

`scripts/audit_startup_contract.py` 查两件事：

- 源码里容易导致进不去的写法：可选接口当启动条件、加载用固定长时间 setTimeout、直接 `director.loadScene`、`game.run` 出现多次、Retry 重用同一个请求。每处要么改掉，要么在 `docs/startup-contract-review.json` 里写一句为什么没问题（例如"这是首页之后的制作人员页"）。
- 实际 Native 构建的启动下载量（主包 + `--startup-subpackages` 列出的启动分包）不超过 10 MB，且启动下载里没有声音文件。

一键预检会跑源码部分；出包前带 `--native` 和 `--binding` 跑完整版，结果进门禁 LOAD-01。脚本只能拦住已知的写法问题，真正证明"进得去"的是上面的故障测试。


## 页面就绪与后续资源取消重进（2026-10-23）

导航/分包/加载维护及最终出包前，按[页面就绪与取消重进](page-readiness-and-cancel.md)执行。首页resources故障不能覆盖后续包；取消旧导航同时保留资源成果，热缓存页面点击直达；LOAD-01新增audit_page_readiness的最终runtime报告，source_only静态报告不合格。实际输入改变后复验受影响业务链；不要用断言数或ZIP完整性替代漏测路线。

## 无回调＋定时器失效与真正重新请求（2026-10-23）

加载和最终检查必读[加载恢复回归](loading-recovery-regression.md)，执行组合故障与旧/新/正常对照。不得仅以有 Retry 判通过；必须记录底层新请求身份和恢复后真实操作。正常有效共享任务与缓存保留，失败/放弃任务释放，不能用全量清缓存处理所有导航。LOAD-03 另附 audit_loading_recovery 当前报告。


## Native 真入口与 Renderer（2026-10-24）

启动单元替身曾掩盖真实故障：入口先在共享 Canvas 取 `2d` 绘制 fallback，Cocos 随后取 WebGL 被拒；任意对象的 `getContext` 与空 `cc.game.run` 会把它误报通过。启动提示须避开引擎 Canvas 的上下文占用。

涉及入口、adapter、引擎初始化或启动 fallback 的改动，必须从最终 Native `game.js` 走真实 adapter、原引擎 renderer 到实际 active scene；可模拟平台外围 API，不替换 `cc.game.run`、renderer 或浏览器 `HTMLCanvasElement.getContext` 的语义。Web 专用入口、静态扫描和 Node mock 只作独立检查，不能关闭 Native 启动项。

同一真实浏览器先校准：一个 Canvas 先取 2D 后取 WebGL 必须失败，另一个新 Canvas 的 WebGL 必须成功。保留真实旧包失败、修复版通过，以及把同缺陷重新注入修复版后失败的原始结果；校准或故障负例不成立就拒绝结论。记录入口→adapter→renderer→scene 的实际顺序、上下文返回、原引擎函数身份、错误堆栈、scene 与同次截图，并绑定最终 source/Native/Web 和 runner 身份。`scripts/audit_native_startup_renderer.py` 校验证据；Ember 正式维护 gate 强制接入，缺报告、缺原始证据、空 run、替换 renderer 或身份不一致均拒绝。检查工具的拒绝自测与产品运行结果分别报告，不把宿主/真实浏览器模拟升级为物理设备或平台通过。

正式 gate 还须自行执行已审核 runner，再校验本次输出；静态 JSON 不代替执行。受信注册按[项目QA注册](project-qa-registration.md)：项目提供相对路径清单，执行机保存已审阅代码SHA与固定参数，不修改共享Skill；无shell，报告任意command不执行。runner 或依赖变更须重新审查登记，未登记、超时、没有本次输出、Native 在执行期间改变均拒绝。

真实 adapter 的 downloader→parser 数据类型也是启动契约：下载阶段返回的 path／ArrayBuffer／Image 须符合该 Native parser 的实际输入，不能拿 Web parser 或万能替身覆盖。对已发现的类型协议缺陷，须独立重注入该缺陷，在 renderer 正常建立的前提下复现实际解析错误，并保留修复后 active scene；Canvas 反例不能代替这项。受信 runner 的宿主与所有执行依赖同样登记 SHA，正式 gate 执行前逐项核验。

通用接入：`audit_startup_contract.py --native ... --binding ... --renderer-report ...` 的正式 Native 检查执行真实链探针；`--source-only` 仍仅作局部静态预检。`check_known_issues.py` 的正式 LOAD-01 只接受 policy v2 运行报告，并重新执行受信探针，旧静态报告不能满足该项。其他项目须登记审查过的实际 runner，不能借 Ember 的注册或伪造项目路径放行。

## Loading场景假通过补充（2026-10-25）

最终启动验收与平台卡Loading排错必读[具体案例、解决方法和检查器反例](loading-scene-false-positive.md)。renderer检查已强制HOME可用及真实触摸后的玩法变化；缺真实观测拒绝，不接受只填scene.active。
