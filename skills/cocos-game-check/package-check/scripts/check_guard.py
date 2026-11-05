#!/usr/bin/env python3
"""Shared start-of-check guard for Skill check scripts (总表 P20, 2026-11-04 问题普查 T20).

The 11-04 survey counted 969 Skill-side problems: good packages blocked by the checker, checks that ran 0 items and
still said pass, --help parsed as a JSON input, a missing Pillow ending in a Traceback, and a text checker that took
the wrong same-name node as a text's container (这也太牛了: 178 false overflow blocks). Every check script uses these
helpers instead of writing its own:

  engine_of(path)            -> {'major': 2|3|None, 'version': '3.8.8', 'evidence': 'package.json creator.version'}
  zero_items(report, ...)    -> a report that checked 0 items becomes status "not_run", passed False, with the reason
                                 and what is missing. Never "pass", never a silent skip.
  need_modules('PIL', ...)   -> a missing Python module is a "not_run" JSON line with the install command, exit 2.
                                 --help still prints the script's help text.
  NodeIndex(nodes)           -> container / ancestor lookups by node identity (ui_dump id + ancestor_ids), so two
                                 nodes that share a name (and therefore a path string) are never confused.

Python 3.9 compatible, standard library only, no machine paths. Exit code for "not run" is NOT_RUN_EXIT (2), which every
Skill writer already treats as "not passed".
"""
import json
import sys
from pathlib import Path

NOT_RUN_EXIT = 2
INSTALL_HINT = {'PIL': 'python3 -m pip install pillow', 'numpy': 'python3 -m pip install numpy'}
# 总表 P19 ③: the report statuses live in one JSON file; producers and receivers read it here.
STATUS_FILE = Path(__file__).resolve().parents[1] / 'references' / 'check-status.json'


def status_values(kind='check'):
    """The allowed report statuses of one kind ('check' or 'image_review') from references/check-status.json."""
    doc = json.loads(STATUS_FILE.read_text(encoding='utf-8'))
    return tuple(doc[kind]['values'])


def status_passing(kind='check'):
    doc = json.loads(STATUS_FILE.read_text(encoding='utf-8'))
    return tuple(doc[kind].get('passing') or ())


def is_empty(value):
    """An input that is absent or holds nothing: None, '', whitespace, [], {} (a {"n/a": reason} / {"none": reason}
    declaration is not empty: it says why there is nothing)."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def input_gaps(inputs):
    """inputs: {name: value} of what a check needs. -> [name] of every input that is absent or empty, in order.
    总表 P19 ②: an empty list (割草 ad entries) or an unwritten field (人鱼 pause key) is reported here, never skipped."""
    return [name for name, value in inputs.items() if is_empty(value)]


def inputs_not_run(tool, inputs, fix='', **extra):
    """None when every input is there; else the not_run report naming each missing input and how to make it."""
    missing = input_gaps(inputs)
    if not missing:
        return None
    reason = '检查要的输入缺失或为空：%s。本项检查没有执行，不算通过' % '、'.join(missing)
    if fix:
        reason += '；' + fix
    return not_run(tool, reason, missing, **extra)


def help_requested(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    return any(a in ('-h', '--help') for a in argv)


def not_run(tool, reason, missing=(), **extra):
    """The one shape of "this check did not run" (never a pass)."""
    report = {'tool': tool, 'status': 'not_run', 'passed': False, 'checked': 0, 'reason': reason,
              'missing': list(missing)}
    report.update(extra)
    return report


def emit_not_run(tool, reason, missing=(), out=None, **extra):
    report = not_run(tool, reason, missing, **extra)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(NOT_RUN_EXIT)


def need_modules(*names, tool=None, doc=None):
    """Import check for third-party modules a script needs at import time. --help prints the help text (the module
    docstring) plus what is missing and exits 0; any other call prints a not_run line and exits 2."""
    missing = []
    for name in names:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if not missing:
        return
    main = sys.modules.get('__main__')
    tool = tool or Path(getattr(main, '__file__', '') or 'check').stem
    fix = '；'.join(INSTALL_HINT.get(m, 'python3 -m pip install ' + m) for m in missing)
    if help_requested():
        print((doc or getattr(main, '__doc__', None) or tool).strip())
        print('\n运行需要：%s（这台电脑的 %s 没装，先运行：%s）' % ('、'.join(missing), sys.executable, fix))
        raise SystemExit(0)
    emit_not_run(tool, '缺少 Python 模块 %s，本项检查没有执行，不算通过' % '、'.join(missing), missing,
                 fix=fix, python=sys.executable)


def engine_of(path):
    """Cocos engine major version of a source project, a web/minigame export or a package folder. Unknown is None
    (callers must report it, never skip the check group)."""
    root = Path(path)
    if root.is_file():
        root = root.parent
    try:
        pkg = json.loads((root / 'package.json').read_text(encoding='utf-8-sig'))
        version = str((pkg.get('creator') or {}).get('version') or '')
        if version[:1].isdigit():
            return {'major': int(version.split('.')[0]), 'version': version, 'evidence': 'package.json creator.version'}
    except (OSError, ValueError, AttributeError):
        pass
    try:
        proj = json.loads((root / 'project.json').read_text(encoding='utf-8-sig'))
        version = str(proj.get('version') or '')
        if proj.get('engine') == 'cocos-creator-js' or version.startswith('2.'):
            return {'major': 2, 'version': version, 'evidence': 'project.json'}
    except (OSError, ValueError, AttributeError):
        pass
    for rel, major in (('cocos/cocos2d-js-min.js', 2), ('cocos/cocos2d-js.js', 2), ('cocos2d-js-min.js', 2)):
        if (root / rel).is_file():
            return {'major': major, 'version': '', 'evidence': rel}
    if (root / 'cocos-js').is_dir():
        return {'major': 3, 'version': '', 'evidence': 'cocos-js/'}
    if any(root.glob('cocos2d-js*.js')) or any(root.glob('src/settings*.js')):
        return {'major': 2, 'version': '', 'evidence': 'cocos2d-js / src/settings.js'}
    return {'major': None, 'version': '', 'evidence': 'no package.json creator.version, project.json or engine file'}


def zero_items(report, checked_key='checked', what='', need='', engine=None):
    """A report that would pass after checking nothing becomes not_run. Returns the (changed) report."""
    if report.get('passed') is True and not report.get(checked_key):
        report['passed'] = False
        report['status'] = 'not_run'
        report['reason'] = '实际检查 0 项%s，不能判通过%s' % (
            '（%s）' % what if what else '', '；需要：%s' % need if need else '')
        if engine is not None:
            report['engine'] = engine
    return report


class NodeIndex:
    """ui_dump node identity. A dump path is built from names, so same-name siblings share a path string and
    path-prefix tests pick the wrong parent. With id + ancestor_ids (ui_dump.js since v7.8) every node gets an
    identity key with one id per path segment; old dumps without ids fall back to the path string and the index says
    so (ambiguous_paths lists the paths that more than one node shares)."""

    def __init__(self, nodes):
        self.nodes = [n for n in nodes if isinstance(n, dict)]
        counts = {}
        for n in self.nodes:
            counts[str(n.get('path', ''))] = counts.get(str(n.get('path', '')), 0) + 1
        self.ambiguous_paths = sorted(p for p, c in counts.items() if c > 1)
        keys = [self._id_key(n) for n in self.nodes]
        self.by_id = all(k is not None for k in keys) and bool(keys)
        self._key = {id(n): (k if self.by_id else str(n.get('path', ''))) for n, k in zip(self.nodes, keys)}

    @staticmethod
    def _id_key(n):
        segs = str(n.get('path', '')).split('/')
        ids = [n.get('id')] + list(n.get('ancestor_ids') or [])
        if not n.get('id') or len(ids) < len(segs):
            return None
        return '/'.join('%s@%s' % (s, ids[len(segs) - 1 - i]) for i, s in enumerate(segs))

    def key(self, n):
        return self._key.get(id(n)) or str(n.get('path', ''))

    def under(self, n, anc):
        """n is anc or a descendant of anc (identity, not name)."""
        a, b = self.key(n), self.key(anc)
        return a == b or a.startswith(b + '/')

    def ancestors(self, n, pred=None, include_self=False):
        return [x for x in self.nodes if (x is not n or include_self) and self.under(n, x) and (pred is None or pred(x))
                and (x is n or self.key(x) != self.key(n))]

    def nearest_ancestor(self, n, pred=None, include_self=False):
        found = self.ancestors(n, pred, include_self)
        return max(found, key=lambda x: self.key(x).count('/')) if found else None
