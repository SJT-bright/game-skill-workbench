#!/usr/bin/env python3
"""Find platform async calls whose result can be lost (Monkey Dash 2026-10-21).

Read-only. Scans PROJECT/assets *.ts/*.js (comments ignored) for calls to TikTok platform APIs that
return a result asynchronously, and checks that every return channel reaches the code:

  reward queries   getShortcutMissionReward, getEntranceMissionReward
                   The SDK may answer through the success callback OR through the returned Promise.
                   Both channels must reach one single-settle path. blocking when:
                     - success callback given but the returned Promise is dropped or only .catch()-ed
                       (the v8 bug: Promise.resolve({canReceiveReward}) never settled -> CHECKING forever)
                     - Promise handled but no success callback (callback-only SDK builds lose the result)
                     - neither channel handled
  navigation       addShortcut, startEntranceMission: blocking only when no channel is handled at all
  rewarded video   createRewardedVideoAd: listed; .show() whose Promise is neither awaited nor
                   .then/.catch-ed is listed for review (show rejection must end the wait)

A deliberate wrapper can be declared on the call line or the line above:
    // async-contract: <reason, e.g. "wrapper normalises callback+Promise in PlatformBridge.query">
Declared sites become "review" (reason is listed), not blocking.

The report also lists every reward API found ("reward_apis"); check_known_issues.py requires a declared
reward entry for each of them, so a mechanism that exists in code always produces its own checks.
Static scanning cannot prove behaviour: ASYNC-01 still needs the return-channel matrix, the
"SDK and timer both held" recovery run and a known-bad run of the same check.

Usage:
  python audit_async_contracts.py --project GAME [--native PATH_OR_ZIP] [--binding review.json] [--out result.json]
Exit codes: 0 nothing blocking, 1 blocking sites found, 2 bad input.
"""
import argparse
import json
import re
import zipfile
from pathlib import Path

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles'}
CODE = {'.ts', '.js'}
REWARD_QUERY = ('getShortcutMissionReward', 'getEntranceMissionReward')
NAVIGATION = ('addShortcut', 'startEntranceMission')
REWARDED_AD = ('createRewardedVideoAd',)
ALL_APIS = REWARD_QUERY + NAVIGATION + REWARDED_AD
CALL = re.compile(r'(?:(?<=[^\w$])|^)(' + '|'.join(ALL_APIS) + r")(?:['\"]\])?\s*\(")
DECLARE = re.compile(r'async-contract\s*:\s*(.{8,})', re.I)
DEF_PREFIX = re.compile(r'(?:^|[;{}\n])\s*(?:(?:export|public|private|protected|static|async|get|set|override)\s+)*$')


def blank_comments(text):
    """Replace comments by spaces (newlines kept) so positions and line numbers stay valid."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        c = text[i]
        if c in '"\'`':
            q, i = c, i + 1
            while i < n and text[i] != q:
                i += 2 if text[i] == '\\' else 1
            i += 1
        elif text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
        else:
            i += 1
    return ''.join(out)


def close_paren(code, i):
    """code[i] == '(' -> index after the matching ')' (strings skipped); -1 when unbalanced."""
    depth, n = 0, len(code)
    while i < n:
        c = code[i]
        if c in '"\'`':
            q, i = c, i + 1
            while i < n and code[i] != q:
                i += 2 if code[i] == '\\' else 1
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def chain_after(code, end):
    """Methods chained after the call: ['then', 'catch', ...]."""
    found, i = [], end
    while True:
        m = re.match(r'\s*\??\.\s*(then|catch|finally)\s*\(', code[i:])
        if not m:
            return found
        found.append(m.group(1))
        j = close_paren(code, i + m.end() - 1)
        if j < 0:
            return found
        i = j


def promise_resolve_chain_after(code, start, end):
    """Follow a show() promise wrapped by Promise.resolve(...).then/catch."""
    window_start = max(0, start - 300)
    window = code[window_start:start]
    for match in re.finditer(r'\bPromise\s*\.\s*resolve\s*\(', window):
        open_i = window_start + match.end() - 1
        close_i = close_paren(code, open_i)
        if close_i >= end:
            chain = chain_after(code, close_i)
            if any(method in {'then', 'catch'} for method in chain):
                return chain
    return []


def expression_start(code, start):
    """Walk back over the receiver chain (a.b?.c['d']) before the API name."""
    i = start
    while i > 0:
        ch = code[i - 1]
        if ch.isalnum() or ch in '_$.?]["\'':
            i -= 1
        elif ch.isspace() and re.search(r'[.?]\s*$', code[:i]):
            i -= 1
        else:
            break
    return i


def block_rest(code, end):
    """Text from the call to the end of the enclosing block, so a reused variable name elsewhere does not count."""
    depth, i, n = 0, end, len(code)
    while i < n:
        c = code[i]
        if c in '"\'`':
            q, i = c, i + 1
            while i < n and code[i] != q:
                i += 2 if code[i] == '\\' else 1
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth < 0:
                return code[end:i]
        i += 1
    return code[end:]


def classify(code, m):
    api = m.group(1)
    start = m.start(1)
    open_i = m.end() - 1
    end = close_paren(code, open_i)
    if end < 0:
        return None
    before = code[:start]
    receiver = before.rstrip()[-1:] in ('.', '[') or before.endswith("['") or before.endswith('["')
    after = code[end:].lstrip()
    if not receiver and (re.search(r'function\s*\*?\s*$', before) or
                         (DEF_PREFIX.search(before) and after[:1] in ('{', ':'))):
        return None  # a definition (wrapper method), not a call
    args = code[open_i + 1:end - 1]
    callback = bool(re.search(r'\bsuccess\s*[:(,}]|\bsuccess\s*=', args))
    chain = chain_after(code, end)
    expr = expression_start(code, start)
    prefix = code[:expr].rstrip()
    promise = 'dropped'
    if 'then' in chain or re.search(r'\b(await|yield)$', prefix):
        promise = 'handled'
    elif 'catch' in chain:
        promise = 'catch_only'
    else:
        assign = re.search(r'(?:\b(?:const|let|var)\s+)?([A-Za-z_$][\w$]*)\s*(?::[^=;]+)?=\s*$', prefix)
        if assign and not prefix.endswith(('==', '!=', '<=', '>=')):
            var, rest = assign.group(1), block_rest(code, end)
            v = re.escape(var)
            if re.search(r'\b' + v + r'\s*\??\.\s*then\s*\(|\bawait\s+' + v + r'\b|'
                         r'Promise\s*\.\s*(?:race|all|allSettled|any)\s*\(\s*\[[^\]]*\b' + v + r'\b', rest):
                promise = 'handled'
            else:
                # truthiness/type guards and .catch() do not consume the success result (the v8 pattern)
                other = re.sub(r'\b' + v + r'\s*\??\.\s*catch\s*\(|\btypeof\s+' + v + r'\b|!\s*' + v + r'\b|'
                               r'\bif\s*\(\s*' + v + r'\s*\)|\b' + v + r'\s*(?:&&|\|\||\?(?!\.)|[!=]==?)', ' ', rest)
                if re.search(r'\b' + v + r'\b', other):
                    promise = 'forwarded'
                elif re.search(r'\b' + v + r'\s*\??\.\s*catch\s*\(', rest):
                    promise = 'catch_only'
        elif prefix.endswith('=>'):
            executor = re.search(r'new\s+Promise\s*\(\s*(?:async\s*)?\(?[\w$\s,]*\)?\s*=>$', prefix[-120:])
            promise = 'dropped' if executor else 'forwarded'
        elif re.search(r'\breturn$', prefix) or prefix.endswith((',', '(')):
            promise = 'forwarded'
    return api, start, end, callback, promise, chain


def scan_file(label, text, sites):
    code = blank_comments(text)
    lines = text.splitlines()
    for m in CALL.finditer(code):
        got = classify(code, m)
        if not got:
            continue
        api, start, end, callback, promise, chain = got
        line = code.count('\n', 0, start) + 1
        declared = None
        for ln in (line, line - 1):
            if 1 <= ln <= len(lines):
                d = DECLARE.search(lines[ln - 1])
                if d:
                    declared = d.group(1).strip()
        site = {'where': f'{label}:{line}', 'api': api, 'callback': callback, 'promise': promise,
                'code': ' '.join(text[start:min(end, start + 160)].split())}
        if api in REWARD_QUERY:
            site['kind'] = 'reward_query'
            if callback and promise == 'handled':
                site['status'] = 'ok'
            elif callback and promise == 'forwarded':
                site['status'] = 'review'
                site['reason'] = 'Promise 被返回/传给别处：确认上层把它的成功结果接进同一个单次结算'
            elif callback:
                site['status'] = 'blocking'
                site['reason'] = ('只接了 success 回调，返回的 Promise 只 catch 没 then' if promise == 'catch_only'
                                  else '只接了 success 回调，返回的 Promise 被丢掉') + '：Promise 返回的资格结果会丢，CHECKING 不结束'
            elif promise in ('handled', 'forwarded'):
                site['status'] = 'blocking'
                site['reason'] = '只接了 Promise，没有 success 回调：只走回调的 SDK 版本结果会丢'
            else:
                site['status'] = 'blocking'
                site['reason'] = '回调和 Promise 都没接：查询结果没有任何去处'
        elif api in NAVIGATION:
            site['kind'] = 'navigation'
            ok = callback or promise in ('handled', 'forwarded') or re.search(r'\b(fail|complete)\s*[:(,}]', code[m.end():end])
            site['status'] = 'ok' if ok else 'blocking'
            if not ok:
                site['reason'] = '导航结果没有任何去处：失败/取消时界面不会结束等待'
        else:
            site['kind'] = 'rewarded_ad'
            site['promise'] = 'n/a'
            site['status'] = 'ok'
        if declared:
            site['declared'] = declared
        if site['status'] == 'blocking' and declared:
            site['status'] = 'review'
            site['reason'] = '已声明：' + declared + '（原问题：' + site.get('reason', '') + '）'
        sites.append(site)
    if 'createRewardedVideoAd' in code:
        for sm in re.finditer(r'\.\s*show\s*\(\s*\)', code):
            chain = chain_after(code, sm.end())
            if not any(method in {'then', 'catch'} for method in chain):
                chain = promise_resolve_chain_after(code, sm.start(), sm.end())
            prefix = code[:sm.start()]
            awaited = re.search(r'\bawait\s+[\w$.?\[\]\'"]*$', prefix)
            if not any(method in {'then', 'catch'} for method in chain) and not awaited:
                line = code.count('\n', 0, sm.start()) + 1
                sites.append({'where': f'{label}:{line}', 'api': 'RewardedVideoAd.show', 'kind': 'rewarded_ad_show',
                              'callback': False, 'promise': 'dropped', 'status': 'review',
                              'reason': 'show() 的 Promise 没接：show 失败时等待面板要结束并提示',
                              'code': ' '.join(text[sm.start():sm.start() + 80].split())})


def native_texts(path):
    path = Path(path)
    if path.is_file() and path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith('.js'):
                    yield 'zip:' + name, z.read(name).decode('utf-8', errors='replace')
    elif path.is_dir():
        for p in sorted(path.rglob('*.js')):
            yield 'native:' + p.relative_to(path).as_posix(), p.read_text(encoding='utf-8', errors='replace')
    else:
        raise ValueError(f'native path not found: {path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--native', type=Path, help='Native build folder or upload ZIP (only used to find APIs)')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if not (a.project / 'assets').is_dir():
            raise ValueError(f'no assets folder in {a.project}')
        if a.out and a.out.exists():
            raise ValueError(f'output exists: {a.out}')
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError(f'no binding object in {a.binding}')
        sites, files = [], 0
        for p in sorted((a.project / 'assets').rglob('*')):
            if not p.is_file() or p.suffix not in CODE or p.name.endswith('.d.ts') or \
                    SKIP_DIRS & {x.lower() for x in p.relative_to(a.project).parts}:
                continue
            files += 1
            scan_file(p.relative_to(a.project).as_posix(), p.read_text(encoding='utf-8', errors='replace'), sites)
        native_apis = set()
        if a.native:
            for label, text in native_texts(a.native):
                files += 1
                native_apis.update(api for api in ALL_APIS if api in text)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False))
        return 2
    blocking = [s for s in sites if s['status'] == 'blocking']
    review = [s for s in sites if s['status'] == 'review']
    reward_apis = sorted({s['api'] for s in sites if s['api'] in REWARD_QUERY + REWARDED_AD} |
                         (native_apis & set(REWARD_QUERY + REWARDED_AD)))
    report = {'tool': 'audit_async_contracts', 'checked': len(sites), 'files': files, 'failed': len(blocking),
              'passed': not blocking, 'reward_apis': reward_apis, 'native_only_apis': sorted(native_apis - {s['api'] for s in sites}),
              'checks': [{'id': s['where'], 'passed': s['status'] != 'blocking', **s} for s in sites], 'review': review,
              'note': 'Every return channel (callback, Promise, both, void, complete-only, reject/throw) must reach one '
                      'single-settle path with a visible end state. Static scan only; ASYNC-01 still needs the runtime matrix, '
                      'the SDK-and-timer-held recovery and a known-bad run.'}
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checked': len(sites), 'blocking': len(blocking), 'review': len(review), 'reward_apis': reward_apis,
                      'found': [{k: s[k] for k in ('where', 'api', 'reason')} for s in blocking[:8]],
                      'look_at': [{k: s.get(k) for k in ('where', 'api', 'reason')} for s in review[:5]]}, ensure_ascii=False))
    return 1 if blocking else 0


if __name__ == '__main__':
    raise SystemExit(main())
