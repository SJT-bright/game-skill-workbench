---
name: cocos-tiktok-package-check
description: "已有Cocos Native或ZIP的最终文件检查、启动故障诊断及成品增量出包；新制作完整验收由打包主入口分流。"
---

**浏览器用途规则（用户 2026-10-27 最新更正）**：Agent 代测使用 Ego 浏览器的 **Google Chrome iPhone touch** 模式，先按 `ego-browser` 绑定自有测试空间并取得当前 CDP 端点，再用 `chrome_touch.py --cdp-url <当前Ego-CDP端点>` 执行；固定 viewport/DPR/UA/has_touch，`input_transport=playwright_cdp_touch`。代测不启动本机独立 Google Chrome，不使用 `--user-approved-chrome --channel chrome`，也不因 Ego 不可用自动切换本机 Chrome。仅在完全交给用户亲自试玩时，使用本地固定手机尺寸预览并打开本机 Google Chrome。代测服务使用 `--no-browser`，不通过 `--keep` 提前触发本机浏览器；交接用户时再按试玩流程打开。Ego 测试结束由 Agent 关闭自有空间并核实；不接管其他会话。此规则替代此前“代测默认独立 Chrome”的规定，Codex 内置浏览器仍不作触摸通过证据。


# 最终Native/ZIP检查与成品增量出包

接在用户已授权的出包或具体启动故障维护之后。新制作完整验收由[打包主入口](../cocos-game-tiktok-package/SKILL.md)选择范围；本入口不重做全游戏玩法、美术或所有历史事故。只读检查已有ZIP仍可单独执行。

遇到 Cocos debug/release 资源格式差异或触摸执行器迁移时，按[格式与执行器兼容](references/check-contract.md#构建格式与触摸执行器兼容2026-10-27)处理；保留真实缺图/假触摸拒绝断言，并验证实际 writer 接线。

1. 锁当前Native、目标App ID、稳定新ZIP路径、项目与证据。按[检查合同](references/check-contract.md)先核根入口、原生坐标、引擎/adapter、分包/场景、资源、未压缩体积；[检查顺序](references/gate-order-and-identity.md)先拒绝确定错误。
2. 按[资源与历史问题门禁](references/resource-and-reported-issues.md)，运行当前生产调用清单反查。清单漏项、未知动态域、固定问题历史缺失、未复验/失败/失效拒包。相关问题有效时仅核证据与依赖，不重新跑该运行器。
3. 验[同版Native启动恢复](../cocos-game-to-english/references/final-package-startup-gate.md)，保留HOME→真实触摸→玩法变化及失败→Retry新请求→恢复。现有可信runner走[项目QA注册](../cocos-game-to-english/references/project-qa-registration.md)。
4. 轻量writer一次完成Native前检、必要启动、ZIP回读和原Native全字节；成功后不手动紧接着跑同一check_package。失败只修复对应链；具体WebP、触摸、资源路径等症状从[当前合同](../cocos-game-to-english/references/current-contracts.md)路由。
5. 最终交付对实际链接路径运行prepare_delivery；它核同版材料与字节，不再次执行相同启动runner。检查期间新增问题、清单/Native/证据变化拒绝发布。

```sh
python scripts/build_checked_zip.py --native <Native> --expected-app-id <ID> \
  --out <稳定新ZIP> --report <内部新报告.json> --project <工程> \
  --resource-manifest <当前资源清单.json> --startup-contract <当前启动合同.json> \
  --loading-recovery-runtime <当前恢复索引.json>
python scripts/prepare_delivery.py --zip <上述同一ZIP> --native <同一Native> \
  --expected-app-id <ID> --record <新交付回执.json> --project <工程> \
  --resource-manifest <同一资源清单.json> --startup-contract <同一启动合同.json> \
  --loading-recovery-runtime <同一恢复索引.json>
```

已报告拖动/音频问题另按[实际交互与声音](references/drag-audio-postconditions.md)带当前trace。启动/资源故障缺同版运行证据不得只用Web可玩、ZIP CRC或旧CI覆盖；定位首错和实际依赖，不在错误版本上刷长测。共享代码在相邻cocos-game-to-english/scripts，两个目录必须同级安装。

交稳定ZIP链接和必要说明，并给同版已启动的[固定手机预览](../cocos-game-to-english/references/user-phone-preview.md)。报告与故障原件留项目，不混进游戏包；不改变已批准美术，不自动上传平台。

同期广告模拟、制作统计、Credits和评价等规则按[当前合同](../cocos-game-to-english/references/current-contracts.md)选择相关正文，不复制事故全文。

**最终包触摸证据（用户 2026-10-27）**：本地启动或回解验证使用 Google Chrome DevTools/CDP 触摸模式，固定移动设备参数并记录 `playwright_cdp_touch`；鼠标仅作辅助排错，Chrome 模拟仍与物理手机、TikTok Native 和真实广告分开记录。

**广告入口的 Native 存储前置门禁（用户2026-10-27）**：写测试包时，广告检查必须覆盖“按钮→Native存储读取→SDK create/show→回调→奖励保存→原消费者”全链。浏览器/本地广告模拟只能证明模拟业务回调，不替代 Native 存储桥和真实 SDK 边界。应按平台契约与键语义验证缺省、Boolean、字符串/数字、损坏对象和坏字符串等适用形态；坏值不得静默发奖。缺少逐项证据时不能标全链通过。当前 writer 对合同的自动核验能力有限，见下方审查纠偏；不能把它当作完整拒包保障。

**最终包先做 Chrome 触摸短检（用户 2026-10-27）**：回解最终 ZIP 的本地预览使用Ego 浏览器的 Google Chrome iPhone CDP 触摸；Codex 内置浏览器只能查看，不得作为手机点击通过依据。广告入口、取消、超时、重复回调和按钮结果按[Chrome iPhone 触摸预检矩阵](../cocos-game-to-english/references/chrome-touch-preflight-matrix.md)执行。

**广告存储合同必须接入 writer（2026-10-27 复审修订）**：已识别激励广告或已有存储合同的项目，按 [adapter 存储证据 v2](../cocos-game-to-english/references/ad-storage-evidence-contract.md)核验逐形态原始 JSON、Native/runner/宿主身份及业务断言。v1 拒绝沿用；共享 `package_obligations.verify` 已调用此检查。合同同时强制本地玩家链与旧故障对照；入口清单及运行器语义仍须审阅，本地验证不产生真实平台结论。

**输出必须标明 Chrome 测试层（用户 2026-10-27）**：凡输出“测试通过”“手机触摸通过”“按钮已验证”或交付预览，必须注明 `Google Chrome iPhone touch`、设备尺寸/DPR、`input_transport=playwright_cdp_touch` 和业务结果。只在 Codex 内置浏览器查看或点击，必须写“仅查看，未作为手机触摸测试”，不得写成测试通过。

**2026-10-27 审查纠偏**：合同列出形状不等于执行；每一形状需独立原始证据与业务断言。当前脚本核 adapter 形态及本地玩家链的身份/断言/失败对照，关键字扫描仍可能漏广告，不能代替运行器和入口清单审阅；须人工核对所有真实广告入口、旧故障复现、测试 runner 实际注入位置及最终 Native 同版，并保留完整回调与奖励读回证据。模拟注入、哈希或设备尺寸均不证明真实 TikTok SDK/物理设备通过；缺证据标未验证。

**真实广告不是本地交付门槛（用户2026-10-27）**：电脑本地不要求真实 TikTok 广告填充或播放；用独立SDK边界模拟验证实际触摸、奖励与恢复，不得因缺少真实广告而停工、拒包或等待用户。适用检查通过即完成授权交付，日常不重复免责声明。统一规则见[电脑本地广告验收边界](../cocos-game-to-english/references/tiktok-device-stage.md#电脑本地广告验收边界用户2026-10-27明确)。

广告前置读取或 Native adapter 故障修复时，执行[本地广告修复闭环](../cocos-game-to-english/references/native-ad-local-repair.md)：忠实存储/能力替身、真实按钮到 SDK 与到账、超时重试、迟到回调、保存重试及原消费者；以业务结果和旧故障对照收口。

**条件画面与禁用入口的出包检查（2026-10-27）**：受影响的倒计时、价格、广告结果及教程状态，按[成屏回归](../cocos-game-art-redo/references/rendered-ui-regression-review.md#条件状态与检查器自校准2026-10-27)留实际运行证据，已反馈缺陷通过当前 Native 的可执行问题复验接入 writer；不是每次重新审全部美术。`package_obligations.verify` 强制执行源码/Native 的分享与排行榜残留检查，发布前复查同一结果；图片字与动态入口仍须实际页面检查，扫描不替代触摸。
