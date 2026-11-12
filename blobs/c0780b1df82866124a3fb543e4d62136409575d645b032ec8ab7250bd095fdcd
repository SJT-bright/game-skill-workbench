# 每次交付的主包与分包体积复查

TikTok 的同一命令会在体积、分包和 CRC 通过后，对同一 SHA-256 的 ZIP 在独立临时目录解包，自动执行 `ttmg check` 和 `ttmg build`。两个 writer 完成内部写包和回读后，正式交付只由 `prepare_delivery.py` 对实际交付路径执行一次并保存新回执，无需再单独跑下方命令。专项候选、仅重发、外来包或同版改名，走下方命令生成本次新回执。回执的 `size_passed`、`tiktok_cli.check`、`tiktok_cli.build` 分别保留结果，`passed` 是最终文件前提总判定，并非可玩性通过；TikTok还须有同字节正式writer回执，否则保留体积/CLI结果但总判定拒绝。`delivery_ready`固定false，正常交付继续由`prepare_delivery.py`核当前启动/存储与同版试玩。已知拒包证据通过 `--platform-feedback` 传入独立检查或 `prepare_delivery.py`。平台拒绝同一 SHA、任一必需检查失败或未运行时不交包。

新电脑安装此更新后的 Skill 后，首次运行会用 npm 官方源将固定的 `@ttmg/cli@0.4.7` 安装到用户缓存，后续复用。须有受该版本支持的 Node.js（20.19.1 至 20.x 或 22 及以上），首次安装还需 npm 和 npm 官方源可访问。离线检查无需开发者登录或手机。安装或执行失败保留原因。本地结果覆盖归档与 CLI 构建，平台上传和真机单独验证。

游戏回归按改动和实际依赖选项，未受影响且有效的美术、音效、玩法证据直接沿用。只更新 CLI 检查不触发游戏验收重跑。

用户 2026-11-05：每次给测试包都重新检查，不设来源、版本、旧报告或返工范围例外。此步骤只读最终 ZIP，不触发全游戏 CI。已存在的启动、资源和功能门禁仍按原范围执行。

```sh
python3 -B <skills>/remake-core/scripts/upload_size_gate.py \
  --zip <本次实际要链接的最终ZIP绝对路径> --platform tiktok \
  --report <本次新的size-时间戳.json>
```

每次运行重新读取所有载荷并核 CRC、SHA-256，报告带绝对路径、UTC 时间和唯一运行 ID；不接受覆盖旧回执。通过后若文件内容或最终路径变化，按最终路径重跑。`prepare_delivery.py` 在其他检查前自动执行并保存 `<交付回执>.size.json`，不复用 writer/历史体积结果；仅索取已有包的会话也必须直接执行上面的入口。

TikTok 只认小写 `subpackages`；抖音小游戏当前文档使用 `subPackages`，不能混用，也不能同时放两个字段猜兼容。按目标平台校验相对目录、大小写、非空唯一 name、重复/嵌套 root、目录有文件、game.js 入口、独立标记类型；Cocos 3 同时对照 `src/settings.json` 和实际 bundle config 的名称。普通分包不计主包，但计总包；主包是最终 ZIP 中排除所有有效分包目录的其余文件。按未压缩字节计 TikTok 主包≤4,000,000、总包≤30,000,000、独立分包各≤4,000,000；ZIP 压缩大小不能替代。路径用完整目录前缀匹配，避免 `res/` 误排除 `resources/`。

官方参考（2026-11-05 核对）：[TikTok 技术概览](https://developers.tiktok.com/docs/en/mini-games-technical-overview)、[TikTok 分包统计异常排查](https://developers.tiktok.com/docs/en/mini-games-development-troubleshooting)、[抖音小游戏分包](https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/framework/subpackages/basic)。

**尾斜杠兼容修正（2026-11-08）**：旧本机增量中“root 末尾有 `/` 就阻断”的规则错误，已撤销。合法相对目录 `subpackages/res` 与 `subpackages/res/` 按同一个目录前缀核对文件、入口、重叠和体积；检查只做内存归一化，不改写受检 ZIP，不因这个格式差异要求重新构建、重拍或重打包。新配置可以统一写成无尾斜杠，但已有合法配置不能仅因此判失败。

先对原路径做安全检查，再归一化；绝对路径、反斜杠、`..`、空路径段仍拒绝。归一化后的重复/嵌套目录、大小写不符、目录或入口缺失、体积超限与平台拒绝均继续阻断。本次用用户确认历史上传成功的 CarEscape 原 ZIP、ttmg-pack 0.4.13 本地打包及加/去斜杠单变量对照核验。此结果证明旧门禁误报，不替代平台上传结果；历史成功包也不是本轮云端对照。平台报 10.17 MB 等无法与实际包内字节对应时保留待查，不仅凭斜杠差异推定来源。

出现“本地主包合格、平台仍将整包计主包”时，保留失败 ZIP 与平台原错误，先确认相同 SHA、目标平台及实际上传层级，再复核字段、路径、根入口和引擎加载配置。项目保存 `{"platform":"tiktok","rejected_sha256":"<失败ZIP的SHA-256>","message":"<平台原错误>"}`，本次命令加 `--platform-feedback <该文件>`。同字节拒绝包明确拦截；修复后的新字节仍标平台待复验，不能仅以本地算术关闭平台反馈。报告同时列出分包失效时的整体字节数，便于解释两种统计口径。

仅 ZIP CRC/哈希通过不是合格交付；体积通过也不覆盖其他门禁或代替真实上传结果。缺文件、无报告、失败、运行中换包一律不交可上传包。

TikTok 最终 ZIP 同时运行 `enforce_tiktok_host`，用语法树检查主包、适配器和分包业务脚本的微信宿主引用，按文件和行号报错。直接调用全局 `wx`、`window.wx`、`globalThis.wx` 及其别名仍拒绝；注释、字符串和词法作用域内的普通局部对象不按全局宿主处理。标准件明确先选择 `TTMinis` 和 `tt`、最后才保留 `wx` 的 SDK 兼容候选值允许通过，不按文件名整份放行。缺 Node 或脚本解析失败时拒绝，不能当作没有问题。此项用标准件实际源码、合法回退和非法直接调用作正反对照，启动、宿主加载遮罩及输入验收仍分别记录。

**R7缺口约束（2026-11-12）**：只读`inspect_zip`仍能诊断外来归档的体积，不能作为交付入口；最终命令在体积和CLI合格后拒绝无正式writer回执的自写ZIP。改名可按同目录原回执的SHA匹配；改字节、只有手填passed或失配回执拒绝。详见[消费者与交付约束](../../../remake-core/references/startup-storage-consumer-gate.md#最终文件与可交付结论不能混用)。
