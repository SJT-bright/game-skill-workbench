# Native 场景加载失败：路径、SDK边界与交付防复发

2026-10-24。触发：Cocos小游戏加载维护、`scene-load-failed`、本地能玩但手机卡启动、分包迁移、最终测试包。适用于真实存在这些机制的项目，不要求重写无关玩法或搬用本案例私人路径。

## 症状与证据不要混淆

- 平台白色加载页：入口/分包/首帧都需排查，不能仅凭录像断言唯一SDK根因。
- 游戏自己的错误页出现：只证明错误恢复UI执行过。`scene-load-failed`指向SceneAsset或其依赖失败，**不是已经修好**。
- Retry仍回到同一错误：先追踪实际请求路径、错误详情、请求身份和文件，不能让用户反复点或仅延长超时。
- 本案例修复：在拒绝父目录跳转的受控文件边界下，准确旧包复现同形错误；修复后本地成功。未取得底层手机日志或新包手机成功，不能说手机根因已唯一证明或永久解决。

## 已复现的失效机制

1. Cocos2 `bundle.base + nativeBase`直接拼接。把native资源移到普通分包后，配置可能产生`assets/resources/../../subpackages/core/...`。浏览器URL自动整理掩盖原生文件/图片接口差异。ZIP目录/CRC合法不证明运行时URL合法。
2. 预览`access`对所有非用户路径直接成功，或用DOM全局/补造SDK no-op绕过Native分支，导致缺文件与适配问题漏检。
3. 旧ByteDance适配器用可选`getOpenDataContext`存在性推断子域，直接索引可选SDKVersion，或把TikTok版本套入旧抖音补丁分支。safeArea缺省也需按实际调用测试，不能把潜在分支当作已证实手机根因。
4. 只监听图片onload属性，没有覆盖实际load/error事件、无回调及重复终态。按SDK能力兼容，旧属性桥去重；不能仅测试DOM Image。
5. 引擎启动函数返回、scene已创建或已派发UI请求，被误当成HOME呈现/可玩。首帧、必需图片、输入和手机结果须分别证明。

## 修复位置与不变量

优先让资源配置输出规范包内路径；若Cocos2必须相对跨bundle，在**最终请求transform之后、进入真实Native文件/图片API之前**归一化。不修改远程URL或用户存储scheme；越出包根拒绝。修复进入可重复构建脚本，保留原导出和旧包。

Cocos Pipeline自定义pipe必须把列表写回`task.output`；仅返回null会使后续管线接收null。安装需幂等；覆盖动态场景及依赖，不能只改首屏某一图片地址。正常、路径异常、task.output为空、重复安装都要测试。

必需Canvas/WebGL/当前分包能力按实际依赖检查；可选弹窗、toast、开放数据和版本字段不能成为启动前置。按实际接收者调用。第一个屏幕Canvas与Cocos共用；失败兜底若绘制WebGL须恢复状态并释放自有资源。HOME须必需资源完成且取得实际绘制事件，再用触屏PLAY及移动/计分证明可玩。错误UI生效不能算成功。

## 同一判据的三组测试

- **准确旧包负例**：只在外部SDK/文件边界限制父目录路径或真实缺失能力，保留最终请求路径、底层错误及原包SHA；不改被测场景回调伪造失败。
- **当前正常控制**：严格Native全局；文件exists/access实际核文件，大小写错误/缺失文件必须失败。缺可选接口、TTMinis单命名空间、SDK字段缺省、图片事件/旧属性边界按实际机制覆盖。
- **当前故障恢复**：至少两种手机比例。阻断真实SceneAsset/依赖文件→记录scene-load-failed→解除外部故障→**一次真实触屏Retry**→实际新请求→HOME呈现→PLAY→真实输入改变角色/棋盘/计分。再在最终ZIP独立回解树重复这条链，逐文件绑定Native；浏览器helper单独列出，不能打入Native。

后台、持续递增进度、无回调、原watchdog失效、旧成功/失败迟到和热重开沿现有loading-recovery-regression执行，不能用本路径测试替代。新代码失败也保留（例如pipe丢task.output）；修正后同判据重跑。最终指纹变更后按依赖复验，不拿旧报告重新贴新SHA。

## 可执行的出包拒绝

`audit_native_resource_paths.py --native NATIVE --out REPORT [--proof RUNTIME.json]`扫描`assets/*/config.json`里的nativeBase/importBase与bundle base拼接风险。默认不把`../`或存在文件当作运行时通过；有风险而无当前请求/回解触屏证据时退出2。

正式`make_tiktok_zip.py`在写ZIP前调用此审计，review通过`native_resource_paths_runtime`引用证据（相对review路径）。原完整known-issue、加载、存档、运行覆盖及ZIP检查仍执行；不能为“维护/测试包”另设宽松writer。项目自有writer必须同样接入，不得只引用本Skill已更新。

证明文件schema：`native_resource_paths_runtime.v1`；`native_files`为当前完整Native相对路径→SHA256；`raw_evidence`是相对证明文件目录的path/sha256；`requests`每条含实际`raw_path/final_path/success/evidence_refs`；每个风险bundle都要真实请求覆盖。最终路径必须规范且实际存在。`scene_retry`逐比例包含viewport及actual_scene_failure、single_trusted_retry、fresh_resource_request、home_presented、play_entered、gameplay_input_changed、extracted_native和evidence_refs。`strict_filesystem`、`old_same_boundary_failed`及calibration_evidence_refs必需。布尔值必须从原始轨迹人工核对，不能手填pass充数。

审计只查结构、路径、引用和指纹；原始日志真实性、触屏变化和图像仍需负责人检查。该工具单测只证明拒绝机制，不是新游戏通过。物理iPhone、真实IAA、平台接受/审核/发布独立记录；不承诺未知环境永不失败。


## 复盘结论及证据准确性补充（2026-10-25）

用户确认本次复用旧截图，只要求复盘和沉淀；不能将同一图片再次出现记为v18新失败。先确认截图所属版本及重试表现，保留输入身份，不反复OCR相同哈希/同一要求已有明确失败回执的图片。

**本案例准确结论**：旧v17在拒绝父目录路径的受控文件边界下，实际Cocos场景加载失败，底层错误包含原资源路径。当前修复实际完成场景、首页、PLAY与角色移动。它证明一种足以导致同形故障的兼容性缺陷及其修复，不证明该iPhone原生接口确实拒绝父目录；没有手机底层日志时保留这层未知。

**方案选择**：有可编辑工程时优先让Cocos构建生成直接可用的bundle相对资源地址，迁移分包必须同步配置/require及依赖。只有导出包时，在最终transform之后、原生调用之前统一规范化，是避免修改引擎和逐个资源打补丁的局部方案。不能为了移除配置里的../把资源原样全部搬回首包、丢声音、清存档或仅换错误提示。其他版本/引擎先确认其URL处理方式，不能无条件套用本项目代码。

**采样位置限制**：`__RainyNativePaths.snapshot().samples`记录transform前后地址，不能称作FileSystemManager/createImage实际入参日志。旧v18证明格式v1及其成功只说明配置风险、文件存在、指纹和经人工整理的现有运行证据；不等价于逐请求原生SDK取证。新故障调查必须在SDK函数被adapter捕获之前安装只记录、不改结果的调用跟踪，采集请求ID、原始/最终路径、read/access/image成功或原错误、重试ID和时序。跟踪要覆盖首次请求、失败、一次触屏Retry的新请求及旧回调隔离，证据按采集位置标明transform/sdk_boundary/physical_device，不把transform数据改名成SDK证据。无原生可用日志时可以受控边界复现，但标清层级。

**扫描范围**：`assets/*/config.json`和`subpackages/**/config.json`均须扫描；同一风险bundle缺证据保持拒绝。没有扫描到此种配置风险只表示此特定检查不触发，不表示场景资源闭包、网络、图片编解码、SDK适配或加载业务全部通过。

**门禁不能自我放行**：实际正式writer失败后，不添加“测试/检测/维护候选”豁免把blocked当可交付，不另写ZIP writer绕过。用户要求缩小测试范围时如实保留缺口；已执行失败仍需解决。历史项目曾通过自有维护分支产生的包只保留原事实，不能将其追认成现行完整正式门禁通过。


## 场景贴图挂起、解析队列与未提交 import（2026-10-26）

场景 JSON 的明确失败恢复通过，仍不能覆盖其依赖贴图的无回调。对 Cocos 2.4 的实际场景贴图另做 HTTP/原生图片响应挂起：首个响应保持挂起，只放行未来请求，真实触摸一次 Retry，断言同 URL 新底层请求、首页、PLAY 和玩法变化。只扣自绘首页 Logo 不能替代这条场景依赖链；第一次 Retry 再报反序列化错误也不能算恢复。

先校准宿主：Native `fs.access` 是异步存在性检查。浏览器模拟若用同步 XHR 读取图片，HTTP 挂起会冻结整个 JS，不能据此判游戏 watchdog 失败。使用真实文件元数据/异步 HEAD 核存在性，再在后续实际 Image GET/解码边界挂起；保留被校准掉的工具错误，不冒称产品负例。

已复现的失败链是：旧场景图片 parser 未结算，Retry 被合入原等待队列；失败场景的变异 import 数据继续被重用，随后出现 `scene-load-failed` 或反序列化异常。修复应包住**当前 Native adapter 真正注册的图片解析器**，保持实际 SDK Image 与接收者。前台无进展超时或场景放弃时，将原 Cocos 完成回调以错误结算一次，释放引擎等待队列；支持时中止旧传输，始终隔离迟到回调，再允许同 URL 发起新解析/传输。不得换成 Web 解码器、只包后来未调用的 API、改 ready 或靠缓存查询参数冒充重试。

按实际引擎版本清理未提交的 import 中间数据：在 Cocos 2.4.15 已核对 `_files`、`_parsed` 与 `assets` 的关系，只移除失败启动图中尚无成功 Asset 的 `@import` 项，保留已成功资源、其他有效缓存和用户存档；这些内部字段与范围不能无核对地跨版本照搬。新请求从自身创建/最近有效进度计时；同批真实完成可以表示活动，后台排除，双调度超时共享同一预算。

修复用相同挂起条件作旧版失败→修复→正常对照，两种手机比例均执行首次真实 Retry 和玩法输入。正式问题账本绑定加载接线、parser 守卫、场景/资源配置与运行器；新源变化使对应证明失效，正式 writer 不能使用旧 Native 签名放行。浏览器宿主/受控 Native 的修复证据仍不等于手机唯一根因或平台通过。

复测弹窗中的 HOME/Retry 等按钮时，等待实际交互布局稳定，从当前节点世界矩阵、相机/可见尺寸和 Canvas 矩形计算触点。弹入缩放尚未结束时的旧固定坐标不能作为按钮无响应的产品负例；保留原始触点与失败记录，修正测量后只补对应 case。
