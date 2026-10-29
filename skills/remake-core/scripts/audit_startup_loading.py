#!/usr/bin/env python3
"""LOAD-03: startup / enter-level timing, loading-animation freezes and first-screen size (user rules 2026-10-20/21/23).

Reads the startup plan (written BEFORE measuring) and the report folders written by
chrome_touch.py (runs in Ego Lite via ego-browser nodejs, plan "timing": true, --record). Every single run
must pass; averages never hide a failure.

  python audit_startup_loading.py --plan startup-plan.json --runs RUN_DIR [RUN_DIR ...]
         [--binding review.json] [--out report.json]

Plan (startup-plan.json):
  {"declared_at": "2026-10-21T10:00:00+08:00",
   "viewports": [[393, 852], [412, 915]],                 # two different aspect ratios
   "profiles": {
     "local":         {"network": null, "cold": 3, "warm": 1},        # "budgets": {...} only for a product target
     "first_network": {"network": {"download_kbps": 10000, "upload_kbps": 5000, "latency_ms": 80},
                       "cold": 3, "warm": 1},
     "slow_network":  {"network": {"download_kbps": 2000, "upload_kbps": 1000, "latency_ms": 150},
                       "cold": 1, "warm": 0}},
   "animation_freeze_ms": 1000, "frame_gap_ms": 250,
   "loading_roi": {"bootstrap": [x, y, w, h], "enter_level": [x, y, w, h]},   # CSS px of the spinner/bar
   "max_home_asset_kb": 500, "home_assets_allowed": ["home_bg"],
   "idle_timeout_ms": 10000, "old_deadline_ms": 15000, "retry_grace_ms": 2000}

Each timed run's plan carries "profile", "viewport", "cache", "timing": true, "record": true,
"startup_plan_sha256" and marks first_feedback, home_usable, play_touch, level_ready, first_effect.
Fault runs carry "fault": slow_progress | background_wait | stall_retry | late_callback (see
cocos-game-check/startup/references/startup-loading-timing.md for what each must show).
No fixed finish times (user 2026-10-23, second message: a big game cannot meet "home in 4 s", and a number it
cannot meet makes the AI cut corners elsewhere). The Skill judges what does NOT depend on the game's size:
  stuck        the loading animation never stops > 1 s, a stall shows Retry (idle_timeout_ms <= 10 s without progress,
               Retry <= 2 s later), every route really ends in a playable level (a mark that never comes = fail)
  wasted time  each wait is compared with what this game really loads in it (bytes from the report, the profile's
               network): allowed = base (home 3 s, level 1.5 s) + 0.3 s per MB loaded + 1.5 x the download time +
               4 round trips; over it = time spent on nothing (fixed timers, serial awaits, slow progress tween,
               loading things the page does not use). Reported per run as <wait>_ms, <wait>_allowed_ms, <wait>_waste_ms.
  fake wait    home usable later than max(2 s, 25% of the home time) after the last download finished
  re-entry     optional marks next_touch/next_ready, retry_touch/retry_ready, map_touch/map_ready are judged like
               PLAY -> level; tapped but never ready = "cannot enter the game"
Plan budgets are optional project targets: when present the stricter of plan and size rule applies; a plan may not
loosen the stuck limits (animation_freeze_ms, idle_timeout_ms, retry_grace_ms).
Exit codes: 0 pass, 1 problems found, 2 bad input.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime
import sys
from pathlib import Path

MARKS = ('first_feedback', 'home_usable', 'play_touch', 'level_ready', 'first_effect')
POLICY_VERSION = 'startup-raw-v2'
MINIMUM_RUNS = {'local': {'cold': 3, 'warm': 1}, 'first_network': {'cold': 3, 'warm': 1}, 'slow_network': {'cold': 1, 'warm': 0}}
# user 2026-10-23: no fixed finish times (a big game cannot meet them); judge stuck and wasted time instead.
# Limits for "stuck" do not depend on the game's size, so a plan may be stricter but never looser.
STUCK_LIMITS = {'animation_freeze_ms': 1000, 'idle_timeout_ms': 10000, 'retry_grace_ms': 2000}
# first feedback = the tiny index.html splash, before any engine or asset: same for small and big games (plan may override)
FEEDBACK_MS = {'local': 1000, 'first_network': 2000, 'slow_network': 3000}
BASE_MS = {'home': 3000, 'level': 1500}      # engine start / scene switch that every game needs
DECODE_MS_PER_MB = 300                       # parse/decode/upload per MB actually loaded in that wait
TRANSFER_FACTOR, ROUND_TRIPS = 1.5, 4        # download time of those bytes on the profile's network, plus latency
TAIL_MIN_MS, TAIL_SHARE = 2000, 0.25         # home after the last download: more than max(2 s, 25%) = fake wait
# optional re-entry marks, judged like PLAY -> level (size rule and plan play_to_ready_ms): next level / retry / map node -> level ready
REENTRY = (('next_touch', 'next_ready'), ('retry_touch', 'retry_ready'), ('map_touch', 'map_ready'))
FAULTS = ('slow_progress', 'background_wait', 'stall_retry', 'late_callback',
          'optional_api_missing', 'native_modal_no_callback', 'image_no_callback', 'audio_fail')
# deferred_bundle_fail is required when the plan lists deferred_bundles (Rainy Duck 2026-10-21).


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transfer_ms(nbytes, network):
    return nbytes * 8 / max(1, network.get('download_kbps') or 1) if network else 0


def explained_ms(nbytes, network):
    """Time the bytes loaded in a wait really need on this network (download + round trips), ms."""
    return transfer_ms(nbytes, network) + (ROUND_TRIPS * (network.get('latency_ms') or 0) if network else 0)


def allowed_ms(kind, nbytes, network):
    """Size rule: base + decode per MB + 1.5 x the real download time + round trips (no fixed finish time)."""
    return int(BASE_MS[kind] + DECODE_MS_PER_MB * nbytes / 1048576 + TRANSFER_FACTOR * transfer_ms(nbytes, network)
               + (ROUND_TRIPS * (network.get('latency_ms') or 0) if network else 0))


def loaded_between(rep, start, end):
    return sum(r.get('bytes', 0) for r in rep.get('requests', []) if not r.get('failed') and start < r.get('t_ms', 0) <= end)


def frames_of(run_dir, rep):
    rec = rep.get('recording') or {}
    folder = Path(rec.get('dir') or run_dir / 'frames')
    if not folder.is_absolute():
        folder = run_dir / folder
    if not folder.is_dir() or not rec.get('first_frame_epoch') or not rep.get('entry_epoch'):
        return []
    offset = (rec['first_frame_epoch'] - rep['entry_epoch']) * 1000
    out = []
    frame_rows = []
    for f in folder.glob('*.jpg'):
        try:
            frame_rows.append((int(f.stem.split('_')[1].rstrip('ms')), f))
        except (IndexError, ValueError):
            continue
    for milliseconds, f in sorted(frame_rows, key=lambda row: (row[0], row[1].name)):
        out.append((offset + milliseconds, f))
    return out


def roi_signature(path, roi, viewport, image_module):
    with image_module.open(path) as im:
        im = im.convert('L')
        scale = im.width / viewport[0]
        x, y, w, h = [int(v * scale) for v in roi]
        crop = im.crop((x, y, x + max(1, w), y + max(1, h))).resize((24, 24))
        return list(crop.get_flattened_data()) if hasattr(crop, "get_flattened_data") else list(crop.getdata())


def longest_freeze(frames, start, end, roi, viewport, image_module):
    """Longest time the loading indicator area did not change inside [start, end] (ms).
    Screencast only sends frames when something changes, so a gap with no frames counts as frozen."""
    inside = [(t, f) for t, f in frames if start <= t <= end]
    if not inside:
        return end - start, 0
    worst, last_change, prev = 0, start, None
    max_gap, prev_t = 0, start
    for t, f in inside:
        sig = roi_signature(f, roi, viewport, image_module)
        max_gap = max(max_gap, t - prev_t); prev_t = t
        if prev is None or sum(abs(a - b) for a, b in zip(sig, prev)) / len(sig) > 1.5:
            worst = max(worst, t - last_change)
            last_change = t
        prev = sig
    worst = max(worst, end - last_change)
    return worst, max(max_gap, end - prev_t)


def check(plan, run_dirs, plan_sha):
    try:
        from PIL import Image
    except ImportError:
        raise ValueError('Pillow is required for the loading-animation check: pip install pillow')
    problems, runs, coverage = [], [], {}
    vps = plan.get('viewports')
    if not (isinstance(vps, list) and len(vps) >= 2 and len({round(w / h, 3) for w, h in vps}) >= 2):
        raise ValueError('plan needs two viewports with different aspect ratios')
    profiles = plan.get('profiles', {})
    for need in ('local', 'first_network', 'slow_network'):
        if need not in profiles:
            raise ValueError('plan profile missing: ' + need)
        for cache, minimum in MINIMUM_RUNS[need].items():
            value = profiles[need].get(cache, 0)
            if type(value) is not int or value < minimum:
                problems.append('%s %s count must be at least %d; the plan cannot waive coverage' % (need, cache, minimum))
    for name in ('first_network', 'slow_network'):
        network = profiles[name].get('network')
        if not isinstance(network, dict) or not all(type(network.get(k)) in (int, float) and math.isfinite(network[k]) and network[k] > 0 for k in ('download_kbps', 'upload_kbps', 'latency_ms')):
            problems.append(name + ': actual positive throttling parameters required')
    try:
        declared = datetime.fromisoformat(plan['declared_at'])
        if declared.tzinfo is None:
            raise ValueError('timezone missing')
        declared_epoch = declared.timestamp()
    except (KeyError, ValueError, TypeError):
        declared_epoch = None
        problems.append('startup plan must be declared with timezone before measuring')
    for k, cap in STUCK_LIMITS.items():
        if plan.get(k, cap) > cap:
            problems.append('plan %s %s is looser than the stuck limit %s (a loading screen that does not move or a stall '
                            'without Retry looks broken in any game size); %s used' % (k, plan[k], cap, cap))
    freeze_limit = min(plan.get('animation_freeze_ms', 1000), STUCK_LIMITS['animation_freeze_ms'])
    gap_limit = plan.get('frame_gap_ms', 250)
    roi = plan.get('loading_roi', {})
    max_kb = plan.get('max_home_asset_kb', 500)
    allowed = plan.get('home_assets_allowed', [])
    faults_seen = {}
    for d in run_dirs:
        d = Path(d)
        rp = d / 'report.json'
        if not rp.is_file():
            raise ValueError('no report.json in ' + str(d))
        rep = json.loads(rp.read_text(encoding='utf-8'))
        plan_run = rep.get('plan_copy') or {}
        name = d.name
        res = {'run': name, 'report_sha256': sha(rp), 'problems': []}
        P = res['problems']
        if rep.get('startup_plan_sha256') != plan_sha:
            P.append('run was not made for this startup plan (startup_plan_sha256 differs or missing)')
        if rep.get('status') != 'completed_pending_business_and_visual_review':
            P.append('run did not complete: ' + str(rep.get('error', rep.get('status'))))
        marks = rep.get('marks') or {}
        if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in marks.values()):
            P.append('startup marks must be finite nonnegative measurements')
        entry = rep.get('entry_epoch')
        if type(entry) not in (int, float) or not math.isfinite(entry) or entry <= 0:
            P.append('actual navigation entry epoch required')
        elif declared_epoch is not None and declared_epoch > entry + .001:
            P.append('startup plan was declared after this run')
        fault = rep.get('fault')
        vp = rep.get('viewport_requested') or {}
        vp = [vp.get('width'), vp.get('height')]
        run_roi = plan.get('loading_roi_by_viewport', {}).get('%sx%s' % tuple(vp), roi)
        if fault:
            faults_seen.setdefault(fault, []).append(name)
            res['fault'] = fault
            idle = min(plan.get('idle_timeout_ms', 10000), STUCK_LIMITS['idle_timeout_ms'])
            if fault == 'slow_progress':
                stage = rep.get('slow_progress_stage', 'bootstrap')
                duration = (marks.get('level_ready', 0) - marks.get('play_touch', 0)
                            if stage == 'enter_level' else marks.get('home_usable', 0))
                if stage == 'enter_level' and not all(k in marks for k in ('play_touch', 'level_ready')):
                    P.append('slow_progress: enter-level requires play_touch and level_ready')
                if stage not in ('bootstrap', 'enter_level') or duration <= plan.get('old_deadline_ms', idle):
                    P.append('slow_progress: the selected startup/enter-level load must cross the old total deadline')
                if 'first_effect' not in marks:
                    P.append('slow_progress: a real input must change the game after loading')
            elif fault == 'background_wait':
                bg = rep.get('background') or []
                if not bg or bg[0].get('visibility_while_away') != 'hidden':
                    P.append('background_wait: the page was not really hidden while away')
                elif bg[0]['to_ms'] - bg[0]['from_ms'] <= idle:
                    P.append('background_wait: stay in background longer than idle_timeout_ms')
                if 'first_effect' not in marks:
                    P.append('background_wait: after returning, a real input must change the game')
            elif fault == 'stall_retry':
                if 'retry_shown' not in marks:
                    P.append('stall_retry: Retry never appeared (mark retry_shown)')
                elif marks['retry_shown'] > idle + min(plan.get('retry_grace_ms', 2000), STUCK_LIMITS['retry_grace_ms']) + marks.get('stall_started', 0):
                    P.append('stall_retry: Retry appeared too late (%d ms)' % marks['retry_shown'])
                if not any(s.get('action', {}).get('type') == 'unblock' for s in rep.get('steps', [])):
                    P.append('stall_retry: unblock the resource and tap Retry')
                if 'first_effect' not in marks:
                    P.append('stall_retry: after Retry a real input must change the game (not just the home screen)')
            elif fault in ('optional_api_missing', 'native_modal_no_callback'):
                if not rep.get('init_js_sha256'):
                    P.append('%s: needs plan "init_js" that stubs the platform SDK (missing showModal/showLoading, or a modal that never answers)' % fault)
                for m in ('home_usable', 'first_effect'):
                    if m not in marks:
                        P.append('%s: the game must still reach %s; optional SDK features never block startup' % (fault, m))
                if fault == 'native_modal_no_callback':
                    if rep.get('optional_modal_unused') is True:
                        if type(rep.get('optional_modal_calls')) is not int or rep.get('optional_modal_calls') != 0:
                            P.append('native_modal_no_callback: unused declaration contradicts actual modal call counter')
                    elif 'fallback_prompt_shown' not in marks:
                        P.append('native_modal_no_callback: mark fallback_prompt_shown (in-game prompt within ~5 s, then a tap recovers)')
            elif fault == 'image_no_callback':
                if not rep.get('held_requests') and not any(s.get('action', {}).get('type') == 'unhang' for s in rep.get('steps', [])):
                    P.append('image_no_callback: use plan "hang_urls" on a first-screen image, then "unhang" and tap Retry')
                for m in ('retry_shown', 'home_usable', 'first_effect'):
                    if m not in marks:
                        P.append('image_no_callback: mark %s missing (Retry must send a NEW request and lead to real play)' % m)
            elif fault == 'audio_fail':
                if not rep.get('requests') or not any(r.get('failed') for r in rep.get('requests', [])):
                    P.append('audio_fail: block the audio files/bundle with "block_urls" so they really fail')
                for m in ('home_usable', 'first_effect'):
                    if m not in marks:
                        P.append('audio_fail: home and play must work without sound (%s missing)' % m)
            elif fault == 'deferred_bundle_fail':
                for m in ('home_usable', 'first_effect', 'deferred_failure_message'):
                    if m not in marks:
                        P.append('deferred_bundle_fail: mark %s missing (a later page fails politely, play still works)' % m)
            elif fault == 'late_callback':
                for m in ('old_result_arrived', 'first_effect'):
                    if m not in marks:
                        P.append('late_callback: mark %s missing' % m)
            else:
                P.append('unknown fault ' + str(fault))
            res['passed'] = not P
            runs.append(res)
            continue
        prof_name = rep.get('profile')
        prof = profiles.get(prof_name)
        if prof is None:
            P.append('run profile %r not in plan' % prof_name)
            res['passed'] = False; runs.append(res); continue
        if (prof.get('network') or None) != (rep.get('network_applied') or None):
            P.append('network actually applied differs from the plan profile')
        cache = rep.get('cache_mode')
        if cache == 'cold' and rep.get('cache_disabled') is not True:
            P.append('cold run without cache disabled')
        if cache == 'warm' and not rep.get('warmup_done'):
            P.append('warm run without a finished warm-up visit')
        for m in MARKS:
            if m not in marks:
                P.append('mark %s missing' % m)
        b = prof.get('budgets') or {}                     # optional project targets
        net = prof.get('network') or None
        t = lambda k: marks.get(k)
        feedback = b.get('feedback_ms', FEEDBACK_MS.get(prof_name, 2000))
        if t('first_feedback') is not None and t('first_feedback') > feedback:
            P.append('first feedback %d ms > %d (the splash in index.html shows before the engine and any asset)'
                     % (t('first_feedback'), feedback))

        def judge(kind, label, start, end, budget_key):
            nbytes = loaded_between(rep, -1, end) if kind == 'home' else loaded_between(rep, start, end)
            spent = end - start
            rule = allowed_ms(kind, nbytes, net)
            limit = min(rule, b[budget_key]) if budget_key in b else rule
            key = label.split(' (')[0].replace(' ', '_')
            res[key + '_ms'] = spent
            res[key + '_allowed_ms'] = limit
            res[key + '_waste_ms'] = int(max(0, spent - explained_ms(nbytes, net)))
            if spent > limit:
                why = ('plan budget' if limit < rule else
                       'this game loads %d KB here: %.1f s base + %.1f s per MB + 1.5 x download time'
                       % (nbytes // 1024, BASE_MS[kind] / 1000, DECODE_MS_PER_MB / 1000))
                P.append('%s %d ms > %d (%s): about %d ms of it is not explained by downloading - find the waste (serial '
                         'loads, fixed timers, slow progress tween, loading what this page does not use; '
                         'cocos-game-check/startup/references/startup-loading-timing.md)' % (label, spent, limit, why, res[key + '_waste_ms']))

        if t('home_usable') is not None:
            judge('home', 'home usable', 0, t('home_usable'), 'home_ms')
        if None not in (t('play_touch'), t('level_ready')):
            judge('level', 'enter level', t('play_touch'), t('level_ready'), 'play_to_ready_ms')
        for a_, z_ in REENTRY:
            if None not in (t(a_), t(z_)):
                judge('level', 'enter level again (%s)' % a_.split('_')[0], t(a_), t(z_), 'play_to_ready_ms')
            elif t(a_) is not None and t(z_) is None:
                P.append('%s tapped but %s never reached: the level could not be entered again' % (a_, z_))
        if t('home_usable') is not None:
            done = [r.get('t_ms', 0) for r in rep.get('requests', []) if not r.get('failed') and r.get('t_ms', 0) <= t('home_usable')]
            if done:
                tail = t('home_usable') - max(done)
                tail_limit = max(TAIL_MIN_MS, int(TAIL_SHARE * t('home_usable')))
                res['home_after_last_download_ms'] = tail
                if tail > tail_limit:
                    P.append('home usable %d ms after the last download finished (limit max(2 s, 25%% of the home time) = %d): '
                             'no fake minimum loading time, slow progress-bar tween or fixed timer - show the home page as soon '
                             'as it is ready (user 2026-10-23)' % (tail, tail_limit))
        frames = frames_of(d, rep)
        if not frames:
            P.append('no recording frames (run with "record": true) - loading animation cannot be checked')
        else:
            for seg, (a, z) in (('bootstrap', ('first_feedback', 'home_usable')), ('enter_level', ('play_touch', 'level_ready'))):
                if None in (t(a), t(z)):
                    continue
                span = t(z) - t(a)
                res[seg + '_visible_ms'] = span
                if span < 300:
                    continue                      # instant, no loading screen needed
                phase_rois = plan.get('loading_phase_rois_by_viewport', {}).get('%sx%s' % tuple(vp))
                if phase_rois:
                    phases = {x.get('file'): x.get('phase') for x in (rep.get('recording') or {}).get('frame_phases', [])}
                    source_rows = (rep.get('observed') or {}).get('phases')
                    if not isinstance(source_rows, list) or not source_rows:
                        P.append('%s: missing observed Cocos phase-boundary evidence' % seg); continue
                    source_events, source_invalid = [], False
                    previous_at = -float('inf')
                    for event in source_rows:
                        event_at, event_phase = event.get('at'), event.get('phase')
                        if (type(event_at) not in (int, float) or not math.isfinite(event_at) or
                                event_at < previous_at or not isinstance(event_phase, str) or not event_phase):
                            source_invalid = True
                            break
                        previous_at = event_at
                        if source_events and event_at == source_events[-1][0]:
                            if event_phase != source_events[-1][1]:
                                source_invalid = True
                                break
                            continue
                        if source_events and event_phase == source_events[-1][1]:
                            continue
                        source_events.append((event_at, event_phase))
                    if source_invalid or not source_events:
                        P.append('%s: invalid or ambiguous observed Cocos phase-boundary evidence' % seg); continue

                    # Build the actual observed phase intervals. The input touch remains
                    # the timing origin, while an already-visible old ready page is not
                    # treated as a loading spinner. Each subsequent loading phase starts
                    # at its own recorded Cocos boundary, not at the preceding touch.
                    at_start = [e for e in source_events if e[0] <= t(a)]
                    if not at_start:
                        P.append('%s: no observed phase boundary establishes the state at interval start' % seg); continue
                    active_phase = at_start[-1][1]
                    cursor = t(a)
                    phase_intervals = []
                    for event_at, event_phase in source_events:
                        if event_at <= t(a) or event_at > t(z):
                            continue
                        phase_intervals.append((active_phase, cursor, event_at, event_at == t(a)))
                        cursor, active_phase = event_at, event_phase
                    phase_intervals.append((active_phase, cursor, t(z), False))

                    # A carried-forward ready phase at PLAY must be supported by a
                    # recent original ready frame and this plan's explicit old-page
                    # transition contract. It is a known non-loading state, not an
                    # unknown-phase exemption.
                    initial_ready = phase_intervals[0][0] == 'ready'
                    if initial_ready and seg == 'enter_level':
                        transition = plan.get('scene_transition_contract') or {}
                        meaning = transition.get('meaning', '')
                        preceding = [(at, f, phases.get(f.name)) for at, f in frames if at <= t(a)]
                        if ('old-page/scene' not in meaning or 'no loading spinner is claimed if absent' not in meaning or
                                not preceding or t(a) - preceding[-1][0] > gap_limit or preceding[-1][2] != 'ready'):
                            P.append('%s: old ready scene cannot be excluded without the frozen transition contract and a recent ready frame' % seg); continue

                    phase_frames = [(at, f, phases.get(f.name)) for at, f in frames if t(a) <= at <= t(z)]
                    phase_mismatch = False
                    for at, f, frame_phase in phase_frames:
                        source_active = [e for e in source_events if e[0] <= at]
                        if not source_active:
                            P.append('%s: recorded frame has no preceding observed phase boundary' % seg)
                            phase_mismatch = True
                            break
                        # Screenshot filenames round milliseconds; tolerate only the
                        # existing sub-millisecond capture-boundary skew.
                        current_source_phase = source_active[-1][1]
                        next_source = next((e for e in source_events if e[0] > at), None)
                        if next_source and next_source[1] == frame_phase and next_source[0] - at <= 1:
                            current_source_phase = next_source[1]
                        if not frame_phase or current_source_phase != frame_phase:
                            P.append('%s: frame phase lacks a matching observed Cocos phase boundary' % seg)
                            phase_mismatch = True
                            break
                    if phase_mismatch:
                        continue

                    freeze = gap = 0
                    phase_metrics = []
                    for phase, phase_start, phase_end, _ in phase_intervals:
                        if phase_end < phase_start:
                            P.append('%s: observed phase interval is reversed' % seg); phase_mismatch = True; break
                        if phase == 'ready':
                            phase_metrics.append({'phase': phase, 'start_ms': phase_start, 'end_ms': phase_end,
                                                  'loading_indicator_checked': False, 'reason': 'source-observed ready scene has no claimed loading spinner'})
                            continue
                        if phase not in phase_rois:
                            P.append('%s: missing/unknown observed indicator phase %s' % (seg, phase)); phase_mismatch = True; break
                        group = [(at, f) for at, f, frame_phase in phase_frames
                                 if frame_phase == phase and phase_start <= at <= phase_end]
                        fr, gp = longest_freeze(group, phase_start, phase_end, phase_rois[phase], vp, Image)
                        freeze, gap = max(freeze, fr), max(gap, gp)
                        phase_metrics.append({'phase': phase, 'start_ms': phase_start, 'end_ms': phase_end,
                                              'frame_count': len(group), 'max_freeze_ms': fr, 'max_frame_gap_ms': gp,
                                              'loading_indicator_checked': True})
                    if phase_mismatch:
                        continue
                    res[seg + '_phase_intervals'] = phase_metrics
                else:
                    if seg not in run_roi:
                        P.append('loading_roi.%s missing in plan' % seg); continue
                    freeze, gap = longest_freeze(frames, t(a), t(z), run_roi[seg], vp, Image)
                res[seg + '_max_freeze_ms'] = freeze
                if freeze > freeze_limit:
                    P.append('%s loading animation froze for %d ms (limit %d)' % (seg, freeze, freeze_limit))
                elif gap > max(gap_limit, freeze_limit):
                    P.append('%s: frame samples too sparse (%d ms)' % (seg, gap))
        if t('home_usable') is not None:
            big = [r for r in rep.get('requests', []) if not r.get('failed') and r.get('t_ms', 0) <= t('home_usable')
                   and r.get('bytes', 0) > max_kb * 1024 and not any(a in r.get('url', '') for a in allowed)]
            res['home_bytes'] = sum(r.get('bytes', 0) for r in rep.get('requests', [])
                                    if not r.get('failed') and r.get('t_ms', 0) <= t('home_usable'))
            for r in big[:5]:
                P.append('big asset loaded before home (%d KB): %s - load it later unless the home page uses it'
                         % (r['bytes'] // 1024, r['url'][-80:]))
        key = (prof_name, '%dx%d' % tuple(vp), cache)
        if not P:
            coverage[key] = coverage.get(key, 0) + 1
        res['passed'] = not P
        runs.append(res)
    for prof_name, prof in profiles.items():
        for w, h in vps:
            for cache in ('cold', 'warm'):
                need = prof.get(cache, 0)
                got = coverage.get((prof_name, '%dx%d' % (w, h), cache), 0)
                if got < need:
                    problems.append('%s %dx%d %s: %d passing runs, need %d' % (prof_name, w, h, cache, got, need))
    for f in FAULTS + (('deferred_bundle_fail',) if plan.get('deferred_bundles') else ()):
        if f not in faults_seen:
            problems.append('fault test missing: ' + f)
    return runs, problems


def check_report(report, report_directory=None, actual_current_binding=None):
    """Compatibility hook for project packaging scripts: a current, passing LOAD-03 report or an error list."""
    errors = []
    if not isinstance(report, dict) or report.get('tool') != 'audit_startup_loading':
        errors.append('not an audit_startup_loading report')
    elif not (report.get('passed') is True and report.get('failed') == 0 and report.get('checked', 0) >= 1):
        errors.append('LOAD-03 startup/loading report is not passing')
    if actual_current_binding is not None and isinstance(report, dict) and report.get('binding') != actual_current_binding:
        errors.append('LOAD-03 report belongs to another build')
    return errors


def raw_manifest(run_dirs):
    reports, frames = {}, {}
    for value in run_dirs:
        directory = Path(value).resolve()
        raw_file = directory / 'report.json'
        reports[str(raw_file)] = sha(raw_file)
        raw = json.loads(raw_file.read_text(encoding='utf-8'))
        folder = Path((raw.get('recording') or {}).get('dir') or directory / 'frames')
        if not folder.is_absolute():
            folder = directory / folder
        folder = folder.resolve()
        if not folder.is_relative_to(directory):
            raise ValueError('recording frames outside run directory')
        for f in sorted(folder.glob('*.jpg')):
            frames[str(f.resolve())] = sha(f)
    return reports, frames


def validate_report(report, expected_binding=None, recheck=True):
    """Reopen the exact plan, run records and pixels; never accept a pass stamp alone."""
    errors = []
    try:
        if report.get('policy_version') != POLICY_VERSION:
            errors.append('startup policy version missing/stale')
        if report.get('passed') is not True or report.get('failed') != 0:
            errors.append('startup report not passing')
        plan_file = Path(report['plan_file']).resolve()
        if sha(plan_file) != report.get('plan_sha256'):
            errors.append('startup plan changed')
        plan = json.loads(plan_file.read_text(encoding='utf-8'))
        dirs = [Path(p).resolve() for p in report['run_directories']]
        if not dirs or len(set(dirs)) != len(dirs):
            errors.append('startup run directories missing/duplicated')
        if report.get('checked') != len(dirs):
            errors.append('startup run count inconsistent')
        raw, frames = raw_manifest(dirs)
        if raw != report.get('raw_reports') or frames != report.get('raw_frames') or not frames:
            errors.append('startup raw reports/frames missing or changed')
        if expected_binding is not None:
            if report.get('binding') != expected_binding:
                errors.append('startup report binding stale')
            for path in raw:
                record = json.loads(Path(path).read_text(encoding='utf-8'))
                if record.get('binding', plan.get('binding')) != expected_binding:
                    errors.append('startup execution binding stale: ' + path)
        if recheck and not errors:
            runs, problems = check(plan, dirs, report['plan_sha256'])
            errors.extend(problems)
            errors.extend(r['run'] + ': ' + p for r in runs for p in r['problems'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
        errors.append('invalid startup raw evidence: ' + str(e))
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--runs', nargs='+', required=True)
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        plan = json.loads(a.plan.read_text(encoding='utf-8'))
        runs, problems = check(plan, a.runs, sha(a.plan))
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError('no binding object in ' + str(a.binding))
        if a.out and a.out.exists():
            raise ValueError('output exists: ' + str(a.out))
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    failed = sum(1 for r in runs if not r['passed']) + len(problems)
    raw_reports, raw_frames = raw_manifest(a.runs)
    report = {'tool': 'audit_startup_loading', 'policy_version': POLICY_VERSION, 'plan_file': str(a.plan.resolve()),
              'run_directories': [str(Path(p).resolve()) for p in a.runs], 'raw_reports': raw_reports, 'raw_frames': raw_frames,
              'plan_sha256': sha(a.plan), 'checked': len(runs), 'failed': failed,
              'passed': failed == 0, 'coverage_problems': problems,
              'checks': [{'name': r['run'], 'passed': r['passed']} for r in runs], 'runs': runs,
              'note': 'Browser simulation (Ego Lite) timing. Every run must pass; not a TikTok device measurement.'}
    if binding is not None:
        report['binding'] = binding
    if report['passed']:
        metadata_errors = validate_report(report, binding, recheck=False)
        if metadata_errors:
            problems.extend(metadata_errors)
            report['failed'] += len(metadata_errors)
            failed = report['failed']
            report['passed'] = False
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'checked': len(runs), 'failed': failed, 'coverage_problems': problems[:8],
                      'failed_runs': [{'run': r['run'], 'problems': r['problems'][:3]} for r in runs if not r['passed']][:8]},
                     ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
