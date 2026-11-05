# 先量后做：排版预算与页面全覆盖（Saul 2026-11-04）

Saul 2026-11-04 发来蛋壳特工队的六张图（角色奖励卡露出 WATCH AD TO CLAIM、LEGENDARY REWARDS 说明伸出金条、VIP 的 Watch 压在徽章上、Get Free 压视频图标又伸出按钮、Quick Patrol 长句跑出面板、邮件 10000 跑出金币卡），问「为什么检查过了还查不出来」，要求「从源头」解决。查下来是两个原因，本页把它们都改在做的时候：

1. **检查根本没看到那几页。** 那一轮美术检查的采集门只看 `docs/art/screens.json` 手写的 8 个页面；工程里有字或按钮的页面和弹窗有 48 个，34 个从没采集过。六张图里五张在没采集过的弹窗上（VipLayer、PatrolFastLayer、LetterLayer、RewardSkinLayer）。
2. **量字的方法太粗。** 旧检查拿节点框比节点框：字只和它的父节点比，SHRINK/CLAMP 的字不查，旁边的卡片、按钮里的图标、海报里画好的金条都不算；`dump_ui` 在 Layout 还没排完时读位置，VIP 那一行在 dump 里和截图上不在一个地方。

## 一、开工就拿到全部页面

- 第一次能采集时（英化：第 1 阶段中文原版链接起来以后，或者第一次英文导出以后）先 dump 首页，跑：
  `python3 <skills>/remake-core/scripts/audit_page_coverage.py --project <工程> --dumps <采集目录> --out <工程外>/page-coverage.json`
  它从工程的预制体和场景里列出**所有有字或按钮的页面、弹窗**（名字以 Layer、Panel、Dialog、Popup、View、Window、Page、Menu 等结尾，或者挡触摸，或者接近一屏大），对照 dump 说哪些还没采集、哪些只采了一种尺寸。这张表就是本轮美工的工作清单和采集清单，不再靠人记。
- 打不开的页面（按英化规则删掉的更多游戏、只有断网才出的提示……）写进 `docs/art/screens.json`，每条写原因，没写原因的照样算缺：
  `"not_reachable": [{"prefab": "MoreGameLayer", "why": "更多游戏入口按英化规则删了，代码不再打开"}]`
- 打开弹窗的方法：在试玩页里点真实入口最好；入口藏得深的，可以在页面里调游戏自己打开这个弹窗的函数（例如 `constants.layers.VipLayer` 那样的打开接口），弹窗里的字和状态由游戏代码填，才算数。只把预制体单独实例化出来不算：代码填的字（次数、金额、倒计时）都没有。
- `art_check.py` 有一行「有字或按钮的页面、弹窗都在两种尺寸采集过」，缺一个就不通过。它还列出**从没在任何采集里出现过的英文**（copy-table 里还在预制体上的句子，例如 PatrolFastLayer 的「Get Free」那个状态没打开过），这一项只提示：有的是代码会盖掉的占位字、被字图换掉的 Label，看一眼确认就行；确实打不开的写 `"text_not_shown": [{"text": "...", "why": "..."}]`。

## 二、做图之前先量：排版预算

带字的按钮、标题、底板、数量槽，**先量再生图**，不是生完图放进去再看放不放得下：

1. 把这一页的 Label 换成定稿英文（英化第一轮本来就先换字），导出，两种尺寸 `dump_ui`（新版 `ui_dump.js` 会先让 Label、Layout、ALWAYS Widget 排完再读位置，还记下每段字真正的宽度和对齐）。
2. 数字、次数、金额先写最长的合理值（看经济表和关卡表），放进 `docs/art/longest-text.json`：
   `{"labels": [{"path": "*/LetterLayer/*/propItem/num", "text": "99999", "why": "邮件奖励最多 5 位"}]}`
3. 跑 `python3 <skills>/remake-core/scripts/audit_text_fit.py --project <工程> --dumps <这页的采集> --plan <工程外>/text-plan.md`。表里每一行是一段字：字宽多少、它所在的底板/按钮减去同一行的图标、间距和两边留白后还剩多宽、「底板至少要」多宽。
4. 余量是负数的，这一页的图就按「底板至少要」的宽度生成（按钮按「图标宽＋间距＋完整英文宽＋两侧留白」），或者换行、缩短英文；字号不低于可读下限（[saul-art-rules.md](saul-art-rules.md) T01）。海报里要放字的金条、说明条，在海报图上量金条内宽再定字号。长句按面板内区和关闭键留位换行。
5. 生成以后接进游戏，**这一页马上**重新 dump、再跑一次 `audit_text_fit.py`（几秒），改到零发现再做下一页。每轮给试玩链接前的完整 `art_check.py` 照旧要过，它也跑这一项。

切图时每一格先写清是什么（无字卡底、角色、图标、带字按钮），见[图集切片](atlas-slice-integrity.md)；带字的图不能当卡底垫在角色后面。

## 三、`audit_text_fit.py` 查什么、报了怎么改

字的宽度用游戏自己的字体量：新 dump 用页面里量好的 `text_w`；旧 dump 用工程里的 TTF / `.fnt`。字所在的底板从 dump 里找：它所在按钮自己的图；不在按钮里就找画在它前面、盖住它中心、比它大的那张图，可见范围按 PNG 的不透明部分算。全屏的背景和弹窗遮罩下面的东西不归这一页查（下面那一页有自己的 dump）。截图里那个位置看不到这段字的颜色（被别的面板盖住、是关卡里怪物头上的数字、页面还在滑动），不报。

| 报出 | 意思 | 怎么改 |
|---|---|---|
| `text_outside_plate` | 字伸出它的卡片/按钮/面板 | 按排版预算加宽底板，或缩字号、换行；数字槽按最长值留 |
| `text_on_icon` | 字压到同一块底板上的图标、徽章 | 图标、间距、字各自留位；重算按钮可读内宽 |
| `text_on_text` | 两段字叠在一起 | 分行或拉开；同一行的字交给 Layout 排 |
| `text_off_screen` | 字有一部分跑出屏幕 | 按最窄的手机（iPhone SE）排，长句换行 |
| `text_off_band` | 字比海报图里画好的色条宽 | 先量色条内宽：缩短英文、缩字号或重画色条 |
| `text_cut` | CLAMP 把字尾裁掉了（新 dump 才报） | 加宽框、换行或缩短 |
| `words_covered` | 一张画着字的图被别的图盖住一部分，字露在外面 | 这里要无字的底图；回查切图这一格的用途 |
| `text_over_words` | Label 写在已经画着字的图上（两层字） | 去掉旧字层或换无字底图 |
| `longest_does_not_fit` | `longest-text.json` 里的最长值放不下 | 按最长值重排 |
| `unsettled_dump` | 旧版 `ui_dump.js` 在排版没跑完时采的，同一行字在 dump 里互相压着 | 用新版 `ui_dump.js` 重新采这一页 |

提示（不拦）：`tight_for_longer_values`（同样位数换成最宽的数字就放不下）、`text_on_edge`（字跨在一块大内框的边上）、位图字压图标（截图上没法按颜色确认，看图）。

## 四、这一项管不到的

- 画风、配色、字好不好看，照[美术总表](saul-art-rules.md)和看图清单。
- 节点都在、截图上却被别的图层盖住的按钮（自定义批量绘制把升级按钮盖到卡片下面、装备角标只露一条边），按[图文内区检查](local-ui-contract.md)给这类控件配像素参照；工程里登记了 `docs/art/visual-slots.json` 的，`art_check.py` 照查（合了 Codex 的「美工切片与图文内区防漏检」补丁以后才有）。
- 没打开过的状态它不知道长什么样：页面表和「没出现过的英文」把它们列出来，打开采集是做的人的事。

## 五、验证（2026-11-04，正式版简化.11.5 加本补丁）

- 蛋壳特工队第 3 轮当时的 16 个采集原样重跑 `art_check.py`：页面那一行报 34 个页面从没采集过（含 VipLayer、PatrolFastLayer、LetterLayer、RewardSkinLayer）；量字那一行报商店海报 DRAWS TO GUARANTEE 伸出金条 32px，两种尺寸都报。
- 第 4 轮修之前的采集：邮件 10000 伸出金币卡左边 14px；VIP 那一页报 `unsettled_dump`，按 Layout 的排法把那一行排好以后报「Watch 压在 rank 上，还伸出它 10px」，位置和截图一致（56.9–113.1px）；Claim 压视频图标 7px。第 3 轮签到页的 Catch Up 压视频图标、伸出按钮 7px 也自动报出，不用登记。
- 六张图逐张对应的小样例在 `remake-core/scripts/test_text_fit.py`（17 个），页面表在 `test_page_coverage.py`（6 个），`ui_dump.js` 的排版等待在 `test_ui_dump_settle.cjs`。
- 12 款游戏现有的 1209 个采集页一起跑，报出 61 条，抽看截图大多是真问题（字伸出按钮、跑出屏幕、压图标）；剩下的是小于 7px 的贴边，按图改一下或看过放过。
