# TikTok Native 与 IAA

**本地验证的已知前提与汇报（用户 2026-10-25）**：用户已知本地源码检查、Web/浏览器模拟、Native文件校验均不属于TikTok真机或真实广告验证；用户会将最终测试包上传后进行真机和真实广告验证。内部记录继续准确区分证据层级，不冒称已验证；日常进度、预览、出包和定时更新汇报不再重复“不是TikTok真机”“没有真实广告”“不代表平台通过”等已知前提，不将其列成默认警告或待办。仅用户询问范围、实际结果存在混淆，或出现具体失败/需要用户处理的事项时说明相关事实。


IAA 广告接入是本 Skill 的默认工作内容，不能在只完成英文界面时就收尾；用户明确只做试玩、待配置等中间阶段时按其范围交付并保留待办。技术概览解释运行环境，不是中文翻译教程。以下为 2026-10-11 读取的官方资料，构建前重核会变化的配置、限制与工具版本。

- [技术概览中文入口](https://developers.tiktok.com/docs/zh-Hans/mini-games-technical-overview)；无法读取时使用[英文正文](https://developers.tiktok.com/docs/en/mini-games-technical-overview)，说明访问缺口。
- [Cocos 小游戏适配](https://developers.tiktok.com/docs/en/build-mini-games-with-cocos)
- [IAA SDK](https://developers.tiktok.com/docs/en/mini-games-sdk-iaa)
- [SDK 概览](https://developers.tiktok.com/docs/en/mini-games-sdk-overview)

按 [本地审查与测试广告 ID](local-review-and-test-ids.md) 由 Agent 完成逐按钮美术优化、真实试玩和广告窗口检查；不以用户审美确认阻断已授权的平台接入。已有 App ID、公开 Client Key、广告位时直接回填、实重建和联调，不登录或打开 TikTok 后台，不把账号或后台权限列为本地修复/构建/打包前提。仅用户明确要求创建应用或操作后台时，按 [独立 TikTok 应用创建](tiktok-app-creation.md) 执行该后台任务。随后回到本地审查参考做最终审查；英文转换、广告接入或引用教程本身不授权后台登录、创建、上传或发布。真实广告仍以 Runtime 和设备结果另验；后台未核实与实际 SDK 失败分开记录。

## 构建与配置

Native 环境是 JS/WASM 小游戏运行时，不是完整网页 DOM。先从 Cocos 支持的小游戏平台导出，再按官方指南适配入口、资源加载、配置和 API；不能把 Web ZIP 改名当 Native。Native 直接使用 `TTMinis.game`，不用 HTML 版 minis.js 或 TTMinis.init。

2026-10-02 SDK 概览说明 `TTMinis.game`、`tt` 和 `wx` 前缀兼容；引擎适配器保留低层兼容调用时，业务广告仍显式使用国际 TikTok 接口，并在目标 Runtime 验证。Cocos 3.8 的 bundle 配置与旧版本不同，不能只给 .meta 写 compressionType 就声称分包成功。检查实际导出目录、game.json 和引擎资源配置；采用构建后迁移时，分包脚本入口和 config.json 路径须与 Cocos 加载器一致。

源码 ZIP 是可编辑工程；平台 ZIP 根目录应直接有 game.js、game.json、project.config.json 等所需文件，不能再套交付父目录。独立审计 Native ZIP 与外层说明包。2026-10-05 版概览的非 Unity 限制：总包 30MB、主包 4MB、独立子包各 4MB，普通子包计入总包、不再有单独大小上限。以当前平台检查为准，含子包工程不能只看 ZIP 压缩体积。

**出包只用 [`cocos-game-tiktok-package`](../../cocos-game-tiktok-package/SKILL.md)（`make_tiktok_zip.py`），所有叫法（打包、上传测试包、检测包、压缩包）都只出这一种包（BUILD-04，用户 2026-10-23）**：SquareRush 旧包 resources 留在主包，主包 8,754,975 字节＞4,000,000 被拒；`assets/resources` 等大 bundle 必须配成 Cocos 小游戏普通分包。最终交付的上传文件必须是单独可下载、可直接选择或拖入后台代码包上传区域的 Native ZIP；不能只放在源码总包里面。用游戏名、TikTok上传包、测试/正式目标及版本标清文件，包外附必要说明。根目录保持真实游戏入口及配置，不加入交付父目录、源码、试玩网页、技能、说明、个人后台截图或凭据。

从最终上传 ZIP 实际独立解压，核对 CRC、安全路径、全部文件字节、根 game.js/game.json/project.config.json、目标 App ID、实际编入的公开配置及广告位、分包和体积；在此解压结果上执行当前可用的官方离线检查。完工回复同时给同版本地试玩链接和上传 ZIP 链接、对应 App ID 和“直接上传，无需解压重压”，并写明"已在浏览器模拟中测试，未做 TikTok 真机测试（不在本 Skill 范围）"；本地服务按[交付细则](delivery-and-handoff.md)核验。已经核验且未改字节的文件不重复跑相同检查，只需确认最终交付仍是它。

可先用本技能的通用本地检查脚本，再对独立解压结果执行官方离线检查：

```sh
python3 scripts/verify_native_zip.py /path/to/Game_TikTok.zip \
  --expected-app-id "YOUR_APP_ID" \
  --expected-tree /path/to/independently-extracted-native \
  --report /path/to/new-native-report.json
```

此命令在技能根目录执行，或使用脚本绝对路径。它核对根文件、JSON、App ID、CRC、安全路径、声明分包、全部SHA及与给定目录的字节；内置 TikTok 限额（用户 2026-10-23 起强制：未压缩主包≤4,000,000 字节、总包≤30,000,000、独立分包各≤4,000,000，普通分包只计入总包），`--max-*-bytes` 只能更严；也拒绝外层文件夹、Web 构建、源码文件、ZIP 套 ZIP、Mac/Windows 垃圾文件和非 ASCII 路径。平台改限额时按新官方文档改脚本常量并写日期。expected-tree 应来自最终上传 ZIP 的实际独立解压，也可额外与本次 Native 构建对照。脚本不查公开Key/广告位归属、SDK调用、设备或平台接受，不能替代后续步骤。

代码包可直接选择上传是交付格式要求，不代表平台已经接受、真实广告通过或正式发布。缺配置、权限、CLI登录、手机等实证步骤时明确标记测试/待配置状态及具体待办，不用文件名代替验收，也不擅自上传或发布。用户要求更新技能时直接更新已安装技能，不用新技能ZIP代替游戏上传文件。

新工程使用属于同一个游戏应用的 App ID/MinisID、公开 Client Key、Active Rewarded Placement ID；未知配置保持为空并说明。默认不混用其他游戏配置。用户明确指定复用同一测试组时，另建独立测试副本，App ID/公开 Key/广告位整组保持，原独立应用工程不覆盖；只记录公开配置来源和未核实事项，不能仅沿用一个广告位配另一个App。不把 Client Secret 写到客户端、截图、技能或交付包。用户是源码交付方时，企业发布资格不应阻止英文工程与接口源码交付。

用户已授权所有新游戏默认使用该组（见[配置复用](ad-configuration-reuse.md)）。广告配置的来源顺序见[配置复用](ad-configuration-reuse.md)（Skill 自带的是[预设广告配置](../assets/ad-config.json)）与 [回填核验步骤](local-review-and-test-ids.md#已授权的共享测试广告预设)。默认位必须接到实际业务入口，三个 Rewarded 位均须保留并核对实际编入；独立正式目标与共享测试副本分别保留，最终只交当前指定目标的一个上传 ZIP，不默认同时交两套。即使只有一个广告入口，也不能让构建器静默丢掉其余公开位。仅有用户报告“已启用”时记该来源，未经后台/真机核验不写成平台验收通过。

已取得 App ID 与 Client Key、尚缺广告位时，将已知公开配置同步到工程及明确标记的 Native 候选，rewardedPlacementId 留空。默认完整 Native 构建应在写源码/输出前拒绝缺失配置；只有显式待配置模式才允许生成候选，且不得把空值改成假 ID。更新配置后重新构建，独立核对源码、project.config.json、构建脚本内的标识与交付配置一致，保留旧 ZIP 不覆盖。

## 激励广告

为每次请求创建新实例：`TTMinis.game.createRewardedVideoAd({adUnitId})`。官方实例为单次使用，显示后不能复用；不能沿用国内 tt SDK 的长期缓存/重复 load 模式。

先挂 onClose/onError，再 show。show Promise 成功只表示展示；只在 `onClose` 的 `isEnded === true` 时发奖，取消、失败、无填充、错误和缺配置都不发奖。使用一次结算锁，解除事件订阅，阻止重复回调、旧局/已销毁 UI 的广告结果触发奖励。退出时取消请求的后续业务作用。

保留原免费流程；普通浏览器没有真实 SDK 时说明广告不可用，不自动调用奖励回调伪装成功。GM/debug 模拟奖励不得带入正式构建。用模拟检查覆盖完成、提前关闭、show 拒绝、onError、同步 throw、重复回调、并发请求和旧 UI 退出；这些不是手机广告证据。

电脑审查版的广告入口与预览窗口独立于 SDK、登录和广告位可用性；缺 ID 只阻止真实请求，不妨碍用户查看窗口、奖励说明、失败提示、关闭及返回流程。预览窗口使用本游戏 Cocos UI 并保留画风，标明 LOCAL PREVIEW；不能称 TikTok 官方视频窗口。真实 Runtime 仍按真实配置及严格回调发奖，预览 UI 不改变这条奖励路径。

## 主页回访能力

最终 TikTok 包必须按 [主页回访功能](tiktok-home-growth.md) 检查并补齐桌面快捷方式和个人主页回访：主页英文入口、真实 SDK、回访资格及奖励必须一起核对。静态按钮不能代替功能，官方离线 API 提示消失也不能代替手机验收。当前不可用的分享按钮隐藏或移除。

## 验收边界

分别记录源码检查、Cocos 导出、Native 离线校验、DevTool 编译、后台上传、手机运行、真实广告、送审/发布。普通 Web 试玩不能验证真实 IAA。后台登录、Cocos 登录和 CLI 登录各自独立；手机扫码与账号认证以当前 DevTool 实际说明为准。收到码后仍须看到设备连接、真实广告完整播放和奖励正确发放，才能称真实接入验收完成。未经授权不自动创建应用、上传或发布。

用户收到上传失败缺 game.json、问源包/试玩怎么用时，读取 [游戏交付与验证](delivery-and-handoff.md)。维护已接入版本的授权局部修复，保持本应用配置并同步重建 Web/Native；不把它当成需要从创建应用重新开始的新任务。

新游戏复用、Native包公开Key/全部声明广告位的静态核对和错误码排查，见 [广告配置复用与排错](ad-configuration-reuse.md)。

## SDK 能力识别与玩家提示

按[官方 SDK 概览](https://developers.tiktok.com/docs/en/mini-games-sdk-overview)（2026-10-02）支持的 `TTMinis.game / tt / wx` 入口，统一按本次调用所需的方法解析；空对象或缺方法的首个入口不能挡住后面的可用入口。保留选中对象作为调用接收者；成对订阅/退订来自同一对象。广告、生命周期和回访能力分别按自身方法检查，不把“对象存在”当成“广告可用”。

在真实源及本次编译 Native 上保留只有各入口、首个空对象加后续可用、全部不可用的最小样例，以及严格完成一次/取消失败零奖励对照。旧包必须在同一检查中失败，实际打包入口现场执行。手机原始能力未捕获时，条件复现只证明兼容缺陷，不确定为唯一真机根因。玩家状态文字不显示版本、SDK 字段、配置键或内部码；限界诊断留日志。自有 `sdk-missing` 表示前置能力检查失败，不能直接归因广告位注册或网络。

广告/奖励的上传前回归以[统一清单](known-issue-checklist.md)为准：跨实例会话、真实SDK终态后的显式重试、完整凭证的保存重试、实际消费和切场销毁均要有当前source/Native结果。历史适配器快照不自动继承为已验证实现。
