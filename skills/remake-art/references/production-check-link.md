# 制作与美工检查共用证据

固定英文按钮、透明切片和首次接入的风险控件共用现有配方、`visual-slots.json` 与采集结果，不另建第二套验收。按[制作与采集节奏](art-iteration-workflow.md)先由 Codex 看源图样件与实际预算做预防，再集中制作与接入；冻结候选后，用本次完整采集的代表数据做唯一正式首件核验，让适用检查共用这一轮。共享做法与输入没变时，不为不同检查器重复首件、构建或采集。

## 生产记录与真实用途

关键整图按钮、独立图标和皮肤默认单资产大图，可逐个生成；集中制作不等于拼一张小图集。只有版式稳定、每格源像素充足且切分可核时才选图集，不以省调用为由牺牲有效尺寸。固定按钮核整词拼写和底图来源；图集先核主体、描边、阴影与安全边界。继续用原制作入口联动登记：

```sh
python3 <skills>/remake-art/scripts/compose_fixed_button.py PROJECT/docs/art/claim/recipe.json PROJECT/assets/ui/claim.png --project PROJECT --asset-id claim --cases claim-ready-small claim-ready-tall
python3 <skills>/remake-art/scripts/cut_sheet_frame.py PROJECT/docs/art/source.png --grid 2 3 --cell 1 2 --out PROJECT/assets/ui/item.png --project PROJECT --asset-id item --cases inventory-small inventory-tall
```

cases 是现有状态/视口 ID，列全实际消费者。同素材同 ID 保留已登记用途，不为每页重新制作。成功才登记原料、配方、参数与输出；失败后遗留的旧文件不能冒充本次成功。生成记录不替代语义核图，裁切通过也不证明选中了正确格子。只因工具版本变化时保留旧规则来源，在当前规则下核原始输入并重放比对现有成品；尺寸、逐像素和几何仍一致就沿用，不要求重新生成，也不维护另一套历史哈希放行清单。

## 显示尺寸、分辨率和字距一次定好

源图像素、实际显示框和点击区分别确定。先从真实布局取得最大 CSS 用途，不重复乘 DPR；高清图不扩大按钮。可用 `--usage-budget`、`--final-size W H` 保留最终需求与同比输出，不提前反复执行全项目 source。先锁全部用途、最大槽位和最长文字，直接生成够大的完整原图。制作建议可留 2x 源像素余量，用户可调，实际清楚即可，不把建议当验收硬倍率。保留大原图供多个用途同比缩小复用，只压缩或缩小派生文件；禁止先缩小源文件再拿它放大，插值也不产生新细节。显示尺寸、用途或字形变化先重算预算，再制作或接入。

分辨率的权威配置为 `docs/art/clarity-policy.json`：`clarity_policy.v1`，默认 `preset:"default"`＝普通图和背景 `min_ratio:1` / `background_min_ratio:1`、`severity:"advisory"`；只有显式 `preset:"strict"` 才默认 2 / 1.5、blocking。用户也可显式声明自定倍率与级别，实际参数以工具 `--help` 为准。旧预算里的 `density:2` 等值原样保留为制作预留建议，不是验收下限；默认未达到旧预留也只提示，strict 按当前政策而非历史预留判定。倍率提示不自动触发生图；真实模糊、缺字、断边和可读性仍按原检查处理。

首次单资产预算可直接用现有入口：

```sh
python3 <skills>/remake-core/scripts/art_usage_budget.py --plan-individual --asset-id claim --purpose "Complete CLAIM button" --max-css 300 84 --reserve-ratio 2 --out OUTSIDE_PROJECT/claim-budget.json
```

该规划只计算建议原图尺寸，不生成、不重试、不阻断；普通图默认余量 2x、背景 1.5x，可用 `--reserve-ratio` 调整，均不改变验收倍率。用 `--generator-size W H` 登记实际可选尺寸；已有原图可用 `--source-image FILE --render-css W H` 核真实像素与 SHA，CSS 尺寸仍须有真实布局依据。

普通图预算示例：`{"unit":"css_px","density":1,"cases":[{"id":"home-small","css_size":[18.5,26.1]},{"id":"result-small","css_size":[24,33.9]}]}`。预算先用于出图尺寸和提示词；`art_usage_budget.py --budget FILE --expected-cases ID...` 可计算需求，`--size W H` 核选定输出。尺寸、用途或预算变化只重算相关项；未知变换先补依据，不填猜测值。

共享位图数字先确定字符全集、真实 `.fnt` 指标、字距和各槽最长串，再批量接入。字距继续按现有规则；不改字体、不减字号、不假设 SHRINK 来掩盖溢出。字体预算示例：`{"unit":"css_px","cases":[{"id":"wallet-small","text":"4444M","font_size_css":18,"available_css":[74,18],"min_font_size_css":16,"spacing_css":0,"min_gap_css":1.5}]}`。槽已扣图标和留白，字号为最终 CSS 字号。

若 source 已对登记图片做同比缩小或无损重编码，可用原入口重新核准派生结果：

```sh
python3 <skills>/remake-core/scripts/art_production.py --project PROJECT --adopt-source-resize ASSET_ID
```

它必须从原料重算并核完整像素，不能用更新摘要放行裁漏、任意放大或有损变化。

九宫格及奖励槽按[实际拼装预防](production-prevention.md#九宫格内区与奖励图标核实际拼装)接入：已核 `source_safe` 由原卡片工具映射；dump `inner` 仅是 stretch center，不能取代它。沿用适用的 `visual-slots`、`display_budget` 与稳定单 Sprite 的 `pixel_reference`，不用九宫格整图均值证明每处正常。原页面入口的 `sprite_assembly_findings` 将实际尺寸/位置超中心或外框、缺测量和归属/职责歧义保留为独立 `visual_reviews` / `visual_review_required`，完整检查进入原 `look_list`，首件也保留。Codex 查看同批原图后记实际结论；技术 passed 不替代视觉通过，不重跑同输入清需看项。名称 `btn_*` 仅是需看线索，只有现有 `button-set.caption_frames` 已核含词整钮在非交互奖励槽误用才报问题。正常九宫格、真正按钮、纯符号及有设计依据的外溢保留，不新增清单或命令。

## 首件与完整检查沿用同一判定

源图首件先由 Codex 按最窄槽、最长值和最大显示预算核画风、拼写与完整轮廓，不为这一步构建或采集。全部素材、布局、配方和接线完成并冻结后，才用本次完整采集中的短屏及必要状态数据做唯一正式首件核验；读回资源、icon/plate/caption 角色、尺寸写入者、颜色、内区、点击区和字体度量。不拿首页一张图代表全部用途，也不把全矩阵再包装成另一轮首件。

```sh
python3 <skills>/remake-core/scripts/art_check.py --project PROJECT --production-only --dumps FIRST_PIECE_DUMPS --board localize --first-piece-case VISUAL_SLOT_ID --out FRESH_OUTSIDE_PROJECT
```

局部参数只选实际首件；缺材料记 `not_run`，不强求未制作的全游戏。首件不签发完整试玩通过。完整候选冻结后，原文字、布局、图文槽、像素及其它适用检查共同读取同一批证据，一次列全问题；已经覆盖且输入没变的判定沿用，不再重跑首件入口。当前首件绑定仍包括整批生产资源与相关工具，制作中新增无关原料也会使其失效；不能凭 history 捕获等价就跳过生产/policy 依赖。因此正式核验安排在本批冻结后，不在铺量前后各跑一次，也不删真实依赖来标缓存命中。

## 失败只回到对应层

真实原料缺陷修原料，接入缺陷修绑定/布局，采集缺项补相应状态，工具错误最小修后只重算对应报告。所有已知同因修正集中后再构建与定点复验；真实变更不能完全免验。纯工具修复不重画、不构建、不重采，也不扩成无关的框架改造。

像素分析缓存位于 `.tiktok-kit/art-analysis-cache/v1`，绑定截图、节点、附件、素材和适用规则。缓存只减少同输入计算，不改变截图来源或覆盖结论；相关规则改变重算对应报告，游戏证据没变就复用原证据。缓存坏了可重算，不能因此重做游戏。`--no-analysis-cache` 只用于必要的缓存对照，不是每轮附加任务。

修复后核对实际失败项与受影响依赖，旧有效项保留。记录实际执行、沿用、未覆盖与实耗；有限样本不写成所有问题必然不会再出现。
