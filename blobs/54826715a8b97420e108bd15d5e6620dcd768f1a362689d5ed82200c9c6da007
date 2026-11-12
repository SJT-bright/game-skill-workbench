# TikTok 跨平台语义与旧存档升级（2026-11-11）

适用于 TikTok Native 的 Cocos 2.x/3.x。首次平台接入及相关依赖变化时使用；不是每轮重跑全部游戏。源自 Music Slice v32→v33 受控 Native 复现及平台层既有历史。普通 Web、换 iPhone 尺寸、UA、`platform: ios`、Android 通过或 ttmg check/build 均不能替代此项。

## 先预防，再执行可复用的定点检查

1. 接入存档时盘点真实读写点与 schema。新版多键存储先装平台 `storage-guard.js`，写文本；SaveStore 键继续由 SaveStore 自身 schema 管。旧游戏不强行更换全套存档，但必须按自己的原始存档验证同一契约。不得将合法 Boolean 一律视为数字，不能全游戏硬编码 Coin。
2. **存在但不可读 ≠ 缺键**。元数据确认不存在才按新玩家初始化；无法确定或已有值不可读时，保留原始值、禁止默认值覆盖。同步桥读不出时可按本游戏明确数值 schema 调 `require('./storage-guard').recoverNumeric(cc, api, specs, callback)`。`specs` 为 `[{key, integer:true, min, max}]`；只接受原类型数字或合法数字文本，读回确认后才放行。本函数不猜 Boolean→0/1，不清存档。普通 Boolean/JSON 键需自己的 schema 恢复，不套数字恢复器。
3. 恢复必须在存档消费者/场景逻辑之前完成，单次等待有界、迟到结果不写旧状态。失败进入玩家可见的存档阶段错误与 Retry/免费退出，不能吞异常后继续永久 loading。仅调用 install 不会自动完成旧档迁移；启动方负责等待恢复回调。不要在每次 reload 重新播种 fixture。
4. 首次得到可维护 Native 时就跑下面的启动/升级最短链，不能等最终打包才发现。复用项目已有 adapter 和存档 fixture，额外覆盖同一层，不把所有玩法乘两遍。

## 最小兼容矩阵（命名为语义模型，不冒称实机 OS）

| 模型 | 实际输入与必须观察到的故障 | 结果 |
|---|---|---|
| 正常/新玩家 | 缺键与实际 SDK 元数据；常规 typed/string 读写 | 首页→真实触控→首个可玩状态与业务结果，遮罩退出 |
| 冷升级 typed 异步恢复 | **引擎启动前**按实际旧schema种入旧类型值；有适用数值字段时覆盖非0/1整数（如45）及合法0；同步读Boolean，异步仍读原类型 | 触发记录必须命中；保留全部原值，迁移后冷重启仍保留；首页→触控→玩法结果 |
| 冷升级无法恢复 | 相同旧fixture，同步与异步均不可读/失败或不回 | 原值不被默认覆盖，不错误发奖/扣费；有界退出loading并展示可重试状态 |
| 平台异步边界 | 实际采用的分包/资源接口：callback、声明兼容的Promise、双通道、失败、无回调、迟到；可选progress缺失；重复零进度 | settle一次；无有效进度会超时；Retry新请求不被旧回调覆盖；慢引擎只初始化一次，ready后才切场景 |
| 前后台 | 游戏实际hide/show，加载/恢复/广告相应阶段 | 返回后可继续或有设计出口；不靠document.hidden冒充平台生命周期 |

字段不适用时用实际代码/schema证据登记；不能通过把字段删空避开迁移检查。数值0与Boolean false含义不同。人为`numbool=all`失败只证明兼容模型不足，不单凭它断言具体iPhone根因。

测试宿主 2.x `ad_regression/host.js`、3.x `runtime_regression/host3x/host.js` 支持：

```
missing=false&syncnumbool=all&async_storage=typed&storage_seed=<URL编码的本游戏旧fixture JSON>
```

`storage_seed` 写宿主隔离空间且在游戏代码前执行；下一次冷重启**移除 seed**。`async_storage=typed` 独立于同步失真；缺键和既有throw模型仍照原样。用 2.x 的 `window.__hostLog`、3.x 的 `window.__H.log` 核对 fault 确实命中。默认`save_restart`同版写后重开记录不能冒充冷升级；使用已有运行器新增这个定点节点，先校准再正式记账。

## 可执行门禁与负例

运行器字段与原始观察格式见[STORAGE-01 v3回执](storage-upgrade-trace-v3.md)。非二值采用本作schema允许的值（如45或0.7），边界用合法0或1，不能塞入本作不接受的45再报产品故障。

- `audit_native_storage_contract.py` v3 核冷升级原始观察、fixture/runner/Native绑定及同runner负例，`check_known_issues.py` 重判。旧v1/v2仍可读，只能证明旧范围，不能当作新跨平台覆盖。依赖未变可沿用v3记录；新增规则只使相应storage节点失效，不扩大到美术/关卡全量。
- 旧故障版或单点反例必须在同一运行器复现：不保值/无法进入首关/永久loading等实际失败，不能只填pass字段。原空字符串缺键反例不能替代数值旧档反例。
- 平台件修改验证：`tests/storage-guard.test.js`、`storage-guard-negative-controls.js`、`storage-recovery.test.js`；宿主修改用 `runtime_regression/tests/storage_host_profiles.cjs`。这些是标准件自测，**不替代本作真实导出引擎实跑**。
- 新鲜证据绑定实际Native树、入口/adapter、runner及依赖、profile与故障命中、旧fixture SHA、before/after、首个异常、遮罩与业务结果。升级fixture、profile或平台存档层变化，仅补这个受影响节点；不能用“改动小/遗留游戏”把缺证写成通过。

## 真机与交付的边界

分别记录本地语义模型、Android真实TikTok、iOS真实TikTok、真实IAA和平台上传接受；禁止相互代填。正式宣称双平台可用前，两系统各需同版实际TikTok短路径：冷启动→PLAY→操作，冷重开保值，切后台返回；有广告时补真实完成/取消及回游戏。缺设备可以交明确待测候选，不能标双平台完整验收。已获有效同版设备证据按依赖复用。

记录设备/OS/TikTok/SDK/引擎版本、包SHA、冷/热缓存及新/旧存档、发生阶段和首个异常；不要记账号/完整用户存档。加载阶段诊断与看得见的Retry是制作要求，避免下次只收到“99%卡住”无法定位。

官方依据（2026-11-11核读）：[Cocos接入](https://developers.tiktok.com/docs/en/build-mini-games-with-cocos)、[技术环境边界](https://developers.tiktok.com/docs/en/mini-games-technical-overview)、[存储API](https://developers.tiktok.com/docs/en/mini-games-sdk-storage)。官方存储契约允许多类型数据；Boolean失真是历史/受控兼容模型，不是官方承诺的iOS行为。

恢复器只保护经过guard的读写，不拦截直接SDK写入或removeItem/clear；游戏错误分支禁止清档，实际业务矩阵必须核removed_keys与写入轨迹。恢复批次使用最新请求所有权；Retry验证已成功写入的文本后解除写锁，旧批次迟到不得再写。
