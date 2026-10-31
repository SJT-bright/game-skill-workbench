#!/usr/bin/env python3
"""完整美术自检：首次整套美术或整体换画风后、交用户试玩前运行。
局部按钮/单页改图按references/art-before-trial.md复查受影响整页与相关检查，不为局部结果补齐全游戏dump。
本入口先核采集材料，材料齐全才启动完整质量分析；材料缺失不代表美术失败或通过。

用户 2026-10-21：第二轮美术还会做出空白关卡卡片、蓝色占位方块、深色粗字、字超出按钮、首页中间大片空白；
用户 2026-10-23：深色粗字永久禁止（任何颜色、游戏中 HUD 和图片字也算），单独一行"深色粗字（永久禁止）"，不能标不适用；
用户 2026-10-23：所有字都是生成的图片字、和画面一体（标题一张 logo、按钮连字一张图、数字用生成的位图字），单独一行
"文字一次成图（标题logo、整张按钮、图片数字）"，两个板块都查；只有公告、玩法说明这类大段文字可以用细一点的字体；
美术的检查要放在美术制作之后，最后的测试只查玩法和功能。所以美术线的"做完"= 本脚本全部通过 + Codex 看过总览图。

先在浏览器里用 chrome_touch.py 的 dump_ui 读每个页面和弹窗（含游戏中，两种比例，写 purpose：home、result_win、
result_fail、settings、settings_sound、map、shop、skins、pause、revive、trial、league…），截图自动存进 docs/test。然后：

  python art_check.py --project <工程> [--dumps <文件夹>] [--board localize|remake] [--binding review.json] [--out <输出>]

用户 2026-10-24：screens.json 必须证明真实运行时核验；精确 screen ID 的 dump＋截图才覆盖该状态，源码盘点或相同 purpose 的另一个状态不算。
用户 2026-10-23：图片字不能被压扁/拉长（每个字单独裁边、等比缩放）、不能用 Canvas 字体画字、一页的字不能全一个颜色，
单独一行"字不压扁拉伸、字色有变化"；所有能点开的页面和弹窗列在 docs/art/screens.json，一起改、每个都要有 dump，
单独一行"全部页面和弹窗"；同组按钮的字做法/底板/颜色不一致（mixed_caption_style）、不在整套按钮里、扁平按钮、打字箭头单独一行
"同组按钮同一种风格"（用户 2026-10-23）；位置穿模（字压图标、图伸出按钮/胶囊、按钮重叠、主功能字写成按钮下的小字）单独一行，
并给每个页面出一张"穿模审查图"（overlap/，按钮、胶囊、数字的放大裁图），每次把图拼到一起都要看。只改美工（重做美工/重新设计按钮/logo/图标）也走本脚本（remake-art）。

依次运行（缺输入就是"需处理"，不跳过）：
  页面内容    audit_page_richness.py   纯色背景、单调页面、只有字的按钮、系统字体、空白面板/卡片、占位图、纯色方块、
                                       深色粗字、字超出按钮、大片空白、按钮超过40%、单调弹窗（只有字和按钮）、首页大标题和封面、选关≥6关、设置两个标签
  领奖窗      audit_claim_double.py    签到/转盘结果/礼包领奖窗：一个广告入口、「看广告双倍」默认勾上、有免费 CLAIM（Saul 2026-10-31）
  大块深色    audit_dark_area.py       每张截图：大块深色、纯黑/纯色底、大白板、大块纯色（只查负向，不设亮度下限，用户 2026-10-28）
  布局        extract_ui_layout.py + audit_ui_coverage.py   玩法区≥80%、弹窗≤60%、内容不压边框、首页设置在上角/功能按钮紧凑放在下方
  文字放得下  audit_copy_quality.py --require-runtime        字超出按钮/底图、被截断、中文残留、拼写
  开发用字    audit_dev_text.py --final                      PROTOTYPE/LOCAL PREVIEW、占位图
  清晰度      dump 里运行时的图（low_res）+ audit_image_clarity.py   两个板块、第一轮起就必须通过（用户 2026-10-23：
                                       最终验收 ART-04 才发现 22 张图不到节点 2 倍、背景 1.47 倍，那时美术已经给用户确认过）；
                                       英化原游戏没改的原图写进 docs/art/clarity-exempt.json（每条写 why），新做/重做的图不能豁免
  最终总检测不查美术（用户 2026-10-24，remake-core/references/check-stages.md）：美术只在本脚本查（英化 1.8 每轮、重塑第二轮美术、
                                       remake-art）；锁定后又改了美术，只对改动重跑本脚本，不进最终门禁
  顶部资源栏  audit_top_bar.py         货币/体力/关卡进度在首页（和地图）最上方、货币贴合题材、体力是闪电；
                                       "过关后数字变大"留到测试阶段（这里只提示）
  关卡地图    audit_level_plan.py      有关卡的游戏有地图且显示总关数；无尽游戏没有地图（关卡表本身的问题这里只提示）
  礼盒10帧    docs/modules.json gift_box.frames_dir   首页礼盒是 10 帧动画：10 张、同尺寸、≥128px、至少 8 张不同
                                       （用户 2026-10-24：只在美术阶段查，不进最终总检测）
最后生成总览图（make_contact_sheet.py）和一页 art-check.md：Codex 打开总览图，按里面的"看图清单"逐项看。

结果：<输出>/art-check.md、art-check.json（tool art_check，供门禁 ART-06）、logs/。退出码 0 全部通过，1 有需处理，2 参数错误。
v7.8（U7 补，Saul 10-30）：分析跑完还写 <工程>/.tiktok-kit/art-receipt.json（art_receipt.py：通过 pass / 失败 fail，
工程里全部图片的指纹）；缺采集时 2.4 不动旧回执，3.x 写 not_covered_3x（3.x 未覆盖，不是通过）。两个写包入口和
serve_preview.py --keep 只核对这份回执、不重跑本脚本：重塑新游戏没有回执、不是通过或图对不上就不出包、不起试玩。
v7.8（H8、H10，art_records.py）：两行不用采集就能查——和底子逐字节相同的图、模型内嵌贴图、声音（docs/art/base-assets.json，
留下的写 docs/art/base-keep.json）；新做的图要在 docs/art/generated.json（代码画的写 docs/art/script-drawn-allow.json）。
缺采集时这两行也写进报告；3.x 工程这两行没通过时回执写 fail（不是 not_covered_3x）。本机 python3 没有 numpy 时，
命令行自动改用带 numpy 的 /usr/bin/python3 重跑。
W90b：这两行只算会进包的文件（在 resources 或资源包里、被场景/预制体等按 uuid 引用、代码写了路径、认不出的；给 --build
时出现在构建里的也算）；工程里没用到的只列成「建议删掉」，不拦。
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
from pathlib import Path
import subprocess
import time
import sys

HERE = Path(__file__).resolve().parent
TIMEOUT = 600
DARK_TEXT_KINDS = {'dark_bold_text', 'dark_picture_text', 'dark_green_text', 'dark_text', 'dev_text'}
# user 2026-10-23 (both boards): every word, number and button is generated picture text in one piece with the art
ONE_PIECE_KINDS = {'spliced_button', 'typed_title', 'font_number', 'font_value_label', 'font_text', 'canvas_text',
                   'canvas_font_code'}
# user 2026-10-23: DETAILS squashed 2.89x into a button; all text on a page one colour (Hazel's teal home, orange Progress popup)
SHAPE_COLOUR_KINDS = {'squashed_text', 'squashed_picture', 'uniform_text_colour'}
# user 2026-10-23: energy "20" over the lightning icon, coin pile hanging off WATCH AD, "WATCH AD" as a caption: 穿模
# v7.8 H11 (企鹅雪道美术 v3 half a penguin, v4 tiny score) + H6 black bands on revive / result pages
HERO_HUD_KINDS = {'home_hero_unknown', 'home_hero_hidden', 'home_hero_small', 'hud_digit_small', 'hud_digit_contrast',
                  'black_edge_band'}
STYLE_KINDS = {'mixed_caption_style', 'off_style_button', 'flat_button', 'text_arrow'}   # user 2026-10-23: one style per group
OVERLAP_KINDS = {'overlap_text_picture', 'overlap_text', 'overlap_buttons', 'clip_out', 'text_outside', 'action_caption',
                 # user 2026-10-23 Daily Rewards: "100" printed as "10" over "100", day-7 car out of its card, checkerboard
                 'glyph_overlap', 'double_number', 'negative_spacing', 'font_advance', 'font_advance_rendered', 'checker_fill', 'checker_unavailable',
                 # v7.8 U11: a button over another frame (Holly v1), plain text on a busy background (Holly v2), one
                 # text drawn in two layers (剪刀达人 v26). No popup-dim opacity limit (Saul 10-31: judged by eye).
                 'overlap_button_picture', 'busy_text_background', 'stacked_text_layers'}
LOOK = [
    '【用户 2026-10-24，动态时钟字距】同帧 runtime dump 与截图齐全；逐个检查动态时钟在 Canvas/节点/Label 缩放后的相邻字形间隙，至少 2.5 CSS px；不足由位置穿模项拦截，缺视口/字体/字形证据不能跳过',
    '【永久禁止，用户 2026-10-23/28，只查负向】放大看每一段字（含游戏中 HUD 的金币/关卡数字、面板里的说明和状态字、图片字）：没有深色/近黑填充的字，尤其深色粗字——不管什么颜色（深青、深绿、藏青、深蓝灰、深棕、深灰、黑），深色只能出现在描边/阴影里；没有特别密集的字（字距/行距过小、一块区域塞满字）；没有特别细的字（细线字、发丝描边，手机上看不清）；字没有压在复杂底图上看不清；没有"HOME SCREEN OPEN""MISSIONS 2/3 RESOLVED"这类状态字',
    '普通游戏页面（含游戏中）都有画出来的背景，没有大片纯色/大白底；已核来源和实际帧的完整官方加载/重试页按 cocos-loading-screen.md 的中性官方样式检查，不套游戏主题图片字规则',
    '【用户 2026-10-28，画风只查负向】画风按启动包 ART_DIRECTION，不按明亮/Q版/糖果色/光泽/华丽与否评判，也不看亮度够不够；只看有没有禁止项：大面积深色、纯黑/纯色底、大白板、单色图标、刺眼的整屏高亮、无层次平涂、图片模糊、按钮/文字被遮挡或穿模',
    '首页：有大标题和封面画面（主角/场景），按钮加起来不超过屏幕 40%，中间没有大片空白；货币在屏幕最上方（不在中间），设置在左上或右上角，主角中部左右各有真实功能入口；PLAY下方所有行合计最多5个，图标沿用固定两倍尺寸，不重复翻倍',
    '没有空白卡片、蓝色/灰色占位方块、大块灰色锁定块；选关页一屏至少 6 关，每关有编号、星星和状态',
    '按钮都有底板；没有纯色方块按钮、没有无层次平涂的扁平色块按钮、没有近黑/藏青/深灰的特粗字；字不超出按钮、不被遮挡',
    '没有单色图标（黑色线框/剪影、整页只有黑白灰），图标下的小字不压图标',
    '【重点，用户 2026-10-23】所有字都是生成的图片字、和画面一体（正例：THE COLLECTION 收藏页；反例：Scissors Master 首页）：游戏大标题是一张按画风一次生成的风格化 logo（不打字、不在底板上拼字母，副标题也在 logo 图里）；每个按钮连同上面的风格化文字一次生成成一整张图（PLAY、VIDEO +50、USE CLASSIC KIT、COMMON/RARE 标签都是整图），不是"生成的底板＋字体字/另一张字图"；金币、体力、关卡、价格、百分比等数字用按画风生成的数字图做成位图字体；页面文字、栏目名、物品名、任务名都是 GPT 图片字；只有公告、玩法说明这类大段文字可以用细一点的字体；没有深绿/深青色字',
    '【用户 2026-10-23】放大看每个图片字：没有被压扁或拉长的字（反例：DETAILS 被压扁 2.89 倍、SKINS/DAILY 1.80 倍）——每个字单独裁到可见边缘、按原比例缩放，放不下就改按钮尺寸或重新生成；不是用 Canvas 字体画出来的字',
    '【用户 2026-10-23】一页的字不全是一个颜色：标题、按钮字、数字、标签不是全一个颜色（反例：Hazel\'s Shelf Scramble 首页标题、PLAY、数字全是青色；Your Progress 弹窗所有字都是同一种橙黄＋棕描边）；具体颜色和字形按启动包画风，不另加花体/装饰字要求',
    '【用户 2026-10-23】docs/art/screens.json 里每个能点开的页面和弹窗都看过、风格一致：没有大白板、没有空背景（灰底/纯色底）、没有和整体配色不搭的颜色',
    '【用户 2026-10-23，穿模审查】打开 overlap/ 里的穿模审查图，放大看每个按钮、资源胶囊、数字：字没有压在图标上（反例：体力"20"压在闪电图标上、还是细字体）、图没有伸出按钮/胶囊（反例：WATCH AD 左边一堆金币伸出按钮）、按钮之间不重叠；主要功能字（WATCH AD、PLAY、CLAIM）在生成的按钮上，按钮下的小字只做解释说明且也是图片字；每次把图拼到一起都要这样看一遍',
    '【用户 2026-10-24，图内装饰遮挡】每个弹窗关闭/返回键都要连同父面板贴图一起看：没有盖住烘焙在面板里的徽章、星章、贴纸或边扣；节点矩形无交叠不代表 SpriteFrame 内部无装饰。把组合截图和精确节点路径记入 docs/art/overlap-review.md',
    '【用户 2026-10-23/24，数字叠印与字距】放大看每个数字，尤其三位数、分隔符和最大值（100、150、200、300、1,250、0:14、00:59:59）：数字之间不重叠、没有"10"叠在"100"上这种印两遍的情况；固定数字和图标/底板一张图，会变的数字用一个位图字体 Label，`.fnt` 每字 xadvance >= xoffset + width + max(2px, 0.1 × lineHeight)，且在两种手机比例实看描边之间留有背景缝隙；不手摆数字图、不叠第二个 Label、不用负字距；卡片奖励图在卡片内且未拉长，卡片底是真画面而非假透明棋盘格',
    '【用户 2026-10-23】道具数量、体力、金币、关卡这些和闯关有关的东西：边框/胶囊、按钮、收集功能键的图案都是生成的图；会变的数字单独生成数字图做成位图字体，不用原生字体',
    '【用户 2026-10-23】同一组按钮（比如首页一排功能键）放在一起看：按钮和下面的字是同一种做法（都烘焙在图标图里，或都用同一种底板＋图片字）、同一种底板、同一种字形和颜色；不能有的是白底条、有的是蓝底条、有的是打字、有的是云朵底板＋打字（反例：LEVELS/SOUVENIRS/SETTINGS/HOME SCREEN +2/PROFILE REVISIT +2 五个键四种风格）',
    '按钮是一整套：主按钮、图标按钮、左右箭头、关闭、返回都同一种材质边框，没有扁平色块、没有打出来的"<"">""X"',
    '面板/弹窗里不空，内容在边框内框里；没有 LOCAL PREVIEW 这类开发用字；每个弹窗都有生成的插图（礼物/宝箱、角色、带游戏图标的手机、奖励物品＋货币图标）和图片字标题，不是浅色平板上只有字和三个扁平按钮（反例：Home screen reward 弹窗）',
    '所有页面风格统一，新做的图和原有的图（英化）或整套新图（重塑）看起来是一套；能用生成图的地方都用生成图，游戏里画质差、无层次平涂、用字体画出来的图都已按画风重新生成替换',
    '顶部资源栏：在最上方、不是深色整条，体力是闪电、货币图标贴合题材（海底→珍珠），数字看得清；右上角给平台胶囊留空',
    '关卡地图（有关卡的游戏，70 关或更多）：显示总关数，奖励关有礼物/宝箱标记，每 10 关（总关数内10、20……整十关；尾章不额外增加）的限定关是大号皇冠/宝箱节点并露出奖励（限定皮肤剪影或一堆金币；限定皮肤可以只在最后一个限定关，也可以每个限定关一款，用户 2026-10-24）',
    '【用户 2026-10-24，只在美术阶段查】首页礼盒：10 帧动画连起来看是一个完整的动作（晃动/盖子弹起/闪光），每帧同一画风、同一位置和大小，不闪不跳',
]


def run(name, args, logs):
    from check_runner import run_tool
    return run_tool(name, args, logs, HERE, TIMEOUT)


def recorded_frame_dirs(dumps):
    """Frame folders saved by chrome_touch.py --record (<out>/frames/NNNNN_TTTTTTTms.jpg) under the dump folder."""
    return sorted({p.parent for p in Path(dumps).rglob('*.jpg') if p.parent.name == 'frames'})


def first_json(text):
    start = text.find('{')
    if start < 0:
        return {}
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except ValueError:
        return {}


def tree_fingerprint(root):
    """Assets of the build the art check looked at (so a later art change shows up as a stale check)."""
    files = {}
    for p in sorted((root / 'assets').rglob('*')):
        if p.is_file() and p.suffix != '.meta':
            files[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def screen_viewport_gaps(screens, viewports, observed):
    """Return exact (screen id, viewport width, viewport height) combinations not dumped.

    `observed` contains only real dumps whose same-frame screenshots exist. This prevents one
    convenient page or viewport from standing in for the full visual review matrix.
    """
    expected = set()
    for screen in screens:
        identity = str(screen.get('id') or '').strip()
        if not identity:
            continue
        for viewport in viewports:
            try:
                width, height = int(viewport['width']), int(viewport['height'])
            except (KeyError, TypeError, ValueError):
                continue
            expected.add((identity, width, height))
    return sorted(expected - set(observed))


def capture_inventory(project, dumps):
    """Cheap prerequisite check, not a visual verdict or runtime authenticity check."""
    errors=[];observed=set();kinds=set();records=[];shots=set()
    dump_files=sorted(dumps.rglob('*ui-dump-*.json')) if dumps.is_dir() else []
    if not dump_files:errors.append('没有运行页面dump；先采集本轮页面，不能以源码清单代替')
    try:
        manifest=json.loads((project/'docs/art/screens.json').read_text(encoding='utf-8-sig'))
        if not isinstance(manifest,dict):raise ValueError('expected object')
    except (OSError,ValueError) as exc:
        return {'ready':False,'errors':errors+['无有效docs/art/screens.json: '+str(exc)],'dump_files':dump_files,'shots':[], 'records':[], 'observed':[], 'listed':[], 'viewports':[]}
    listed=manifest.get('screens');viewports=manifest.get('required_viewports')
    if manifest.get('runtime_verified') is not True:errors.append('页面清单尚未完成运行核对')
    if not isinstance(listed,list) or not listed:
        errors.append('页面清单为空或格式错误');listed=[]
    valid=[];ids=set()
    for row in listed:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'].strip() or not (row.get('name') or row.get('purpose')):
            errors.append('页面项缺稳定id或名称/用途');continue
        if row['id'] in ids:errors.append('重复页面id: '+row['id'])
        ids.add(row['id']);valid.append(row)
    sizes=set();valid_vp=[]
    for vp in viewports if isinstance(viewports,list) else []:
        if not isinstance(vp,dict) or not str(vp.get('name') or '').strip() or any(type(vp.get(k)) is not int or vp[k]<=0 for k in ('width','height')):
            errors.append('视口须有名称与正整数CSS宽高');continue
        size=(vp['width'],vp['height'])
        if size in sizes:errors.append('重复视口尺寸: %sx%s'%size)
        sizes.add(size);valid_vp.append(vp)
    if len(sizes)<2:errors.append('至少需要两种不同手机尺寸')
    for f in dump_files:
        try:
            data=json.loads(f.read_text(encoding='utf-8'))
            if not isinstance(data,dict):raise ValueError('dump must be object')
            identity=data.get('screen');vp=data.get('viewport')
            if not isinstance(identity,str) or not identity or not isinstance(vp,dict) or any(type(vp.get(k)) is not int or vp[k]<=0 for k in ('width','height')):
                raise ValueError('missing screen/CSS viewport')
            shot=Path(data.get('screenshot') or f.name.replace('-ui-dump-','-ui-').rsplit('.',1)[0]+'.png')
            if not shot.is_absolute():shot=f.parent/shot
            if not shot.is_file():raise ValueError('same-frame screenshot missing: '+str(shot))
            observed.add((identity,vp['width'],vp['height']));kinds.add(data.get('kind'));shots.add(shot.resolve());records.append(data)
        except (OSError,ValueError,TypeError) as exc:errors.append(str(f)+': '+str(exc))
    if 'gameplay' not in kinds:errors.append('缺游戏中kind=gameplay的有效采集')
    gaps=screen_viewport_gaps(valid,valid_vp,observed)
    errors.extend('缺采集: %s@%sx%s'%gap for gap in gaps)
    return {'ready':not errors,'errors':errors,'dump_files':dump_files,'shots':sorted(shots), 'records':records,'observed':sorted(observed),'listed':valid,'viewports':valid_vp}


def fixed_text_inventory_findings(page_report):
    """Find visible fixed words/numbers still rendered by runtime fonts in any actual dump."""
    findings = []
    for page in page_report.get('pages', []):
        screen = page.get('screen') or page.get('file') or 'unknown screen'
        for problem in page.get('problems', []):
            kind = str(problem).split(':', 1)[0]
            if kind in {'font_text', 'font_number', 'font_value_label'}:
                findings.append('%s: %s' % (screen, str(problem)[:180]))
    return findings


def visible_label_counts(dump_files, project):
    """Count visible runtime labels and separate justified dynamic/long explanatory copy."""
    try:
        runtime = json.loads((project / 'docs' / 'text' / 'runtime-text.json').read_text(encoding='utf-8-sig'))
        patterns = [str(x['path']) for x in runtime.get('labels', [])
                    if isinstance(x, dict) and x.get('path') and str(x.get('why', '')).strip()]
    except (OSError, ValueError, AttributeError, TypeError):
        patterns = []
    total = dynamic = long_copy = 0
    for dump_file in dump_files:
        try:
            data = json.loads(dump_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for node in data.get('nodes', []):
            comps = node.get('comps') or {}
            label = comps.get('label') or comps.get('richtext')
            value = str((label or {}).get('string') or '').strip()
            if not value or float(node.get('opacity', 1) or 0) <= 0:
                continue
            total += 1
            path = str(node.get('path') or '')
            if any(fnmatch.fnmatch(path, glob) or fnmatch.fnmatch(path, '*/' + glob) for glob in patterns):
                dynamic += 1
            elif len(value) > 40:
                long_copy += 1
    return total, dynamic, long_copy


def overlap_sheets(dump_files, out):
    """Zoomed composite crops of buttons, capsules/counters and numbers for 穿模 review.

    Include nearby parent-panel art around buttons, and the full backing capsule around counters. User 2026-10-24:
    a close button covered an ornament baked into its parent SpriteFrame, which node rectangles cannot see.
    The target node's own box is outlined in magenta. Returns the sheet paths.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return []
    folder = out / 'overlap'
    folder.mkdir(parents=True, exist_ok=True)
    made = []
    for k, f in enumerate(dump_files):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        shot = f.parent / (d.get('screenshot') or f.name.replace('-ui-dump-', '-ui-').rsplit('.', 1)[0] + '.png')
        if not shot.is_file():
            continue
        nodes = [n for n in d.get('nodes', []) if n.get('opacity', 1) > 0.05 and n.get('rect')]
        by_path = {n.get('path'): n for n in nodes}
        def a_(n):
            return n['rect'][2] * n['rect'][3]
        pick = []
        for n in nodes:
            c = n.get('comps', {})
            holder = 'sprite' in c and a_(n) < 0.06 and any(m is not n and m['path'].startswith(n['path'] + '/') for m in nodes)
            number = any(ch.isdigit() for ch in str((c.get('label') or {}).get('string', '')))
            if 0.0008 < a_(n) < 0.5 and ('button' in c or holder or number):
                if not any(n['path'].startswith(q['path'] + '/') for q in pick):
                    pick.append(n)
        if not pick:
            continue
        with Image.open(shot) as im:
            im = im.convert('RGB')
            W, H = im.size
            cells = []
            for n in pick[:24]:
                r = n.get('screen') or n['rect']
                c = n.get('comps', {})
                path = n.get('path', '')
                parent_path = path.rsplit('/', 1)[0] if '/' in path else ''
                parent = by_path.get(parent_path)
                siblings = [m for m in nodes if parent_path and m.get('path', '').rsplit('/', 1)[0] == parent_path and m is not n]
                backdrops = [m for m in siblings if m.get('comps', {}).get('sprite', {}).get('frame') in ('panel', 'panel_clear', 'card', 'capsule')]
                number = any(ch.isdigit() for ch in str((c.get('label') or {}).get('string', '')))
                if number and backdrops:
                    # Show the whole plate behind a changing string; its internal icon/free-text zones matter.
                    backdrop = max(backdrops, key=lambda m: (m.get('screen') or m['rect'])[2] * (m.get('screen') or m['rect'])[3])
                    r = backdrop.get('screen') or backdrop['rect']
                    mx, my = r[2] * 0.08, r[3] * 0.08
                else:
                    mx, my = r[2] * 0.25, r[3] * 0.25
                    if 'button' in c and parent:
                        # Keep the nearby parent art visible, especially corner badges under close controls.
                        pr = parent.get('screen') or parent['rect']
                        mx = max(mx, pr[2] * 0.18)
                        my = max(my, pr[3] * 0.12)
                box = (int(max(0, r[0] - mx) * W), int(max(0, r[1] - my) * H), int(min(1, r[0] + r[2] + mx) * W), int(min(1, r[1] + r[3] + my) * H))
                if box[2] - box[0] < 4 or box[3] - box[1] < 4:
                    continue
                crop = im.crop(box)
                ImageDraw.Draw(crop).rectangle([int(r[0] * W) - box[0], int(r[1] * H) - box[1], int((r[0] + r[2]) * W) - box[0] - 1,
                                                int((r[1] + r[3]) * H) - box[1] - 1], outline=(255, 0, 160))   # the node's own box
                scale = min(330 / crop.width, 150 / crop.height)
                cells.append((n['path'].split('/')[-1][:28], crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))))))
        if not cells:
            continue
        cols = 4
        rows_ = (len(cells) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 340, rows_ * 175), (235, 235, 235))
        dr = ImageDraw.Draw(sheet)
        for i, (name, c) in enumerate(cells):
            x, y = (i % cols) * 340 + 5, (i // cols) * 175 + 5
            sheet.paste(c, (x, y))
            dr.text((x, y + 155), name, fill=(20, 20, 20))
        target = folder / ('%02d-%s.png' % (k, str(d.get('screen') or f.stem)[:40].replace('/', '_')))
        sheet.save(target)
        made.append(target)
    return made


def gift_box_row(proj):
    """(title, ok, detail): the 10-frame home gift box declared in docs/modules.json (user 2026-10-24: art stage only)."""
    title = '礼盒10帧动画（首页礼盒）'
    f = proj / 'docs' / 'modules.json'
    if not f.is_file():
        return title, None, '没有 docs/modules.json：设计关（design_check.py）先定内置板块，再做礼盒 10 帧'
    try:
        dec = json.loads(f.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        return title, False, 'docs/modules.json 读不了：%s' % exc
    gb = dec.get('gift_box') if isinstance(dec, dict) and isinstance(dec.get('gift_box'), dict) else {}
    from audit_game_modules import gift_frames
    ok, detail = gift_frames(proj, gb.get('frames_dir'))
    return title, ok, detail


H8_TITLE = '底子原图原声不留（H8：和底子逐字节相同的图、模型内嵌贴图、声音）'
H10_TITLE = '新做的图都有生成记录（H10：代码画的按钮和数字不算图片字）'


def base_generated_rows(proj, board, build=None):
    """v7.8 H8 + H10 (art_records.py): static, needs no page capture. -> ([(title, ok, detail, log)], summary)."""
    try:
        import art_records
        result = art_records.check(proj, board, build=build)
    except Exception as exc:  # noqa: BLE001 - a broken check never passes
        return [(H8_TITLE, False, '查不了：%r' % exc, ''), (H10_TITLE, False, '查不了：%r' % exc, '')], {'error': repr(exc)}
    b, g = result['base'], result['generated']
    return [(H8_TITLE, b['ok'], b['message'], art_records.BASE_FILE.as_posix()),
            (H10_TITLE, g['ok'], g['message'], art_records.GENERATED_FILE.as_posix())], art_records.summary(result)


def numpy_python():
    """v7.8: art_check's checkers need numpy + Pillow (checkerboard, busy background). Homebrew's python3 has no numpy
    (rows then said checker_unavailable), so the command line re-runs itself with a Python that has both (macOS
    /usr/bin/python3). None when this Python has them, or when no other Python does (the old message stays)."""
    import importlib.util
    import os
    import shutil
    if importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL'):
        return None
    if os.environ.get('ART_CHECK_REEXEC'):
        return None
    here = os.path.realpath(sys.executable)
    for cand in ('/usr/bin/python3', shutil.which('python3'), '/usr/local/bin/python3', '/opt/homebrew/bin/python3'):
        if not cand or not os.path.exists(cand) or os.path.realpath(cand) == here:
            continue
        try:
            ok = subprocess.run([cand, '-c', 'import numpy, PIL'], capture_output=True, timeout=60).returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        if ok:
            return cand
    return None


def main():
    started = time.monotonic()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--ui-contract', type=Path, help='opt-in affected-state runtime UI contract; runs no full-art/CI checks')
    ap.add_argument('--ui-native', type=Path, help='exact Native tree for the local UI contract')
    ap.add_argument('--ui-runner', help='Skill-reviewed fixed runner registry key')
    ap.add_argument('--ui-variant', default='final')
    ap.add_argument('--ui-calibrate', action='store_true', help='execute known-bad and single-defect controls with same checker')
    ap.add_argument('--dumps', type=Path, help='folder with chrome_touch dump_ui files and screenshots (default <project>/docs/test)')
    ap.add_argument('--loading-only', action='store_true', help='affected official loading presentation; never a full ART-06 pass')
    ap.add_argument('--board', choices=['localize', 'remake'])
    ap.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied into the report (ART-06)')
    ap.add_argument('--build', type=Path, help='v7.8 H8/H10: build folder or package ZIP; files found in it count as shipped')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    if a.loading_only:
        if a.ui_contract or a.ui_native or a.ui_runner or a.ui_calibrate:
            ap.error('--loading-only cannot be combined with UI contract mode')
        target = a.out or a.project / 'docs/art/loading-review'
        cmd = [sys.executable, '-B', str(HERE / 'audit_official_loading.py'), '--project', str(a.project),
               '--dumps', str(a.dumps or a.project / 'docs/test'), '--out', str(target / 'loading-presentation.json')]
        if a.binding:
            cmd += ['--binding', str(a.binding)]
        return subprocess.call(cmd)
    if a.ui_contract:
        if not (a.ui_native and a.ui_runner and a.out):
            ap.error('--ui-contract requires --ui-native, --ui-runner and fresh --out')
        cmd = [sys.executable, '-B', str(HERE / 'audit_ui_contract.py'), '--project', str(a.project),
               '--native', str(a.ui_native), '--contract', str(a.ui_contract), '--runner', a.ui_runner,
               '--variant', a.ui_variant, '--out', str(a.out)]
        if a.ui_calibrate: cmd.append('--calibrate')
        return subprocess.call(cmd)
    if a.ui_native or a.ui_runner or a.ui_calibrate:
        ap.error('local UI probe flags require --ui-contract')
    proj = a.project.resolve()
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    board_file = proj / 'docs' / 'board.txt'
    recorded = board_file.read_text(encoding='utf-8').strip().lower() if board_file.is_file() else ''
    board = a.board or (recorded if recorded in ('localize', 'remake') else 'remake')
    style_file = proj / 'docs' / 'art-style.txt'
    remake_art = board == 'remake' or (style_file.is_file() and style_file.read_text(encoding='utf-8').strip().lower() == 'remake')
    dumps = (a.dumps or proj / 'docs' / 'test').resolve()
    out = (a.out or proj.parent / (proj.name + '-artcheck') / dt.datetime.now().strftime('%Y%m%d-%H%M%S')).resolve()
    if out.is_relative_to(proj):
        ap.error('output must be outside the project')
    if out.exists() and any(out.iterdir()):
        ap.error('output folder exists and is not empty: %s' % out)
    logs = out / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    rows = []

    def add(title, ok, detail, log=''):
        rows.append({'check': title, 'status': '通过' if ok is True else ('提示' if ok is None else '需处理'), 'detail': detail, 'log': log})

    inventory = capture_inventory(proj, dumps)
    (out/'input-inventory.json').write_text(json.dumps({k:v for k,v in inventory.items() if k not in ('records','dump_files','shots')},ensure_ascii=False,indent=2)+'\n')
    # v7.8 H8 / H10: static rows, also when the page capture is missing
    static_rows, static_summary = base_generated_rows(proj, board, a.build)
    static_failed = [r for r in static_rows if r[1] is False]
    if not inventory['ready']:
        report={'tool':'art_check','schema':1,'passed':False,'status':'blocked_inputs','checked':0,'static_checked':len(static_rows),
                'failed':len(inventory['errors'])+len(static_failed),'input_errors':inventory['errors'],'total_elapsed_seconds':round(time.monotonic()-started,6),
                'rows':[{'check':'采集材料','status':'缺采集','detail':e} for e in inventory['errors']]+
                       [{'check':t,'status':'通过' if ok is True else ('提示' if ok is None else '需处理'),'detail':d,'log':lg} for t,ok,d,lg in static_rows],
                'base_generated':static_summary,'time':dt.datetime.now().isoformat(timespec='seconds')}
        (out/'art-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        md='# 美术检查：先补采集\n\n本轮尚未运行美术分析，不能判定美术通过或失败。补齐以下具体材料后再运行：\n\n'+'\n'.join('- '+e for e in inventory['errors'])+'\n'
        md+='\n不用采集就能查的两行（v7.8 H8、H10）：\n\n'+'\n'.join('- %s：%s　%s'%(t,'通过' if ok is True else ('提示' if ok is None else '需处理'),d) for t,ok,d,_ in static_rows)+'\n'
        # v7.8 U7（补）: Cocos 2.4 keeps its earlier receipt (missing inputs are no verdict); a 3.x project cannot be
        # captured by ui_dump yet, so its receipt records the images as "3.x 未覆盖" (never a pass) -- unless H8 / H10
        # already failed: then the receipt is a fail (3.x remakes such as 企鹅雪道 would otherwise pass the writers).
        import art_receipt
        if art_receipt.engine(proj) == 3:
            if static_failed:
                art_receipt.write(proj,'fail',report,out/'art-check.json',
                                  note='3.x 未覆盖页面检查；不用采集的 H8/H10 没通过：'+'；'.join(r[0] for r in static_failed))
                md+='\n美术回执：%s（fail：H8/H10 没通过；重塑新游戏不出包）\n'%art_receipt.receipt_path(proj)
            else:
                receipt=art_receipt.not_covered_3x(proj,report,out/'art-check.json')
                md+='\n美术回执：%s（3.x 未覆盖，不是通过；写包入口照样放行但会标出）\n'%art_receipt.receipt_path(proj)
        (out/'art-check.md').write_text(md,encoding='utf-8');print(md);return 1
    from audit_no_social_features import audit as audit_no_social
    social=audit_no_social(proj,dumps=a.dumps)
    if not social['passed']:
        print(json.dumps(social,ensure_ascii=False,indent=2));return 2
    dump_files=inventory['dump_files'];shots=inventory['shots']
    kinds={record.get('kind') for record in inventory['records']}
    add('读到的页面',True,'%d 个dump、%d张同帧截图；输入矩阵齐全，不代表美术通过'%(len(dump_files),len(shots)))
    binding=['--binding',a.binding] if a.binding else []

    # Rectangle-in-texture checks miss neighbour fragments and clipped silhouettes.
    code, text = run('audit_atlas_slices.py', ['--project', proj, '--dumps', dumps, '--out', out / 'atlas_slices'], logs)
    try:
        atlas = json.loads((out / 'atlas_slices' / 'report.json').read_text(encoding='utf-8'))
        detail = '检查 %d 个切片、%d 条实际帧观测' % (atlas.get('checked', 0), atlas.get('runtime_observations', 0))
        if atlas.get('issues'):
            detail += '；' + '；'.join(str(x.get('frame','')) + ':' + x['kind'] for x in atlas['issues'][:10])
        applicable = atlas.get('applicable', True)
        add('图集裁切完整性（主体不截断、不混入相邻图、运行帧一致）',
            (code == 0 and atlas.get('passed') is True) if applicable else None,
            detail if applicable else '未发现受支持的 frames.json 透明图集；其他格式需接入适配器，本项未对其作通过判定', 'atlas_slices/report.json')
    except (OSError, ValueError, TypeError):
        add('图集裁切完整性（主体不截断、不混入相邻图、运行帧一致）', False, text.strip()[-400:], 'atlas_slices')

    # Standalone PNGs can contain adjacent-sheet remnants; atlas manifests do not cover them.
    code, text = run('../../remake-art/scripts/check_native_sprite_sources.py',
                     [proj, '--dumps', dumps, '--out', out / 'sprite_sources.json'], logs)
    source = first_json(text)
    source_ok = code == 0 and source.get('status') == 'no_signals' and source.get('checked', 0) > 0
    add('独立透明UI源图（残片、安全边与实际帧清点）', source_ok,
        '检查 %s 项；%s；信号须结合源图及实景复核，非整页验收' % (source.get('checked', 0), source.get('status', 'tool_error')),
        'sprite_sources.json')

    code, text = run('audit_page_richness.py', ['--project', proj, '--dumps', dumps, '--out', out / 'page_richness.json', *binding], logs)
    j = first_json(text)
    found = '；'.join('%s：%s' % (x.get('screen') or '缺页面', p[:90]) for x in j.get('found', []) for p in x.get('problems', [])[:2])[:900]
    add('页面内容与背景', code == 0, found or '通过（%s 个页面）' % j.get('checked', 0), 'page_richness.json')
    # v7.8 (Saul 10-31, W100): check-in / wheel result / gift-pack claim windows: one ad entry, a 「看广告双倍」 box
    # that starts ticked, a free CLAIM
    code, text = run('audit_claim_double.py', ['--project', proj, '--dumps', dumps, '--out', out / 'claim_double.json'], logs)
    j = first_json(text)
    add('领奖窗看广告双倍（签到/转盘结果/礼包：一个默认勾上的勾选框、有免费 CLAIM）', code == 0,
        '；'.join(p[:120] for p in j.get('problems', []))[:700] or '通过（%s 个领奖窗）' % j.get('screens', 0), 'claim_double.json')
    # user 2026-10-23: dark bold text is permanently banned (any hue, HUD and picture text too): its own row, never waived
    dark = []
    try:
        rep = json.loads((out / 'page_richness.json').read_text(encoding='utf-8'))
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.split(':', 1)[0] in DARK_TEXT_KINDS:
                    dark.append('%s：%s' % (pg.get('screen') or pg.get('file') or '?', prob[:80]))
        dark_ok = bool(rep.get('pages')) and not any(pg.get('stats', {}).get('official_loading') is False for pg in rep.get('pages', []))
    except (OSError, ValueError, AttributeError):
        dark_ok = False
    add('深色粗字（永久禁止）', dark_ok and not dark, '；'.join(dark[:6])[:700] if dark else
        ('通过：没有深色粗字/深色图片字/状态字' if dark_ok else '没有页面报告：先 dump 全部页面（含游戏中 HUD）'), 'page_richness.json')
    solid_text = []
    solid_unavailable = []
    if dark_ok:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.startswith('dark_solid_text_backplate:'):
                    solid_text.append('%s: %s' % (pg.get('screen') or '?', prob))
                if prob.startswith(('no_screenshot:', 'checker_unavailable:')):
                    solid_unavailable.append(prob)
    add('文字与数字后深色实心底块（禁止）', dark_ok and not solid_text and not solid_unavailable,
        '；'.join((solid_text + solid_unavailable)[:8])[:900] if solid_text or solid_unavailable else
        ('通过：实际文字周围未检出深色实心 UI 填充；仍须检查生成贴图 Alpha 与合成图' if dark_ok else '缺实际页面截图与文字采集'), 'page_richness.json')
    # user 2026-10-29 (冲鸭小巴 "数据后面有纯色背景的在skill也要限制住", 坦克 blue box behind coins, 人鱼逃脱 blue strip behind
    # "LEVEL 1 • +10 PEARLS"): no flat colour box of ANY colour behind level/score/currency values
    flat_plate = []
    if dark_ok:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.startswith('flat_value_plate:'):
                    flat_plate.append('%s: %s' % (pg.get('screen') or '?', prob[:120]))
    add('数据后面的纯色底板（任何颜色都禁止）', dark_ok and not flat_plate, '；'.join(flat_plate[:6])[:700] if flat_plate else
        ('通过：等级、分数、货币数字后面没有纯色方块；底板都是生成的图' if dark_ok else '缺实际页面截图与文字采集'),
        'page_richness.json')
    one = []
    try:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.split(':', 1)[0] in ONE_PIECE_KINDS:
                    one.append('%s：%s' % (pg.get('screen') or pg.get('file') or '?', prob[:80]))
    except (NameError, AttributeError):
        pass
    try:
        one += ['工程代码：%s' % p_[:90] for p_ in rep.get('setup', []) if p_.split(':', 1)[0] in ONE_PIECE_KINDS]
    except (NameError, AttributeError):
        pass
    add('文字一次成图（标题logo、整张按钮、图片数字）', dark_ok and not one, '；'.join(one[:6])[:700] if one else
        ('通过：标题是 logo 图、按钮字和按钮一张图、数字是生成的位图字、没有用 Canvas 字体画字' if dark_ok else '没有页面报告：先 dump 全部页面'),
        'page_richness.json')
    # user (Codex 美工调查 2026-10-30, A02/A11): flashes when tapping, paging, changing the volume or clearing tiles
    # ("这个问题必须沉淀进检查的skill，出现很多次了很多游戏都有") are invisible on still screenshots. Every art round
    # records those actions with chrome_touch.py --record (frames/ next to the dumps) and runs audit_frame_glitches.py.
    frame_dirs = recorded_frame_dirs(dumps)
    glitches = []
    for index, frame_dir in enumerate(frame_dirs[:12]):
        g_out = out / 'frame_glitches' / ('%02d' % index)
        code_g, _ = run('audit_frame_glitches.py', [frame_dir, '--out-dir', g_out, '--report', g_out / 'report.json'], logs)
        if code_g != 0:
            glitches.append('%s：%s' % (frame_dir.parent.name, '有闪屏/空帧，证据见 %s' % g_out if code_g == 1 else '工具出错 %d' % code_g))
    add('动态闪屏（录屏：点按钮、开关弹窗、调音量、局内消除）', bool(frame_dirs) and not glitches,
        '；'.join(glitches[:6]) if glitches else (
            '检查 %d 段录屏，没有闪黑、闪白、空帧或闪烁' % len(frame_dirs) if frame_dirs else
            '没有录屏帧：用 chrome_touch.py --record 录首页点按钮、弹窗开关、调音量、局内消除各一段，帧放在 dump 目录下的 frames/'),
        'frame_glitches')
    text_findings = fixed_text_inventory_findings(rep if dark_ok else {})
    label_total, dynamic_total, long_copy_total = visible_label_counts(dump_files, proj)
    text_detail = ('可见运行时文字 %d 项：动态白名单 %d 项、40 字以上说明 %d 项、固定短文字/数字违规 %d 项' %
                   (label_total, dynamic_total, long_copy_total, len(text_findings)))
    if text_findings:
        text_detail += '；' + '；'.join(text_findings[:8])
    add('全屏可见文字清点（固定字成图、动态字有窄范围理由）',
        dark_ok and bool(dump_files) and not text_findings, text_detail if dark_ok else '没有可读页面报告，文字清点不能通过',
        'page_richness.json')
    shape = []
    try:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.split(':', 1)[0] in SHAPE_COLOUR_KINDS:
                    shape.append('%s：%s' % (pg.get('screen') or pg.get('file') or '?', prob[:90]))
    except (NameError, AttributeError):
        pass
    add('字不压扁拉伸、字色有变化', dark_ok and not shape, '；'.join(shape[:6])[:700] if shape else
        ('通过：图片字按原比例缩放、标题/按钮/数字/标签颜色不全一样' if dark_ok else '没有页面报告：先 dump 全部页面'), 'page_richness.json')
    lap = []
    try:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.split(':', 1)[0] in OVERLAP_KINDS:
                    lap.append('%s：%s' % (pg.get('screen') or pg.get('file') or '?', prob[:90]))
        lap += ['工程字体：%s' % p_[:90] for p_ in rep.get('setup', []) if p_.split(':', 1)[0] in OVERLAP_KINDS]
    except (NameError, AttributeError):
        pass
    add('位置穿模（字和图不互相压、数字不叠印、不伸出按钮/胶囊/卡片、主功能字在按钮上、没有假透明格子）', dark_ok and not lap, '；'.join(lap[:6])[:700] if lap else
        ('通过：没有字压图、数字叠印、图伸出按钮/胶囊/卡片、按钮互相重叠、假透明格子，主功能字都在生成的按钮上' if dark_ok else '没有页面报告：先 dump 全部页面'),
        'page_richness.json')
    same = []
    try:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.split(':', 1)[0] in STYLE_KINDS:
                    same.append('%s：%s' % (pg.get('screen') or pg.get('file') or '?', prob[:110]))
        same += ['%s' % p_[:110] for p_ in rep.get('setup', []) if p_.split(':', 1)[0] == 'button_set']
    except (NameError, AttributeError):
        pass
    add('同组按钮同一种风格（按钮和下面的字做法、底板、颜色一致）', dark_ok and not same, '；'.join(same[:6])[:700] if same else
        ('通过：每组按钮的字都是同一种做法、同一种底板和颜色，按钮全部来自同一套' if dark_ok else '没有页面报告：先 dump 全部页面'),
        'page_richness.json')
    hero = []
    try:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.split(':', 1)[0] in HERO_HUD_KINDS:
                    hero.append('%s：%s' % (pg.get('screen') or pg.get('file') or '?', prob[:110]))
    except (NameError, AttributeError):
        pass
    add('首页主角露全、HUD 数字够大够清楚、复活/结算页没有黑边（H11、H6）', dark_ok and not hero, '；'.join(hero[:6])[:700] if hero else
        ('通过：首页主角至少 90%% 在屏内、占屏 8%% 以上；HUD 数字字高至少屏高 3%%、对比度至少 3:1；复活和结算页上下没有黑边' if dark_ok
         else '没有页面报告：先 dump 首页、游戏中、复活和结算页'), 'page_richness.json')
    sheets_ = overlap_sheets(dump_files, out)
    add('穿模审查图（给 Codex 看）', None if sheets_ else False, ('%d 张：%s（放大看每个按钮、胶囊、数字有没有穿模）' % (len(sheets_), out / 'overlap'))
        if sheets_ else '没有可裁的按钮/胶囊（缺 dump 或截图）', 'overlap')
    add('实际页面状态与截图（docs/art/screens.json）', True, '输入完整：%d个精确页面状态'%len(inventory['listed']), 'input-inventory.json')
    add('全页面双比例覆盖（每个精确状态各有同帧 dump+截图）', True, '输入完整：%d个页面/尺寸组合'%len(inventory['observed']), 'input-inventory.json')

    if shots:
        code, text = run('audit_dark_area.py', [*shots, '--project', proj, '--dumps', dumps, '--out', out / 'screens.json', *binding], logs)
        j = first_json(text)
        over = '；'.join('%s：%s' % (Path(x['path']).name, '、'.join(x['problems'])) for x in j.get('over', [])[:5])
        add('大块深色与纯色底（画风禁止项，不设亮度下限）', code == 0, over or '通过（%d 张截图）' % j.get('checked', 0), 'screens.json')
    else:
        add('大块深色与纯色底（画风禁止项，不设亮度下限）', False, '没有截图')

    layout = out / 'ui-layout.json'
    if dump_files:
        overrides = proj / 'docs' / 'ui-layout-overrides.json'
        layout_args = [*dump_files, '--out', layout]
        if overrides.is_file():
            layout_args += ['--overrides', overrides]
        code, text = run('extract_ui_layout.py', layout_args, logs)
        if code == 0:
            code, text = run('audit_ui_coverage.py', [layout, '--out', out / 'ui_coverage.json', *binding], logs)
            j = first_json(text)
            over = '；'.join('%s：%s' % (x['name'], '、'.join(x['problems'][:2])) for x in j.get('over', [])[:4])
            add('布局（玩法区、弹窗、按钮分布）', code == 0, over or '通过', 'ui_coverage.json')
        else:
            add('布局（玩法区、弹窗、按钮分布）', False, '读不出布局：' + text.strip()[-200:], 'logs/extract_ui_layout.log')
    else:
        add('布局（玩法区、弹窗、按钮分布）', False, '没有 dump')

    code, text = run('audit_copy_quality.py', ['--project', proj, '--dumps', dumps, '--require-runtime', '--out', out / 'copy.json',
                                               '--sheet', out / 'copy-review.md', *binding], logs)
    j = first_json(text)
    found = '；'.join('%s：%s' % (x['text'][:24], x['message']) for x in j.get('found', [])[:4])
    add('文字放得下、拼写', code == 0, found or '通过', 'copy.json')

    code, text = run('audit_bitmap_letter_fonts.py', ['--project', proj, '--out', out / 'bitmap_letter_fonts.json'], logs)
    j = first_json(text)
    found = '；'.join('%s：%s' % (x['kind'], x['detail']) for x in j.get('findings', [])[:4])
    add('位图字只用于数字和符号；句子用真字体；字母大小写不串（不许 HelP/TaP）', code == 0, found or '通过（%s 个位图字体）' % j.get('fonts', 0),
        'bitmap_letter_fonts.json')

    code, text = run('audit_dev_text.py', ['--project', proj, '--final', '--out', out / 'dev_text.json', *binding], logs)
    j = first_json(text)
    add('开发用文字和占位图', code == 0, '通过' if code == 0 else '开发用文字 %s 处，占位图 %s 张' % (j.get('failed', '?'), j.get('placeholder_art', '?')),
        'dev_text.json')

    # user 2026-10-23: ART-04 found 22 runtime frames below 2x their node size (and a 1.47x background) in the FINAL review,
    # after the user had approved the art. The final review's art checks are these same checks, run after every own art round
    # (both boards, first round included): runtime frames from the dumps (low_res) + scene/prefab sprites, one row, blocking.
    try:
        ce = json.loads((proj / 'docs' / 'art' / 'clarity-exempt.json').read_text(encoding='utf-8-sig'))
        exempt = [str(x['frame']) for x in ce.get('frames', []) if isinstance(x, dict) and x.get('frame') and str(x.get('why', '')).strip()]
    except (OSError, ValueError, AttributeError):
        exempt = []
    low = []
    try:
        for pg in rep.get('pages', []):
            for prob in pg.get('problems', []):
                if prob.split(':', 1)[0] == 'low_res':
                    low.append('%s：%s' % (pg.get('screen') or pg.get('file') or '?', prob[9:120]))
    except (NameError, AttributeError):
        pass
    code, text = run('audit_image_clarity.py', ['--project', proj, '--out', out / 'clarity.json'], logs)
    try:
        cj = json.loads((out / 'clarity.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cj = first_json(text)
    static = [x for x in cj.get('findings', []) if isinstance(x, dict) and
              not any(fnmatch.fnmatch(str(x.get('image', '')).lower(), g.lower()) for g in exempt)]
    static_txt = ['%s/%s "%s" %sx%s 显示 %sx%s（%s）' % (x.get('file'), x.get('node'), x.get('image'), *(x.get('source') or ['?', '?']),
                                                   *(x.get('display') or ['?', '?']), '放大使用' if x.get('level') == 'upscaled' else '不到2倍')
                  for x in static[:4]]
    clear_ok = dark_ok and not low and not static
    add('清晰度（ART-04：运行时的图≥节点2倍、背景≥1.5倍）', clear_ok,
        '；'.join(low[:5] + static_txt)[:900] if (low or static) else
        ('通过：运行时 dump 里的图和场景里的图都够清晰（已豁免 %d 条原图）' % len(exempt) if dark_ok else '没有页面报告：先 dump 全部页面（含游戏中）'),
        'clarity.json')

    # 用户 2026-10-22：体力/货币/关卡进度放在最上方，货币贴合题材；有关卡就有地图（显示总关数），无尽游戏没有地图
    code, text = run('audit_top_bar.py', ['--project', proj, '--dumps', dumps, '--out', out / 'top_bar.json', *binding], logs)
    try:
        checks = json.loads((out / 'top_bar.json').read_text(encoding='utf-8'))['checks']
    except (OSError, ValueError, KeyError):
        checks = [{'id': 'run', 'passed': False, 'detail': text.strip()[-200:]}]
    art = [c for c in checks if not c['passed'] and not c['id'].startswith('live_')]
    later = [c for c in checks if not c['passed'] and c['id'].startswith('live_')]
    add('顶部资源栏', False if art else (None if later else True),
        '；'.join(c['detail'][:110] for c in art[:3]) if art else ('通过；测试阶段再看过关后数字变大' if later else '通过'), 'top_bar.json')
    code, text = run('audit_level_plan.py', ['--project', proj, '--dumps', dumps, '--out', out / 'level_plan.json', *binding], logs)
    try:
        checks = json.loads((out / 'level_plan.json').read_text(encoding='utf-8'))['checks']
    except (OSError, ValueError, KeyError):
        checks = [{'id': 'run', 'passed': False, 'detail': text.strip()[-200:]}]
    pages = {'map_page', 'map_shows_total', 'endless_no_map', 'mode_recorded', 'run'}
    art = [c for c in checks if not c['passed'] and c['id'] in pages]
    plan = [c for c in checks if not c['passed'] and c['id'] not in pages]
    add('关卡地图', False if art else (None if plan else True),
        '；'.join(c['detail'][:110] for c in (art or plan)[:3]) or '通过', 'level_plan.json')

    # 用户 2026-10-24：礼盒 10 帧只在美术阶段查（原来在 audit_game_modules.py / 最终门禁里）
    add(*gift_box_row(proj))
    for title, ok, detail, log in static_rows:     # v7.8 H8 / H10 (computed before the capture check)
        add(title, ok, detail, log)

    if shots:
        code, text = run('make_contact_sheet.py', [*shots, '--out', out / 'sheets', *binding], logs)
        add('总览图（给 Codex 看）', None if code == 0 else False, str(out / 'sheets') if code == 0 else text.strip()[-200:])
    blocking = [r for r in rows if r['status'] == '需处理']
    report = {'tool': 'art_check', 'schema': 1, 'board': board, 'art_style': 'remake' if remake_art else 'original',
              'assets_fingerprint': tree_fingerprint(proj), 'checked': len(rows), 'failed': len(blocking),
              'passed': not blocking, 'status': 'pass' if not blocking else 'fail', 'rows': rows, 'look_list': LOOK,
              'base_generated': static_summary, 'time': dt.datetime.now().isoformat(timespec='seconds')}
    if a.binding:
        try:
            b = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError):
            b = None
        if not isinstance(b, dict):
            ap.error('no binding object in %s' % a.binding)
        report['binding'] = b
    from check_runner import read_timings
    report['check_timings'] = read_timings(logs)
    report['total_elapsed_seconds'] = round(time.monotonic()-started,6)
    (out / 'art-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # v7.8 U7（补）: the package writers and serve_preview --keep only check this receipt (never re-run the art check)
    import art_receipt
    receipt = art_receipt.after_art_check(proj, report, out / 'art-check.json')
    md = ['# 美术自检', '', '工程：%s　板块：%s　美术：%s　时间：%s' % (proj, '英化' if board == 'localize' else '重塑',
                                                             '按重塑画风' if remake_art else '沿用原画风', report['time']), '',
          '美术回执：%s（%s，%d 张图的指纹；出包和用户试玩只核对它，图再改就要重跑本脚本）' % (
              art_receipt.receipt_path(proj), receipt['status'], receipt['images_count']), '',
          ('**需处理 %d 项：改完重新读页面、重新跑本脚本，全部通过才交用户。**' % len(blocking)) if blocking else '**脚本检查全部通过。**接着 Codex 看总览图：',
          '', '| 检查 | 结果 | 说明 |', '| --- | --- | --- |']
    md += ['| %s | %s | %s |' % (r['check'], r['status'], r['detail'].replace('|', '/')) for r in rows]
    md += ['', '## 看图清单（普通游戏页逐项看；已核实官方加载/Retry按cocos-loading-screen.md实看，保留清晰度、比例、边缘及可操作Retry，不套游戏主题生图规则）', ''] + ['- [ ] ' + x for x in LOOK]
    (out / 'art-check.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md))
    print('\n完整结果：%s' % out)
    return 1 if blocking else 0


if __name__ == '__main__':
    _python = numpy_python()
    if _python:      # v7.8: no numpy here -> re-run with one that has it (the checker tools inherit sys.executable)
        import os
        print('art_check: %s 没有 numpy，改用 %s 运行' % (sys.executable, _python), file=sys.stderr)
        raise SystemExit(subprocess.call([_python, '-B', str(Path(__file__).resolve()), *sys.argv[1:]],
                                         env=dict(os.environ, ART_CHECK_REEXEC='1', PYTHONDONTWRITEBYTECODE='1')))
    raise SystemExit(main())
