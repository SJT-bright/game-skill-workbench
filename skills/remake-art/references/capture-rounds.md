# 英文 Web 试玩的截图复用

在已有页面清单上加一份 `docs/art/capture-plan.json`。每个实际状态 × 手机视口一条记录。同屏不同奖励状态各有自己的 id 和可验证的节点特征。例如：

```json
{"cases":[{"id":"settings-max-se","screen":"settings","kind":"popup","width":375,"height":667,"dpr":2,"stable":false,"recipe":"settings.open; audio=5; fixture save-v2","environment":"en, locale/en-US, renderer-webgl-v1, fonts-v1","anchor":true,"witness":[{"path":"Canvas/Settings/Volume","text":"5"}]}]}
```

已有采集目录可运行 `python3 <skills>/remake-core/scripts/art_capture_batch.py init 历史采集目录 PROJECT/docs/art/capture-plan.json` 生成候选表：默认全部重拍，只取状态名和尺寸，不导入历史截图身份。AI 对照原流程补齐 recipe、environment、DPR、状态见证并确认可复用范围。这里只展示一条记录，实际工程按所有页面、条件状态和两种手机尺寸填。选定每种尺寸的一个轻量锚点，始终重拍它以确认实际浏览器环境。默认 stable=false。同类静态 UI 只有经下面独立稳定性确认后才可给 stable=true；战斗、动画轨迹、随机/联网内容、存档不固定、需遮罩或单独渲染报告的状态始终重拍。数据、语言、字体环境、状态到达脚本或美工批准范围变了，更新 recipe/environment。状态缺见证不收图。历史无版本证明的图只能用作对照。

1. 生成任务先列“改哪张图、在哪些状态/尺寸可见、共用者是谁”。先做最窄或最多层的一件。本轮开始执行 `node <skills>/remake-core/scripts/art_capture_round.mjs start PROJECT WEB_EXPORT`。导出或制作清单再变，就开新轮。此处 WEB_EXPORT 是真实可运行 Web 目录。
2. 通过本包采集器采集。用新建的独立测试页，先设置手机 viewport、DPR、触摸和 UA，再调用下例。使用已有动作脚本到达真实状态；优先把同一段到达流程的状态一起采，源图或构建还在写时停止。本工具在仅本机可访问、独立端口的预览上提供已核准字节，限制外部依赖和 Service Worker。同一采集器把其打开以来读过的资源都算入依赖，跨状态预载可能多拍，但能保留实际依赖。每个独立到达流程另开采集器可缩小范围。需要外部网络、Worker 或专用动画证据时保留专用采集并实际复核，不能声明该状态可跨轮复用。
3. `plan PROJECT WEB_EXPORT 上轮目录` 列出 fresh/reuse/recapture 和原因；锚点未取得时计划是暂定的。运行 `python3 <skills>/remake-core/scripts/art_capture_batch.py assemble PROJECT WEB_EXPORT 上轮目录 本轮新目录`，自动只复制允许沿用的 dump 和原 PNG，不改文件内容。按计划补拍剩余项，两种视口的锚点先拍；再跑 plan。若锚点环境变了，上一轮该尺寸全部重拍。登记新页、改变代码/字体/布局/图集、无法对应的新旧源文件、缺身份材料都全部重拍。复用仅覆盖输出文件清单不变、已存在的独立 PNG/JPEG 内容变化且可验证影响范围的情况。加载过改图的所有状态都重拍。脚本不会给旧图换上新轮次。
4. 正常跑 `art_check.py --project PROJECT --board localize --dumps 本轮目录 --build WEB_EXPORT`。脚本先核对状态列表、采集来源、文件字节和当前导出，再跑原有完整视觉检查。完整报告 passed=true、逐页看图后，仅对已确认可复用的稳定状态执行 `review PROJECT WEB_EXPORT 本轮目录 状态ID 完整art-check.json 独立复拍目录`。已知问题所在页先修并重拍。此动作记录图像来源与人工看过的状态，最终通过仍由完整检查决定。下轮不得复用未确认的项。原图回放、文字/图片指纹或补写时间戳不能登记成真实新采集。

在持有真实浏览器 Page 的 Node 动作脚本里：
```js
import {openCapture} from './remake-core/scripts/art_capture_round.mjs';
const session = await openCapture({project, build, out: currentDumpDirectory});
try {
  await session.navigate(page);
  await reachSettingsAndSetVolumeToFive(page);
  await session.capture(page, 'settings-max-se');
} finally { await session.close(); }
```
普通 Cocos 页面读取包里的 ui_dump。需要不同引擎适配时，可给 capture 传入 `{dumpExpression}`，其 SHA-256 填入该状态的 adapterSha，且必须从当前页面真实读取节点；截图始终由采集器直接读取浏览器像素。关闭自己的测试页/空间。报告中 ready 只表示采集材料齐全，结论仍看 art_check 的 failed、截图和交互。任何缺项、状态名碰撞或来源不明，回到相应真实页面。

已有 `chrome_touch.py` 的 Ego 动作计划也能直接用：计划增加 `"art_capture":{"build":"build/web-mobile","out":"docs/test/本轮目录"}`；每个 `dump_ui` 增加 `"case":"settings-max-se"`，运行时传 `--project`。把**实际计划文件的 SHA-256** 记入各状态的 `planSha`；这样动作、初始数据或测试脚本改了也不会沿用旧证据。采集器用本轮导出的独立本机 URL；普通手机测试仍按原计划。每轮可传 `--art-dumps 新目录`，沿用原动作计划及 SHA。自定义 `dump_expression` 还须登记 `adapterSha`。通过检查器的输入证据不豁免交互或美术复核。

同一批改图先合在一次构建里。源文件、已有导出与清单都没有变化时，用 identity 核对现有 Web 导出，直接进入本轮采集。专用状态先在采集适配里预留实际报告路径，再从同一次采集生成遮罩、录屏等附件。试玩放行时重新核对附件内容。

## 优先省去重复启动，保留新截图

按视口和同一真实到达流程组成批次：一次 navigate，采首页，真实点开设置、采集、关闭，再真实进入下一弹窗。每次采集仍读新 dump 和新 PNG，不能只改 screen 名；状态有前置数据或不可回退时另起一批。采集器累计保留整条路线实际读过的依赖，不清空读取集合换取更多复用。不要每张图重新启动引擎。恐龙真实六状态对照为6次启动32.318秒、2次启动12.284秒，六张全是新截图；仅说明该次六状态，不外推66张或整轮九小时。

## 静态沿用需要独立证据

stable=true 是申请条件，不能单凭声明放行。完整源码和状态清点已确认不依赖日期、倒计时、随机/延迟出现、联网、动态背景时，才能写 `externalInputs:[]`；已知依赖写明在数组里，未知就不填，均重拍。不得为了复用而临时暂停游戏或隐藏手势/背景。两次相同画面只证明两个时点，不能自动推断永远静态。

先定义受控游戏存档/初始数据，再从实际采集 proof 的 storage 观察核对该 fixture 的 SHA，填 `storageSha` 后开始新轮；不能把任意历史存储直接封为批准 fixture。采集器只保存摘要，不保存存储值；IndexedDB 未确认空或存储不可读/采集中变化时拒绝沿用。随机 localhost 端口不等于空存档，不清理用户浏览器资料来凑条件。

在同一版本/轮次，用两个独立 `openCapture` 和真实重新进入取得同状态的两套目录。两次整页 PNG 必须完全相同，环境、状态、资源读取集合和受控存储一致；不能遮掉圆角、背景动画或小点，也不用宽松差异阈值。完整 art_check 通过后 review 同时绑定这两份证据。本轮每个视口还必须重拍 anchor，实际存储摘要与待沿用案例一致；锚点使用不同fixture就重拍该页，不硬套。缺独立复拍、全报告未过、存档变了、未知外部输入或共享脚本/字体变化，统一重拍。

恐龙设置/桌面页实测节点一致而整页像素不同，属于不能沿用的真实负例。原66份历史证据缺少新身份链，不补时间戳、不重新封签。新规则会使既有未绑定稳定性证明的 review 失效；这是重新核对来源，不要求无关游戏重新生图或构建。优先用上述连续批采降低这次补证成本。


## 整轮像素检查前先核输入（11.17.4）

完整 `art_check.py` 会先核采集范围与来源，再进入像素分析。需要单独定位缺采或版本问题时，可以运行只读预检：

```sh
python3 <skills>/remake-core/scripts/art_check.py --project PROJECT --board localize --dumps CURRENT_DUMPS --build WEB_EXPORT --inputs-only --out OUTSIDE_FRESH_DIRECTORY
```

它只检查实际采集目录、文件命名、case/视口覆盖和原 capture_round 身份，不分析像素、不写 ART 回执。input-preflight.json 的 ready 仅表示可进入后续检查；visual_passed 始终为空。缺项或来源未确认时先补相应采集，保留其它仍有效 case，不先跑完整像素分析。不要把多轮历史目录递归塞进当前集，也不能按文件名年份/版本猜测后批量删掉。目录计数帮助核查范围，安全沿用仍由实际依赖、存档和稳定性证明决定。

若完整检查的 --build 指向 Native 供资源检查，另传 `--capture-build WEB_EXPORT` 给实际 Web 截图身份校验；这两个参数用途不同。已识别的 Web dump 在完整英化入口同样强制核版本，不能借 Native 路径跳过。显式给错 Web 目录会拒绝，不退回其它导出。Web 来源成立不等于 Native 实际显示已验收，Native 的原专项检查继续执行。非 Web 专用采集仍走对应入口；输入预检报告会列 board、版本是否核准和两种构建路径。

本次用蛋壳原112份混合集验证，缺采集计划/版本链会在像素分析前拒绝；这是避免对无效输入做整轮分析，不代表同一完整检查已按此比例加速，也不代表这112份图中的视觉问题已检查通过。
