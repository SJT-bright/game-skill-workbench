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
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_entry_consistency.py
"""
import os
import re
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
OWN = ('cocos-game-to-english', 'cocos-game-check', 'remake-core', 'remake-art') + AD_BOARDS
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
        self.assertIn('Saul 要求创新玩法时才按广告板块做', block)
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
        self.assertIn('英化自动用的只有固定入口的数额', eco.split('\n---', 1)[0])
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
        for name in ('cocos-game-to-english',) + AD_BOARDS:
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
        for name in AD_BOARDS:
            self.assertIn('- %s：' % name, skills)
        if CODEX_TEXT.is_file():
            self.assertNotIn('本包不需要重塑包', CODEX_TEXT.read_text(encoding='utf-8'))


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

    def test_entry_sends_too_few_ads_to_ad_boost_with_english_limits(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        block = text.split('**看广告的几项按广告板块做', 1)[1].split('\n## ', 1)[0]
        self.assertEqual(block.count('**Saul 说广告太少时用 ad-boost（Saul 2026-10-31）**'), 1)
        part = block.split('**Saul 说广告太少时用 ad-boost', 1)[1]
        for phrase in ('~/.kiro/crew/skills/ad-boost/SKILL.md', '可多选的选择题',
                       'Saul 在 ad-boost 的选择题里选了哪个板块，就是授权', '没选的不加',
                       '只在原游戏本来就有这个系统时才加', '原首页按钮一个都不动', '新入口只放空位', '跟原游戏画风走'):
            self.assertIn(phrase, part)

    def test_ad_board_copy_has_the_ad_boost_section(self):
        lines = (PACK / 'remake-ads' / 'SKILL.md').read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines.count('## 加广告载体用 ad-boost（Saul 2026-10-31）'), 1)
        self.assertEqual(sum(l.startswith('- [ ] 用 ad-boost 加的板块（Saul 2026-10-31）') for l in lines), 1)
        section = '\n'.join(lines).split('## 加广告载体用 ad-boost', 1)[1].split('\n## ', 1)[0]
        self.assertIn('英化游戏只在 Saul 说广告太少', section)
        self.assertIn('原首页按钮不动', section)

    def test_redesign_keeps_the_original_art_style(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split('## 美工 Skill 只在点名时用', 1)[1].split('\n## ', 1)[0]
        for phrase in ('“重新设计”英化游戏时，画风也照原游戏', '原图能用就用', '按钮底色不用深色', '图标后面不另加底板',
                       '只有他明说换画风'):
            self.assertIn(phrase, section)


class OriginalTrialServer(unittest.TestCase):
    """The stage-1 command (no --keep, no --project) serves the fixed-phone page for a Chinese-original export."""

    def test_original_export_is_served_without_project(self):
        with tempfile.TemporaryDirectory() as td:
            web = Path(td) / '本地试玩_中文原版（不用上传）'
            web.mkdir()
            (web / 'index.html').write_text('<html><canvas id="GameCanvas"></canvas></html>', encoding='utf-8')
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GAME_SKILL_LOCK_DIR=str(Path(td) / 'locks'))
            p = subprocess.Popen([sys.executable, '-B', 'serve_preview.py', '--directory', str(web), '--snapshot',
                                  '--no-browser', '--idle-minutes', '0', '--name', 'test 中文原版'], cwd=str(HERE), env=env,
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
