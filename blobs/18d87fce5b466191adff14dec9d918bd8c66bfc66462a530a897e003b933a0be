#!/usr/bin/env python3
"""audit_page_coverage.py -- pages come from the project's prefabs, not from a hand-written list (Saul 2026-11-04,
蛋壳特工队: 21 of 47 layers had never been dumped and the capture gate passed). Run: python3 -m unittest test_page_coverage"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_page_coverage as C  # noqa: E402


def prefab(root, children):
    """A Cocos 3.x-shaped prefab: [cc.Prefab, root node, child nodes..., components...]."""
    arr = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
           {'__type__': 'cc.Node', '_name': root, '_children': [], '_components': []}]
    for name, kind, text in children:
        node = {'__type__': 'cc.Node', '_name': name, '_children': [], '_components': []}
        arr.append(node)
        arr[1]['_children'].append({'__id__': len(arr) - 1})
        if kind:
            comp = {'__type__': kind}
            if text is not None:
                comp['_string'] = text
            arr.append(comp)
            node['_components'].append({'__id__': len(arr) - 1})
    return arr


class Coverage(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='pagecov_'))
        (self.root / 'assets/layer').mkdir(parents=True)
        (self.root / 'docs/test').mkdir(parents=True)
        self.write('VipLayer', [('title', 'cc.Label', 'VIP Perks'), ('btnClose', 'cc.Button', None)])
        self.write('PatrolFastLayer', [('Label', 'cc.Label', 'Claim 300 minutes of Patrol rewards now'),
                                       ('btnGet', 'cc.Button', None), ('getLabel', 'cc.Label', 'Get Free')])
        self.write('propItem', [('num', 'cc.Label', '100')])          # a part used inside pages, not a page
        self.n = 0

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, name, children):
        (self.root / 'assets/layer' / (name + '.prefab')).write_text(json.dumps(prefab(name, children)), encoding='utf-8')

    def dump(self, size, paths_texts):
        self.n += 1
        nodes = [{'path': p, 'name': p.rsplit('/', 1)[-1], 'order': i, 'opacity': 1, 'rect': [0, 0, .1, .1],
                  'comps': {'label': {'string': t}} if t else {}} for i, (p, t) in enumerate(paths_texts)]
        d = {'tool': 'ui_dump', 'schema': 1, 'screen': 's%d' % self.n, 'kind': 'popup', 'scene': 'Main',
             'viewport': {'width': size[0], 'height': size[1]}, 'canvas_css': [0, 0, size[0], size[1]], 'nodes': nodes}
        (self.root / 'docs/test' / ('%03d-ui-dump-s%d.json' % (self.n, self.n))).write_text(json.dumps(d), encoding='utf-8')

    def result(self):
        return C.audit(self.root, [self.root / 'docs/test'])

    def test_popup_never_opened_is_listed(self):
        for size in ((393, 852), (375, 667)):
            self.dump(size, [('Canvas/layer1/VipLayer/title', 'VIP Perks')])
        r = self.result()
        self.assertFalse(r['passed'])
        self.assertEqual([m['root'] for m in r['missing']], ['PatrolFastLayer'])
        self.assertIn('PatrolFastLayer', C.summary(r))
        self.assertNotIn('propItem', [p['root'] for p in r['pages_list']])

    def test_one_phone_size_is_not_enough(self):
        self.dump((393, 852), [('Canvas/layer1/VipLayer/title', 'VIP Perks'),
                               ('Canvas/layer1/PatrolFastLayer/Label', 'Claim 300 minutes of Patrol rewards now')])
        self.dump((375, 667), [('Canvas/layer1/VipLayer/title', 'VIP Perks')])
        r = self.result()
        self.assertEqual([(m['root'], m['status']) for m in r['missing']], [('PatrolFastLayer', 'seen_once')])

    def test_all_covered_or_declared_unreachable(self):
        self.write('MoreGameLayer', [('title', 'cc.Label', 'More Games')])
        (self.root / 'docs/art').mkdir(parents=True)
        (self.root / 'docs/art/screens.json').write_text(json.dumps(
            {'not_reachable': [{'prefab': 'MoreGameLayer', 'why': '更多游戏入口按英化规则删了'}]}), encoding='utf-8')
        for size in ((393, 852), (375, 667)):
            self.dump(size, [('Canvas/layer1/VipLayer/title', 'VIP Perks'),
                             ('Canvas/layer1/PatrolFastLayer/Label', 'Claim 300 minutes of Patrol rewards now')])
        r = self.result()
        self.assertTrue(r['passed'], r['missing'])
        self.assertEqual([x['root'] for x in r['not_reachable']], ['MoreGameLayer'])

    def test_reason_is_required(self):
        self.write('MoreGameLayer', [('title', 'cc.Label', 'More Games')])
        (self.root / 'docs/art').mkdir(parents=True)
        (self.root / 'docs/art/screens.json').write_text(json.dumps({'not_reachable': [{'prefab': 'MoreGameLayer'}]}),
                                                          encoding='utf-8')
        for size in ((393, 852), (375, 667)):
            self.dump(size, [('Canvas/layer1/VipLayer/title', ''), ('Canvas/layer1/PatrolFastLayer/Label', '')])
        self.assertIn('MoreGameLayer', [m['root'] for m in self.result()['missing']])

    def test_renamed_instance_found_by_its_nodes(self):
        self.write('ShopLayer', [('Draw1', 'cc.Button', None), ('Draw10', 'cc.Button', None), ('poster', 'cc.Label', 'Shop'),
                                 ('guarantee', 'cc.Label', 'DRAWS TO GUARANTEE')])
        for size in ((393, 852), (375, 667)):
            self.dump(size, [('Canvas/layer1/VipLayer/title', ''), ('Canvas/layer1/PatrolFastLayer/Label', ''),
                             ('Canvas/layer1/shopPopup/Draw1', ''), ('Canvas/layer1/shopPopup/Draw10', ''),
                             ('Canvas/layer1/shopPopup/poster', 'Shop'), ('Canvas/layer1/shopPopup/guarantee', '')])
        self.assertTrue(self.result()['passed'])

    def test_state_never_opened_is_a_hint(self):
        (self.root / 'docs/copy').mkdir(parents=True)
        (self.root / 'docs/copy/copy-table.csv').write_text(
            'zh,en,source,field\n'
            '免费获得,Get Free,assets/layer/PatrolFastLayer.prefab,/7/_string\n'
            '旧的,Old Text,assets/layer/PatrolFastLayer.prefab,/2/_string\n', encoding='utf-8')
        for size in ((393, 852), (375, 667)):
            self.dump(size, [('Canvas/layer1/VipLayer/title', 'VIP Perks'),
                             ('Canvas/layer1/PatrolFastLayer/Label', 'Claim 300 minutes of Patrol rewards now')])
        r = self.result()
        self.assertTrue(r['passed'])                       # pages decide; the text list is to look at
        self.assertEqual([s['text'] for s in r['strings_missing']], ['Get Free'])   # the stale row is skipped
        self.assertIn('Get Free', C.summary(r))


if __name__ == '__main__':
    unittest.main()
