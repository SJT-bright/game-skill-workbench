#!/usr/bin/env python3
"""English entry self-checks for the release selftest (v7.8, 10.1).

1. The stage-4 trial script reaches the shared preview server. Until v7.8 serve_preview.py forwarded to
   cocos-game-core (the v6 name of the shared library), which no English pack has had since v7, so every English
   trial link stopped with "Missing modular cocos-game-core preview server" and no test noticed.
2. The pack README lists every fixed item of the entry. Until v7.8 the README still listed 6 items after
   看广告复活 became item 7 of SKILL.md.
3. (10.1) The English pack says the same thing everywhere: English games use this pack by default and the remake
   boards only for new gameplay Saul asks for (Saul 2026-10-30); stage 1 gives Saul the Chinese original's trial link
   first and goes on without waiting (Saul 2026-10-31); local in-match places may stay (Saul 2026-10-31).
4. (10.1) The stage-1 command really serves a Chinese-original web export without --keep / --project.
5. (10.2) The ad and economy boards are in the pack and the English work uses them without being asked (Saul
   2026-10-31: "英化skill需要自动做的时候就使用广告skill"): result x2, ad revive, the claim-window checkbox, ad timing
   and qa/ad-regression.json route to remake-ads, amounts to remake-economy; no doc still says those boards are
   missing; every link of the entry and the two boards reaches an existing file and heading.
6. (10.2.1) The result page is the ad board's design (Saul 2026-10-31, "Claim统一放到x2正下方一行小字"): Watch Ad x2 is
   the biggest button and Claim is one line of clickable small text right under it, named LinkClaim / link_claim* so
   the shared art check (audit_page_richness.py result_claim_link) finds it. Until 10.2 the English entry said Claim
   sits beside x2, which that check reports.
7. (10.2.2, Saul 2026-10-31) When Saul says a game has too few ads, the English entry sends the work to the separately
   installed ad-boost Skill with the English limits (only the boards Saul ticks, original home buttons untouched, some
   boards only when the original game has that system), and the pack's remake-ads copy has the same ad-boost section as
   the remake pack. A "redesign" request keeps the original game's art style (香肠太难了 Redesign v2 replaced it).
8. (10.2.4, Saul 2026-10-31) Round-1 art regenerates buttons and text with the art Skill in the original style; the
   English link needs only a start check and comes with the manual checklist typed into the reply; the trial-and-improve
   stage runs no checks; every check, the old pre-link ones included, runs after Saul says the trial is fine.
9. (10.2.5, Saul 2026-10-31) Round 1 regenerates every button; the ad Skill ad-boost ships in the pack (item 8) and the
   English work runs its diagnosis and adds the recommended ad boards without asking, with the English limits.
10. (10.2.7, Saul 2026-10-31) The first link waits only for the main pages' new art (the rest and the ad-boost boards come
   in round 2); the local Creator version table and the 2.4.3 build extension; parallel division by file; the four
   recurring pitfalls; every export is checked for old pictures (check_export_images.py, own test file).
11. (10.2.8, Saul 2026-10-31 "加速，你看哪些方面你可以继续优化一下结构") Structure only: a one-screen summary and a
   reading map come first (the 98 KB fixed-adaptation page is still binding, but the start reads its ~30 KB of rules a
   session acts on; the auto-installed standard parts are read when a gate names them); the two ad sections follow the
   item table; the revision line keeps only the current version (history in 版本历史.md) and the README's old version
   notes move to 更新记录.txt; the English-pack copies of the shared docs that still asked for checks before the trial
   carry the English exception where the old sentence stands (2026-10-30 timing reports: 3.5-5 h before the link).
12. (10.2.10, Saul 2026-10-31 "我的英化skill基本是给别人用的……各个步骤都要具有不同电脑的通用性") Any computer: a machine
   check first, Creator found by script (Dashboard record, usual folders, COCOS_CREATOR), every browser command wrapped
   by browser_env.py (Ego when installed, else Chrome/Edge/Chromium), the 3.x entry-page fix, Windows wording, and
   what to do without an image tool or Grok; no Saul-only command or path left in the entry and the version doc.
13. (10.2.12, Saul 2026-11-01 "能不能在skill放一个阶段用时的汇报……全面一点设计") Timing report: every stage and step is
   timed by stage_timer.py; the entry says when to run which command in each stage, the step names and reference times
   in the entry are the tool's own, and the report goes to Saul after every stage, with every trial link and at delivery.
14. (简化.11, Saul 2026-11-01, 总表第 28 条) Every English trial link passes the Chinese check first (Garden Guardians:
   "高波来袭！" in one slice of a Spine atlas reached Saul's trial while the old image record said no Chinese): the
   summary, the stage lead, stages 2-5 and the art copy say so, stage 1 marks its link --chinese-original, the English
   serve_preview.py offers --chinese-original / --draft, and the 10.2.4 "only three start checks" wording is replaced
   by "the Chinese check, then three start checks" (the gate itself is tested in test_serve_preview_gate.py).
15. (简化.11.15, Saul 2026-11-04 "出包后的返工修改，就只检查修改涉及的那些部分") Rework after a test package: stage 5 says to run
   rework_scope.py against the last delivered package, check by hand only what it lists, and let the writers rerun only
   the browser checks the change can affect (the reuse rules themselves are tested in test_rework_scope.py).
16. (前期预防, written by the 蛋壳特工队 session 2026-11-04, Saul 2026-11-05 "前期预防也收进 11.15") The stage lead points at
   references/early-prevention.md: stage 1 also lists conditional states, shared-part users and what a change saves;
   stages 2 and 4 get a representative piece right before copying it and check a changed feature where it is wired;
   qa/ad-regression.json is started in stages 1-2 without blocking the trial link; full suites stay in stage 5.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_entry_consistency.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent
PACK = ENTRY.parent
README = PACK / 'README_先看这里.txt'
CODEX_TEXT = PACK / '发给Codex自动安装_复制这段话.txt'
AD_BOARDS = ('remake-ads', 'remake-economy')
# This pack's Skill folders (an install folder such as ~/.agents/skills also holds other people's Skills).
SKIN_BOARD = 'remake-skins'   # 简化.11.4 (Saul 2026-11-04): the skin board ships with the English pack
OWN = ('cocos-game-to-english', 'cocos-game-check', 'remake-core', 'remake-art') + AD_BOARDS + (SKIN_BOARD,)
LINK = re.compile(r'\]\(([^)\s]+)\)')


def slug(heading):
    """GitHub heading anchor: drop punctuation and symbols, lower-case, spaces to hyphens."""
    text = re.sub(r'[*`]', '', heading).strip().lower()
    return ''.join(c for c in text if unicodedata.category(c)[0] in 'LNM' or c in ' -_').replace(' ', '-')


def headings(md):
    out, seen, fenced = set(), {}, False
    for line in md.read_text(encoding='utf-8').splitlines():
        if line.lstrip().startswith('```'):
            fenced = not fenced
            continue
        m = None if fenced else re.match(r'^#{1,6}\s+(.*?)\s*$', line)
        if m:
            s = slug(m.group(1))
            n = seen.get(s, 0)
            out.add(s if n == 0 else '%s-%d' % (s, n))
            seen[s] = n + 1
    return out


def own_docs():
    return [p for name in OWN if (PACK / name).is_dir() for p in sorted((PACK / name).rglob('*.md'))]


def entry_items(skill_text):
    """Numbers of the rows in the 「只做这几件事」 table of SKILL.md."""
    part = skill_text.split('## 只做这几件事', 1)[1].split('\n## ', 1)[0]
    return [int(m.group(1)) for m in re.finditer(r'^\| *(\d+) *\|', part, re.M)]


def readme_items(readme_text):
    """Numbers of the lines under 「英化做什么（只有这些）：」 in the pack README."""
    part = readme_text.split('英化做什么（只有这些）：', 1)[1].split('\n\n', 1)[0]
    return [int(m.group(1)) for m in re.finditer(r'^(\d+)\. ', part, re.M)]


def read(*parts):
    return PACK.joinpath(*parts).read_text(encoding='utf-8')


class PreviewForwarder(unittest.TestCase):
    def test_serve_preview_reaches_shared_server(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        r = subprocess.run([sys.executable, '-B', 'serve_preview.py', '--help'], cwd=str(HERE), env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, 'serve_preview.py --help failed: ' + (r.stderr or r.stdout)[-400:])
        for option in ('--directory', '--keep', '--open', '--idle-minutes', '--snapshot'):
            self.assertIn(option, r.stdout)


class ReadmeMatchesEntry(unittest.TestCase):
    def setUp(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')

    def test_readme_lists_every_entry_item(self):
        skill = entry_items((ENTRY / 'SKILL.md').read_text(encoding='utf-8'))
        readme_text = README.read_text(encoding='utf-8')
        self.assertEqual(skill, list(range(1, len(skill) + 1)), 'SKILL.md fixed-item rows are not 1..N')
        self.assertEqual(readme_items(readme_text), skill, 'README fixed items differ from SKILL.md')
        self.assertIn('（上面 %d 项）' % len(skill), readme_text)

    def test_readme_agrees_with_entry(self):
        text = README.read_text(encoding='utf-8')
        self.assertNotIn('不需要安装重塑包', text)
        self.assertIn('中文原版的手机试玩链接', text)


class EnglishDocsAgree(unittest.TestCase):
    def test_entry_stage1_gives_the_chinese_original_link_first(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        stage1 = text.split('1. **盘点**', 1)[1].split('\n2. ', 1)[0]
        for phrase in ('中文原版的手机试玩链接', '不等回复', 'serve_preview.py', '--open --idle-minutes 0',
                       '本地试玩_中文原版（不用上传）', '原工程一个文件都不动', '同样接着做'):
            self.assertIn(phrase, stage1)
        self.assertLess(stage1.index('中文原版的手机试玩链接'), stage1.index('tiktok_finalize.py init'))

    def test_entry_does_not_contradict_innovation(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('不需要安装重塑包', text)
        self.assertIn('创新玩法', text)

    def test_local_places_may_stay(self):
        row4 = [l for l in (ENTRY / 'SKILL.md').read_text(encoding='utf-8').splitlines() if l.startswith('| 4 |')]
        self.assertEqual(len(row4), 1)
        self.assertIn('局内本地名次可以留', row4[0])
        self.assertIn('局内本地名次可以留', (ENTRY / 'references' / 'fixed-entries.md').read_text(encoding='utf-8'))

    def test_claim_window_checkbox_rule(self):
        text = (ENTRY / 'references' / 'fixed-entries.md').read_text(encoding='utf-8')
        self.assertIn('默认勾上', text)
        self.assertIn('audit_claim_double.py', text)

    def test_shared_library_notes_match(self):
        self.assertIn('默认不适用于英化', read('remake-core', 'SKILL.md'))
        boards = read('remake-core', 'references', 'two-boards.md')
        self.assertNotIn('本包只管重塑', boards.splitlines()[0])
        self.assertIn('英化（本包 cocos-game-to-english）', boards)
        self.assertIn('首页规则只管重塑', boards)
        flow = read('remake-core', 'references', 'stage-flow.md')
        self.assertNotIn('英化的优化清单', flow)
        self.assertNotIn('→ 写优化清单 →', flow)
        self.assertIn('先给中文原版试玩链接（不等回复', flow)


class AdBoardsUsedWithoutAsking(unittest.TestCase):
    """10.2 (Saul 2026-10-31): English work that touches ads uses the ad board by itself; amounts come from economy."""

    def test_boards_are_in_the_pack(self):
        for name in AD_BOARDS:
            self.assertTrue((PACK / name / 'SKILL.md').is_file(), '%s is not next to cocos-game-to-english' % name)

    def test_entry_routes_the_ad_items(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        block = text.split('**看广告的几项按广告板块做', 1)[1].split('\n## ', 1)[0]
        for target in ('../remake-ads/SKILL.md', '../remake-ads/references/end-flow-one-video.md',
                       '../remake-ads/references/rewarded-revive-and-help-layout.md',
                       '../remake-ads/references/ad-mechanism.md', '../remake-ads/references/ad-timeout-and-regression.md',
                       '../remake-economy/SKILL.md', '../remake-economy/references/economy-rules.md'):
            self.assertIn('](%s' % target, block)
        self.assertIn('不用 Saul 点名', block)
        self.assertIn('由第 8 项 ad-boost 默认按诊断推荐加', block)
        rows = {l.split('|')[1].strip(): l for l in text.splitlines() if re.match(r'^\| *[67] *\|', l)}
        for n in ('6', '7'):
            self.assertIn('看广告的几项按广告板块做', rows[n])
        stage2 = text.split('2. **修改**', 1)[1].split('\n3. ', 1)[0]
        where = [l for l in stage2.splitlines() if '**广告规则去哪看**' in l]
        self.assertEqual(len(where), 1)
        self.assertIn('../remake-ads/references/ad-timeout-and-regression.md', where[0])
        self.assertNotIn('只装了英化包时', where[0])
        self.assertNotIn('v7.9 起', text)

    def test_fixed_entries_route_to_the_boards(self):
        text = (ENTRY / 'references' / 'fixed-entries.md').read_text(encoding='utf-8')
        for target in ('../../remake-ads/SKILL.md', '../../remake-ads/references/ad-mechanism.md',
                       '../../remake-ads/references/rewarded-revive-and-help-layout.md',
                       '../../remake-economy/references/economy-rules.md#二货币和结算2'):
            self.assertIn('](%s' % target, text)
        self.assertIn('GameAudioManager', text)

    def test_board_notes_say_fixed_items_need_no_ask(self):
        ads = (PACK / 'remake-ads' / 'SKILL.md').read_text(encoding='utf-8')
        eco = (PACK / 'remake-economy' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('不用 Saul 点名', ads.split('\n---', 1)[0])         # description
        self.assertIn('> **英化包说明（Saul 2026-10-31）**', ads)
        self.assertIn('不用等 Saul 点名', ads)
        self.assertIn('只指新加的看广告入口', ads)
        self.assertIn('英化自动用的是固定入口的数额', eco.split('\n---', 1)[0])
        self.assertIn('> **英化包说明（Saul 2026-10-31）**', eco)
        self.assertIn('原游戏的货币名、价格、礼盒和其他数值都不改', eco)

    def test_no_doc_says_a_present_board_is_missing(self):
        present = [n for n in OWN if (PACK / n / 'SKILL.md').is_file()]
        for p in own_docs():
            text = p.read_text(encoding='utf-8')
            for name in present:
                self.assertNotIn('（重塑包 %s 板块，英化包不含）' % name, text, p.relative_to(PACK).as_posix())

    def test_links_of_entry_and_boards_resolve(self):
        bad = []
        for name in ('cocos-game-to-english',) + AD_BOARDS + (SKIN_BOARD,):
            for p in sorted((PACK / name).rglob('*.md')):
                for m in LINK.finditer(p.read_text(encoding='utf-8')):
                    t = m.group(1)
                    if re.match(r'[a-z]+:', t):
                        continue
                    path, _, anchor = t.partition('#')
                    target = Path(os.path.normpath(str(p.parent / path))) if path else p
                    if not target.exists():
                        bad.append('%s -> %s (no file)' % (p.relative_to(PACK).as_posix(), t))
                    elif anchor and target.suffix == '.md' and anchor.lower() not in headings(target):
                        bad.append('%s -> %s (no heading)' % (p.relative_to(PACK).as_posix(), t))
        self.assertEqual(bad, [])

    def test_pack_texts_list_the_boards(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        readme = README.read_text(encoding='utf-8')
        skills = readme.split('本包的 Skill：', 1)[1].split('\n\n', 1)[0]
        for name in AD_BOARDS + (SKIN_BOARD,):
            self.assertIn('- %s：' % name, skills)
        if CODEX_TEXT.is_file():
            self.assertNotIn('本包不需要重塑包', CODEX_TEXT.read_text(encoding='utf-8'))


class SkinBoardLinks(unittest.TestCase):
    """简化.11.4 (Saul 2026-11-04): skins always come with the currency and the ads; the three boards point at each other."""

    def test_skin_board_is_in_the_pack_and_says_so(self):
        text = (PACK / SKIN_BOARD / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('## 皮肤一定连着货币和广告（Saul 2026-11-04）', text)
        for target in ('../remake-economy/SKILL.md', '../remake-ads/SKILL.md',
                       '../remake-economy/references/economy-rules.md#6-看广告试用皮肤的弹窗econ-skintrial'):
            self.assertIn('](%s' % target, text)
        self.assertIn('skin_links', text)

    def test_economy_and_ads_link_back(self):
        for name in AD_BOARDS:
            self.assertIn('](../remake-skins/SKILL.md)', (PACK / name / 'SKILL.md').read_text(encoding='utf-8'), name)


class ResultPageClaimLink(unittest.TestCase):
    """10.2.1 (Saul 2026-10-31): Claim is one line of small text right under the x2 button, as remake-ads says."""
    BESIDE = re.compile(r'(普通领取|Claim)[^。；\n|]{0,8}在它?旁边')     # "Claim 在它旁边", "普通领取在旁边" (until 10.2)

    def test_entry_row6_puts_claim_under_x2(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        row6 = [l for l in text.splitlines() if l.startswith('| 6 |')]
        self.assertEqual(len(row6), 1)
        self.assertIn('最大、最显眼的按钮', row6[0])
        self.assertIn('正下方一行可点的小字', row6[0])
        self.assertIn('](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)', row6[0])
        self.assertNotIn('比旁边的普通领取按钮', text)
        block = text.split('**看广告的几项按广告板块做', 1)[1].split('\n## ', 1)[0]
        self.assertIn('Claim 是它正下方一行可点的小字', block)

    def test_fixed_entries_name_the_nodes_the_art_check_reads(self):
        text = (ENTRY / 'references' / 'fixed-entries.md').read_text(encoding='utf-8')
        section = text.split('## 结算页', 1)[1].split('\n## ', 1)[0]
        for phrase in ('x2 正下方的一行可点小字', '`LinkClaim`', '`link_claim*`', '`BtnDouble`', '`btn_x2_*`',
                       'result_claim_link', '不超过 x2 按钮的一半', '至少 44px', '不能比 x2 大'):
            self.assertIn(phrase, section)

    def test_ad_board_note_and_readme_agree(self):
        note = [l for l in (PACK / 'remake-ads' / 'SKILL.md').read_text(encoding='utf-8').splitlines()
                if l.startswith('> **英化包说明')]
        self.assertEqual(len(note), 1)
        self.assertIn('Claim 是它正下方一行可点的小字', note[0])
        if README.is_file():
            row = [l for l in README.read_text(encoding='utf-8').splitlines() if l.startswith('6. ')]
            self.assertEqual(len(row), 1)
            self.assertIn('正下方一行可点的小字', row[0])

    def test_no_english_doc_puts_claim_beside_x2(self):
        docs = own_docs() + ([README] if README.is_file() else [])
        found = ['%s: %s' % (p.relative_to(PACK).as_posix(), m.group(0)) for p in docs
                 for m in self.BESIDE.finditer(p.read_text(encoding='utf-8'))]
        self.assertEqual(found, [])


class AdBoostAndRedesign(unittest.TestCase):
    """10.2.2 (Saul 2026-10-31): ad-boost for "too few ads", and a redesign keeps the original art style."""

    def test_entry_runs_ad_boost_by_default_with_english_limits(self):
        """10.2.5 (Saul 2026-10-31): runs by default without asking; until 10.2.4 only when Saul said "too few ads"."""
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        block = text.split('**看广告的几项按广告板块做', 1)[1].split('\n## ', 1)[0]
        mark = '**默认按 ad-boost 加广告板块，不问 Saul（Saul 2026-10-31：英化 Skill 融合广告 Skill，默认执行，不需要询问）**'
        self.assertEqual(block.count(mark), 1)
        part = block.split(mark, 1)[1]
        for phrase in ('](../ad-boost/SKILL.md)', '--mode localize', '不出选择题、不问 Saul', '「缺必备」或「少」加前 3 个',
                       '「一般」加前 2 个', '「多」加第 1 个', '只在原游戏本来就有这个系统时才加', '奖励关会动原关卡，不加',
                       '原首页按钮一个都不动', '新入口只放空位', '没有空位时不问', '跟原游戏画风走', 'CHANGELOG.md',
                       # 前期预防 (Saul 2026-11-05 收进 11.15): this operation's reward and save are checked when wired;
                       # the full README section 8 acceptance and the ad regression stay in stage 5
                       '接入时先验证本次操作的奖励、保存和防重复结果', '各板块 README 第 8 节的完整验收及广告回归放到第 5 阶段',
                       '英化游戏以本页为准', '按英化默认做法加入'):
            self.assertIn(phrase, part, phrase)
        for old in ('Saul 说广告太少时用 ad-boost', '选择题里选了哪个板块，就是授权', '没有空位时问 Saul 放哪'):
            self.assertNotIn(old, text, old)

    def test_ad_board_copy_has_the_ad_boost_section(self):
        lines = (PACK / 'remake-ads' / 'SKILL.md').read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines.count('## 加广告载体用 ad-boost（Saul 2026-10-31）'), 1)
        self.assertEqual(sum(l.startswith('- [ ] 用 ad-boost 加的板块（Saul 2026-10-31）') for l in lines), 1)
        section = '\n'.join(lines).split('## 加广告载体用 ad-boost', 1)[1].split('\n## ', 1)[0]
        self.assertIn('英化游戏默认由英化入口跑 ad-boost', section)
        self.assertNotIn('英化游戏只在 Saul 说广告太少', section)
        self.assertIn('原首页按钮不动', section)
        self.assertIn('21 个板块', section)                      # ad-boost v1.2.11 battle-pass (11.8); 20 from v1.2.0, 15 until 10.2.10
        self.assertNotIn('15 个板块', section)

    def test_redesign_keeps_the_original_art_style(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split(ART_HEADING, 1)[1].split('\n## ', 1)[0]
        for phrase in ('“重新设计”英化游戏时，画风也照原游戏', '原图能用就用', '按钮底色不用深色', '图标后面不另加底板',
                       '只有他明说换画风'):
            self.assertIn(phrase, section)


ART_HEADING = '\n## 美工：第一轮按美工 Skill 照原画风重做按钮和文字'


class TrialFirstThenFullChecks(unittest.TestCase):
    """10.2.4 (Saul 2026-10-31): round-1 art regenerates buttons and text with the art Skill in the original style; the
    English link needs only a start check and comes with a manual checklist typed in the reply; Saul's trial-and-improve
    stage runs no checks; every check (the 10.2.3 pre-link ones included) runs after he says the trial is fine."""

    def stages(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split('\n## 阶段', 1)[1].split('\n## ', 1)[0]
        parts = re.split(r'\n(?=[1-5]\. \*\*)', section)
        return section, {int(p[0]): p for p in parts if p[:1].isdigit()}

    def test_order_link_then_trial_improve_then_full_checks(self):
        section, st = self.stages()
        self.assertEqual(sorted(st), [1, 2, 3, 4, 5])
        self.assertIn('英文试玩链接＋人工检测清单', st[3])
        self.assertIn('试玩改进', st[4])
        self.assertIn('全量检查和出包（Saul 说试玩没问题以后）', st[5])
        lead = section.split('1. **盘点**', 1)[0]
        for phrase in ('修复并复查通过后给英文试玩链接', '已知问题、平台兼容和写包入口仍在第 5 阶段', '以本页为准'):
            self.assertIn(phrase, lead, phrase)
        for early in ('art_check.py', 'iPhone SE', '真实点击', '动态画面', '修复'):
            self.assertIn(early, st[3])
        self.assertIn('复查受影响整页、共享组件和新增页面', st[4])
        for late in ('check_known_issues.py', 'preflight.py', 'make_tiktok_zip.py',
                     'build_checked_zip.py', '广告回归 10 例', 'tiktok_finalize.py source', 'image-review.json'):
            self.assertNotIn(late, st[3], late)
            self.assertNotIn(late, st[4], late)
            self.assertIn(late, st[5], late)

    def test_trial_link_requires_language_art_and_playable_start(self):
        _, st = self.stages()
        # 简化.11 (Saul 2026-11-01): the Chinese check comes first, then the same three start checks
        for phrase in ('中文专项检查和完整美工检查都通过后，再确认三件', '能进首页', '能开始玩一局', '没有报错卡死', '--ad-simulator', '不加 `--keep`',
                       '--idle-minutes 0'):
            self.assertIn(phrase, st[3], phrase)
        self.assertNotIn('--snapshot --keep', st[3])
        self.assertIn('--snapshot --keep --project', st[5])

    def test_manual_checklist_is_typed_in_the_reply(self):
        _, st = self.stages()
        self.assertIn('写在回复正文里', st[3])
        self.assertIn('不写成文件、不发文件路径', st[3])
        bullets = [l.split('：', 1)[0] for l in st[3].splitlines() if l.startswith('   - ')]
        self.assertEqual(bullets, ['   - 画面', '   - 新加的东西', '   - 游玩', '   - 玩法改进', '   - 不用你查', '   - 怎么告诉我'])
        dont = [l for l in st[3].splitlines() if l.startswith('   - 不用你查')][0]
        for phrase in ('广告', 'TikTok', '手机上'):
            self.assertIn(phrase, dont)

    def test_trial_improve_rechecks_changed_art_before_next_link(self):
        _, st = self.stages()
        # 前期预防 (11.15): the round's own change is checked as it is made; the full suites still wait for stage 5
        for phrase in ('本轮功能的局部验证随实现完成，完整套件留到第 5 阶段', '不提前跑第 5 阶段的完整套件', '一次全部改完', '只构建一次',
                       '复查受影响整页、共享组件和新增页面', 'Saul 点名', '直到 Saul 说试玩没问题',
                       '先停掉上一轮的试玩服务', '不能只叫他刷新'):
            self.assertIn(phrase, st[4], phrase)
        self.assertNotIn('刷新同一个链接', (ENTRY / 'SKILL.md').read_text(encoding='utf-8'))

    def test_full_checks_keep_every_check(self):
        _, st = self.stages()
        for phrase in ('检查一条不减', '核对最后通过的美工证据与当前交付版本一致', '缺图、变形、色带', '不重复评审已认可的画风和配色',
                       '用户可见的改动先给通过美工检查的新链接确认', 'logic_check.py', 'TikTok 固定适配', '运行时套件由写包入口跑',
                       '不再问一次'):
            self.assertIn(phrase, st[5], phrase)

    def test_round1_art_uses_the_art_skill_in_the_original_style(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        _, st = self.stages()
        art = [l for l in st[2].splitlines() if l.startswith('   - **第一轮美工')]
        self.assertEqual(len(art), 1)
        for phrase in ('](../remake-art/SKILL.md)', '照原画风', '原图放进参考图', '代码和字体画的按钮、数字不算',
                       'art_records.py generated', '新加的按钮', '不等点名', '第一轮所有按钮都重新生成'):
            self.assertIn(phrase, art[0], phrase)
        self.assertNotIn('好的照用', art[0])          # 10.2.4 kept good icon buttons; 10.2.5 regenerates every button
        self.assertNotIn('## 美工 Skill 只在点名时用', text)
        self.assertIn('仍只在 Saul 点名时做', text.split(ART_HEADING, 1)[1].split('\n## ', 1)[0])
        art_skill = (PACK / 'remake-art' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('英化流程不自动调用', art_skill)
        self.assertIn('英化第一轮由英化入口调用', art_skill.split('\n---', 1)[0])
        self.assertIn('英化第一轮由英化入口调用本 Skill', art_skill)

    def test_readme_says_the_new_order(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        text = README.read_text(encoding='utf-8')
        self.assertIn('人工检测清单', text)
        self.assertIn('英化第一轮按它照原画风重新生成按钮和文字', text)
        self.assertNotIn('只在你点名时使用，英化流程不自动调用', text)

    def test_records_for_packaging_do_not_block_the_link(self):
        _, st = self.stages()
        # 前期预防 (11.15): the adapter's real entries are found in stages 1-2, the file is completed and run in stage 5
        for record, when in (('`qa/ad-regression.json`', '第 1 / 2 阶段定位真实入口与字段，第 5 阶段补齐并运行完整套件'),
                             ('`docs/english/image-review.json`', '第 5 阶段写')):
            line = [l for l in st[2].splitlines() if l.startswith('   - **') and record in l.split('**')[1]]
            self.assertEqual(len(line), 1, record)
            self.assertIn(when, line[0], record)
            self.assertIn('不挡英文试玩链接', line[0].split('**')[1], record)

    def test_art_redo_starts_with_samples(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split(ART_HEADING, 1)[1].split('\n## ', 1)[0]
        for phrase in ('**重做美术先出小样（Saul 2026-10-31）**', '2～3 套', '1 张首页加 2 个按钮', '保持原画风，只改英文和新入口',
                       '他选了再做整套', '不碰美术的部分', 'docs/samples/samples.json'):
            self.assertIn(phrase, section, phrase)

    def test_samples_three_points(self):
        # v7.9 (Saul 2026-11-01「把这三点补进v7.9一起改」): show the buttons on the real page, pass the art check first,
        # pick once and keep it
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split('**重做美术先出小样（Saul 2026-10-31）**', 1)[1].split('\n\n', 1)[0]
        for phrase in ('**给 Saul 挑的是做出来的样子**', '游戏真实首页', '不拿一次画出的整页效果图给他挑',
                       '**每套先过美术检查再给他看**', '`art_check.py`', '按钮底色不深、物品图标不另垫底板', '深色粗字（永久禁止）',
                       '**挑一次就定死**', '之后每轮美工不再重新挑', '颜色（HEX）、材质、圆角、描边', '先做 3 个放进游戏看对不对'):
            self.assertIn(phrase, section, phrase)
        samples = (PACK / 'remake-art' / 'references' / 'ui-style-and-samples.md').read_text(encoding='utf-8')
        step4 = [l for l in samples.splitlines() if '样板阶段不停下等用户' in l]
        self.assertTrue(step4 and all('英化' in l for l in step4), step4)   # the English copy says English games wait for Saul


class AdBoostBundled(unittest.TestCase):
    """10.2.5 (Saul 2026-10-31): the ad Skill ad-boost ships in the pack and the English work runs it without asking."""

    def test_ad_boost_is_in_the_pack(self):
        for rel in ('SKILL.md', 'CHANGELOG.md', 'scripts/diagnose_ads.py', 'scripts/doctor.py', 'modules/wheel/README.md'):
            self.assertTrue((PACK / 'ad-boost' / rel).is_file(), rel)
        manifest = PACK / 'distribution-manifest.json'
        if manifest.is_file():
            self.assertIn('ad-boost', json.loads(manifest.read_text(encoding='utf-8'))['skills'])

    def test_entry_lists_ad_boost_as_item_8(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        row8 = [l for l in text.splitlines() if l.startswith('| 8 |')]
        self.assertEqual(len(row8), 1)
        for phrase in ('广告加量', '](../ad-boost/SKILL.md)', '不问 Saul', '原首页按钮不动'):
            self.assertIn(phrase, row8[0], phrase)
        self.assertIn('按上表 1–8 做', text)

    def test_stages_carry_the_ad_boards(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split('\n## 阶段', 1)[1].split('\n## ', 1)[0]
        st = {int(p[0]): p for p in re.split(r'\n(?=[1-5]\. \*\*)', section) if p[:1].isdigit()}
        lead = section.split('1. **盘点**', 1)[0]
        self.assertIn('第一轮美工和 ad-boost 诊断', lead)          # 10.2.7: the boards themselves come in round 2
        self.assertIn('ad-boost 板块也先查再带入链接', lead)
        self.assertIn('默认加哪几个板块', st[3])
        self.assertIn('第 8 项加的板块', st[3])
        self.assertIn('modules/<板块>/README.md` 第 8 节验收', st[5])
        self.assertIn('double_claim', st[5])

    def test_readme_and_install_text_name_ad_boost(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        readme = README.read_text(encoding='utf-8')
        skills = readme.split('本包的 Skill：', 1)[1].split('\n\n', 1)[0]
        self.assertIn('- ad-boost：', skills)
        # v7.9 手机问题源头约束: 9 items (item 9 in-level pause key); ad-boost stays item 8
        self.assertIn('（上面 9 项）', readme)
        if CODEX_TEXT.is_file():
            self.assertIn('ad-boost', CODEX_TEXT.read_text(encoding='utf-8'))


class FasterFirstLink(unittest.TestCase):
    """10.2.7 (Saul 2026-10-31 approved Kiro's recommendation): the first link waits only for the main pages' new art;
    the local Creator version table; parallel division by file; the four recurring pitfalls; the stale-export check."""
    VERSIONS = ('2.4.15', '2.4.3', '2.4.4', '2.4.5', '2.4.6', '3.0.0', '3.6.2', '3.7.1', '3.8.8')

    def stages(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split('\n## 阶段', 1)[1].split('\n## ', 1)[0]
        return text, {int(p[0]): p for p in re.split(r'\n(?=[1-5]\. \*\*)', section) if p[:1].isdigit()}

    def test_first_link_waits_only_for_the_main_pages(self):
        _, st = self.stages()
        art = [l for l in st[2].splitlines() if l.startswith('   - **第一轮美工')][0]
        for phrase in ('**分两批做（10.2.7', '第一个链接只等主要页面', '首页、设置、暂停、复活、结算', '局内的等级、关卡号、分数、货币数字',
                       '其余页面', 'ad-boost 板块的图', '第二轮链接带上', '第一轮所有按钮都重新生成'):
            self.assertIn(phrase, art, phrase)
        self.assertIn('还是原图的页面', st[3])
        self.assertIn('第二轮链接带上', st[3])
        for phrase in ('等的时候接着做第一个链接没等的部分', '其余页面的按钮和图片字', '第 8 项 ad-boost 板块', '先改他说的',
                       '不为了等图拖住他的修改', '至少要有一轮链接带齐所有页面的新图和第 8 项的板块'):
            self.assertIn(phrase, st[4], phrase)

    def test_ad_boost_install_moves_after_the_first_link(self):
        text, _ = self.stages()
        part = text.split('**默认按 ad-boost 加广告板块', 1)[1].split('\n## ', 1)[0]
        self.assertIn('第一个链接前只跑 ⓪ ①', part)
        self.assertIn('第二轮链接带上', part)
        self.assertNotIn('和第一轮美工一起排生图', text)

    def test_every_export_is_checked_for_old_pictures(self):
        _, st = self.stages()
        self.assertIn('check_export_images.py --project <工程> --export', st[3])
        self.assertTrue((HERE / 'check_export_images.py').is_file())
        self.assertTrue((HERE / 'test_check_export_images.py').is_file())
        r = subprocess.run([sys.executable, '-B', str(HERE / 'check_export_images.py'), '--help'], capture_output=True,
                           text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_version_table_lists_every_installed_creator(self):
        text, st = self.stages()
        self.assertIn('](references/local-creator-versions.md)', st[1])
        doc = (ENTRY / 'references' / 'local-creator-versions.md').read_text(encoding='utf-8')
        rows = [l for l in doc.splitlines() if l.startswith('| ')]
        for v in self.VERSIONS:
            self.assertTrue(any(v in r.split('|')[1] for r in rows), v)
        for phrase in ('--use-gl=desktop', 'build-worker-canvas-compat', '**构建报一次 WebGL 初始化错误就别再试，改用同一小版本里装了的另一个**',
                       'index.html', 'fix_web_entry_3x.py', '退出码是 36', 'find_creator.py --project', 'find_creator.py --busy',
                       '.cocos/profiles/editor.json', 'COCOS_CREATOR', 'CocosCreator.exe'):
            self.assertIn(phrase, doc, phrase)
        for gone in ('pgrep', '！游戏学习库', '这台电脑上实测'):     # 10.2.10: no Saul-only command or path
            self.assertNotIn(gone, doc, gone)
        ext = ENTRY / 'assets' / 'build-worker-canvas-compat'
        for name in ('README.md', 'main.js', 'package.json'):
            self.assertTrue((ext / name).is_file(), name)
        self.assertIn("version !== '2.4.3'", (ext / 'main.js').read_text(encoding='utf-8'))

    def test_parallel_division_section(self):
        text, _ = self.stages()
        self.assertEqual(text.count('\n## 并行分工（10.2.7'), 1)
        section = text.split('\n## 并行分工', 1)[1].split('\n## ', 1)[0]
        for phrase in ('子进程最多 3 个', '按文件分', '**美术**', '**代码**', '**文字**', '**只有主线程**', '不构建、不起试玩服务',
                       '不轮询', '主线程只构建一次', '活不多时不开子进程'):
            self.assertIn(phrase, section, phrase)
        self.assertLess(text.index('\n## 并行分工'), text.index(ART_HEADING))

    def test_pitfalls_section(self):
        doc = (ENTRY / 'references' / 'english-ui-rebuild.md').read_text(encoding='utf-8')
        self.assertEqual(doc.count('\n## 常见坑（英化包 10.2.7'), 1)
        section = doc.split('\n## 常见坑', 1)[1].split('\n## ', 1)[0]
        nums = re.findall(r'^([1-9])\. \*\*', section, re.M)
        # Saul 10-31 的 4 条在前；R4N5（11-05）接着加了 5～7 条。编号要连续，原来 4 条的要点都还在。
        self.assertGreaterEqual(len(nums), 4)
        self.assertEqual(nums, [str(i) for i in range(1, len(nums) + 1)])
        for phrase in ('染黑', 'sprite-frame', 'check_export_images.py', 'node.width', 'overflow',
                       'english_copy_guard.py', 'charset.json', '--nodes'):
            self.assertIn(phrase, section, phrase)

    def test_readme_names_the_current_version(self):
        """10.2.8: the README names the current version; 10.2.7 and older notes moved to 更新记录.txt."""
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        text = README.read_text(encoding='utf-8')
        # 10.2.9 (2026-10-31): the title names this release, 10.2.8 or later, and its own note comes first; a version
        # number written into the test made every later hotfix fail here.
        title = re.match(r'Cocos 游戏 Skill —— 英化包（简化版）\d{8}-english-simple\.(\d+(?:\.\d+)*)\n', text)
        self.assertIsNotNone(title, text.split('\n', 1)[0])
        self.assertGreaterEqual(tuple(int(x) for x in title.group(1).split('.')), (10, 2, 8))
        self.assertIn('\n\nenglish-simple.%s / 2026-' % title.group(1), text)
        self.assertNotIn('english-simple.10.2.7 / 2026-10-31', text)
        self.assertIn('english-simple.10.2.7 / 2026-10-31', UPDATES.read_text(encoding='utf-8'))


UPDATES = PACK / '更新记录.txt'
AD_SECTION = '\n## 看广告：固定几项按广告板块做，第 8 项默认加 ad-boost 板块'
OLD_VERSION_NOTES = ('11.16', '11.15', '11.14.1', '11.14', '11.13', '11.12', '11.1', '11', '10.2.12', '10.2.11', '10.2.10', '10.2.9', '10.2.8', '10.2.7', '10.2.6', '10.2.5', '10.2.4', '10.2.3', '10.2.2', '10.2.1',
                     '10.2', '10.1', '10')
# (English-pack copy of a shared doc, the old "before the trial" sentence, the English exception written next to it)
PRE_TRIAL_NOTES = (
    ('remake-art/SKILL.md', '两轮自审', '英化第一轮重新生成按钮和文字不算下文说的“完整首次重做”'),
    ('remake-art/references/art-before-trial.md', '加载失败/重试状态', '英化每轮英文试玩链接前同样要完成美工检查'),
    ('remake-art/references/page-richness.md', '至少两轮自审', '每轮英文试玩链接前须按英化入口第 3 阶段完成美工检查'),
    ('remake-core/references/tiktok-home-growth.md', '交用户试玩前就做小样本', '英化游戏例外：都放到英化入口第 5 阶段做'),
    ('remake-core/assets/user-playtest-checklist-template.md', 'AI 在给你试玩前已经走过', '英化游戏不用本模板'),
    ('remake-core/references/stage-flow.md', '所有美术测试在交用户试玩前完成', '英化同样在每轮英文试玩链接前完成美工检查'),
    ('remake-core/references/check-stages.md', '| 美术关 |', '英化在每轮英文试玩链接前查'),
    ('cocos-game-to-english/references/dynamic-text-glyph-review.md', '成功/失败结算', '第 5 阶段全量检查时覆盖'),
)


class StructureAndReadingMap(unittest.TestCase):
    """10.2.8 (Saul 2026-10-31): structure only; every rule of 10.2.7 is still in the entry or its version history."""

    def text(self):
        return (ENTRY / 'SKILL.md').read_text(encoding='utf-8')

    def test_summary_and_reading_map_come_before_the_details(self):
        text = self.text()
        order = [text.index(h) for h in ('\n## 一屏看懂', '\n## 读哪些文件', '\n## 只做这几件事', AD_SECTION, '\n## 阶段',
                                         '\n## 并行分工', ART_HEADING)]
        self.assertEqual(order, sorted(order))
        summary = text.split('\n## 一屏看懂', 1)[1].split('\n## ', 1)[0]
        self.assertEqual(re.findall(r'^- ([①②③④⑤]) ', summary, re.M), ['①', '②', '③', '④', '⑤'])
        ads = text.split(AD_SECTION, 1)[1].split('\n## ', 1)[0]
        self.assertEqual(ads.count('**看广告的几项按广告板块做'), 1)
        self.assertEqual(ads.count('**默认按 ad-boost 加广告板块'), 1)
        for n in ('6', '7', '8'):
            row = [l for l in text.splitlines() if l.startswith('| %s |' % n)][0]
            self.assertNotIn('见上面「', row, n)

    def test_reading_map_keeps_the_fixed_adaptation_binding(self):
        part = self.text().split('\n## 读哪些文件', 1)[1].split('\n## ', 1)[0]
        for phrase in ('](../cocos-game-check/references/tiktok-fixed-adaptation.md#已定口径不再让模型临场决定)', '必须遵循',
                       '第二部分：跨游戏通用流程」8 条', '第一部分第 9 条', '「第四部分：不要做」', '「出包时怎么装」', '到第 5 阶段出包前再读',
                       '门禁报到哪一条再读那一条', '照样必须遵循', '**子进程**', '子进程不整页读 TikTok 固定适配', '新游戏和旧游戏'):
            self.assertIn(phrase, part, phrase)
        par = self.text().split('\n## 并行分工', 1)[1].split('\n## ', 1)[0]
        self.assertIn('每个子进程读哪些文件见上面「读哪些文件」', par)

    def test_revision_line_keeps_only_the_current_version(self):
        rev = [l for l in self.text().splitlines() if l.startswith('修订：')]
        self.assertEqual(len(rev), 1)
        # 10.2.12: the revision is 10.2.12 or later (a version written into the test failed every later release)
        version = re.search(r'english-simple\.(\d+(?:\.\d+)*)`', rev[0])
        self.assertIsNotNone(version, rev[0])
        self.assertGreaterEqual(tuple(int(x) for x in version.group(1).split('.')), (10, 2, 12))
        self.assertIn('](版本历史.md)', rev[0])
        # 简化.11.9: sessions read this line to tell whether their install is current; 11.4-11.8 still said 11.3.2.
        # In the release tree and the ZIP the pack README title carries the version (installs have no README: skipped).
        if README.is_file():
            title = README.read_text(encoding='utf-8').splitlines()[0]
            pack = re.search(r'english-simple\.(\d+(?:\.\d+)*)', title)
            self.assertIsNotNone(pack, title)
            self.assertEqual(version.group(1), pack.group(1), 'SKILL.md 修订行 %s，README 标题 %s' % (version.group(1), pack.group(1)))
        for old in ('10.2.10：', '10.2.8：', '10.2.7：', '10.2.5：', '10.1：', '上一版 `2026-10-28.english-simple.1`'):
            self.assertNotIn(old, rev[0], old)
        history = (ENTRY / '版本历史.md').read_text(encoding='utf-8')
        if 'english-simple.10.2.12`' not in rev[0]:
            self.assertIn('10.2.12：用时汇报', history)
        for old in ('10.2.10：换电脑也能用', '10.2.8：只调结构', '10.2.7：第一个链接只等主要页面的新图', '10.2.5：第一轮所有按钮都重新生成',
                    '上一版 `2026-10-28.english-simple.1`'):
            self.assertIn(old, history, old)
        self.assertLess(len((ENTRY / 'SKILL.md').read_text(encoding='utf-8').split('\n---', 2)[0]), 1000)   # description

    def test_pre_trial_sentences_carry_the_english_exception(self):
        for rel, old, note in PRE_TRIAL_NOTES:
            text = read(*rel.split('/'))
            self.assertIn(old, text, rel)
            self.assertIn(note, text, rel)
        lead = self.text().split('\n## 阶段', 1)[1].split('1. **盘点**', 1)[0]
        for shared in ('第 3 阶段和美工 Skill 验收清单','其余全量检查和出包','写包入口仍在第 5 阶段'):
            self.assertIn(shared, lead, shared)

    def test_readme_keeps_only_the_current_note(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        readme, updates = README.read_text(encoding='utf-8'), UPDATES.read_text(encoding='utf-8')
        self.assertIn('见同目录「更新记录.txt」', readme)
        for v in OLD_VERSION_NOTES:
            mark = 'english-simple.%s / 2026-' % v          # 10.2.12: 10.2.11 is dated 2026-11-01
            self.assertNotIn('\n' + mark, readme, v)
            self.assertIn(mark, updates, v)
        self.assertLess(len(readme.encode('utf-8')), 16000)


class PortableOnAnyComputer(unittest.TestCase):
    """10.2.10 (Saul 2026-10-31): the English Skill is used on other people's computers: a machine check first, Creator
    found by script, every browser command wrapped so it runs without Ego, Windows wording, and what to do without an
    image tool or Grok."""
    TOOLS = ('check_machine.py', 'find_creator.py', 'browser_env.py', 'fix_web_entry_3x.py')

    def text(self):
        return (ENTRY / 'SKILL.md').read_text(encoding='utf-8')

    def stages(self):
        section = self.text().split('\n## 阶段', 1)[1].split('\n## ', 1)[0]
        return {int(p[0]): p for p in re.split(r'\n(?=[1-5]\. \*\*)', section) if p[:1].isdigit()}

    def test_section_sits_before_the_reading_map(self):
        text = self.text()
        self.assertEqual(text.count('\n## 换电脑也能用（10.2.10'), 1)
        order = [text.index(h) for h in ('\n## 一屏看懂', '\n## 换电脑也能用', '\n## 读哪些文件', '\n## 阶段')]
        self.assertEqual(order, sorted(order))
        summary = text.split('\n## 一屏看懂', 1)[1].split('\n## ', 1)[0]
        self.assertIn('check_machine.py', [l for l in summary.splitlines() if l.startswith('- ①')][0])

    def test_section_covers_every_portability_point(self):
        part = self.text().split('\n## 换电脑也能用', 1)[1].split('\n## ', 1)[0]
        for phrase in ('**「Saul」是谁**', '正在用这个 Skill 的人', 'check_machine.py --project', 'find_creator.py --project',
                       'find_creator.py --busy', 'fix_web_entry_3x.py --export', 'browser_env.py --`', '**不用让用户装 Ego。**',
                       '--browser chrome', '不要让用户重启 Ego', 'make_tiktok_zip.py', 'build_checked_zip.py', 'check_package.py',
                       'prepare_delivery.py', 'ad_regression.py', 'runtime_regression.py', 'serve_preview.py --keep',
                       'chrome_touch.py', '逐条相同', '**自己看画面**', 'page_errors', '**Windows**', '`python3` 写成 `python`',
                       '`pgrep` 用 `find_creator.py --busy`', '`/usr/bin/python3` 用 `python`', '`cp -c`', '`open -R`',
                       '**试玩链接打不开窗口**', '**没有生图工具**', 'art-todo.json', 'record_manual.py', '**没有 Grok**',
                       '**只在 Saul 电脑上有的路径**'):
            self.assertIn(phrase, part, phrase)

    def test_stages_use_the_tools(self):
        st = self.stages()
        for phrase in ('check_machine.py --project <中文原工程>', 'find_creator.py --project <副本>', 'fix_web_entry_3x.py'):
            self.assertIn(phrase, st[1], phrase)
        self.assertIn('fix_web_entry_3x.py --export <这轮的 Web 导出>', st[3])
        self.assertIn('scripts/browser_env.py --`', st[5])
        for n in (1, 3):
            self.assertIn('怎么自己看画面见「换电脑也能用」', st[n], n)

    def test_no_saul_only_instruction_left_in_the_entry(self):
        text = self.text()
        for gone in ('pgrep -fl', '本机 Creator 版本表', '/Applications/', '本机已装'):
            self.assertNotIn(gone, text, gone)
        # the only pgrep left is the Windows note that replaces it
        self.assertEqual(text.count('pgrep'), text.count('`pgrep` 用 `find_creator.py --busy`'))
        ui = (ENTRY / 'references' / 'english-ui-rebuild.md').read_text(encoding='utf-8')
        self.assertNotIn('每张图都用 GPT/Codex 内置 image_gen，', ui)
        self.assertNotIn('使用 Codex 内置 image_gen，', ui)

    def test_tools_are_present_and_start(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for name in self.TOOLS:
            r = subprocess.run([sys.executable, '-B', str(HERE / name), '--help'], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, name + ': ' + r.stderr[-300:])
        self.assertTrue((HERE / 'cdp_browser.mjs').is_file())
        self.assertTrue((HERE / 'test_portable_tools.py').is_file())
        node = shutil.which('node')
        if node:
            r = subprocess.run([node, str(HERE / 'cdp_browser.mjs'), '--help'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])

    def test_readme_and_install_text_name_the_tools(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        readme = README.read_text(encoding='utf-8')
        for name in self.TOOLS:
            self.assertIn(name, readme, name)
        if CODEX_TEXT.is_file():
            codex = CODEX_TEXT.read_text(encoding='utf-8')
            self.assertIn('check_machine.py', codex)
            self.assertIn('不用装 Ego', codex)


class TimingReport(unittest.TestCase):
    """10.2.12 (Saul 2026-11-01): a timing report after every stage, with every step (the art included), every trial
    round and the whole run; the entry and stage_timer.py use the same step names and reference times."""
    HEADING = '\n## 用时汇报（10.2.12'

    def text(self):
        return (ENTRY / 'SKILL.md').read_text(encoding='utf-8')

    def section(self):
        return self.text().split(self.HEADING, 1)[1].split('\n## ', 1)[0]

    def stages(self):
        part = self.text().split('\n## 阶段', 1)[1].split('\n## ', 1)[0]
        return {int(p[0]): p for p in re.split(r'\n(?=[1-5]\. \*\*)', part) if p[:1].isdigit()}

    def tool(self):
        sys.path.insert(0, str(HERE))
        import stage_timer
        return stage_timer

    def test_section_sits_between_the_stages_and_the_parallel_division(self):
        text = self.text()
        self.assertEqual(text.count(self.HEADING), 1)
        order = [text.index(h) for h in ('\n## 阶段\n', self.HEADING, '\n## 并行分工')]
        self.assertEqual(order, sorted(order))
        summary = text.split('\n## 一屏看懂', 1)[1].split('\n## ', 1)[0]
        self.assertIn('每个阶段做完都把用时发给 Saul，见「用时汇报」', summary)

    def test_section_says_when_to_run_every_command(self):
        part = self.section()
        for phrase in ('scripts/stage_timer.py --project <工程>`', '`<工程>/docs/timing/stage-timing.jsonl`', '不要自己估、自己算',
                       '`T stage <1-5>`', '`T done`', '原样发给 Saul', '单独发一条短消息，不等回复', '`T begin <步骤>`',
                       '`T end <步骤>`', '`--count 图=<张数>`', '`--who 美术子进程`', '子进程自己不记', '`T link <第几轮>`',
                       '`T ask <事情>`', '`T back`', '不算进 Saul 等你的时间', '`T mark 中文原版链接`', '`T mark 改要求：<几个字>`',
                       '`T link <N>`', '贴在新链接那条回复最后', '`T mark 交付`、`T done`、`T report --all`',
                       '`docs/timing/timing-report.md`', '每阶段、每轮只提醒一次', '不是硬限制，不为了赶时间少做一步', '`T status`',
                       '`--at 时:分`', '**不挡流程**'):
            self.assertIn(phrase, part, phrase)

    def test_reference_times_and_step_names_are_the_tools_own(self):
        st = self.tool()
        part = self.section()
        for n, minutes in st.REF_MIN.items():
            self.assertIn('第 %d 阶段 %s' % (n, st.fmt(minutes * 60)), part, n)
        self.assertIn('从 Saul 回复到新链接 %s' % st.fmt(st.ROUND_REF_MIN * 60), part)
        # 简化.11.9: the other way round too -- a stage the tool no longer reminds about is not listed with a time
        listed = part.split('参考用时是', 1)[1].split('（等 Saul', 1)[0]
        for n in st.STAGES:
            if n not in st.REF_MIN and n != 4:
                self.assertNotRegex(listed, r'第 %d 阶段 \d' % n, n)
        self.assertIn('第 3 阶段先不设', part)
        self.assertIn('由 `serve_preview.py` 自动记', part)
        table = part.split('| 阶段 | 步骤名', 1)[1].split('\n\n', 1)[0]
        rows = {}
        for line in table.splitlines()[2:]:
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows[cells[0]] = cells[1]
        for n, names in st.STEPS:
            label = '%d %s' % (n, st.STAGES[n]) if n else '哪个阶段都可能有'
            self.assertIn(label, rows, label)
            for name in names:
                self.assertIn(name, rows[label], (label, name))

    def test_every_stage_says_when_to_time(self):
        st = self.stages()
        lead = self.text().split('\n## 阶段', 1)[1].split('1. **盘点**', 1)[0]
        self.assertIn('`T` 是 `python3 <skills>/cocos-game-to-english/scripts/stage_timer.py --project <工程>`', lead)
        for n, phrases in ((1, ('`T stage 1`', '`T mark 中文原版链接`', '`T done`')), (2, ('`T stage 2`', '`T done`')),
                           (3, ('`T stage 3`', '`T link 1`', '`T done`', '贴在这条回复最后')),
                           (4, ('`T stage 4`', '`T back`', '`T link <第几轮>`', '`T done`')),
                           (5, ('`T stage 5`', '`T mark 交付`', '`T report --all`'))):
            for phrase in phrases:
                self.assertIn(phrase, st[n], (n, phrase))
        par = self.text().split('\n## 并行分工', 1)[1].split('\n## ', 1)[0]
        self.assertIn('`T begin <步骤> --who 美术子进程`', par)
        self.assertIn('子进程自己不记', par)

    def test_tool_and_its_test_ship_with_the_entry(self):
        self.assertTrue((HERE / 'stage_timer.py').is_file())
        self.assertTrue((HERE / 'test_stage_timer.py').is_file())
        r = subprocess.run([sys.executable, '-B', str(HERE / 'stage_timer.py'), '--help'], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8'))
        self.assertEqual(r.returncode, 0, r.stderr[-300:])

    def test_readme_names_the_timing_report(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        readme = README.read_text(encoding='utf-8')
        self.assertIn('stage_timer.py', readme)
        self.assertIn('用时', readme)


class ChineseAuditBeforeTrial(unittest.TestCase):
    """简化.11 (Saul 2026-11-01, 总表第 28 条): every English trial link passes the Chinese check first."""

    def text(self):
        return (ENTRY / 'SKILL.md').read_text(encoding='utf-8')

    def stages(self):
        section = self.text().split('\n## 阶段', 1)[1].split('\n## ', 1)[0]
        return section, {int(p[0]): p for p in re.split(r'\n(?=[1-5]\. \*\*)', section) if p[:1].isdigit()}

    def test_summary_and_lead_put_the_check_before_every_link(self):
        summary = self.text().split('\n## 一屏看懂', 1)[1].split('\n## ', 1)[0]
        three = [l for l in summary.splitlines() if l.startswith('- ③')][0]
        four = [l for l in summary.splitlines() if l.startswith('- ④')][0]
        self.assertIn('chinese_audit.py', three)
        self.assertIn('不过不给链接', three)
        self.assertLess(three.index('中文专项检查'), three.index('能进首页'))
        self.assertIn('中文专项检查', four)
        self.assertNotIn('④ 试玩改进：不跑检查', summary)
        section, _ = self.stages()
        lead = section.split('1. **盘点**', 1)[0]
        self.assertIn('中文专项检查、完整美工检查，修复并复查通过后给英文试玩链接', lead)
        self.assertNotIn('只确认能进首页、能玩一局，不跑检查。', lead)

    def test_stage_three_runs_scan_review_check_and_the_gated_link(self):
        _, st = self.stages()
        three = st[3]
        for phrase in ('chinese_audit.py', '`scan --project <工程> --export <这轮的 Web 导出>`', '`sheet --project <工程> --pending`',
                       'review --project <工程> --id <编号> --verdict', '--evidence', '`false_positive`', 'not_displayed --reason',
                       '`check --project <工程> --export <这轮的 Web 导出>`', 'isolated_render', '不能当成没有字',
                       'trial-links.json', '--draft', '一字不差', '手写的记录不算'):
            self.assertIn(phrase, three, phrase)
        link = [l for l in three.splitlines() if l.startswith('   起链接：')][0]
        self.assertIn('serve_preview.py --directory <这轮的 Web 导出> --project <工程> --snapshot --open --idle-minutes 0', link)
        self.assertLess(three.index('**中文专项检查'), three.index('中文专项检查和完整美工检查都通过后，再确认三件'))

    def test_stage_one_link_is_marked_chinese_original(self):
        _, st = self.stages()
        self.assertIn('--idle-minutes 0 --chinese-original --name "<游戏> 中文原版"', st[1])

    def test_later_rounds_and_the_delivery_link_check_again(self):
        _, st = self.stages()
        self.assertIn('每轮起新链接前做中文专项检查和受影响范围的完整美工复查', st[4])
        self.assertIn('scan 只识新加和改过的图', st[4])
        self.assertIn('中文专项检查照第 3 阶段对这份导出再过一次', st[5])
        self.assertIn('不能拿试玩的结果代替', st[5])

    def test_image_record_follows_the_chinese_check(self):
        _, st = self.stages()
        bullet = [l for l in st[2].splitlines() if l.startswith('   - **图片复核记录')][0]
        for phrase in ('照中文专项检查的结果写', 'docs/english/chinese-audit/', 'chinese_audit 自动扫描', '不能凭印象手写'):
            self.assertIn(phrase, bullet, phrase)

    def test_any_computer_section_names_the_recognizers(self):
        part = self.text().split('\n## 换电脑也能用', 1)[1].split('\n## ', 1)[0]
        bullet = [l for l in part.splitlines() if l.startswith('- **识字工具**')][0]
        for phrase in ('Vision', 'Windows', 'tesseract', '`sheet`', '不能当成没有字'):
            self.assertIn(phrase, bullet, phrase)

    def test_art_copy_names_the_exception(self):
        self.assertIn('中文专项检查另行照做；广告回归、平台兼容和其余出包检查仍在英化入口第 5 阶段', read('remake-art', 'references', 'art-before-trial.md'))

    def test_wrapper_offers_the_two_flags_and_the_tools_exist(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        r = subprocess.run([sys.executable, '-B', 'serve_preview.py', '--help'], cwd=str(HERE), env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-300:])
        for flag in ('--chinese-original', '--draft'):
            self.assertIn(flag, r.stdout, flag)
        for name in ('chinese_audit.py', 'ocr_vision.swift', 'ocr_windows.ps1', 'test_chinese_audit.py',
                     'test_serve_preview_gate.py'):
            self.assertTrue((HERE / name).is_file(), name)


class ReworkAfterDelivery(unittest.TestCase):
    """简化.11.15 (Saul 2026-11-04「出包后的返工修改，就只检查修改涉及的那些部分」): after a test package went out, a rework
    checks only what it changed; the entry says how, the shared tool exists and both writers take the old package."""
    CHECK = PACK / 'cocos-game-check' / 'package-check'

    def text(self):
        return (ENTRY / 'SKILL.md').read_text(encoding='utf-8')

    def test_stage5_says_how_to_rework(self):
        part = self.text().split('\n## 阶段', 1)[1].split('\n## ', 1)[0]
        stage5 = part.split('\n5. **', 1)[1]
        self.assertEqual(stage5.count('**出包后返工（简化.11.15'), 1)
        rework = stage5.split('**出包后返工（简化.11.15', 1)[1]
        for phrase in ('比如我修改了贴图，之后出包甚至又要检查一遍音频', 'rework_scope.py --old <出包文件夹> --native',
                       '先在构建的副本上装平台件、压 PNG', '出完包写包入口自己再记一份',
                       '`<工程>/docs/checks/rework-<时间>.json`', '「你（AI）自己要查的」', '不再听声音',
                       '不重测存档、广告流程', '改了代码：就地验证改的那个功能', '`--rework-of` 默认 `auto`',
                       '静态检查和 ZIP 核对每次都跑', '「返工范围」', '`--rework-of none`',
                       '](../cocos-game-check/package-check/references/runtime-regression.md#出包后返工只查改动简化1115saul-2026-11-04)'):
            self.assertIn(phrase, rework, phrase)
        summary = self.text().split('\n## 一屏看懂', 1)[1].split('\n## ', 1)[0]
        self.assertIn('见第 5 阶段「出包后返工」', [l for l in summary.splitlines() if l.startswith('- ⑤')][0])

    def test_tool_and_writers(self):
        tool = self.CHECK / 'scripts' / 'rework_scope.py'
        self.assertTrue(tool.is_file())
        self.assertTrue((self.CHECK / 'scripts' / 'test_rework_scope.py').is_file())
        r = subprocess.run([sys.executable, '-B', str(tool), '--help'], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8'))
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        for writer in (self.CHECK / 'scripts' / 'build_checked_zip.py', PACK / 'remake-core' / 'scripts' / 'make_tiktok_zip.py'):
            self.assertIn("'--rework-of', default='auto'", writer.read_text(encoding='utf-8'), writer.name)
        doc = (self.CHECK / 'references' / 'runtime-regression.md').read_text(encoding='utf-8')
        self.assertEqual(doc.count('\n### 出包后返工只查改动（简化.11.15'), 1)

    def test_readme_names_the_tool(self):
        if not README.is_file():
            self.skipTest('installed copies have no pack README; the release tree and ZIP do')
        self.assertIn('rework_scope.py', README.read_text(encoding='utf-8'))


class PreventionAtFirstBuild(unittest.TestCase):
    """前期预防 (蛋壳特工队会话 2026-11-04 写的，Saul 2026-11-05「前期预防也收进 11.15」): stage 1 also lists conditional
    states, the users of shared parts and what a change saves; stages 2 and 4 get one representative piece right before
    copying it and check a changed feature where it is wired. The full regression and packaging suites stay in stage 5."""
    PAGE = ENTRY / 'references' / 'early-prevention.md'

    def text(self):
        return (ENTRY / 'SKILL.md').read_text(encoding='utf-8')

    def test_stage_lead_points_at_the_page(self):
        lead = self.text().split('\n## 阶段', 1)[1].split('\n1. **', 1)[0]
        mark = '**前期预防（Saul 2026-11-04）**'
        self.assertEqual(lead.count(mark), 1)
        self.assertLess(lead.index(mark), lead.index('**先查美工，再给英文试玩链接'))
        para = [l for l in lead.splitlines() if l.startswith(mark)][0]
        for phrase in ('[前期预防](references/early-prevention.md)', '第 1 阶段读取', '先确认代表件实际状态，再批量制作',
                       '“第 5 阶段检查”指完整回归与出包套件', '不推迟这些制作和接入时的局部验证'):
            self.assertIn(phrase, para, phrase)

    def test_stage2_and_new_features_use_it(self):
        _, stages = TrialFirstThenFullChecks().stages()
        self.assertIn('按[前期预防](references/early-prevention.md)先确认本批代表件和实际状态，再铺到所有受影响使用位置',
                      stages[2].splitlines()[0])
        self.assertIn('新增功能先按[前期预防](references/early-prevention.md)做局部验证，玩法、经济等完整回归留到第 5 阶段',
                      self.text())

    def test_page_keeps_the_full_suites_in_stage5(self):
        page = self.PAGE.read_text(encoding='utf-8')
        for heading in ('## 第 1 阶段：按实际状态盘点，提前确定接入契约', '## 第 2 阶段：先把共享组件做对，再铺到其余位置',
                        '## 改功能时：保存和生命周期跟着实现一起处理', '## 发现新遗漏时如何避免再犯'):
            self.assertEqual(page.count('\n' + heading + '\n'), 1, heading)
        for phrase in ('完整广告、平台与出包套件仍在第 5 阶段', '这里不新增审批、独立清单或全量测试轮次',
                       '这里只做接入准备，正式套件仍由第 5 阶段执行', '未修改的系统不因此全量重测',
                       '这些局部结果也不代替第 5 阶段平台回归', '不填假成功、宽泛豁免或臆造命令'):
            self.assertIn(phrase, page, phrase)


class OriginalTrialServer(unittest.TestCase):
    """The stage-1 command (no --keep, no --project) serves the fixed-phone page for a Chinese-original export."""

    def test_original_export_is_served_without_project(self):
        with tempfile.TemporaryDirectory() as td:
            web = Path(td) / '本地试玩_中文原版（不用上传）'
            web.mkdir()
            (web / 'index.html').write_text('<html><canvas id="GameCanvas"></canvas></html>', encoding='utf-8')
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GAME_SKILL_LOCK_DIR=str(Path(td) / 'locks'))
            p = subprocess.Popen([sys.executable, '-B', 'serve_preview.py', '--directory', str(web), '--snapshot',
                                  '--no-browser', '--idle-minutes', '0', '--chinese-original', '--name', 'test 中文原版'],
                                 cwd=str(HERE), env=env,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            lines = []
            reader = threading.Thread(target=lambda: [lines.append(l) for l in p.stdout], daemon=True)
            reader.start()
            try:
                url, deadline = None, time.time() + 60
                while url is None and time.time() < deadline and p.poll() is None:
                    found = re.search(r'http://127\.0\.0\.1:\d+/', ''.join(lines))
                    url = found.group(0) if found else None
                    time.sleep(0.1)
                self.assertIsNotNone(url, 'no trial link printed: ' + ''.join(lines)[-800:])
                body = None
                for _ in range(100):
                    try:
                        body = urllib.request.urlopen(url, timeout=5).read()
                        break
                    except OSError:
                        time.sleep(0.1)
                self.assertIsNotNone(body, 'trial link did not answer')
                self.assertIn(b'fixed-phone-v1', body)
                self.assertNotIn('不起试玩服务', ''.join(lines))
            finally:
                p.terminate()
                try:
                    p.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
                reader.join(timeout=5)
                p.stdout.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
