---
name: cocos-game-tiktok-package
description: "用户提到测试包、上传包、平台包、TikTok ZIP或重新出包时，调用本技能生成同版Native测试包，并同步交付同版本固定手机本地预览。"
---

# TikTok小游戏出包与交付

用户2026-10-27明确：writer拒包是当前任务的修复输入，不是对话终点。自动处理具体缺口、重建并复验，直到writer及交付核验真实通过并给出ZIP；不能用“尚未放行”的总结结束或等待用户再次说继续。只在确需用户提供、且本机无法取得的外部信息或用户明确暂停时停下；不得降低门禁或伪造证据。

本入口负责用户授权的测试包、上传ZIP与重新出包。只有真实Cocos Native构建可以生成平台ZIP；根目录直接包含game.js、game.json、project.config.json，不带外层文件夹、源码、Web套壳、套娃ZIP和QA跳关标记。成品制作流程通过后按当前合同连续出包；仅检测/评审/试玩遵守用户边界；本入口不授权平台上传或发布。

## 选择执行范围

| 当前任务 | 执行路线 |
|---|---|
| 新制作首次完整验收/明确完整重做 | 当前适用review通过后用共享 `make_tiktok_zip.py`；完整review与必要启动/存储门禁保留 |
| 已批准成品的局部修改或同版重出 | 使用[最终文件检查与轻量writer](../cocos-tiktok-package-check/SKILL.md)，沿用有效功能证据；仅补受影响问题，不重做已批准美术和无关游戏CI |
| 单独判断已有ZIP | `verify_native_zip.py <ZIP>`或最终检查器；只读诊断不等于已完成可交付门禁 |

共同策略见[执行去重](../cocos-game-to-english/references/review-execution-plan.md)。适用检查已通过、证据有效且无新改动/失败/疑点即停止，不因表格不同重复操作。

## 两条writer共用的必要门禁

- 当前目标App ID、真实Native根入口/引擎/adapter/分包、静态资源完整性和场景组件绑定。
- 按[皮肤试用频率的项目验收](../cocos-game-ad-design/SKILL.md#皮肤试用频率的项目验收2026-10-27)盘点适用性并核对与最终候选绑定的实际运行证据；适用但未验证或失败不得当作通过，修复复验后继续出包。
- 固定未压缩限额：总包≤30,000,000、主包≤4,000,000、每个独立分包≤4,000,000字节，普通分包计总包。按 `upload_size_gate.py`执行；压缩后大小不能替代。
- [生产资源清单与已报告问题](../cocos-tiktok-package-check/references/resource-and-reported-issues.md)：动态请求反查漏项，未知有限域明确拒绝；固定项目问题历史缺失/未复验/失败/相关证据失效拒绝。有效问题证据只读回相关文件，不重放无关矩阵。
- [当前Native启动与恢复](../cocos-game-to-english/references/final-package-startup-gate.md)：HOME可操作→可信输入→玩法变化，故障后Retry产生新请求并恢复；同一次可信启动不在交付阶段再跑一遍。
- 最终ZIP CRC、安全路径、逐文件与Native同字节、独立带空格目录回解核对；发送前核实际交付路径。

先拒绝便宜、确定失败项，再运行必要启动/功能门禁。失败继续修复→重建→定点复验，不以中途报告等待下一句“继续”，也不为了变绿而删断言或改限额。项目专用运行器按[项目QA注册](../cocos-game-to-english/references/project-qa-registration.md)，路径、App ID与故障原件留项目。

- Cocos debug/release 资源与 Chrome CDP 证据兼容按[格式与执行器检查](../cocos-tiktok-package-check/references/check-contract.md#构建格式与触摸执行器兼容2026-10-27)，同一共享门禁必须继续拦截缺图、未知 UUID 和无原始触摸的证据。

## 正式writer命令

```sh
python <skills>/cocos-game-to-english/scripts/make_tiktok_zip.py \
  --native <Native> --app-id <目标AppID> --out <稳定交付目录/新版本.zip> \
  --project <工程> --web <同版Web> --build-tag <版本> --review <本轮review.json> \
  --resource-manifest <当前资源清单.json> --startup-contract <当前启动合同.json> \
  --loading-recovery-runtime <当前恢复索引.json>
```

完整制作的其他合同见[检查点](../cocos-game-to-english/references/execution-checkpoints.md)、[包形式](references/package-forms.md)。仅持有Native的维护输入使用已审阅的项目适配，不伪造源码或删门禁；新适配补充共同验证，旧项目兼容合同升级时保留。

## 交付

writer成功后按[最终交付核对](../cocos-tiktok-package-check/SKILL.md)对实际ZIP生成新回执，不重新手跑相同文件检查。最终回复主动给当前稳定ZIP可点击链接和同版本已启动的可点击试玩入口，默认不堆报告。原始材料、旧包、用户存档保持；本地结果不冒称设备/真实广告/平台通过。

**测试包必同步本地预览（用户 2026-10-27）**：用户只要提到“测试包、上传包、平台包、TikTok ZIP、出包、重新打包”或同义出包意图，必须调用本技能；交付物必须同时包含当前同版 Native 测试包和固定手机尺寸的 Codex 本地预览链接。预览必须从本轮最终 Web 导出启动，使用固定手机外壳（通常390×844），并通过文件树/构建绑定确认预览版本与 ZIP 对应同一源码、同一版本标识和同一候选。只交 ZIP、只给旧预览、用旧版本试玩页或把 Ego/Chrome QA 页面当用户预览都不算完成。

出包前先启动并验证本地预览的 HOME→PLAY→玩法变化；writer 生成后再次核对预览服务仍指向同版导出。最终回复必须同时给 ZIP 链接和本地预览链接，并明确预览为本地 Web 手机试玩层，和 Native、物理手机、真实广告、平台接受分开记录。用户试玩预览在用户结束试玩或被新版替代后由 Agent 按现有收尾规则关闭；若本轮仍需用户试玩则保留并标记交付。

同期广告模拟、制作统计、Credits和评价等规则按[当前合同](../cocos-game-to-english/references/current-contracts.md)选择相关正文，不复制事故全文。

**出包前触摸输入（用户 2026-10-27）**：涉及首页、PLAY、按钮、拖动或启动恢复的本地回归，按最终检查入口的[最终包触摸证据](../cocos-tiktok-package-check/SKILL.md#最终包触摸证据用户-2026-10-27)执行；不把电脑鼠标通过写成手机触摸通过。

**出包前触摸预检（用户 2026-10-27）**：在交当前 Native 测试包前，先使用独立 Google Chrome iPhone CDP 触摸完成受影响入口矩阵；Codex 内置浏览器不能替代。读取[Chrome iPhone 触摸预检矩阵](../cocos-game-to-english/references/chrome-touch-preflight-matrix.md)。

**输出必须标明 Chrome 测试层（用户 2026-10-27）**：凡输出“测试通过”“手机触摸通过”“按钮已验证”或交付预览，必须注明 `Google Chrome iPhone touch`、设备尺寸/DPR、`input_transport=playwright_cdp_touch` 和业务结果。只在 Codex 内置浏览器查看或点击，必须写“仅查看，未作为手机触摸测试”，不得写成测试通过。

**真实广告不是本地交付门槛（用户2026-10-27）**：电脑本地不要求真实 TikTok 广告填充或播放；用独立SDK边界模拟验证实际触摸、奖励与恢复，不得因缺少真实广告而停工、拒包或等待用户。适用检查通过即完成授权交付，日常不重复免责声明。统一规则见[电脑本地广告验收边界](../cocos-game-to-english/references/tiktok-device-stage.md#电脑本地广告验收边界用户2026-10-27明确)。

**每轮修改主动交预览（用户2026-10-28）**：每轮游戏代码、美术、玩法、广告或打包相关修改完成后，主动在回复中给出当前同版本可点击的固定手机预览链接，无需等用户再次索取。按[用户本地试玩](../cocos-game-to-english/references/user-phone-preview.md)执行；交接前确认服务可访问且指向本轮完成的构建。
