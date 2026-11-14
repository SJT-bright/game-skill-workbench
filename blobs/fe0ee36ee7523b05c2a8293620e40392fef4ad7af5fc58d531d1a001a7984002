#!/usr/bin/env python3
"""已作废说法残留检查（规则口径统一，基于 11.17.27）。

新规则以前是在各 Skill 开头加一条横幅，旧正文留着：入口表、验收清单、触发描述里还是旧说法，只读到这些地方的
模型会按旧口径做。这个检查把已经作废的说法列成表：这些句子再出现在包里，就报文件和行号。

一句旧说法可以留在两种地方：
1. 同一行里写明它是旧口径（有“旧合同”“局部维护”“取代”这类词），用来说明旧合同怎么维护；
2. 下面 KNOWN 里列出的文件。每一项都写了现在不能改的原因；文件清理干净以后这一项要删掉，不删测试会失败。

新增一条作废说法时：在 RETIRED 里加一行，写上现行规则在哪、一个会被抓住的旧句子、一个允许保留的写法。
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_retired_phrases.py
"""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parents[1]
PACK_SKILLS = ('ad-boost', 'chrome-mobile-testing', 'cocos-game-check', 'cocos-game-to-english', 'ego-browser',
               'grok-delegate', 'grok-image-review', 'mobile-touch-computer-use', 'remake-ads', 'remake-art',
               'remake-core', 'remake-economy', 'remake-skins')
PACK_FILES = ('README_先看这里.txt', '六节点融合说明.md', '本次补丁合并说明.md')
TEXT = ('.md', '.txt', '.json', '.py', '.js', '.mjs', '.cjs', '.ts', '.yaml', '.yml')

# 同一行里有这些词，说明这句话是在讲旧口径或旧合同，可以保留。
LEGACY = ('旧合同', '旧调度', '旧口径', '旧说法', '原调度', '原口径', '局部维护', '取代', '作废', '已撤销')

RETIRED = (
    {'id': 'revive-energy-bar',
     'pattern': r'能量条做法|设计一个真实失败点（能量条',
     'retired': '11.17.23（2026-11-10）',
     'current': 'cocos-game-to-english/references/fixed-entries.md「看广告复活」：没有失败状态的游戏按玩法挑一个合理的结束点，'
                '用增加一次真实游戏机会承接，不增造失败条件或能量条',
     'stale': '没有失败状态的游戏也加（按 MusicSlice v30 的能量条做法）。',
     'legacy_ok': '2026-11-10 起取代原来的能量条做法。'},
    {'id': 'trial-before-level',
     'pattern': r'第 ?3(、6、9[…\.·]*)? ?关开始前',
     'retired': '用户 2026-11-11（六标准）',
     'current': 'remake-economy/references/economy-rules.md 第十五节第 6 条：完整六标准制作在真实完成第 3、6、9……局后的局间邀请'
                '（ad-boost round-trial）',
     'stale': '有皮肤就有试用弹窗：前 2 关不弹，第 3、6、9……关开始前弹。',
     'legacy_ok': '已交付旧合同的局部维护沿用第 3、6、9……关开始前弹。'},
    {'id': 'energy-only-original',
     'pattern': r'没有(体力)?不新增|不因此新增体力|原游戏有体力才(做|写)|不新加体力|不新增体力',
     'retired': '用户 2026-11-11（六标准）',
     'current': 'remake-economy/references/economy-rules.md 第十节：原游戏没有体力时，完整六标准制作先装真实体力系统再接看广告 +3',
     'stale': '原游戏有体力才做，没有不新增。',
     'legacy_ok': '已交付旧合同的无关局部维护不新增体力。'},
    {'id': 'english-no-skins',
     'pattern': r'英化(游戏)?默认不加皮肤',
     # 这句话原来常和“取代 10-21 的英化＋优化”写在同一行，所以这一条不认“取代”，只认下面三个词。
     'ok_words': ('旧合同', '局部维护', '六标准'),
     'retired': '用户 2026-11-11（六标准）',
     'current': 'remake-skins/SKILL.md：英化完整六标准制作主动调用皮肤板块，补齐至少 10 款永久皮肤和周期试用',
     'stale': '英化游戏默认不加皮肤，Saul 要求创新玩法时才用。',
     'legacy_ok': '用户 2026-11-11 六标准取代了“英化默认不加皮肤”。'},
    {'id': 'ads-only-on-request',
     'pattern': r'新加别的看广告入口[^。\n]*只在 Saul 要求创新玩法时做',
     'retired': '用户 2026-11-11（六标准）',
     'current': 'remake-ads/SKILL.md：完整制作由同包 ad-boost 补齐六标准类，本板块管这些入口的广告行为',
     'stale': '新加别的看广告入口（首页礼盒、体力、局内道具）只在 Saul 要求创新玩法时做。',
     'legacy_ok': '用户 2026-11-11 六标准取代了“新加别的看广告入口只在 Saul 要求创新玩法时做”。'},
    {'id': 'adboost-by-recommendation',
     'pattern': r'按诊断推荐加|按推荐加看广告的板块',
     'retired': '用户 2026-11-11（六标准）',
     'current': 'ad-boost/SKILL.md：六类标准节点全部必备，按六标准类核实并补齐，不再按广告量推荐前几名',
     'stale': '默认按本包的 ad-boost 诊断，按推荐加看广告的板块（转盘、礼包、签到……）。',
     'legacy_ok': '用户 2026-11-11 六标准取代了旧的“按诊断推荐加”。'},
    {'id': 'core-rules-unused',
     'pattern': r'英化(流程)?不使用其中的重塑板块规则',
     'retired': '用户 2026-11-11（六标准）',
     'current': 'remake-core/SKILL.md：英化只在六标准广告需要时用其中的经济、皮肤、签到规则',
     'stale': '英化流程不使用其中的重塑板块规则（关卡、经济、皮肤、签到、教程等）。',
     'legacy_ok': '用户 2026-11-11 六标准取代了“英化不使用其中的重塑板块规则”。'},
)

# 现在还留着旧说法、这次有意不改的文件。值是原因。清理干净以后要从这里删掉（test_known_entries_are_still_needed）。
KNOWN = {}


def skipped(rel):
    """历史记录、学习库副本、测试和清单不查。"""
    name = rel.rsplit('/', 1)[-1]
    return (rel.startswith('ad-boost/vendor/')                                   # 学习库副本，从学习库同步
            or rel == 'remake-core/assets/active-skill-advice.json'              # 维护期禁用句式与反例登记，不是制作指令
            or name in ('更新记录.txt', '版本历史.md', 'CHANGELOG.md', '验收记录.md')    # 历史与验收记录
            or name in ('distribution-manifest.json', 'PROVENANCE.json')         # 分发清单
            or name.startswith('test_') or '.test.' in name                      # 测试本身会引用旧句子
            or '/fixtures/' in rel or '/tests/' in rel or '/test/' in rel)        # 测试夹具


def hits_in_line(line):
    """这一行里没有标成旧口径的作废说法：[(规则 id, 命中的文字)]。放行词默认是 LEGACY，规则可以用 ok_words 另定。"""
    found = []
    for rule in RETIRED:
        match = re.search(rule['pattern'], line)
        if match and not any(word in line for word in rule.get('ok_words', LEGACY)):
            found.append((rule['id'], match.group(0)))
    return found


def scan(root=PACK):
    """返回 {相对路径: [(行号, 规则 id, 命中文字)]}，只含有命中的文件，跳过 skipped()。"""
    files = [root / name for name in PACK_FILES if (root / name).is_file()]
    for skill in PACK_SKILLS:
        base = root / skill
        if base.is_dir():
            files += [p for p in sorted(base.rglob('*')) if p.is_file() and p.suffix in TEXT
                      and '__pycache__' not in p.parts and 'node_modules' not in p.parts]
    out = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        if skipped(rel):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        rows = [(number, rule_id, words) for number, line in enumerate(text.split('\n'), 1)
                for rule_id, words in hits_in_line(line)]
        if rows:
            out[rel] = rows
    return out


class RetiredPhrases(unittest.TestCase):
    def test_each_rule_catches_its_stale_sentence_and_allows_the_legacy_form(self):
        for rule in RETIRED:
            self.assertIn(rule['id'], [rid for rid, _ in hits_in_line(rule['stale'])], rule['id'] + '：旧句子没被抓住')
            self.assertEqual(hits_in_line(rule['legacy_ok']), [], rule['id'] + '：标明旧口径的写法被误报')

    def test_no_retired_phrase_outside_the_known_files(self):
        found = scan()
        new = {rel: rows for rel, rows in found.items() if rel not in KNOWN}
        lines = ['%s:%d 「%s」已作废（%s）。现行：%s' % (rel, number, words, rule['retired'], rule['current'])
                 for rel, rows in sorted(new.items()) for number, rule_id, words in rows
                 for rule in RETIRED if rule['id'] == rule_id]
        self.assertEqual(new, {}, '\n' + '\n'.join(lines))

    def test_known_entries_are_still_needed(self):
        found = scan()
        for rel, why in KNOWN.items():
            if (PACK / rel).is_file():
                self.assertIn(rel, found, rel + ' 已经没有作废说法，请从 KNOWN 里删掉这一项（原来留着的原因：' + why + '）')

    def test_active_production_advice_has_no_retired_steps(self):
        import importlib.util
        source = PACK / 'remake-core/scripts/active_skill_advice.py'
        spec = importlib.util.spec_from_file_location('retired_active_advice', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.scan(PACK), [])

    def test_scan_finds_a_planted_stale_line(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill = root / 'remake-skins'
            skill.mkdir()
            (skill / 'SKILL.md').write_text('# 皮肤板块\n\n英化游戏默认不加皮肤，Saul 要求创新玩法时才用。\n', encoding='utf-8')
            (skill / 'ok.md').write_text('已交付旧合同的局部维护沿用第 3、6、9……关开始前弹。\n', encoding='utf-8')
            found = scan(root)
        self.assertEqual(list(found), ['remake-skins/SKILL.md'])
        self.assertEqual(found['remake-skins/SKILL.md'], [(3, 'english-no-skins', '英化游戏默认不加皮肤')])


if __name__ == '__main__':
    found = scan()
    kept = {rel: rows for rel, rows in found.items() if rel in KNOWN}
    if kept:
        print('已知遗留（这次有意不改）：')
        for rel in sorted(kept):
            print('  %s  %d 处。%s' % (rel, len(kept[rel]), KNOWN[rel]))
    unittest.main()
