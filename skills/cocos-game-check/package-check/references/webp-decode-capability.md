# WebP：Canvas 导出能力不等于 Image 解码能力

2026-10-25，已有 Cocos 2.4.15 Native 包在手机进入游戏自己的 load-error/Retry 页面；无 vConsole，视频只能证明启动业务失败，不能独断手机唯一根因。

已在准确旧包的实际引擎与适配器复现一条同形故障：外部 Canvas.toDataURL('image/webp') 返回 PNG，但 SDK Image 仍可真实解码 WebP。旧 adapter 把 Canvas 的编码结果写入 cc.sys.capabilities.webp，Texture2D._parseExt 因 false 跳过包内唯一的 WebP 格式，触发 3121/启动失败。桌面 Canvas 同时支持编码与解码会掩盖它；ZIP 静态检查不捕获此运行条件。

修复应在纹理反序列化之前，使用真实 SDK createImage 对有效 WebP 样本执行 load/error，验证宽高大于0后再设置解码能力。成功、失败、超时、重复回调只结束一次；支持当前事件 API，旧属性 API 仅兼容分支。不能无条件把 webp 设置为 true；不能只检查 Canvas 编码或浏览器可解码就宣称 Native 成功。不为绕过误判改玩法、美术或把所有贴图转 PNG 造成超限。

仅存在 WebP 纹理并依赖此能力判定的项目追加局部测试：准确旧包在“PNG-only encoder + working WebP decoder”边界失败；修复在同边界成功、正常编码对照成功；真实 decoder 失败/超时不能被改成成功。实际引擎首页、一次输入与加载修改对应的失败→单次触摸Retry→新请求→可操作，从最终ZIP回解复验。保留原包SHA、实际能力值、首条异常、探针结果、请求和原始输入效果；项目私有视频与游戏文件不随Skill分发。

这是特定已复现机制，未有手机首错或新包实机结果时，不写“手机唯一根因已证明/全部扫码故障解决”。通用静态检查仍只证明文件闭包、资源引用与体积；动态能力必须按实际生产链验证。

官方能力合同：[Canvas](https://developers.tiktok.com/docs/en/mini-games-sdk-canvas) 分别定义 createImage 与 toDataURL；不能以一个接口的编码结果替另一个接口的解码结论。

## 自动触发与执行

`check_package.py` 检查目录或最终ZIP时，发现 `.webp` 自动输出 `runtime_requirements` 中的 `webp_decode_capability`，状态为 `requires_runtime_evidence`，含实际资源列表与七类回归。该字段是运行待核项，不能因静态检查成功而删除或改为已通过；最终交付前由 Agent 按本页执行并关联当前Native/ZIP指纹的实际证据。当前脚本没有伪装成能自动操作手机，也不会仅凭资源后缀拒绝本来可用的包。

项目采用 `module.exports = function(root, ready)`（Cocos 2.4）或 `exports.check(cc, sdk, timeout, done)` + `exports.apply(cc, ok)`（Cocos 3.x，`cc.sys.hasFeature(cc.sys.Feature.WEBP)`）的能力探针时，运行：

```sh
node scripts/test_webp_decode_probe.cjs /absolute/project/probe.js --package /解包后的包目录
```

脚本自动认接口，读取并执行实际模块，验证成功、错误、超时、旧属性事件、已有支持、零尺寸及SDK抛错七项；成功/错误/超时重复终态只结束一次；3.x 另验证 `apply` 只在真解码成功时把"不支持"改成"支持"，引擎原本是"支持"时不改回"不支持"。v7.5 起（Mabel's Meadow 问题 3 取代 Basil 那份"把 fix1 探针做成标准件"）：探针的 `img.src` 必须是包内相对路径的 .webp 文件，**出现 data: URI 就判失败（做备用也不行）**；带 `--package` 时还检查这张图真的在主包里（不在 `subpackages/`）且是 WebP 文件。通过只证明探针模块合同，不能替代旧包故障、最终Native真实图片/纹理选择、HOME显示、触控与最终ZIP回解的定点复验。

## 标准件（v7.5，待真机复测）

统一规则：新游戏图片只用 PNG/JPG，不用 WebP；老游戏要保留 WebP，必须带下面的标准探针，出包检查 G4（`remake-core/scripts/package_gates/webp.py`）拦住没有探针、探针用 data: URI、探针图不在主包的包。v7.7 起新游戏工程里的 WebP 由 `tiktok_finalize.py source` 自动换成 PNG/JPG，构建产物里还有 `.webp` 就拦（`K_S_webp`）；只有缩完图仍超 30 MB 的 2.4 新游戏能走 WebP 例外（源码段和写包入口都给同一个 `--keep-webp-exception <原因>`），这时标准探针由出包入口自动装（需要平台包 `main.js`），不再手接，规则见 [TikTok 固定适配·第 6 条](../../references/tiktok-fixed-adaptation.md)。平台包 `main.js` 每次都带着 `webp-decode-probe.js` 脚本（不开例外时不执行），探针图和开关行只在例外时装。3.x 在 v7.7 没有 WebP 例外：带这个参数源码段、产物段和写包门禁都拒绝（`K_webp_exception_3x`），3.x 新游戏只能用 PNG/JPG 和 `max_side` 缩到 30 MB 以内，3.x 探针放到 v7.8。下面的手接方法只给保留 WebP 的旧游戏。

- Cocos 2.4：`remake-core/assets/platform-kit/webp-probe/cocos2.4/webp-decode-probe.js` + `loading/webp-probe.webp`（Mabel's Meadow r8 原字节）。放主包；在 `adaptEngine()` 之后、加载 `src/settings.js`/`main.js` 之前调用 `require('./webp-decode-probe')(root, done)`；`done` 里 `cc.sys.capabilities.webp` 仍是 false 就显示 Retry，Retry 重新跑探针。5 秒没回应算不支持。
- Cocos 3.x：`remake-core/assets/platform-kit/webp-probe/cocos3.x-reference/`（LunasJade v0.10.1 的 `webp-probe.js`、`webp-check.webp`、`boot-loading.js`），v7.5 删掉了原件的 data: 备用，只解码 `webp-check.webp`（VP8L 无损，和游戏美术同类）。只作已有 3.x 游戏的参考。

已在 `test_webp_decode_probe.cjs` 上核对：Mabel r8 探针、标准件两套通过；Mabel r7、Basil fix1（data: URI）、LunasJade v0.10.1 原件（data: 备用）、把 r8 改回 data: URI、强制设 true、探针图不在包里都失败。

## 本次漏测的直接原因

旧本地SDK边界直接返回桌面 Canvas/Image，两者在桌面同时支持WebP，未独立控制编码能力。因此“真实引擎已跑过”仍不足以覆盖手机能力差异。改进的关键是只改变外部能力边界，让准确旧引擎/adapter自己失败，并让修复在相同边界自己成功；禁止在游戏回调中直接注入3121或把失败结果伪造成旧包反例。
