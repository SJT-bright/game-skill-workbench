# TikTok 跨平台语义与旧存档（2026-11-11；存档部分 2026-11-12 重写）

适用于 TikTok Native 的 Cocos 2.x/3.x。首次平台接入及相关依赖变化时使用；不是每轮重跑全部游戏。普通 Web、换 iPhone 尺寸、UA、`platform: ios`、Android 通过或 ttmg check/build 均不能替代此项。

## 存档的总规则：读不出来不能让游戏停下（2026-11-12）

**存档读不出来，就当这个值不存在，用默认值继续玩。** 不抛错、不卡加载页、不弹“无法继续”的页面、不锁住存档不让写。能拿回原值就拿回，拿不回也照常进游戏。

为什么改：2026-11-11 把平台存档保护件改成“读不懂就抛错并锁住这个键”，理由来自电脑上的模拟模型，没有手机证据。结果用它出的包在真手机上打不开（快乐星猫 R7：`Stored value unreadable; preserve save and retry typed recovery: IS_GAME_MUSIC`，首页没出来）；游戏自己照这条规则写的保护也让手机反复加载失败（Music Slice v34：`Unreadable saved numeric value: RewardIndex; save preserved`）。随后的补救是给每款游戏逐个键加恢复页和大量检查，没有回头改保护件。2026-11-10 及以前的保护件（本机几百份游戏包里是这一版）读到布尔值或空值时返回“没有值”，不抛错也不上锁。现在回到那个行为，并且底层读取本身抛错时也按“没有值”处理。

代价要说清楚：读不出来不等于确认缺键。一个确实存在、但同步/异步都拿不回的值会在本次使用默认值，之后真正保存时可能被覆盖；读取、默认值展示本身不覆盖原值。裸数值/布尔旧档是本次已知风险，文本写入减少裸类型依赖，不能保证已存文本永不损坏或读取永不失败。读取失败不清档；可取回的旧值仍按下文显式迁移。

### 标准件已经做好的（游戏不用写代码）

- `storage-guard.js`（出包时自动装）：写入一律转成文本；读到字符串、对象原样给，数字转成文本；读到 `true`、`false`、空串、`undefined`、`null`、`NaN` 或读取抛错，一律返回 `null`。平台键列表里确实存在的空串仍是空串。任何键都能写，不上锁。
- 读到布尔值、读取抛错、或平台列出了这个键却读不出东西时，每个键在控制台打一行（最多 20 个键）：`[TikTokKit] storage <键名>: boolean_read true, read as no value`。手机上开 vConsole 就能看到平台实际返回了什么，这是判断手机存储行为的第一手材料。没人列出的键读到 `null` / `undefined`（普通的“没存过”）不打。
- `SaveStore`：存档键不存在就建新档；存档读不出来或已损坏，把原文备份到 `<键>:corrupt-backup`，从默认值开始，并把一次性平台奖励记为已领（不会重复发）。之后照常能保存。

### 游戏自己的代码要守的

1. 读存档得到 `null`、空串或格式不对的值时用默认值，不抛错。原游戏里 `JSON.parse(读到的值)`、`读到的值.split(...)` 这类写法要先判空。新玩家读每个键得到的也是 `null`，所以新玩家能玩就已经覆盖了大部分情况。
2. 不要自己再包一层“读不懂就抛错 / 进恢复页 / 锁住功能”的存档保护。金币等余额读不出来同样按默认值继续，不做“保档并阻止继续”。
3. 不要绕过 `cc.sys.localStorage` 直接调 `tt.getStorageSync` / `wx.getStorageSync` 读存档；绕过了保护件就管不到。
4. 不清档：错误分支里不调 `removeItem` / `clear`。
5. 默认值只留在内存；getter、标签刷新和首帧展示不负责写默认值或迁移。显式迁移写入失败时，保留已验证的可读值继续启动。真正发奖、扣款等业务写入失败仍沿用原事务的重试/失败反馈，不把“能进入游戏”当成“已保存成功”。

### 想保住老玩家旧值时（可选）

只有“以前上线过、且旧版本原样写过数字或布尔值”的游戏需要。在读存档之前调用一次：

```js
var guard = globalThis.TikTokStorageGuard;        // 保护件装上后放在这里；浏览器预览里没有保护件时是 undefined
if (!guard) return startGame();
var platform = globalThis.TTMinis && TTMinis.game || globalThis.tt;
guard.recoverTyped(cc, platform, [                // Cocos 3.x 第一个参数传 null
  {key: 'Coin', type: 'integer', min: 0},        // 同步读成布尔值时，去异步接口取回真实数字，存成文本
  {key: 'IS_MUSIC', type: 'boolean'},            // 真正的布尔开关：布尔值本身就是它的值
  {key: 'GuideDone', type: 'integer', min: 0, max: 1, acceptBoolean: true}   // 只有 0/1 的标记
], function (error, results) {
  if (error && error.code === 'TIKTOK_STORAGE_SUPERSEDED') return;   // 被更新的一次调用接管
  if (error) console.error('storage schema', error);                 // 清单写错了：改清单
  startGame();                                                       // 其他情况一律进游戏
}, 5000);
```

它不会让启动失败：异步接口失败、不回调、超时（只算前台时间）、又返回布尔值、值不合清单时，这个键按“没有值”读，回调照常到达且不带错误。`results[键]` 写明每个键的结果（`value_recovered`、`boolean_kept`、`absent`、`async_failed_no_value`、`timeout_no_value` 等，全表在 `storage-guard.js` 文件头）。不把布尔值猜成任意数字；平台没列出的键读到 `false` 按缺键处理。

## 收到“手机打不开”：先判故障在哪一层（2026-11-12）

收到手机“还是打不开”立即保留原结果但撤销手机故障已解决的结论：按现有[手机问题账本](../../cocos-game-check/package-check/references/resource-and-reported-issues.md)登记手机实际包、原话、入口与能取得的日志。无法确认平台选择的版本就明确未知，不预设旧包/缓存/网络或唯一原因。平台加载页无游戏画面，不等于游戏存档卡住；平台自身加载页也可能覆盖已经开始的游戏执行，必须用入口日志/首帧证据区分。

先分四层：①包获取/挂载及入口是否执行；②adapter/引擎至首帧；③游戏首场景/资源/存档；④进入玩法后的输入/广告/恢复。第③④层通过不能排除①②层。没有ENTRY日志只能写“未观察到入口执行”，不能猜代码必然没跑。

Cocos2适用包先做当前`audit_upload_startup.py`轻量审计：SDKVersion索引、缺getOpenDataContext误判子域、包内fs.access等待三种已知旧式由共享`package_gates.adapter_fix`规范化；重建后再次核实际产物。该审计的已知前提检查现在拒绝这些未规范化旧式，不能拿legacy警告或ZIP体积/CLI通过代替。实际Native入口定点对照至少覆盖本作涉及的缺SDKVersion、缺开放数据可选API、包内access不回；不向测试SDK无条件注入这些字段再标iOS兼容。首次修复实际PLAY须用触控进入玩法。

这些是有机制依据的兼容对照，不是手机根因确认。仍需原始手机画面/日志匹配或同版真机成功记录才能解除手机故障；平台权限、地区、客户端、版本挂载等由真实平台证据判断。原故障无法复现时使用既有`defer-external`（需用户明确原话），不能自动解释“给测试包”为允许跳过。只补发生问题的入口链和相关依赖，不重跑无关广告/美术/关卡。

手机日志里出现 `[TikTokKit] storage …` 行时照抄进账本：它说明哪个键、平台返回了什么。出现 `Stored value unreadable` 或 `save preserved` 字样说明包里还是 2026-11-11 的保护件或游戏自写的抛错保护，按上一节改掉后重新出包。

## 启动链上其余要守的（2026-11-12）

- 读取或显示旧值时不顺手写回；缺省值只放在内存里，真正有业务变化才写。迁移到新键失败不能拖死已经能显示的首页。
- 首页拿到的平台信息（键列表、异步读取结果）要让后面的 PLAY、广告等共用，不能首页通过后 PLAY 又去要一个不存在的同步接口。迁移/恢复的有效、缺省、超时结果归属同一次启动尝试；后续消费者复用该状态，旧尝试的迟到回调不能覆盖新尝试。每个 SDK 方法从实际提供它的对象上调用并保留 receiver；一个命名空间对象存在不等于它有所有方法。
- 下载完成不代表图片已经解析。适用时用共享平台件的解析层超时/重试和请求归属，故障后真实点 Retry，确认新请求、首帧、首页和触控开局。新加载层用已有引擎渲染；禁止先对主 WebGL 画布取 2D 上下文。
- **加载失败**（分包、资源下不来）仍要有可见 Retry：系统弹窗的 fail / Promise 拒绝 / 无回调不能当作“已经给了重试入口”，要用实际能点的控件。这一条只管加载失败，不管存档；存档读不出来不出恢复页。

启动检查仍分别保留 home_ready、play_entered 及原始错误，不能用一个 passed 盖住降级状态。

## 最小兼容矩阵（命名为语义模型，不冒称实机 OS）

| 模型 | 实际输入 | 必须看到的结果 |
|---|---|---|
| 正常/新玩家 | 缺键与实际 SDK 元数据；常规读写 | 首页→真实触控→首个可玩状态与业务结果，遮罩退出 |
| 旧值读不出来 | **引擎启动前**把游戏读的每个存档键种成读回布尔值的样子，异步存储不可用，一次全 `true`、一次全 `false`，其中一次拿不到键列表 | 没有异常，遮罩退出，首页→真实触控→玩法；其他已有数据不被删改 |
| 旧值可取回（仅“上线过且写过原始值”的游戏） | 启动前种入本作合法的旧类型值（非 0/1 数值如 45 或 0.7，及边界 0 或 1）；同步读成布尔值，异步仍是原类型 | 原值保留并转成文本，冷重启后仍在；首页→触控→玩法 |
| 平台异步边界 | 实际采用的分包/资源接口：callback、声明兼容的 Promise、双通道、失败、无回调、迟到；可选 progress 缺失；重复零进度 | settle 一次；无有效进度会超时；Retry 新请求不被旧回调覆盖；慢引擎只初始化一次，ready 后才切场景 |
| 前后台 | 游戏实际 hide/show，加载/广告相应阶段 | 返回后可继续或有设计出口；不靠 document.hidden 冒充平台生命周期 |

数值 0 与布尔 false 含义不同。人为 `numbool=all` 失败只证明兼容模型不足，不单凭它断言具体 iPhone 根因。

测试宿主 2.x `ad_regression/host.js`、3.x `runtime_regression/host3x/host.js` 的参数（都在游戏代码前生效，默认行为不变）：

| 参数 | 实际模型 |
| --- | --- |
| `storage_seed=<URL编码JSON对象>` | 入口前安装 fixture；下一次冷重启**去掉**这个参数 |
| `syncnumbool=all` | 同步读数字返回布尔值（非 0 为 true，0 为 false） |
| `async_storage=unavailable` / `error` / `hang` | 异步接口不存在、失败、不回调；`storage_fault_key=<键>` 可只对一个键生效 |
| `async_storage=typed` | 异步读保留原类型（“旧值可取回”那一行用） |
| `storage_info=missing` / `throw` | 拿不到键列表 |
| `missing=true/false/undefined/null/throw` | 缺键时同步读返回什么 |

“旧值读不出来”的两次运行例子（把 `Coin`、`IS_MUSIC` 换成本作实际读的键）：全 true 用 `storage_seed={"Coin":45,"IS_MUSIC":45}&syncnumbool=all&async_storage=unavailable&storage_info=missing`，全 false 用 `storage_seed={"Coin":0,"IS_MUSIC":0}&syncnumbool=all&async_storage=unavailable`。用 2.x 的 `window.__hostLog`、3.x 的 `window.__H.log` 核对故障确实命中。默认 `save_restart` 同版写后重开不能冒充这一项。

## 检查（STORAGE-01）

字段格式见[回执 v3](storage-upgrade-trace-v3.md)，从 Native 里找读存档代码的办法见[存档读取点与交付约束](startup-storage-consumer-gate.md)。要点：

- 新玩家能玩（原 23 项，证据按增量账本沿用）。
- 旧值读不出来时照样能玩：上表第二行的两次运行，覆盖最终 Native 里找到的每个存档键；`upgrade_observations.legacy_unreadable_preserved` 记其中一个键的“带默认值启动”。**首次上线、或每个上线版本都装着保护件的游戏只需要这一项**，在 trace 里写 `legacy_data.earlier_release_wrote_raw_values:false` 和依据。
- 上线过且写过原始值的游戏另外证明旧值能取回（逐键 typed 恢复，格式不变）。
- 反例：同一个 fixture 在旧包或单行改坏的包上确实让启动停住（`unreadable_stops_startup`），或旧的数值桥反例。
- `audit_final_storage.py` 是正式/轻量写包与交付三个入口共用的只读核准门禁；报告引用放在启动合同的 `native_storage_report` 或既有 `review.STORAGE-01.auto_reports`，不能换入口绕过。
- 2026-11-12 之前签发的回执（“保档 + 可见恢复页”那种证据）继续有效，不用重测；新核准不再接受那种证据。
- 平台件自测：`tests/storage-guard.test.js`、`storage-guard-negative-controls.js`、`storage-recovery.test.js`、`storage-typed-recovery.test.js`、`storage-typed-negative-controls.js`、`kit.test.js`；宿主用 `runtime_regression/tests/storage_host_profiles.cjs`。这些只证明标准件，**不替代本作真实导出包实跑，更不替代手机**。

`numeric_snapshot_encoding.v1`（把旧数值另存一份 JSON 快照、关键余额读不出来时显示 Retry）只为已经按它核准的那一款游戏保留，`numeric_snapshot_contract.py` 不改；新游戏不要采用，按本页总规则做。Music Slice v36 于 2026-11-12 获用户“iOS 已能进入”的反馈，这是该包组合修复的入场证据，不是上述阻断式保护更优、所有旧档可恢复或新版通用保护件已获真机验证的证据。案例的原始日志、逐版对照和包身份留项目，不复制到每个游戏。

## 真机与交付的边界

分别记录本地语义模型、Android 真实 TikTok、iOS 真实 TikTok、真实 IAA 和平台上传接受；禁止相互代填。正式宣称双平台可用前，两系统各需同版实际 TikTok 短路径：冷启动→PLAY→操作，冷重开保值，切后台返回；有广告时补真实完成/取消及回游戏。缺设备可以交明确待测候选，不能标双平台完整验收。已获有效同版设备证据按依赖复用。

在开发证据中记录设备/OS/TikTok/SDK/引擎版本、包 SHA、冷/热缓存、新/旧存档、发生阶段、首个异常和控制台里的 `[TikTokKit] storage` 行，不记录账号或完整用户存档。

保护件和 SaveStore 目前都只在 Node 模拟环境测过（清单里标“待真机复测”）。手机上平台到底返回什么，以真机日志为准；与本页的模型不一致时先记录事实，再改模型，不为了迁就模型给游戏加阻断。

官方依据（2026-11-11 核读）：[Cocos接入](https://developers.tiktok.com/docs/en/build-mini-games-with-cocos)、[技术环境边界](https://developers.tiktok.com/docs/en/mini-games-technical-overview)、[存储API](https://developers.tiktok.com/docs/en/mini-games-sdk-storage)。官方存储契约允许多类型数据；布尔失真是历史/受控兼容模型，不是官方承诺的 iOS 行为。
