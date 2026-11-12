# 正式 Native 启动：共用实跑记录

- `audit_startup_contract.py`、`build_checked_zip.py`、`make_tiktok_zip.py`、`prepare_delivery.py` 共用项目 `docs/checks/incremental/ledger.sqlite3` 的 `startup.native.renderer`。只认已登记运行器的真实执行与保留的原始结果；旧通过字样、源码扫描、普通 Web 试玩都不能补一条通过记录。
- 每个入口先按本版证据重判：真实 `game.js`/适配器/引擎链、首页出现、宿主加载遮罩已消失、可信触控确实改变游戏状态。写包和交付另外重判 Retry 证据；复用浏览器执行不豁免这些判据。资料绑定到当前 Native、源码和 Web；试玩仍核对本版完整 Web 指纹。
- Native 文件路径和全树指纹、受信运行器及其依赖、控制场景、启动规则、环境指纹都一致，且原始证据完整，才沿用同一次执行。单独修改 ZIP 包装、版本标记、Web 或源码不强制重复 Native 实跑；仍须提供有效的当前绑定及证据。Native 字节变动、运行条件或规则变动只让启动项重跑；没有独立证明前，不凭“这张图应该只在后面出现”排除 Native 文件。缺原始证据或旧版失败时阻断，按原因恢复或定点补证。
- 正式交付 `checks` 记录 `reused`（沿用）、`rejudged`（重判）、`rerun`（本次执行）或 `not_applicable`，带原因和证据。广告和运行回归按原记录粒度保留，旧汇总不冒充逐项实跑。阻断写 `<record>.blocked.json`，不给成功回执。实际最终 ZIP 的 CRC、体积、分包、TikTok CLI 以及同版试玩复验照常，不从启动账本复用。

- 2026-11-11：运行环境身份包含真实语义profile、故障命中和旧档fixture，不只UA/OS字符串。按[跨平台与冷升级](cross-platform-runtime-contract.md)与STORAGE-01 v3补相应节点；普通启动记录继续保留其原范围，不能据此补写iOS真机或冷升级通过。
