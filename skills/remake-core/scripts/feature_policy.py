"""Explicit optional extension records; missing/malformed records never enable a feature."""
import json
import re
from pathlib import Path

def read_record(project, path):
    try:
        value = json.loads((Path(project) / path).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def enabled(project):
    return {'league': False,  # 2026-10-24: historical decisions cannot enable rankings
            # Remake package (user 2026-10-27): the 7-day check-in is a required module, so it is on unless a project
            # explicitly writes false (which audit_optional_features.py then rejects).
            'checkin': read_record(project, 'docs/features.json').get('daily_checkin') is not False}

LEAGUE_WORDS = re.compile(r'leader|ranking|rank|league|排行|排名', re.I)
CHECKIN_WORDS = re.compile(r'check[-_ ]?in|sign[-_ ]?in|签到|daily[-_ ]?(reward|bonus|login)', re.I)
PERMANENT_WORDS = re.compile(r'share|分享|invite|邀请|more[-_ ]?games?|cross[-_ ]?promo|更多游戏|互推|串联', re.I)

def removed(value, flags):
    return bool(PERMANENT_WORDS.search(value) or
                (not flags.get('league') and LEAGUE_WORDS.search(value)) or
                (not flags.get('checkin') and CHECKIN_WORDS.search(value)))

def economy_disabled(project, module_report=None):
    """Only a real explicit no-skins record and an empty collection table allow N/A; when a module report is given it
    must be passing and say no skins. The final audit passes None (user 2026-10-24: MOD-01 is a design-stage check,
    the final audit reads the project record only)."""
    core = read_record(project, 'docs/modules.json')
    if (core.get('schema') != 'game_modules.v1' or not str(core.get('asked', '')).strip()
            or not isinstance(core.get('skins'), dict) or core['skins'].get('user_choice') is not False):
        return False
    if module_report is not None and (not isinstance(module_report, dict) or module_report.get('passed') is not True
                                      or (module_report.get('decision') or {}).get('skins') is not False):
        return False
    for path in ('assets/resources/config/unlock_table.json', 'docs/economy/unlock_table.json'):
        file = Path(project) / path
        if file.exists():
            data = read_record(project, path)
            if not isinstance(data.get('items'), list) or data['items']:
                return False
    return True
