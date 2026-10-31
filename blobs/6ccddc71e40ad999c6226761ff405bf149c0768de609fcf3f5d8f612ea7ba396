#!/usr/bin/env python3
"""一键预检：GUI 测试之前，用便宜的脚本把能静态查出的问题一次查完，只输出一页摘要。

  python preflight.py --project <工程> --board localize|remake [--native-zip <测试包.zip>] [--screens <截图文件夹>]
                      [--levels <总关数>] [--ads-config <广告配置.json>] [--maintenance-scope <维护范围.json>]
                      [--binding <当前review.json>] [--maintenance-visual-policy <视觉映射.json>]
                      [--copy-table <文案表.csv>] [--glossary <词表.json>] [--out <输出文件夹>]

--board：localize = 英化（中文源码转英文，只做英化入口 cocos-game-to-english 列的固定几项，核心玩法、关卡、原画风和原声音不动；docs/art-style.txt 写 remake 时美术按重塑查），remake = 重塑（启动包做游戏）。
不写时读 <工程>/docs/board.txt；都没有时按重塑（最严）检查并提示。见 remake-core/references/two-boards.md。
英化：查英文、新图、删掉的分享/排行、两个音量和通用项；默认不补关、不加皮肤/经济/签到/教程（Saul 2026-10-28，旧的“英化＋优化”清单作废），
工程里没有关卡表、皮肤表、docs/modules.json 这些板块记录时，设计关那几行写不适用；Saul 要求创新玩法、用了对应板块时照查（Saul 2026-10-30）；清晰度和音频来源只作提示（原图、原声音文件保留）。

跑哪些检查（缺对应输入的自动跳过）：
  清晰度        audit_image_clarity.py    场景/预制体里被放大、不到2倍的图片
  音频来源      audit_audio_sources.py    每个音频都有合格授权记录
  中文残留      audit_english_coverage.py 源码/包里的中文候选数量（需人工分类：注释不算）
  英文文案      audit_copy_quality.py     拼写、中文/全角标点、占位符、中式英语、叫法统一、字放不下（读 docs/test 里的 dump_ui）
  广告接入标记  audit_platform_markers.py 激励广告和成长（加桌面、主页回访）必需的接口调用；状态不正常就是需处理
  互推          audit_platform_markers.py 跳转其他小游戏（navigateToMiniProgram 等）
  异步返回方式  audit_async_contracts.py  奖励查询的回调和 Promise 都接住了吗（Monkey Dash 2026-10-21）
  触屏写法      audit_mobile_input.py     已知会让手机点不中的写法
  分享/排行榜   audit_no_social_features.py --stage final   分享、排行榜、邀请入口（v7.5 细菌2048）
  分享换奖励    audit_share_entries.py    “本平台不可用”的死按钮；每个分享调用在 docs/ 记录删掉或改成看广告
  声音设置      audit_sound_settings_static.py  有背景音乐、音乐和音效分开调（实际输出仍看 audit_sound_settings.py）
  逻辑检查      logic_check.py --mode review   静态疑点；--stage final 时 R01–R09 缺失也不通过
  包体估算      audit_package_estimate.py 源码阶段估总包/主包、图片比显示尺寸大3倍以上
  App ID        audit_source_appid.py     settings/bytedance.json 的 appid 是数字（共用测试组 ID 正常）
  平台包        audit_platform_kit_required.py  用本机 2.4.15 出包就必须带平台包（自写广告封装只提示）
  广告入口      audit_ad_entry_reachability.py  激励广告按钮在预制体里关着、又没有代码打开 → 需处理
  上传包结构    verify_native_zip.py      包结构、App ID、测试跳关标记是否残留     （需 --native-zip）
  广告位绑定    audit_ad_binding.py       包里的广告配置与当前广告配置一致           （需 --native-zip）
  画面亮度背景  audit_dark_area.py        截图深色/大块白色/大块纯色/纯黑底         （默认读 docs/test 里 dump_ui 的截图）
  启动契约      audit_startup_contract.py 会让游戏进不去的写法（可选接口当必需、固定截止、直接切场景等）
  开发用文字    audit_dev_text.py         试玩版里玩家看得到的 PROTOTYPE/PLAYTEST 等字样、占位图
  UI不挡玩法    audit_ui_coverage.py      游戏中常驻UI≤20%、弹窗≤60%、内容不压边框  （docs/ui-layout.json 必须是 extract_ui_layout.py 从游戏读出的）
  关卡抽测清单  plan_level_tests.py       哪些关要真实触摸                         （需 --levels）
  皮肤收集梯度  audit_acquisition_progression.py  新建玩法查模板梯度；维护范围查原有收集和经济（自动找 unlock_table.json）
  禁止广告跳关  audit_no_ad_skip.py       源码/场景/上传包里的跳关代码和文字（必须为0）
  排名系统      audit_league.py           加不加排名的判断（重塑按四个问题；英化不新增）、算法未改、参数模拟、皮肤和文案
  可选玩法      audit_optional_features.py 新建玩法查皮肤增益和七日签到模板；维护范围复验已存在的生产 JS
  单调页面      audit_page_richness.py    首页/过关/失败（和排名页）是否单调：纯色底、只有字的按钮、系统字体、空白面板
  顶部资源栏    audit_top_bar.py          货币/体力/关卡进度在最上方、货币贴合题材、体力是闪电、过关后数字马上变
  关卡地图      audit_level_plan.py       有关卡就有地图（显示总关数）、重塑60关及以上（英化保留原关数，不补关）、难度按波浪分档、随机奖励关、每10关限定关奖励；无尽没有地图

用户 2026-10-24（remake-core/references/check-stages.md）：设计和美术在它们自己的阶段查过了（设计关 design_check.py，美术关
art_check.py），默认不再执行：清晰度、大块深色与纯色底、UI不挡玩法、单调页面、皮肤收集梯度、内置板块、排名扩展、
签到扩展、顶部资源栏、关卡地图这些行只记录“本次未执行”，不冒充通过；缺失/改动回所属阶段。
加 --recheck-earlier 时实际执行这些检查，并将失败列为需处理（比如没走设计关/美术关的老工程）。

--stage final（出包前）：任何一项“跳过”都算需处理（比如没给 --native-zip）。
结果：<输出文件夹>/preflight.md（一页摘要）、preflight.json、logs/（每项完整输出）。
退出码：0 全部通过；1 有"需处理"；2 参数错误。
本预检只做静态与截图测量，不代替真实触摸测试、真机和真实广告验收；它的作用是让 GUI 测试少跑几轮。
保留玩法的维护任务同时传 --maintenance-scope 和 --binding；文案表/词表在工程外时传 --copy-table/--glossary。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 用户 2026-10-24：这些行属于前面的阶段（remake-core/references/check-stages.md），预检里只提示
EARLIER_ROWS = {'清晰度': '美术关', '大块深色与纯色底': '美术关', 'UI不挡玩法': '美术关', '单调页面': '美术关', '顶部资源栏': '美术关',
                '关卡地图': '设计关', '皮肤收集梯度': '设计关', '内置板块': '设计关', '排名扩展': '设计关', '签到扩展': '设计关'}
EARLIER_SCRIPT = {'设计关': 'design_check.py', '美术关': 'art_check.py'}
# Rows an English game does not add by default (英化默认没有设计关, Saul 2026-10-28): not applicable, unless the project
# used those boards for new gameplay Saul asked for (any record below exists, Saul 2026-10-30) or a maintenance scope
# rechecks them.
LOCALIZE_NOT_ADDED = {'关卡地图', '皮肤收集梯度', '内置板块', '排名扩展', '签到扩展', '顶部资源栏'}
LOCALIZE_BOARD_RECORDS = ('docs/modules.json', 'docs/features.json', 'docs/top-bar.json', 'docs/league/decision.json',
                          'assets/resources/config/level_plan.json', 'docs/levels/level_plan.json',
                          'assets/resources/config/unlock_table.json', 'docs/economy/unlock_table.json')
USER_ADS = Path.home() / '.game-skill' / 'ad-config.json'
SKILL_ADS = HERE.parent / 'assets' / 'ad-config.json'


def default_ads():
    """Same order as ad-configuration-reuse.md: user file first, then the skill's preset (if filled)."""
    for p in (USER_ADS, SKILL_ADS):
        try:
            if p.is_file() and json.loads(p.read_text(encoding='utf-8-sig')).get('appId'):
                return p
        except ValueError:
            continue
    return None


DEFAULT_ADS = default_ads()
TIMEOUT = 600


def run(name, args, logs):
    from check_runner import run_tool
    return run_tool(name, args, logs, HERE, TIMEOUT)


def first_json(text):
    """Parse the first JSON object printed by a tool (tools print one summary object)."""
    start = text.find('{')
    if start < 0:
        return {}
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except ValueError:
        return {}


def main():
    started = time.monotonic()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--native-zip', type=Path)
    ap.add_argument('--screens', type=Path, help='文件夹：每个页面和弹窗的截图（png/jpg）')
    ap.add_argument('--levels', type=int, help='游戏总关数')
    ap.add_argument('--ads-config', type=Path, default=DEFAULT_ADS)
    ap.add_argument('--expected-app-id')
    ap.add_argument('--unlock-table', type=Path, help='默认找 assets/resources/config/unlock_table.json 或 docs/economy/unlock_table.json')
    ap.add_argument('--coins-per-level', type=int, help='每过一关给多少金币（用来估算攒钱需要几关）')
    ap.add_argument('--maintenance-scope', type=Path,
                    help='已验证的保留原玩法范围；传给支持维护分支的模块/收集/签到审计')
    ap.add_argument('--binding', type=Path, help='当前 known-issue review JSON；maintenance-scope 必须提供')
    ap.add_argument('--maintenance-visual-policy', type=Path,
                    help='配套 maintenance_scope.v1 的实际 UI 模板映射，传给 audit_page_richness.py')
    ap.add_argument('--copy-table', type=Path, help='文案表 CSV；默认为 <project>/docs/copy/copy-table.csv')
    ap.add_argument('--glossary', type=Path, help='词表 JSON；默认为 <project>/docs/copy/glossary.json')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--board', choices=['localize', 'remake'],
                    help='localize=英化（中文源码转英文）, remake=重塑（启动包做游戏）；不写时读 docs/board.txt')
    ap.add_argument('--stage', choices=['code', 'final'], default='code',
                    help='final = 出包前最后一次预检：任何一项“跳过”都算不通过（比如没给 --native-zip），逻辑检查的 R01–R09 缺失也不通过')
    ap.add_argument('--recheck-earlier', action='store_true',
                    help='实际执行设计关/美术关项目，失败计为需处理；默认不执行这些前置阶段检查')
    a = ap.parse_args()
    if a.maintenance_scope and not a.binding:
        ap.error('--maintenance-scope requires --binding so every preservation check is tied to the current source/Web/Native build')
    if a.maintenance_visual_policy and not (a.maintenance_scope and a.binding):
        ap.error('--maintenance-visual-policy requires --maintenance-scope and --binding')
    proj = a.project.resolve()
    if not (proj / 'assets').is_dir():
        ap.error(f'{proj} 不是 Cocos 工程（没有 assets 文件夹）')
    board_file = proj / 'docs' / 'board.txt'
    recorded = board_file.read_text(encoding='utf-8').strip().lower() if board_file.is_file() else ''
    if a.board and recorded in ('localize', 'remake') and a.board != recorded:
        ap.error(f'--board {a.board} 和 docs/board.txt 里记的 {recorded} 不一致；一个游戏只属于一个板块')
    board = a.board or (recorded if recorded in ('localize', 'remake') else '')
    board_guessed = not board
    board = board or 'remake'
    localize = board == 'localize'
    style_file = proj / 'docs' / 'art-style.txt'
    remake_art = localize and style_file.is_file() and style_file.read_text(encoding='utf-8').strip().lower() == 'remake'
    soft_art = localize and not remake_art      # 英化沿用原画风时，原图清晰度只作提示；"按重塑画风重做"后照重塑查
    out = (a.out or proj.parent / (proj.name + '-preflight') / dt.datetime.now().strftime('%Y%m%d-%H%M%S')).resolve()
    if out.is_relative_to(proj):
        ap.error('输出文件夹要放在工程外面（中文扫描不允许把结果写进被扫描的工程）')
    if out.exists() and any(out.iterdir()):
        ap.error(f'输出文件夹已存在且不为空：{out}')
    logs = out / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    rows = []

    def add(title, status, detail, log=''):
        rows.append({'check': title, 'status': status, 'detail': detail, 'log': log})

    # 英化默认没有设计关（Saul 2026-10-28）：不补关、不加皮肤/经济/签到/顶部资源栏/关卡地图，这些行不适用。
    # Saul 要求创新玩法时，新加的部分用关卡/皮肤/经济板块做，板块会写下记录（Saul 2026-10-30）：有记录就照查。
    # 维护已批准的英化成品（--maintenance-scope）照旧复核原有内容。
    used_boards = [r for r in LOCALIZE_BOARD_RECORDS if (proj / r).is_file()]

    def skip_earlier(*titles):
        if localize and not a.maintenance_scope and not used_boards and all(t in LOCALIZE_NOT_ADDED for t in titles):
            for title in titles:
                add(title, '不适用', '英化默认不加这一项（不补关、不加皮肤/经济/签到/顶部资源栏/关卡地图）；'
                    'Saul 要求创新玩法、用了对应板块时（工程里有板块记录）照查')
            return True
        if a.recheck_earlier:
            return False
        for title in titles:
            stage = EARLIER_ROWS[title]
            add(title, '提示', f'{stage}范围：本次未执行；沿用有效前置结论，缺失/改动时回所属阶段检查。不代表本项通过。')
        return True

    if board_guessed:
        add('板块', '提示', '没写 --board，也没有 docs/board.txt：按重塑（最严）检查。英化请加 --board localize，并在 docs/board.txt 写 localize')
    else:
        add('板块', '提示', ('英化，美术按重塑画风重做：美术按重塑查，原声音保留' if remake_art else
                             '英化：查英文、新图、删掉的分享/排行、两个音量、设置页和通用项（默认保留原玩法、原关卡、原画风和原声音；'
                             '创新玩法用了关卡/皮肤/经济板块时照查）') if localize
            else '重塑（启动包做游戏）：执行本轮功能预检，设计与美术归所属阶段')

    # Page entry regression: only static triage here; LOAD-01 still requires runtime coverage.
    code, text = run('audit_page_readiness.py', ['--project', proj, '--source-only', '--out', out / 'page_readiness.json'], logs)
    j = first_json(text)
    if code in (0, 1) and j:
        add('页面就绪/重进', '需处理' if j.get('failed') else '通过',
            f"静态风险{j.get('failed', 0)}项；此项只作代码预检，最终LOAD-01仍需两比例真实页面冷/热/慢加载取消重进报告", 'page_readiness.json')
    else:
        add('页面就绪/重进', '出错', text.strip()[-300:], 'logs/audit_page_readiness.log')

    if not skip_earlier('清晰度'):
        # 1 清晰度
        code, text = run('audit_image_clarity.py', ['--project', proj, '--out', out / 'clarity.json'], logs)
        j = first_json(text)
        if code in (0, 1) and j:
            worst = '；'.join(f"{x['image']}（原图{x['source'][0]}×{x['source'][1]}→显示{x['display'][0]}×{x['display'][1]}）"
                             for x in j.get('worst', [])[:3])
            bad = j.get('upscaled') or j.get('below_2x')
            add('清晰度', ('提示' if soft_art else '需处理') if bad else '通过',
                f"检查{j.get('checked', 0)}张；放大使用{j.get('upscaled', 0)}张，不到2倍{j.get('below_2x', 0)}张" + (f"。最严重：{worst}" if worst else '')
                + ('。英化只要求新做的英文图达标，原游戏没改的图不追究' if soft_art and bad else ''),
                'clarity.json')
        else:
            add('清晰度', '出错', text.strip()[-300:], 'logs/audit_image_clarity.log')

    # 2 音频来源
    code, text = run('audit_audio_sources.py', ['--project', proj, '--out', out / 'audio.json'], logs)
    j = first_json(text)
    if code in (0, 1) and j:
        probs = '；'.join(f"{p['path']}：{p['problem']}" for p in j.get('problems', [])[:3])
        add('音频来源', ('提示' if localize else '需处理') if j.get('failed') else '通过',
            f"检查{j.get('checked', 0)}个；不合格{j.get('failed', 0)}个；需署名{j.get('attribution_required', 0)}个" + (f"。例如：{probs}" if probs else '')
            + ('。英化保留原游戏声音，不用处理' if localize and j.get('failed') else ''),
            'audio.json')
    else:
        add('音频来源', '出错', text.strip()[-300:], 'logs/audit_audio_sources.log')

    # 3 中文残留（候选需人工分类，数量作提示）
    eng_args = ['--source', proj, '--output', out / 'english.json']
    if a.native_zip:
        eng_args += ['--native', a.native_zip]
    code, text = run('audit_english_coverage.py', eng_args, logs)
    j = first_json(text)
    if j and code in (0, 2):
        n, bad = j.get('text_candidates', 0), j.get('unreadable_text', 0)
        add('中文残留', '需处理' if bad else ('提示' if n else '通过'),
            f"中文候选{n}处（含注释，需按英化规则分类）；无法读取的文本{bad}个；需人工看图的图片{j.get('unique_images_requiring_review', 0)}张",
            'english.json')
    else:
        add('中文残留', '出错', text.strip()[-300:], 'logs/audit_english_coverage.log')

    # 3b 英文文案质量（用户 2026-10-21）
    cq_args = ['--project', proj, '--out', out / 'copy_quality.json', '--sheet', out / 'copy-review.md']
    if a.copy_table:
        cq_args += ['--copy-table', a.copy_table]
    if a.glossary:
        cq_args += ['--glossary', a.glossary]
    if a.binding:
        cq_args += ['--binding', a.binding]
    code, text = run('audit_copy_quality.py', cq_args, logs)
    j = first_json(text)
    if j and code in (0, 1):
        found = '；'.join(f"{x['text'][:30]}：{x['message']}" for x in j.get('found', [])[:3])
        add('英文文案', '需处理' if j.get('blocking') else ('提示' if j.get('review') or not j.get('runtime_strings') else '通过'),
            (f"{j['blocking']}处必须改：{found}" if j.get('blocking') else f"检查{j.get('checked', 0)}条文字，没有必须改的")
            + (f"；{j['review']}处待 GPT 看（中式英语、叫法、大小写、可能被截断）" if j.get('review') else '')
            + ('' if j.get('runtime_strings') else '；还没读到运行中游戏的文字：测试时用 chrome_touch 的 dump_ui 把每个页面读一遍')
            + '。审查单 copy-review.md', 'copy_quality.json')
    else:
        add('英文文案', '出错', text.strip()[-300:], 'logs/audit_copy_quality.log')

    # 4 广告接入标记（v7.5 细菌2048 第2条 / 方块迷阵 第2条：成长标记每个 TikTok 游戏都查；status 不是正常值就是需处理）
    pm_args = [proj, '--report', out / 'platform.json']
    if a.native_zip:
        pm_args += ['--native-zip', a.native_zip]
    code, text = run('audit_platform_markers.py', pm_args, logs)
    j = first_json(text)
    if j:
        miss = (j.get('source_missing') or []) + (j.get('native_missing') or [])
        st = j.get('status') or ''
        share = j.get('share_calls_in_source') or {}   # {call: [files]}
        share = share if isinstance(share, dict) else {str(x): [] for x in share}
        bad = miss or st != 'markers_present_requires_behavior_review' or code != 0
        why = []
        if miss:
            why.append('缺少：' + '、'.join(dict.fromkeys(miss)))
        if share or st.startswith('share_feature'):
            why.append(('有分享/互推/排行调用要删：' + '；'.join(f"{k}（{'、'.join(Path(f).name for f in v[:3])}）" for k, v in list(share.items())[:4]))
                       if share else '分享/排行检查没通过（见 platform.json no_social_features）')
        if bad and not why:
            why.append(f'状态 {st or "未知"}（退出码 {code}）')
        add('广告接入标记', '需处理' if bad else '通过',
            '；'.join(why) if bad else '激励广告和成长（加桌面、主页回访）必需的接口调用都在（不代表广告能播）', 'platform.json')
        cross = {k: v for k, v in share.items() if re.search(r'navigateTo(?:MiniProgram|Mini)|MoreGames', k)}
        add('互推', '需处理' if cross else '通过',
            ('互推/跳转其他小游戏要删掉：' + '；'.join(f"{k}（{'、'.join(v[:4])}）" for k, v in cross.items())) if cross
            else '没有跳转其他小游戏的调用', 'platform.json')
    else:
        add('广告接入标记', '出错', text.strip()[-300:], 'logs/audit_platform_markers.log')

    # 4b 异步接口返回方式（Monkey Dash 2026-10-21：只接 success 回调、Promise 结果被丢 → CHECKING 永远不结束）
    ac_args = ['--project', proj, '--out', out / 'async_contracts.json']
    if a.native_zip:
        ac_args += ['--native', a.native_zip]
    code, text = run('audit_async_contracts.py', ac_args, logs)
    j = first_json(text)
    if j and code in (0, 1):
        found = '；'.join(f"{x['where']}：{x['reason']}" for x in j.get('found', [])[:3])
        look = '；'.join(f"{x['where']}：{x['reason']}" for x in j.get('look_at', [])[:3])
        apis = '、'.join(j.get('reward_apis') or []) or '无'
        add('异步返回方式', '需处理' if j.get('blocking') else ('提示' if j.get('review') else '通过'),
            (f"发现{j['blocking']}处结果会丢：{found}" if j.get('blocking') else '奖励查询的回调和 Promise 都接住了')
            + f"。代码里的奖励接口：{apis}（每个都要在检查表里有入口）" + (f"。请确认：{look}" if look else ''),
            'async_contracts.json')
    else:
        add('异步返回方式', '出错', text.strip()[-300:], 'logs/audit_async_contracts.log')

    # 5 触屏写法
    mi_args = [proj, '--stage', 'code', '--report', out / 'mobile_input.json']
    if a.native_zip:
        mi_args += ['--native-zip', a.native_zip]
    code, text = run('audit_mobile_input.py', mi_args, logs)
    j = first_json(text)
    if j:
        risks = j.get('known_risks') or []
        add('触屏写法', '需处理' if risks else '通过',
            (f"发现{len(risks)}处已知会让手机点不中的写法：" + '；'.join(str(r)[:80] for r in risks[:3])) if risks else '没有发现已知的危险写法',
            'mobile_input.json')
    else:
        add('触屏写法', '出错', text.strip()[-300:], 'logs/audit_mobile_input.log')

    # 5b v7.5（细菌2048 第2-8、10条）：SKILL.md 里的必查项和源码阶段就能查出的上传问题，都在预检里跑
    def tool_row(title, script, args, report, judge):
        code, text = run(script, args, logs)
        j = first_json(text)
        if not j or j.get('status') == 'error' or code not in (0, 1, 2):
            add(title, '出错', text.strip()[-300:], f'logs/{Path(script).stem}.log')
            return
        status, detail = judge(code, j)
        add(title, status, detail, report)

    def first_items(items, n=3):
        return '；'.join(str(x)[:120] for x in (items or [])[:n])

    code, text = run('audit_no_social_features.py', ['--project', proj, '--stage', 'final', '--out', out / 'social.json'], logs)
    sj = first_json(text)
    if sj and code in (0, 2):
        hits = sj.get('findings') or []
        add('分享/排行榜', '通过' if code == 0 else '需处理',
            '没有分享、排行榜、邀请入口' if code == 0 else f'发现{len(hits)}处分享/排行榜/邀请（TikTok 版要删掉，核心玩法里的分享奖励改看广告）：'
            + first_items([f"{Path(h.get('file', '')).name} {h.get('match', '')}" if isinstance(h, dict) else h for h in hits]), 'social.json')
    else:
        add('分享/排行榜', '出错', text.strip()[-300:], 'logs/audit_no_social_features.log')

    tool_row('分享换奖励', 'audit_share_entries.py', ['--project', proj, '--out', out / 'share_entries.json'], 'share_entries.json',
             lambda code, j: ('通过', '没有“本平台不可用”的死按钮；每个分享调用都在 docs/ 记录了删掉或改成看广告') if code == 0 else
             ('需处理', first_items(j.get('problems'))))
    tool_row('声音设置', 'audit_sound_settings_static.py', ['--project', proj, '--out', out / 'sound_settings.json'], 'sound_settings.json',
             lambda code, j: ('需处理', first_items(j.get('problems'))) if j.get('status') == 'needs_fix' else
             ('提示', '源码里没认出：' + first_items(j.get('review')) + '；用设置页实际试音乐和音效两个音量') if j.get('status') == 'review' else
             ('通过', '有背景音乐，音乐和音效分开调（实际输出仍由 audit_sound_settings.py 按录制记录判断）'))
    lc_args = ['--project', proj, '--mode', 'review', '--out', out / 'logic.json'] + (['--stage', 'final'] if a.stage == 'final' else [])
    tool_row('逻辑检查', 'logic_check.py', lc_args, 'logic.json',
             lambda code, j: ('需处理', f"静态疑点{j.get('open_findings')}处待处理：" + first_items(j.get('top'))
                             + ('；最终阶段 R01–R09 回归缺失/未测也不通过' if a.stage == 'final' and j.get('status') == 'fail' else ''))
             if j.get('open_findings') or j.get('status') == 'fail' else
             ('通过', f"静态疑点0处；流程 F01–F20 和回归 R01–R09 在触摸测试里补（未测{j.get('flow_problems')}条）"))
    tool_row('包体估算', 'audit_package_estimate.py', ['--project', proj, '--out', out / 'package_estimate.json'], 'package_estimate.json',
             lambda code, j: ('需处理', first_items(j.get('problems'))) if code else
             ('通过', f"估算总包 {(j.get('estimate') or {}).get('total_bytes', 0) / 1e6:.1f}MB、主包 {(j.get('estimate') or {}).get('main_bytes', 0) / 1e6:.1f}MB"
                     + ('；' + first_items(j.get('warnings'), 1) if j.get('warnings') else '')))
    tool_row('App ID', 'audit_source_appid.py', ['--project', proj, '--out', out / 'source_appid.json'], 'source_appid.json',
             lambda code, j: ('需处理', first_items(j.get('problems'))) if code else
             ('通过' if j.get('status') == 'pass' else '不适用', f"settings/bytedance.json appid {j.get('appid')}" if j.get('appid') else first_items(j.get('notes'))))
    tool_row('平台包', 'audit_platform_kit_required.py', ['--project', proj, '--out', out / 'platform_kit.json'], 'platform_kit.json',
             lambda code, j: ('需处理', first_items(j.get('problems'))) if code else
             (('提示' if j.get('warnings') else '通过') if j.get('status') == 'pass' else '不适用',
              first_items(j.get('warnings'), 2) or first_items(j.get('notes'), 1) or '平台包文件与 KIT_MANIFEST 一致'))
    tool_row('广告入口', 'audit_ad_entry_reachability.py', ['--project', proj, '--out', out / 'ad_entry.json'], 'ad_entry.json',
             lambda code, j: ('需处理', first_items(j.get('problems'))) if code else
             ('提示', first_items(j.get('review'), 2)) if j.get('review') else ('通过', f"{j.get('reachable_entries')}个激励广告入口能点到"))

    # 6 上传包结构 + 7 广告位绑定
    if a.native_zip:
        vz = [a.native_zip, '--report', out / 'native_zip.json', '--structure-only']   # v7.7.4: structure row only
        if a.expected_app_id:
            vz += ['--expected-app-id', a.expected_app_id]
        code, text = run('verify_native_zip.py', vz, logs)
        add('上传包结构', '通过' if code == 0 else '需处理',
            '结构、文件校验、无测试跳关标记' if code == 0 else text.strip().splitlines()[-1][:300], 'logs/verify_native_zip.log')
        if a.ads_config and a.ads_config.is_file():
            code, text = run('audit_ad_binding.py', ['--config', a.ads_config, '--native-zip', a.native_zip,
                                                    '--report', out / 'ad_binding.json'], logs)
            j = first_json(text)
            add('广告位绑定', '通过' if code == 0 else '需处理',
                '包里的 App ID 和激励广告位与配置一致' if code == 0 else str(j.get('reason', text.strip()[-300:]))[:300],
                'ad_binding.json')
        else:
            add('广告位绑定', '跳过', '没有填好的广告配置（~/.game-skill/ad-config.json 或 Skill 自带的预设）')
    else:
        add('上传包结构', '跳过', '没有给 --native-zip')
        add('广告位绑定', '跳过', '没有给 --native-zip')

    if not skip_earlier('大块深色与纯色底'):
        # 8 截图亮度与背景（英化只查改过的页面，原画风不重做；用户 2026-10-21：纯色背景没被查出来，
        #   因为没给 --screens 时这一项被跳过了。现在默认读 docs/test 里 dump_ui 一起保存的截图，没有截图就是"需处理"）
        screens = a.screens or (proj / 'docs/test')
        if screens.is_dir():
            shots = sorted(p for p in screens.rglob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
                           and (a.screens or '-ui-' in p.name))
            if shots:
                code, text = run('audit_dark_area.py', [*shots, '--out', out / 'screens.json'], logs)
                j = first_json(text)
                if code in (0, 1) and j:
                    over = '；'.join(f"{Path(x['path']).name}：{'、'.join(x['problems'])}" for x in j.get('over', [])[:4])
                    add('大块深色与纯色底', '需处理' if j.get('failed') else '通过',
                        f"检查{j.get('checked', 0)}张截图；不合格{j.get('failed', 0)}张" + (f"。{over}" if over else ''), 'screens.json')
                else:
                    add('大块深色与纯色底', '出错', text.strip()[-300:], 'logs/audit_dark_area.log')
            else:
                add('大块深色与纯色底', '需处理', '截图文件夹里没有图片：用 chrome_touch 的 dump_ui 读每个页面和弹窗（含游戏中），截图会自动存进 docs/test')
        else:
            add('大块深色与纯色底', '需处理', '没有页面截图：用 chrome_touch 的 dump_ui 读每个页面和弹窗（含游戏中），截图会自动存进 docs/test；交用户看美术之前必须通过')

    if not skip_earlier('UI不挡玩法'):
        # 8b UI 不挡玩法（用户 2026-10-20：玩法区≥80%）
        layout = proj / 'docs/ui-layout.json'
        if layout.is_file():
            code, text = run('audit_ui_coverage.py', [layout, '--out', out / 'ui_coverage.json'], logs)
            j = first_json(text)
            if code in (0, 1) and j:
                over = '；'.join(f"{x['name']}：{'、'.join(x['problems'][:2])}" for x in j.get('over', [])[:4])
                add('UI不挡玩法', '需处理' if j.get('failed') else '通过',
                    f"检查{j.get('checked', 0)}个画面；不合格{j.get('failed', 0)}个" + (f"。{over}" if over else ''), 'ui_coverage.json')
            else:
                add('UI不挡玩法', '出错', text.strip()[-300:], 'logs/audit_ui_coverage.log')
        else:
            add('UI不挡玩法', '需处理', '缺 docs/ui-layout.json：在浏览器里用 chrome_touch 的 dump_ui 读首页、游戏中和每个弹窗（两种比例），'
                '再运行 extract_ui_layout.py 自动生成；不能手填')

    # 8b2 启动契约：游戏必须进得去（躲雨小鸭 2026-10-21）
    code, text = run('audit_startup_contract.py', ['--project', proj, '--source-only', '--out', out / 'startup_contract.json'], logs)
    j = first_json(text)
    if code in (0, 1) and j:
        add('启动契约', '需处理' if j.get('failed') else '通过',
            (f"{j.get('failed')}处可能导致进不去游戏的写法：" + '；'.join(p[:90] for p in j.get('problems', [])[:3])) if j.get('failed')
            else '没有发现会卡住启动的写法（可选接口当必需、固定总截止、直接切场景、重复 game.run、同一请求重试）',
            'startup_contract.json')
    else:
        add('启动契约', '出错', text.strip()[-300:], 'logs/audit_startup_contract.log')

    # 8c 玩家看得到的开发用文字（用户 2026-10-21）
    code, text = run('audit_dev_text.py', ['--project', proj, '--out', out / 'dev_text.json'], logs)
    j = first_json(text)
    if code in (0, 1) and j:
        hits = '；'.join(f"{h['file']}：{h['text'][:40]}" for h in j.get('dev_text', [])[:4])
        add('开发用文字', '需处理' if j.get('failed') else '通过',
            (f"发现{j.get('failed')}处玩家看得到的开发/测试文字。{hits}" if j.get('failed') else '没有 PROTOTYPE/PLACEHOLDER/PLAYTEST 等开发用文字')
            + (f"；仍有{j.get('placeholder_art')}张占位图（美术完成后必须清掉）" if isinstance(j.get('placeholder_art'), int) and j.get('placeholder_art') else ''),
            'dev_text.json')
    else:
        add('开发用文字', '出错', text.strip()[-300:], 'logs/audit_dev_text.log')

    # 9 关卡抽测清单
    if a.levels:
        code, text = run('plan_level_tests.py', ['--total', a.levels, '--out', out / 'level_plan.json'], logs)
        j = first_json(text)
        add('关卡抽测清单', '提示', f"共{a.levels}关，真实触摸测{j.get('tested_count', '?')}关：{j.get('tested_with_real_touch', [])}",
            'level_plan.json')
    else:
        add('关卡抽测清单', '跳过', '没有给 --levels')

    if not skip_earlier('皮肤收集梯度'):
        # 10 New projects audit template progression; preservation projects replay the actual existing catalog.
        table = a.unlock_table or next((c for c in (proj / 'assets/resources/config/unlock_table.json',
                                                     proj / 'docs/economy/unlock_table.json') if c.is_file()), None)
        if table and Path(table).is_file():
            ua = ['--table', table, '--report', out / 'unlock.json']
            if a.coins_per_level:
                ua += ['--coins-per-level', a.coins_per_level]
            if a.maintenance_scope:
                ua += ['--maintenance-scope', a.maintenance_scope, '--project', proj]
                if a.binding:
                    ua += ['--binding', a.binding]
            code, text = run('audit_acquisition_progression.py', ua, logs)
            j = first_json(text)
            if j:
                warn = '；'.join(j.get('warnings') or [])
                checked_text = (f"核对了 {j.get('checked', 0)} 件原有收集内容、原价和当前生产版购买/合并/装备/存档链"
                                if a.maintenance_scope else
                                f"检查{j.get('checked', 0)}件，符合稀有度、五种解锁、R换算和关卡限定规则")
                add('皮肤收集梯度', '通过' if code == 0 else '需处理',
                    (checked_text if code == 0 else '；'.join(j.get('errors', [])[:3]))
                    + (f"。提示：{warn}" if warn else ''), 'unlock.json')
            else:
                add('皮肤收集梯度', '出错', text.strip()[-300:], 'logs/audit_acquisition_progression.log')
        elif a.maintenance_scope:
            ua = ['--project', proj, '--maintenance-scope', a.maintenance_scope, '--report', out / 'unlock.json']
            if a.binding:
                ua += ['--binding', a.binding]
            code, text = run('audit_acquisition_progression.py', ua, logs)
            j = first_json(text)
            if j and code in (0, 2):
                add('皮肤收集梯度', '通过' if j.get('passed') else '需处理',
                    (f"核对了 {j.get('checked', 0)} 件原有收集内容、原价和当前生产版购买/合并/装备/存档链" if j.get('passed')
                     else '；'.join(j.get('errors', [])[:3]) or '当前维护范围的原有收集检查未通过'), 'unlock.json')
            else:
                add('皮肤收集梯度', '出错', text.strip()[-300:], 'logs/audit_acquisition_progression.log')
        else:
            add('皮肤收集梯度', '不适用' if localize else '跳过',
                '没有找到 unlock_table.json' + ('：英化默认不加皮肤/收集系统，原游戏没有就不用；创新玩法加了皮肤时要有 unlock_table.json' if localize else '（游戏没有皮肤/收集系统时可以忽略）'))

    # 11 严格禁止看广告跳关
    ns = ['--project', proj, '--out', out / 'no_ad_skip.json']
    if a.native_zip:
        ns += ['--native-zip', a.native_zip]
    code, text = run('audit_no_ad_skip.py', ns, logs)
    j = first_json(text)
    if j and code in (0, 1):
        found = '；'.join(f"{x['where']}：{x['match']}" for x in j.get('found', [])[:3])
        look = '、'.join(f"{x['where']}（{x['node']}）" for x in j.get('look_at', [])[:3])
        add('禁止广告跳关', '需处理' if j.get('blocking') else ('提示' if j.get('review') else '通过'),
            (f"发现{j['blocking']}处跳关代码/文字，必须删除：{found}" if j.get('blocking') else '没有跳关代码和文字')
            + (f"。请人工看一眼这些 skip 按钮是不是跳关：{look}" if look else ''), 'no_ad_skip.json')
    else:
        add('禁止广告跳关', '出错', text.strip()[-300:], 'logs/audit_no_ad_skip.log')

    if not skip_earlier('内置板块', '排名扩展', '签到扩展', '顶部资源栏', '关卡地图'):
        # 12 内置板块（用户 2026-10-23：货币、结算×2、礼盒、皮肤、关卡、广告机制，按固定模板做；排名/签到/更多游戏/分享删掉）
        gm_args = ['--project', proj, '--board', board, '--out', out / 'game_modules.json']
        if a.maintenance_scope:
            gm_args += ['--maintenance-scope', a.maintenance_scope]
        if a.binding:
            gm_args += ['--binding', a.binding]
        code, text = run('audit_game_modules.py', gm_args, logs)
        j = first_json(text)
        if j and code in (0, 1):
            dec = j.get('decision') or {}
            said = '皮肤板块' + ('要' if dec.get('skins') else '不要' if dec.get('skins') is False else '未记录') + \
                   ('、货币 ' + str(dec['currency']) if dec.get('currency') else '')
            found = '；'.join(f"{x['id']}：{x['detail'][:70]}" for x in j.get('found', [])[:3])
            if j.get('implementation') == 'production_js':
                detail = (f"{j['failed']}项不合格：{found}" if j.get('failed') else
                          '已按当前维护范围核对原有按钮与生产版 JavaScript；没有要求新增玩法模板')
            else:
                detail = f"{said}。" + (f"{j['failed']}项不合格：{found}" if j.get('failed') else '板块决定、按钮审查、广告机制和皮肤表都符合')
            add('内置板块', '需处理' if j.get('failed') else '通过', detail, 'game_modules.json')
        else:
            add('内置板块', '出错', text.strip()[-300:], 'logs/audit_game_modules.log')

        from feature_policy import enabled
        optional = enabled(proj)
        for title, script, name, flag in (('排名扩展', 'audit_league.py', 'league', 'league'),
                                         ('签到扩展', 'audit_optional_features.py', 'optional_features', 'checkin')):
            opt_args = ['--project', proj, '--out', out / (name + '.json')]
            if script == 'audit_league.py':
                opt_args += ['--board', board]
            if a.maintenance_scope and script == 'audit_optional_features.py':
                opt_args += ['--maintenance-scope', a.maintenance_scope]
            if a.binding:
                opt_args += ['--binding', a.binding]
            code, text = run(script, opt_args, logs)
            j = first_json(text)
            status = ('通过' if optional[flag] else '不适用') if j and code == 0 else '需处理'
            detail = text.strip()[-300:]
            if script == 'audit_optional_features.py' and j and code == 0 and j.get('implementation') == 'production_js':
                detail = '已按当前维护范围核对原有签到决定与绑定生产版 JavaScript；没有要求 DailyCheckin.ts 模板'
            add(title, status, detail, name + '.json')

        # 12c 顶部资源栏、关卡地图（用户 2026-10-22：两个板块都要）
        for title, script, name, ok_text in (('顶部资源栏', 'audit_top_bar.py', 'top_bar', '货币、体力、关卡进度都在最上方并实时变化'),
                                             ('关卡地图', 'audit_level_plan.py', 'level_plan', '关卡表、奖励关、限定关和地图都符合')):
            check_args = ['--project', proj, '--out', out / (name + '.json')]
            if script == 'audit_level_plan.py':
                check_args += ['--board', board]
                if a.binding:
                    check_args += ['--binding', a.binding]
            code, text = run(script, check_args, logs)
            j = first_json(text)
            if j and code in (0, 1):
                found = '；'.join(f"{x['id']}：{x['detail'][:70]}" for x in j.get('found', [])[:3])
                add(title, '需处理' if j.get('failed') else '通过',
                    (f"{j['failed']}项不合格：{found}" if j.get('failed') else ok_text), name + '.json')
            else:
                add(title, '出错', text.strip()[-300:], 'logs/%s.log' % Path(script).stem)

    if not skip_earlier('单调页面'):
        # 13 单调页面（用户 2026-10-21 反面案例：纯蓝底只有 NEXT LEVEL、PLAY 只有字、空白排名面板）
        page_args = ['--project', proj, '--out', out / 'page_richness.json']
        if a.maintenance_scope:
            page_args += ['--maintenance-scope', a.maintenance_scope]
        if a.maintenance_visual_policy:
            page_args += ['--maintenance-visual-policy', a.maintenance_visual_policy]
        if a.binding:
            page_args += ['--binding', a.binding]
        code, text = run('audit_page_richness.py', page_args, logs)
        j = first_json(text)
        if j and code in (0, 1):
            found = '；'.join(f"{x.get('screen') or '缺页面'}：{x['problems'][0][:80]}" for x in j.get('found', [])[:3] if x.get('problems'))
            add('单调页面', '需处理' if j.get('failed') else '通过',
                (f"{j['failed']}个页面有问题：{found}" if j.get('failed') else f"检查{j.get('checked', 0)}个页面，没有单调页面")
                + ('' if j.get('checked') else '。还没有读到页面：用 chrome_touch 的 dump_ui 读首页、过关、失败页并写 purpose'), 'page_richness.json')
        else:
            add('单调页面', '出错', text.strip()[-300:], 'logs/audit_page_richness.log')

    # 用户 2026-10-24：设计和美术已在前面阶段查过，这里只提示，不挡触摸测试（remake-core/references/check-stages.md）
    if not a.recheck_earlier:
        for r in rows:
            stage = EARLIER_ROWS.get(r['check'])
            if stage and r['status'] in ('需处理', '出错'):
                r['detail'] = f"（{stage}已查，这里只提示；有改动就重跑 {EARLIER_SCRIPT[stage]}）" + r['detail']
                r['status'] = '提示'
    # v7.5（细菌2048 第2条）：最终阶段“跳过”不能当通过
    if a.stage == 'final':
        for r in rows:
            if r['status'] == '跳过':
                r['status'] = '需处理'
                r['detail'] = '最终阶段不能跳过：' + r['detail']
    todo = [r for r in rows if r['status'] in ('需处理', '出错')]
    md = ['# 一键预检结果', '', f"工程：{proj}", f"板块：{'英化' if localize else '重塑'}", f"时间：{dt.datetime.now():%Y-%m-%d %H:%M}", '',
          f"**需处理 {sum(r['status'] == '需处理' for r in rows)} 项，出错 {sum(r['status'] == '出错' for r in rows)} 项。**"
          + ('先修这些，再开始触摸测试。' if todo else '可以开始触摸测试。'), '',
          '| 检查 | 结果 | 说明 | 详细 |', '| --- | --- | --- | --- |']
    md += [f"| {r['check']} | {r['status']} | {r['detail'].replace('|', '/')} | {r['log']} |" for r in rows]
    md += ['', '说明：本预检只做静态检查和截图测量，不代替真实触摸测试、真机和真实广告验收。']
    (out / 'preflight.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    from check_runner import read_timings
    (out / 'preflight.json').write_text(json.dumps({'project': str(proj), 'board': board, 'stage': a.stage, 'results': rows, 'check_timings': read_timings(logs), 'total_elapsed_seconds': round(time.monotonic()-started,6)}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('\n'.join(md))
    print(f"\n完整结果：{out}")
    return 1 if todo else 0


if __name__ == '__main__':
    raise SystemExit(main())
