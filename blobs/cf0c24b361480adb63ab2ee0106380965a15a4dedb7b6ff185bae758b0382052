# 图集切片内容检查

切片框在纹理内，只能证明坐标合法，不能证明图案完整。支持已校准的透明 frames.json（textures、frames、texture、rect）和扁平 atlas.json（条目含 image、x、y、w、h）；后者按工程 assets 内唯一 PNG 解析贴图，再交同一个主体/残片检查器。贴图缺失、同名歧义、声明帧缺失必须拒绝。其他格式须先接入适配，不能用不适用/检查0项当作内容合格。

1. 一体图标、关卡节点、按钮和单体数字使用 `single_body`；有意多部件声明角色及原因，不能一刀切删除分离装饰。冒号默认允许多轮廓；`two_marks` 明确要求两部分。
2. 在原图 alpha>64 的连通主体上计算：切片是否截断主体、是否包含相邻主体残片。默认显著部分≥max(24px,主体0.5%)，丢失≥max(24px,完整主体0.2%)即拒绝；该阈值仅为本检测的覆盖边界，不证明小于阈值的像素必然合理。
3. 同时查看输出的原图邻域红框和中性底切片。修复 rect/offset/缩放，不用遮盖残片或抹图掩盖错误，不自动改未授权画风。
4. `--dumps` 对照运行帧实际 rect/frame_size，防止清单修好但JS内置清单或场景仍用旧框。两比例验证当前/锁定/完成三态、双位数及页面操作，原始截图留项目。
5. 沉淀前用真实未修版本失败、修复版本通过，加正常图标/有意多部件正常对照；生产代码与素材SHA绑定。脚本自测 `test_atlas_slices.py` 只证明门禁校准，不代替本游戏截图。

命令：

```sh
python3 <skills>/remake-core/scripts/audit_atlas_slices.py --project <当前工程或Native目录> --dumps <当前dump目录> --out <本轮输出>
python3 <skills>/remake-core/scripts/test_atlas_slices.py
```

正式 `art_check.py` 自动调用同一检查并保留独立报告。静态连通轮廓不替代布局、叠层和审美检查。

## 固定格偏移与扁平图集短回放（2026-10-25）

出现按钮上下细线、异色条片或花叶平切时，先对照原图邻域和实际 rect；对原图完整 Alpha 主体求框，不能只在已切坏的 crop 上紧裁。共享图集须检查同来源按钮及别名，保持图案、文字、点击与业务语义。

顺序：项目候选 → 原配置/原图/真实运行旧框失败 → 完整主体和正常多部件对照通过 → 重导出并在两手机比例读取实际 SpriteFrame 与完整弹窗 → 正式沉淀。运行旧框与新配置不同必须报 runtime_rect_differs_from_manifest，不能只看 frame_size。局部可用 `--frames btn_try,btn_nothanks` 声明精确受影响帧，不记作整套图集通过；完整美工默认扫描全部适用条目。

Pippa 原工具对 atlas.json 返回 applicable=false、checked=0；适配后原 TRY OUTFIT/NO THANKS 各命中主体截断和邻排碎片。原图未改，12个按钮与 toast 别名共13框修正后，静态及48条实际帧观测通过；正常 PLAY/NEXT 及有意多部件未误报。回归：`python3 <skills>/remake-core/scripts/test_flat_atlas_adapter.py` 与现有 `test_atlas_slices.py`。实际原图和旧/新矩形固定为回归样本；项目证据留 docs/art/button-slice-review-20261025/。


## 独立源图也可能已经切坏（2026-10-26）

出现平切、横条、按钮缺边或疑似遮盖时，按“源PNG → 实际SpriteFrame → 整页合成”三层短检。独立PNG、rect在纹理内、节点在屏内，都不能证明完整；历史切图可能已丢主体像素，运行时二次裁框又可能藏残片但留下缺边。

1. 保留未修候选，拍完整页面及局部。查源PNG四边连续不透明平切、主体外邻图残片，并对照同组完整按钮。透明单体图可用 `remake-art/scripts/check_native_sprite_sources.py <Native根> <帧名...>` 辅助定位；当前仅支持Cocos2独立序列化SpriteFrame/PNG。它只报告源图疑点，平直边和多个alpha部件可能是合法设计，不直接判美术失败或自动修图。`--role background|tile|multi_body`明确不适用单体判据；`incomplete`/退出2表示缺材料或协议不支持，`needs_review`/退出1表示待对照，`no_signals`只表示未检出这些源图信号，均不认证整页美术。支持assets与普通subpackages的独立import/native布局，其他协议单列缺口；零条目不能通过。
2. 读回运行帧的rect、原始尺寸、纹理URL与资源版本；同时查动态 `new SpriteFrame`/裁框辅助函数。源PNG已缺失不能再缩框或盖住缺边，应恢复完整源或补齐同组素材。配置已改但实际仍用旧框/旧纹理，仍判未修；刷新后重新核对，不以文件哈希替代实景。
3. 按语义组核标题、品质、插画、分页、条件/价格、动作与装饰内区；检查同源弹窗与最长名称。旧版同法须检出，完整正常对照不误报，修复版两手机比例实际复查后再收尾。自然到达实景与隔离呈现回放分别标明；只固化通用方法，项目坐标和截图留项目。

工具校准采用独立合成源图：完整单体、平切边、额外残片、合法多部件、不支持布局、重名和缺图。具体游戏的帧名、数量、图像、裁框和实景结果留项目。本项不增加全游戏CI，也不替代运行SpriteFrame和整页观察。

## v7.8：所有切片都查（Ingrid's Snowball Stack 10-26 连续三轮漏）

`audit_atlas_slices.py` 以前只查 `icon_`、`node_`、`btn_`、`digit_` 开头的切片，图片字、局内棋子、投射物、障碍打进图集后一张都不查。现在其余切片按 `scope_body` 查：主体不能被切片框切断（`connected_body_cut_by_rect`），切片边上不能挂一条细的别家残片（`edge_fragment`，宽或高不到切片的 20%、贴着切片边）；字母、闪光这类自己分开的部分不算。本来就相连的不查（报告 `skipped` 里列出原因）：名字带 tile/tileset/terrain/ground/floor/wall/road/grass/water/map/bg/background/pattern/seamless/border/panel/bar/fill/line 的、九宫格/平铺的、四条边都不透明的整块图，以及 `frames.json` 里写了 `"slice_role": "tileset"` 的。贴图文件不存在的新范围切片也只列进 `skipped`。扁平 `atlas.json`（image/x/y/w/h）不再要求有 btn_/icon_/node_ 开头的条目。

校准：把 Ingrid r3 的独立 PNG（closet、caption_closet、caption_energy、caption_level、snowball 等 12 张）原样打成一张图集，报出 5 张 `edge_fragment`，正是那三轮里修的；r9 修好的同名图全过；v7.7.5 只查到 1 张（btn_play），一张都不报。Holly 的地面 tile 和天空切成 40 格的整块图集全部按 tileset 跳过，不误报。

## .plist 图集也查（v7.8 补）

TexturePacker / Cocos 的 `.plist` 图集（原版中文游戏和英化游戏大多用它）以前一张都不查。现在 `audit_atlas_slices.py --project` 会在同样的根目录里找 `.plist`，只认带 `frames` 字典和 `metadata` 的精灵图集；粒子 `.plist`（没有 frames）、`Info.plist` 之类不算，test/tests/docs/node_modules/.git/build/simulation 下的不进。`plist_atlas_adapter.py` 读 format 0～3（format 2 的 frame/rotated/sourceSize，format 3 的 textureRect/textureRotated/spriteSourceSize/aliases），贴图按 metadata 的 realTextureFileName 或 textureFileName 在 .plist 同目录找，不猜。找不到时照上面口径：普通切片列进 `skipped` 写原因，icon_/node_/btn_/digit_ 单体切片直接报错。

判定和角色不变：帧名去掉文件夹和 `.png` 后再看 icon_/btn_ 前缀、tile/bg 等名字；转过 90° 的帧（rotated）按它在贴图里实际占的 h×w 区域查切片，运行帧对比（`--dumps`）用没转过的 w×h，dump 里帧名带不带 `.png`、用 format 3 别名都能对上；`trim` 关掉的精灵按 sourceSize 对。

打包器出的图集有三处和手拼图集不同，只对 .plist 生效：

1. 间距为 0 时相邻帧的图案会贴在一起。别的帧框里的像素算那一帧的，查本帧主体时先遮掉；主体伸进没有帧占的空白区仍算被切。
2. 打包时开了 extrude（把每张图的边缘像素往外复制 1 像素）的图集，自动识别复制圈的宽度，这一圈不算丢失的主体；主体越过这一圈继续延伸，仍报 `connected_body_cut_by_rect`。
3. 打包器会把每张图紧裁到自身外框，所以图自己的闪光点、武器尖必然贴边。`edge_fragment` 只报两种：落在别的帧框里的像素，或沿切片边延伸的细长条（贴着的那条边方向长度 ≥ 厚度的 4 倍，厚度 ≤ max(3px, 切片 20%)）。

另外，按 Aseprite/拆图默认命名的 `tile000`、`tile001`……帧是动画格，照常检查，不按 tileset 名字跳过。

校准：本机 71 个不重复的 .plist 图集，共 1608 帧，全部当作在页面上显示来跑：查 1498 帧，跳过 108 帧（名字像 tile/bg 的 57 帧，四边都不透明的整块图 51 帧），报 9 帧。不加上面三条时报 190 帧，多出来的 181 帧都是误报（DessertMatch 无间距方格 20 帧、BallPopParty extrude 1 的 140 多帧、特效闪光贴边 14 帧等）。剩下 9 帧里，BallPopParty 的 3 张英文字图和指尖麻将的 backdown 是真问题（重画的图比帧框大 1 像素，描边被切掉一条）；2 帧是图上被抹空、游戏已改用单图的废帧（`empty_slice`）；2 帧是 icon_ 开头但本来就是多部件的图（暂停双竖条、放射光），属于命名规则要求声明角色的情况；1 帧是塔防英雄像素图帽尖贴边的已知误报。真工程 ReefGuard 全流程：34 个 .plist、查 209 帧、1761 条运行帧观测，其中 19 个转过的帧尺寸对上，通过。

命令和原来一样：

```sh
python3 <skills>/remake-core/scripts/audit_atlas_slices.py --project <工程> --dumps <dump目录> --out <输出>
python3 <skills>/remake-core/scripts/audit_atlas_slices.py --manifest <某个.plist> --out <输出>
cd <skills>/remake-core/scripts && python3 -m unittest test_plist_atlas
```

## 两处默认角色修正（美工补丁第三版，2026-10-31）

拿第二版补丁和 v7.8 在本机 13 个图集上对比后改的两处：

1. 名字带 `panel` 的切片不再按 tileset 跳过。PaperCutKid 的 `panel_reward`、`panel_settings` 顶部的礼盒、闪电、齿轮、星星装饰被切掉，以前因为名字带 panel 一张都不查。真正的九宫格面板仍然靠九宫格、平铺标记和"四边都不透明"跳过。
2. 扁平 `atlas.json` 里没写 `slice_role` 的条目，按名字给默认角色：icon_/node_/btn_/digit_N 按一个主体查，其余按 `scope_body` 查，和 frames.json 一样。以前适配器给每个条目都默认 single_body，BalloonRun 的 `txt_Profile_Revisit` 这类几个词分开的图片字被当成"混进别家残片"误报。

第二版补丁里"只查 dump 里显示过的切片"（displayed、edge_sliver）不用了：v7.8 的 scope_body 不要 dump 也能查全部切片，抓得更多；第二版只多抓到 panel_reward，已由上面第 1 条补上。

## 透明拼图切出独立 PNG：先定归属，再紧裁

从生成拼图取按钮、图标、标题时，先看原图确认行列和完整主体（含描边、阴影、分开的字母/图标）。同页行距常不均匀，不能直接用图宽÷列数、图高÷行数切，也不能删掉最大连通块之外的所有像素。优先单独生图。透明且按行列排列的现成拼图，使用 `python3 <skills>/remake-art/scripts/cut_sheet_frame.py sheet.png --grid 行数 列数 --cell 行号 列号 --out 新母图.png`（从 1 数起）。脚本先沿整行找清晰分隔带，再在该行找列间隔，判界使用 alpha>8，保留主体外两像素及框内原始透明值。没有唯一分隔、触边、空格就停在该帧，不硬切。连通的原画、深阴影、偏排或不透明拼图改用已核实的作者帧框或单图。保存裁切收据及母图；行列语义仍须按原图核对。拿母图和引擎实际使用的切片等比并排看四边；母图完好但游戏仍露旧字/角标时查同位置子节点和旧底图。两个独立合法元素重叠不能靠裁掉其中一个修复。

**新美术从源头少切（R4C，普查 sprite_crop_fragment 17 款）**：新生成的美术一张图只放一个主体（按钮、图标、标题、角色各自出图）。条状图和拼图只用脚本切：行列拼图用上面的 `cut_sheet_frame.py`，字宽不等的数字/字母条用 `ad-boost/scripts/art/cut_strip.py --png <条.png> --chars "<字符>" --out rects.json`；不按图宽÷格数手算框，不在图片软件里手裁。切好的图接进节点时用 `bind_art.py`，不手改宽高（见[出图和接图的两条固定做法](production-prevention.md#出图和接图的两条固定做法r4c普查-squashed_image-32-款sprite_crop_fragment-17-款)）。

验收读取实际被使用的帧。Creator 3 源工程以 package.json 的 creator.version 识别，通过 image .meta 的 sprite-frame 子项 displayName 映射独立 PNG。同名不唯一须按 UUID/路径复核。独立图检查零项或缺帧记未覆盖，不能拿 OCR 已过或图集不适用代替。已有孤立碎片标记只要求复核，不自动擦除合法多部件。背景、运行时动态图集和叠层仍需同版本实际截图。

## 生成拼图前先选取框方式

可改显示资源时，记录每格的角色、英文、页面和目标路径，例如“侧栏／外套图标含 OUTFITS”与“标题／纯文字 OUTFITS”用两个条目。同一个词、相同格数都不能代表同一个素材。出图后直接看母图核准行列，把该版母图 SHA-256 记入制作清单。切图命令加 `--source-sha256 <摘要>`，调换到另一张同规格母图就会在写文件前停止。改版母图需重新看格位。

下游能接受独立 PNG 时沿用默认透明带紧裁。下游确实固定取**这张透明母图**上的矩形时，把实际整数源框、透明间隔及目标格次写进生图要求。第一张母图到手后就运行 `cut_sheet_frame.py sheet.png --grid 行数 列数 --cell 行号 列号 --fixed-rect 左 上 右 下 --source-sha256 摘要 --out new.png`。四边从左上角数，右、下不包含。工具分别计算本格漏掉的和外格混入的 alpha>8 像素；任一非零就拒绝出片，干净时保留原固定框尺寸和框内全部透明度。允许自由导入就改用已经定位的紧裁母图；必须保留原框就重排母图留足间隔或单独出图交给原打包器。不要把旋转过的图集存储坐标、Spine 的目标贴回框或屏幕坐标当这里的源框。低透明辉光和轮廓的视觉归属仍要在原画风背景上看。

生成给多个页面共用的样式前，先列出实际绑定旧素材的 prefab/scene 和代码中动态取图的页面。相同材质、固定词与内框可以复用；不同层结构的页面分别决定停用哪层旧图。服装和武器奖励卡曾使用相同说明底图但由两个不同页面生成，只改一个页面会让另一个保留露字。修改视觉绑定时保留原按钮的交互和业务绑定。
