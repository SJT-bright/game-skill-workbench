#!/usr/bin/env python3
"""Image source/render resolution policy, separate from text/layout/visual defects.

Precedence: builtin default -> project JSON -> CLI. An explicit CLI preset selects
that whole preset (replacing project thresholds/severity), then individual CLI fields
apply. A CLI file path replaces the default project file. Unknown/invalid fields fail.
No policy schedules generation; advisory findings never block on ratio alone.
"""
from __future__ import annotations
import json
import hashlib
import math
from pathlib import Path

SCHEMA = 'clarity_policy.v1'
PRESETS = {
    'default': {'min_ratio': 1.0, 'background_min_ratio': 1.0, 'severity': 'advisory'},
    'strict': {'min_ratio': 2.0, 'background_min_ratio': 1.5, 'severity': 'blocking'},
}
KEYS = {'schema', 'preset', 'min_ratio', 'background_min_ratio', 'severity', 'why'}


def positive(value, key):
    try:
        valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value)) and value > 0
    except (ValueError, TypeError, OverflowError):
        valid = False
    if not valid:
        raise ValueError('%s must be a finite positive number, got %r' % (key, value))
    return float(value)


def validate(data, origin):
    if not isinstance(data, dict):
        raise ValueError('%s must contain a JSON object' % origin)
    unknown = set(data) - KEYS
    if unknown:
        raise ValueError('%s: unknown clarity policy fields: %s' % (origin, ', '.join(sorted(unknown))))
    if 'schema' in data and data['schema'] != SCHEMA:
        raise ValueError('%s: schema must be %s' % (origin, SCHEMA))
    if 'preset' in data and (not isinstance(data['preset'], str) or data['preset'] not in PRESETS):
        raise ValueError('%s: unknown preset %r (default or strict)' % (origin, data['preset']))
    for key in ('min_ratio', 'background_min_ratio'):
        if key in data:
            positive(data[key], key)
    if 'severity' in data and data['severity'] not in ('advisory', 'blocking'):
        raise ValueError('%s: severity must be advisory or blocking' % origin)
    if 'why' in data and (not isinstance(data['why'], str) or not data['why'].strip()):
        raise ValueError('%s: why must be a nonempty string' % origin)
    return data


def resolve_policy(project=None, *, cli_preset=None, cli_min_ratio=None,
                   cli_background_min_ratio=None, cli_severity=None, policy_path=None):
    path = Path(policy_path) if policy_path is not None else (Path(project) / 'docs/art/clarity-policy.json' if project else None)
    if path is not None and not path.is_absolute() and policy_path is not None and project:
        path = Path(project) / path
    data, raw = {}, None
    if path is not None and (path.exists() or policy_path is not None):
        try:
            raw = path.read_bytes()
            data = validate(json.loads(raw.decode('utf-8-sig')), str(path))
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError('invalid clarity policy %s: %s' % (path, exc)) from exc
    selected = data.get('preset', 'default')
    result = dict(PRESETS[selected])
    sources = {key: ('project preset' if 'preset' in data else 'builtin default') for key in result}
    for key in result:
        if key in data:
            result[key] = data[key]
            sources[key] = 'project file'
    if cli_preset is not None:
        validate({'preset': cli_preset}, 'CLI')
        selected = cli_preset
        result = dict(PRESETS[selected])
        sources = {key: 'CLI preset' for key in result}
    overrides = {k: v for k, v in {'min_ratio': cli_min_ratio, 'background_min_ratio': cli_background_min_ratio,
                                  'severity': cli_severity}.items() if v is not None}
    validate(overrides, 'CLI')
    result.update(overrides)
    sources.update({key: 'CLI field' for key in overrides})
    result['min_ratio'] = positive(result['min_ratio'], 'min_ratio')
    result['background_min_ratio'] = positive(result['background_min_ratio'], 'background_min_ratio')
    return dict(result, schema=SCHEMA, preset=selected, sources=sources,
                policy_path=str(path.resolve()) if raw is not None else None,
                policy_sha256=hashlib.sha256(raw).hexdigest() if raw is not None else None,
                precedence='builtin default < project file < CLI preset < CLI field',
                auto_regenerate=False, why=data.get('why'),
                boundary='Resolution ratio only; missing glyphs, cropping, distortion, contrast, text size and actual visual review remain independent.')


def add_arguments(parser):
    parser.add_argument('--clarity-policy', type=Path, help='override project docs/art/clarity-policy.json; invalid config is an error')
    parser.add_argument('--clarity-preset', choices=tuple(PRESETS), help='select whole default (1/1 advisory) or strict (2/1.5 blocking) preset over project settings')
    parser.add_argument('--clarity-min-ratio', type=float, help='ordinary source-pixel/render-pixel threshold (>0)')
    parser.add_argument('--clarity-background-min-ratio', type=float, help='background source/render threshold (>0)')
    parser.add_argument('--clarity-severity', choices=('advisory', 'blocking'), help='resolution findings only: advisory or blocking')


def from_args(args, project=None):
    return resolve_policy(project if project is not None else args.project, cli_preset=args.clarity_preset,
                          cli_min_ratio=args.clarity_min_ratio, cli_background_min_ratio=args.clarity_background_min_ratio,
                          cli_severity=args.clarity_severity, policy_path=args.clarity_policy)


def cli_args(policy):
    """Forward fully resolved values to child tools; do not reinterpret a different cwd's project file."""
    return ['--clarity-preset', policy['preset'], '--clarity-min-ratio', str(policy['min_ratio']), '--clarity-background-min-ratio',
            str(policy['background_min_ratio']), '--clarity-severity', policy['severity']]


def measure(source, render, policy, *, background=False):
    sx, sy = (positive(v, 'source dimension') for v in source)
    rx, ry = (positive(v, 'render dimension') for v in render)
    ratios = [sx / rx, sy / ry]
    threshold = policy['background_min_ratio' if background else 'min_ratio']
    below = min(ratios) + 1e-9 < threshold
    return {'source': [sx, sy], 'render': [rx, ry], 'source_render_ratio': min(ratios),
            'axis_source_render_ratios': ratios, 'threshold': threshold, 'background': background,
            'severity': policy['severity'], 'below_threshold': below,
            'blocking': below and policy['severity'] == 'blocking', 'auto_regenerate': False}


def group_result(policy, runtime, static, inputs_ready=True):
    """Three-state art_check row; missing input remains a defect independently of ratio policy."""
    findings = bool(runtime or static)
    if not inputs_ready:
        return False
    if findings:
        return False if policy['severity'] == 'blocking' else None
    return True
