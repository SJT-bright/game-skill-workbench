#!/usr/bin/env python3
"""Are the package-check tools in use the released ones? (v7.8, 总表 B32 d)

企鹅雪道 copied the ad-regression tools into its own qa/ folder, changed them (3.x camera, tap point) and judged its
package with them; nothing said that the result came from a changed tool, and the fix never reached the Skill.
identity(here) hashes the tools a check run uses -- check_package.py, build_checked_zip.py, prepare_delivery.py,
ad_regression.py, runtime_regression.py, everything under ad_regression/ and runtime_regression/ in that folder, and
the shared remake-core/scripts files they import (verify_native_zip, make_tiktok_zip, package_obligations,
package_issue_gate, delivery_folder, package_gates/) -- and compares each with
  * the release record of the Skill the files sit in (<skill>/PROVENANCE.json), and
  * every installed copy (~/.kiro/crew/skills, ~/.codex/skills, ~/.claude/skills, ~/.agents/skills and the packs one
    folder below them; $COCOS_SKILL_INSTALL_ROOTS replaces the list).
A file that matches neither is 「改过的工具」 (changed, or added). A loose copy outside any Skill folder (企鹅雪道's
qa/ad_regression_tool_fix/) is compared by its path inside package-check/scripts/. The check never refuses a package:
check_package and the writers put the list in their report, and write_draft() writes a feedback draft for the Skill
session into ！Skill更新/ (new file only, never overwrites; the same changes on the same day are not written twice).
The Skill maintenance tree (…/_内部/maintenance/…) is the place where the tools ARE changed: status dev_tree, nothing
reported. A run from a scratch or temporary copy (~/.kiro/crew/scratch/…, the system temp folder: a worker's snapshot,
a test fixture) is still reported, but writes no draft into ！Skill更新/ unless out_dir or $COCOS_SKILL_FEEDBACK_DIR asks
for one (10-30 23:01 a selftest snapshot wrote three such drafts there).
Run by hand: python3 -B tool_identity.py [--draft --game <name>]
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_ROOTS = 'COCOS_SKILL_INSTALL_ROOTS'
ENV_FEEDBACK = 'COCOS_SKILL_FEEDBACK_DIR'
FEEDBACK_DIR = Path.home() / 'Downloads' / '！自制游戏' / '启动包工坊' / '！Skill更新'
BASES = ('.kiro/crew/skills', '.codex/skills', '.claude/skills', '.agents/skills')
DEV_MARK = '/_内部/maintenance/'
CHECK_SCRIPTS = ('check_package.py', 'build_checked_zip.py', 'prepare_delivery.py', 'ad_regression.py',
                 'runtime_regression.py', 'tool_identity.py')
CHECK_DIRS = ('ad_regression', 'runtime_regression')
SHARED_SCRIPTS = ('verify_native_zip.py', 'make_tiktok_zip.py', 'package_obligations.py', 'package_issue_gate.py',
                  'delivery_folder.py')
SHARED_DIRS = ('package_gates',)
SKIP = {'__pycache__', '.DS_Store', 'node_modules'}
THROWAWAY_MARKS = ('/.kiro/crew/scratch/',)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install_roots():
    """Folders that hold installed Skills (each may contain cocos-game-check/ and remake-core/)."""
    env = os.environ.get(ENV_ROOTS)
    if env is not None:
        return [Path(p).expanduser().resolve() for p in env.split(os.pathsep) if p.strip()]
    out = []
    for base in BASES:
        root = Path.home() / base
        if not root.is_dir():
            continue
        for cand in [root] + sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith('.')):
            if (cand / 'cocos-game-check').is_dir() or (cand / 'remake-core').is_dir():
                out.append(cand.resolve())
    return out


def _walk(folder):
    for p in sorted(Path(folder).rglob('*')):
        if p.is_file() and not p.is_symlink() and not SKIP & set(p.relative_to(folder).parts) and p.suffix not in ('.pyc',):
            yield p


def tool_files(here=HERE):
    """[(path, skill, path inside the skill)] of the tools one check run uses."""
    here = Path(here).resolve()
    out = []
    for name in CHECK_SCRIPTS:
        if (here / name).is_file():
            out.append((here / name, 'cocos-game-check', 'package-check/scripts/' + name))
    for d in CHECK_DIRS:
        if (here / d).is_dir():
            for p in _walk(here / d):
                out.append((p, 'cocos-game-check', 'package-check/scripts/' + p.relative_to(here).as_posix()))
    shared = here.parents[2] / 'remake-core' / 'scripts' if len(here.parents) > 2 else None
    if shared and shared.is_dir() and here.parent.name == 'package-check':
        for name in SHARED_SCRIPTS:
            if (shared / name).is_file():
                out.append((shared / name, 'remake-core', 'scripts/' + name))
        for d in SHARED_DIRS:
            if (shared / d).is_dir():
                for p in _walk(shared / d):
                    out.append((p, 'remake-core', 'scripts/' + p.relative_to(shared).as_posix()))
    return out


def _provenance(skill_dir):
    try:
        data = json.loads((Path(skill_dir) / 'PROVENANCE.json').read_text(encoding='utf-8'))
        return data.get('revision'), {f['path']: f['sha256'] for f in data.get('files') or [] if isinstance(f, dict)}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None, None


def identity(here=HERE, roots=None):
    """-> {'status': clean | modified | dev_tree | unknown, 'location': installed | elsewhere | dev_tree, 'here',
    'release': revision of the record the files were compared with, 'modified': [{file, skill, rel, kind, sha256,
    release_sha256, installed}], 'summary': [short lines], 'checked': n}"""
    here = Path(here).resolve()
    out = {'here': str(here), 'modified': [], 'summary': [], 'checked': 0}
    if DEV_MARK in here.as_posix() + '/':
        out.update(status='dev_tree', location='dev_tree')
        return out
    roots = [Path(r).resolve() for r in (install_roots() if roots is None else roots)]
    skills_root = here.parents[2] if here.parent.name == 'package-check' and here.parents[1].name == 'cocos-game-check' else None
    out['location'] = 'installed' if skills_root is not None and skills_root in roots else 'elsewhere'
    records = {}
    for skill in ('cocos-game-check', 'remake-core'):
        revision, files = _provenance(skills_root / skill) if skills_root else (None, None)
        records[skill] = files or {}
        if revision and skill == 'cocos-game-check':
            out['release'] = revision
    any_reference = any(records.values())
    for path, skill, rel in tool_files(here):
        out['checked'] += 1
        digest = _sha(path)
        if records[skill].get(rel) == digest:
            continue
        installed = []
        for root in roots:
            other = root / skill / rel
            if other.is_file() and other.resolve() != Path(path).resolve():   # an edited installed file is not its own proof
                any_reference = True
                if _sha(other) == digest:
                    break
                installed.append(str(other))
        else:
            known = rel in records[skill] or bool(installed)
            out['modified'].append({'file': str(path), 'skill': skill, 'rel': rel, 'kind': 'changed' if known else 'added',
                                    'sha256': digest, 'release_sha256': records[skill].get(rel), 'installed': installed})
    if not any_reference:
        out['status'] = 'unknown'
        out['summary'] = ['no release record and no installed copy found to compare with (%s)' % here]
        out['modified'] = []
        return out
    out['status'] = 'modified' if out['modified'] else 'clean'
    out['summary'] = ['%s/%s %s' % (m['skill'], m['rel'], '改过' if m['kind'] == 'changed' else '安装版里没有')
                      for m in out['modified']][:12]
    if out['location'] == 'elsewhere' and out['modified']:
        out['summary'].insert(0, '用的不是安装目录里的工具：%s' % here)
    return out


def _diff(m, limit=80):
    if not m['installed']:
        if m['kind'] == 'added':
            return ['（安装目录里没有这个文件，整份是新加的）']
        return ['（就是安装目录里的文件被直接改了，没有别的副本可以对比；发版记录的 sha256 见上）']
    a, b = Path(m['installed'][0]), Path(m['file'])
    try:
        old = a.read_text(encoding='utf-8').splitlines()
        new = b.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return ['（二进制或读不出，只比了 sha256）']
    lines = list(difflib.unified_diff(old, new, str(a), str(b), n=1, lineterm=''))
    if len(lines) > limit:
        lines = lines[:limit] + ['…（还有 %d 行，见原文件）' % (len(lines) - limit)]
    return lines


def fingerprint(ident):
    return hashlib.sha256(json.dumps(sorted((m['rel'], m['sha256']) for m in ident['modified'])).encode()).hexdigest()[:16]


def throwaway(path):
    """True when the tools run from a scratch or temporary copy (a worker's snapshot, a test fixture)."""
    try:
        p = str(Path(path).resolve())
        tmp = str(Path(tempfile.gettempdir()).resolve()).rstrip(os.sep) + os.sep
    except (OSError, RuntimeError):
        return False
    return any(m in p for m in THROWAWAY_MARKS) or p.startswith(tmp)


def write_draft(ident, game, out_dir=None, today=None):
    """Write the feedback draft for the Skill session. -> path written, or None (nothing modified, dev tree, a scratch /
    temporary copy with no explicit out_dir, or the same changes already have a draft today). Never overwrites: a taken
    name gets _2, _3 ..."""
    if ident.get('status') != 'modified':
        return None
    if out_dir is None and not os.environ.get(ENV_FEEDBACK) and throwaway(ident.get('here') or ''):
        return None
    out_dir = Path(out_dir or os.environ.get(ENV_FEEDBACK) or FEEDBACK_DIR)
    day = (today or datetime.date.today()).strftime('%Y%m%d')
    safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(game or 'unknown'))[:60] or 'unknown'
    stem = '反馈草稿_改过的工具_%s_%s' % (safe, day)
    fp = fingerprint(ident)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(stem + '*.md'):
        try:
            if ('指纹：' + fp) in old.read_text(encoding='utf-8'):
                return None
        except OSError:
            continue
    lines = ['# 反馈草稿：%s 用了改过的检查工具（%s）' % (game, day), '',
             '这份是 check_package / 写包入口自动写的草稿，发给 Skill 制作会话前请人看一遍。', '',
             '- 工具所在：%s（%s）' % (ident['here'], '安装目录' if ident['location'] == 'installed' else '不在安装目录'),
             '- 对照：%s 的发版记录和安装目录里的副本' % (ident.get('release') or '（工具所在处没有 PROVENANCE）'),
             '- 改过的文件：%d 个' % len(ident['modified']), '- 指纹：' + fp, '']
    for m in ident['modified']:
        lines += ['## %s/%s（%s）' % (m['skill'], m['rel'], '改过' if m['kind'] == 'changed' else '安装版里没有'), '',
                  '- 现在用的：%s' % m['file'], '- sha256：%s（发版记录：%s）' % (m['sha256'], m['release_sha256'] or '无'),
                  '', '```diff'] + _diff(m) + ['```', '']
    lines += ['## 要 Skill 会话做的', '', '看上面的改动是不是 Skill 也该改：该改的合进 Skill（照常配坏包/好包证明），'
              '不该改的告诉这款游戏的会话换回安装版工具重测。', '']
    path = out_dir / (stem + '.md')
    n = 2
    while path.exists():
        path = out_dir / ('%s_%d.md' % (stem, n))
        n += 1
    with open(path, 'x', encoding='utf-8') as f:      # 'x': never overwrites a file another run just wrote
        f.write('\n'.join(lines))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--here', type=Path, default=HERE, help='the package-check scripts folder in use (default: this one)')
    ap.add_argument('--draft', action='store_true', help='write the feedback draft when something is modified')
    ap.add_argument('--game', default='unknown')
    ap.add_argument('--out-dir', type=Path, help='draft folder (default $%s or ！Skill更新/)' % ENV_FEEDBACK)
    a = ap.parse_args()
    ident = identity(a.here)
    if a.draft:
        ident['draft'] = str(write_draft(ident, a.game, a.out_dir) or '')
    print(json.dumps(ident, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
