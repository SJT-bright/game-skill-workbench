"""Native step: the three old Cocos 2.4 ByteDance adapter forms (design D77 1.3 row adapter.py, 3.5). Both policies.

Calls the v7.5 package_gates.adapter_fix.apply(native) unchanged (its own tests stay as they are): SDKVersion,
sub-context test and the in-package fs.access probe must each match exactly once and are rewritten; the fixed
form is left alone; an unknown adapter blocks. Cocos 3.x has no such adapter (web-adapter): n/a.
Not done here (open item): the RestoreLines globalThis entry rule ('global_entry'); the design names it but no
exact old/new form has been recorded yet, and a guessed rewrite would not be "exactly once".
"""
from . import Result, sha256

STEP = 'adapter'


def _fix():
    from package_gates import adapter_fix
    return adapter_fix


def detect(ctx):
    if ctx.engine != 2:
        return 'n/a'
    state = _fix().detect(ctx.files(root_only=True) | {k: v for k, v in ctx.files().items()
                                                        if k.startswith('cocos/')})
    rules = set(state['rules'].values())
    if not state['target']:
        return 'n/a'
    if rules & {'ambiguous', 'unknown'}:
        return 'conflict'
    return 'kit_old' if 'old' in rules else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    if ctx.engine != 2:
        r.state = 'n/a'
        return r.as_dict()
    before = ctx.files(root_only=True)
    out = _fix().apply(ctx.root)
    r.state = 'n/a' if not out['target'] else ('kit_old' if out['changed'] else 'kit_current')
    r.blocks += out['blocks']
    after = ctx.files(root_only=True)
    for rel in sorted(set(before) | set(after)):
        if before.get(rel) != after.get(rel):
            what = '; '.join(c['change'] for c in out['changed'] if c['file'] == rel) or 'adapter rewrite'
            r.change(rel, before.get(rel), after.get(rel), what)
    r.info.append('adapter: %s; rules %s' % (out.get('reason'), out.get('rules')))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    """Writer-side self-check: after finalize every rule must be the fixed form."""
    state = _fix().detect(files)
    return [{'id': 'ADAPTER_FIX_' + rule, 'level': 'block', 'message': 'adapter rule %s is %s after finalize'
             % (rule, status)} for rule, status in state['rules'].items() if status != 'fixed']
