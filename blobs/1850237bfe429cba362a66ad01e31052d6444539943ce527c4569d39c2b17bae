from pathlib import Path
import sys, json, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_startup_loading import check
from PIL import Image

results = []
plan = {
    'declared_at': '1970-01-01T00:00:00+00:00',
    'viewports': [[100, 100], [120, 100]],
    'profiles': {k: {'network': None, 'cold': 0, 'warm': 0}
                 for k in ['local', 'first_network', 'slow_network']},
    'loading_phase_rois_by_viewport': {
        '100x100': {
            'web_preview': [0, 0, 20, 20],
            'content_loading': [0, 0, 20, 20],
            'scene_transition': [0, 0, 20, 20],
        }
    },
    'scene_transition_contract': {
        'meaning': 'Observed short real old-page/scene presentation between actual accepted touch/content completion and target ready; no loading spinner is claimed if absent.',
        'first_input_clock': 'Actual trusted touch-end enters page/game input boundary; never shift later to content package request time.',
    },
    'animation_freeze_ms': 1000,
    'frame_gap_ms': 250,
}

with tempfile.TemporaryDirectory(prefix='loading-phase-boundary-') as tmp:
    root = Path(tmp)
    frame_dir = root / 'frames'
    frame_dir.mkdir()
    run_dir = root / 'r3h-phase-fixture'
    run_dir.mkdir()
    report_path = run_dir / 'report.json'

    def fixture(level_ready, source_events, frame_rows, include_content_boundary=True):
        for old in frame_dir.glob('*.jpg'):
            old.unlink()
        frame_phases = []
        for ms, phase, color in frame_rows:
            name = f'frame_{ms}ms.jpg'
            Image.new('RGB', (100, 100), color).save(frame_dir / name)
            frame_phases.append({'file': name, 'phase': phase})
        events = list(source_events)
        if not include_content_boundary:
            events = [x for x in events if x['phase'] != 'content_loading']
        data = {
            'startup_plan_sha256': 'synthetic',
            'status': 'completed_pending_business_and_visual_review',
            'profile': 'local', 'network_applied': None,
            'cache_disabled': True, 'cache_mode': 'cold',
            'viewport_requested': {'width': 100, 'height': 100},
            'entry_epoch': 1,
            'marks': {
                'first_feedback': 0, 'home_usable': 200,
                'play_touch': 1000, 'level_ready': level_ready,
                'first_effect': level_ready + 10,
            },
            'requests': [],
            'observed': {'phases': events},
            'recording': {
                'first_frame_epoch': 1,
                'dir': str(frame_dir),
                'frame_phases': frame_phases,
            },
        }
        report_path.write_text(json.dumps(data))
        return data

    old_home_events = [
        {'at': 0, 'phase': 'web_preview'},
        {'at': 200, 'phase': 'ready'},
        {'at': 1300, 'phase': 'content_loading'},
        {'at': 1340, 'phase': 'scene_transition'},
        {'at': 1350, 'phase': 'ready'},
    ]
    old_home_frames = [
        (999, 'ready', 'black'),
        (1305, 'content_loading', 'black'),
        (1315, 'content_loading', 'white'),
        (1325, 'content_loading', 'black'),
        (1340, 'scene_transition', 'black'),
        (1345, 'scene_transition', 'white'),
        (1350, 'ready', 'black'),
    ]
    fixture(1350, old_home_events, old_home_frames)
    runs, _ = check(plan, [run_dir], 'synthetic')
    assert runs[0]['passed'], runs[0]
    assert runs[0]['enter_level_max_freeze_ms'] < 1000, runs[0]
    metrics = runs[0]['enter_level_phase_intervals']
    assert metrics[0]['phase'] == 'ready' and not metrics[0]['loading_indicator_checked'], metrics
    assert metrics[1]['start_ms'] == 1300 and metrics[1]['end_ms'] == 1340, metrics
    results.append({'scenario': 'old Home without spinner then 40ms actual loading passes', 'correct_verdict': True})

    frozen_events = [
        {'at': 0, 'phase': 'web_preview'},
        {'at': 200, 'phase': 'ready'},
        {'at': 1000, 'phase': 'content_loading'},
        {'at': 2300, 'phase': 'scene_transition'},
        {'at': 2310, 'phase': 'ready'},
    ]
    frozen_frames = [
        (999, 'ready', 'black'),
        (1000, 'content_loading', 'black'),
        (1600, 'content_loading', 'black'),
        (2200, 'content_loading', 'black'),
        (2300, 'scene_transition', 'black'),
        (2305, 'scene_transition', 'white'),
        (2310, 'ready', 'black'),
    ]
    fixture(2310, frozen_events, frozen_frames)
    runs, _ = check(plan, [run_dir], 'synthetic')
    assert not runs[0]['passed'], runs[0]
    assert runs[0]['enter_level_max_freeze_ms'] == 1300, runs[0]
    results.append({'scenario': 'visible loading spinner static for 1300ms is rejected', 'correct_verdict': True})

    fixture(1350, old_home_events, old_home_frames, include_content_boundary=False)
    runs, _ = check(plan, [run_dir], 'synthetic')
    assert not runs[0]['passed'], runs[0]
    assert any('matching observed Cocos phase boundary' in x or 'unknown observed indicator phase' in x
               for x in runs[0]['problems']), runs[0]
    results.append({'scenario': 'frame phase without observed source boundary is rejected', 'correct_verdict': True})

    print(json.dumps({
        'scope': 'Synthetic loading phase-boundary calibration only; not game evidence.',
        'passed': True,
        'cases': results,
    }, ensure_ascii=False))
