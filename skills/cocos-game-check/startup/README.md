# 启动与稳定板块

修订：`2026-10-27.modules-v6`。英化和重塑都用。

**管什么**：启动契约（进得去、首页真的能点）、统一加载页样式、启动加载计时、加载失败/超时/Retry 恢复、Native 场景与分包路径、Native 领奖存档与坏档、空功能旧入口、性能。
**不管什么**：最终 ZIP 字节与平台根目录检查（[最终包检查](../package-check/README.md)）；广告入口本身（广告（重塑包 remake-ads 板块））；奖励数额（经济（重塑包 remake-economy 板块））。

## 防卡住的固定做法（用户 2026-10-27，重塑必做）

扫码一直转圈的根本原因是包做错了（漏打包引擎、主包超 4MB、WebP 被误判、分包没回调、从外网下载），不是缺 Retry。所以先用固定做法防住：

1. 引擎固定 **Cocos Creator 2.4.15**，构建平台选字节小游戏（ByteDance），不用 Web Mobile。
2. TikTok 相关只用 **TikTok 平台包**（`remake-core/assets/platform-kit/`，看里面的 README_接入说明.md）：广告、加桌面/个人主页回访、存档、启动文件、触摸修正。除 `PlatformConfig.js` 外原样复制，不让 AI 自己写这些代码。
3. `assets/resources` 设为字节小游戏分包；图片只用 PNG/JPG；`startSceneAssetBundle` 关闭；`REMOTE_SERVER_ROOT` 留空；`build-templates/bytedance/` 只放平台包的两个文件。
4. 出包前跑 `platform-kit/tools/check_kit_project.py --project <工程>`，不通过不打包。
5. **Retry 只是兜底**：平台包自带（10 秒无进展→Retry→新请求），它自己的测试已覆盖，不再逐个游戏做 Retry 故障矩阵；"冷启动进首页→真实触摸→玩法有反应"仍必须实测。平台包启动阶段（引擎启动前）用 TikTok 宿主的中性加载提示和 Retry 弹窗，属于宿主阶段；引擎启动后的加载页仍按统一加载界面。
6. 平台包有问题只改平台包、升版本号，不在单个游戏里改。

## 规则（唯一正文）

- **TikTok 与 Cocos 的触摸差别（用户 2026-10-28，最严重的一类“点不动”）**：Cocos Creator 2.4 的触摸转换（`getTouchesByEvent`）读触点的 `clientX/clientY`，TikTok 运行环境给的触点只有 `screenX/screenY`，算出的坐标是无效值，扫码后按钮点不动、常卡在首页。浏览器手机模拟会给 `clientX`，**测不出这个问题**。所以每个 Cocos 2.x 的 TikTok 包都必须：用平台包 `build-templates/bytedance/` 原样的 `main.js` 与 `touch-coordinates.js`（不要自写 patch_build 替代），并通过 `remake-core/scripts/audit_upload_startup.py` 里的触摸坐标探针（`probe_cocos2_touch_coordinates.cjs`，对打包产物真实执行，只给 screenX/screenY 也要得到有效坐标）。探针不过不出包。

| 内容 | 正文 |
|---|---|
| 所有游戏必须进得去 | [启动契约](references/startup-contract.md)、[Loading正常≠首页启动完成](references/loading-scene-false-positive.md) |
| 加载页样式与计时 | [统一加载界面](references/cocos-loading-screen.md)、[启动加载计时](references/startup-loading-timing.md) |
| 加载失败、重试、无回调、旧请求 | [加载恢复必测](references/loading-recovery-regression.md)、[加载恢复复盘](references/loading-recovery-casebook.md)、[加载与广告预防](references/loading-and-ad-prevention.md) |
| Native 场景/分包路径 | [Native场景加载失败](references/native-startup-path-casebook.md)、[最终包启动恢复](references/final-package-startup-gate.md) |
| Native 存档、重复领奖、写失败 | [Native奖励存档](references/native-reward-storage-and-empty-features.md) |
| 性能 | [性能与迭代](references/performance-and-iteration.md) |

## 工具（在 [remake-core](../../remake-core/SKILL.md) 的 `scripts/`）

- `audit_startup_contract.py`、`startup_business_contract.py`：启动后首页真实可用。
- `audit_startup_loading.py`（LOAD-03）：读触屏脚本的计时报告。
- `official_loading.py`、`audit_official_loading.py`：统一加载页。
- `audit_loading_recovery.py`：加载失败与重试恢复。
- `audit_native_storage_contract.py`、`run_reward_storage_probe.py`：Native 存档与领奖。
- `audit_final_package_startup.py`、`audit_native_startup_renderer.py`：同版 Native 启动。
- 示例：`assets/loading-recovery-examples/`。

## 修改步骤

1. 先复现：记录卡在哪一步（Loading、首页、首个点击），保存原始日志。
2. 按正文找对应故障类型修复；修完保留"故障→修复→正常对照"证据。
3. 只复测受影响的启动链：首页→真实触摸→玩法变化；失败→Retry 新请求→恢复。

## 联动表：改了启动/存档，要回查

| 改了 | 回查 |
|---|---|
| 启动顺序、场景加载 | 首次进入教程（新手引导）、广告 SDK 初始化（广告） |
| 存档结构 | 钱包、礼盒冷却、关卡进度能否读回（经济、关卡） |
| 加载页 | 加载页画面（美术） |
| 资源路径/分包 | 最终包检查 |

## 验收清单

- [ ] 冷启动进入首页，首页每个按钮真实触摸有反应
- [ ] 加载失败/超时有 Retry，Retry 发新请求并恢复
- [ ] 加载页符合统一样式，启动计时达标
- [ ] 重开后存档一致；坏档不崩、不发免费奖励
- [ ] 广告前后、发奖动画不掉帧
