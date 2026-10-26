# 最终测试包必查：扫码后卡加载的本地启动与恢复链（2026-10-26）

用户明确要求每次新测试包都审查“扫码后进不去、一直停加载”的对应启动风险。本条覆盖旧的“成品轻量出包只做静态检查/可省 Native 运行”的例外；不重跑玩法、经济、广告和已批准美工CI，但最终启动和加载恢复必做。

## 复用的现有检测

- [加载场景假通过](loading-scene-false-positive.md)：真正HOME已绘制、必需资源就绪、加载遮罩退出、PLAY可用、真实输入产生玩法变化；首异常不可隐藏。
- [启动契约](startup-contract.md)：入口→实际adapter→原引擎→场景→业务；宿主全局、资源/分包失败、超时和必要/可选初始化分离。
- [加载恢复回归](loading-recovery-regression.md)：实际Native捕获边界、无回调/超时、失败后可见Retry、真实触摸后新请求、旧回调隔离、恢复后可玩。

不得以HTTP200、进度100%、scene active、Web预览、文件/体积检查通过、手填passed或旧包报告替代。报告必须绑定最终Native树；相同Native仅改ZIP名可以复用原始材料，但轻量writer每次仍执行已登记可信启动runner并核恢复原始材料。Native字节变更旧绑定拒绝，不能只改哈希续用旧证据。缺适配runner或材料就补适配/实测，不删门禁、不写空通过；既有真实扫码失败未闭合不得标普通测试包完成。

每次启动检查同时按[资源生命周期与失败任务重试清单](loading-scene-false-positive.md#启动资源生命周期与失败任务重试清单2026-10-26)核当前存在的机制：切场景资源释放、失败Promise与无回调恢复、分包/图片缓存、宿主别名、Retry最终尺寸与实际点击、运行版本缓存。已知缺陷先做旧失败→修复及正常对照；不能仅以文件检查通过或替身合同通过交付。

## 已接入脚本的门禁

共用 `scripts/audit_final_package_startup.py` 复用现有 `audit_native_startup_renderer.validate`、可信runner及 `audit_loading_recovery.validate`。轻量writer写临时ZIP之前强制执行；正式writer在已有review门禁外强制核同版材料，实际可信重跑沿原review执行，避免重复。最终prepare_delivery重新核材料/原始文件/Native字节，不第二次执行相同runner。

两个writer和prepare_delivery新增参数：

```
--project <源码工程>
--resource-manifest <当前业务资源清单.json>
--startup-contract <audit_startup_contract当前通过报告.json>
--loading-recovery-runtime <当前Native边界恢复原始索引.json>
```

startup-contract须为policy_version=2、runtime_required=true，并引用精确SHA的真实renderer报告；该报告必须满足现有HOME/输入业务判据、真实adapter/引擎和可信执行器要求。恢复runtime依现有合同逐项验证原始证据、失败/正常对照和同版绑定。无任何跳过/仅文件通过开关。资源清单与固定问题历史由[资源完整性与已报告问题门禁](../../cocos-tiktok-package-check/references/resource-and-reported-issues.md)另作快速验证，缺项或未闭合反馈先拒绝，不重跑无关游戏CI。

本地结果只表述为“最终Native本地启动/加载恢复检测”。实际抖音/TikTok扫码仍单列：目标平台/App ID、实际包版本、首条运行异常、账号/客户端及实际恢复结果；没有手机证据不称扫码通过，也不把本地同形故障视为手机唯一根因。用户已知边界，不每次交包重复长免责声明。

回归：`cocos-tiktok-package-check/scripts/test_final_startup_gate.py`（门禁单元校准，不是任一游戏的实跑证明）。


## 启动验证期间的输入稳定（2026-10-26）

共享启动门禁核开始和结束的Native树、启动合同、renderer报告与恢复索引一致，并重新核引用的原始证据。任何变化拒绝；只做哈希/合同复核，不再次运行相同可信启动器。交付核验在这些检查后再比原Native与最终ZIP字节。执行顺序和当前限制见[检查顺序与受检对象一致性](../../cocos-tiktok-package-check/references/gate-order-and-identity.md)。

成品启动维护可用 `audit_startup_contract.py --runtime-only --project ... --native ... --binding ... --renderer-report ... --out ...` 生成当前启动契约；它仍实际执行可信Native运行器，不扫描无关旧源码或重跑完整制作CI。文件、资源和固定上传体积门禁仍由writer执行，不得用runtime-only替代它们。
