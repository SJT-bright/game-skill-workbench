# 每次交付的主包与分包体积复查

用户 2026-11-05：每次给测试包都重新检查，不设来源、版本、旧报告或返工范围例外。此步骤只读最终 ZIP，不触发全游戏 CI。已存在的启动、资源和功能门禁仍按原范围执行。

```sh
python3 -B <skills>/remake-core/scripts/upload_size_gate.py \
  --zip <本次实际要链接的最终ZIP绝对路径> --platform tiktok \
  --report <本次新的size-时间戳.json>
```

每次运行重新读取所有载荷并核 CRC、SHA-256，报告带绝对路径、UTC 时间和唯一运行 ID；不接受覆盖旧回执。通过后若文件内容或最终路径变化，按最终路径重跑。`prepare_delivery.py` 在其他检查前自动执行并保存 `<交付回执>.size.json`，不复用 writer/历史体积结果；仅索取已有包的会话也必须直接执行上面的入口。

TikTok 只认小写 `subpackages`；抖音小游戏当前文档使用 `subPackages`，不能混用，也不能同时放两个字段猜兼容。按目标平台校验相对目录、大小写、非空唯一 name、重复/嵌套 root、目录有文件、game.js 入口、独立标记类型；Cocos 3 同时对照 `src/settings.json` 和实际 bundle config 的名称。普通分包不计主包，但计总包；主包是最终 ZIP 中排除所有有效分包目录的其余文件。按未压缩字节计 TikTok 主包≤4,000,000、总包≤30,000,000、独立分包各≤4,000,000；ZIP 压缩大小不能替代。路径用完整目录前缀匹配，避免 `res/` 误排除 `resources/`。

官方参考（2026-11-05 核对）：[TikTok 技术概览](https://developers.tiktok.com/docs/en/mini-games-technical-overview)、[TikTok 分包统计异常排查](https://developers.tiktok.com/docs/en/mini-games-development-troubleshooting)、[抖音小游戏分包](https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/framework/subpackages/basic)。TikTok 的每个分包 root 必须使用无尾斜杠的相对目录。尾斜杠直接阻断写包和最终 ZIP 检查，修正配置并重新生成 ZIP 后再复查。不把“去尾斜杠”声称为所有平台拒绝的已证实根因。

出现“本地主包合格、平台仍将整包计主包”时，保留失败 ZIP 与平台原错误，先确认相同 SHA、目标平台及实际上传层级，再复核字段、路径、根入口和引擎加载配置。项目保存 `{"platform":"tiktok","rejected_sha256":"<失败ZIP的SHA-256>","message":"<平台原错误>"}`，本次命令加 `--platform-feedback <该文件>`。同字节拒绝包明确拦截；修复后的新字节仍标平台待复验，不能仅以本地算术关闭平台反馈。报告同时列出分包失效时的整体字节数，便于解释两种统计口径。

仅 ZIP CRC/哈希通过不是合格交付；体积通过也不覆盖其他门禁或代替真实上传结果。缺文件、无报告、失败、运行中换包一律不交可上传包。
