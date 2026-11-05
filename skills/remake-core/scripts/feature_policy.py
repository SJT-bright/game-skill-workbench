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

# v7.8 (Saul 10-31, W99): a local in-game ranking is allowed, so plain rank / ranking / 排名 names no longer count
LEAGUE_WORDS = re.compile(r'leader_?board|friend_?rank|league|排行|好友榜|周榜', re.I)
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


# ---------------------------------------------------------------------------------------------------------------
# P20 (问题普查 20261104, T20 rule_conflict / checker_false_block): which board a game belongs to, and whether a rule
# applies to it, are decided HERE and nowhere else. Before this, art_check.py and design_check.py read only
# docs/board.txt (art_check then defaulted to remake), audit_glyph_core.py also read .tiktok-kit/*.json, and
# preflight.py had a third order. An English game whose board was recorded by `tiktok_finalize.py init --board` was
# checked as a remake by art_check and as an English game by audit_page_richness in the same run.
BOARDS = ('localize', 'remake')
BOARD_SOURCES = (('.tiktok-kit', 'finalize-source.json'), ('.tiktok-kit', 'policy.json'), ('docs', 'board.txt'))


def board_of(project, given=None):
    """(board, source). Order: the --board the caller was given, .tiktok-kit/finalize-source.json, .tiktok-kit/
    policy.json (both written by the package writers), docs/board.txt. Nothing recorded -> (None, 'none'); callers
    that must pick one use the strictest, remake, and say so."""
    if given in BOARDS:
        return given, '--board'
    root = Path(project)
    for rel in BOARD_SOURCES:
        path = root.joinpath(*rel)
        if rel[-1].endswith('.json'):
            value = read_record(project, '/'.join(rel)).get('board')
        else:
            try:
                value = path.read_text(encoding='utf-8-sig').strip().lower()
            except OSError:
                value = None
        if value in BOARDS:
            return value, '/'.join(rel)
    return None, 'none'


def art_style(project):
    try:
        value = (Path(project) / 'docs' / 'art-style.txt').read_text(encoding='utf-8-sig').strip().lower()
    except OSError:
        return None
    return value if value in ('original', 'remake') else None


# rule -> what it means for each board: 'block' (fails the check), 'hint' (listed, never fails), 'not_applicable'.
# 'localize_remake_art' is used for an English game whose docs/art-style.txt says remake (art checked as remake).
RULES = {
    # Saul 2026-10-30: new self-made games show samples first; English games skip them
    'samples_first': {'remake': 'hint', 'localize': 'not_applicable'},
    # Saul 2026-10-31 「small_value_font 先只拦重塑」
    'small_value_font': {'remake': 'block', 'localize': 'hint'},
    # remake-style art rules (new generated art, remake home layout): remake games, and English games that chose remake art
    'remake_art_style': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'block'},
    # Saul 2026-10-30: the remake home layout (settings top-left, bottom row = two platform entries) is remake only
    'remake_home_layout': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'not_applicable'},
}


# P20 第 3 点「能力先判」(问题普查 20261104): rules that apply only when the game HAS something. The answer comes from the
# capability record written while the game is made (game_capabilities.py: docs/economy/economy_capabilities.json +
# docs/game_capabilities.json), never from a check's own guess. rule -> (need, what the rule asks). The board table is
# the same as RULES (both boards block unless written).
CAP_RULES = {
    'econ_b': ('wallet', 'find B (ECON-B) and pay B-based coins'),
    'result_x2_coins': ('wallet', 'result watch-ad x2 of coins (ECON-X2)'),
    'result_x2_items': ('no_wallet', 'no-coin result x2 of picked-up items (ECON-NOCUR)'),
    'skin_rules': ('skins', 'skin prices, ad unlock and the skin trial popup (ECON-ADUNLOCK / ECON-SKINTRIAL)'),
    'energy_rules': ('energy', 'energy refill rules (ECON-ENERGY)'),
    'pause_popup_case': ('pause_button', 'resume_play case "pause popup open while the phone takes the game"'),
    'ad_double_entry': ('ad_role:double', 'a result-page Watch Ad x2 entry (英化固定入口第 6 项)'),
    'ad_revive_entry': ('ad_role:revive', 'a revive entry (英化固定入口第 7 项)'),
}


def capability(rule, project=None, caps=None):
    """('applies' | 'not_applicable' | 'not_run', reason) for a CAP_RULES rule. caps: game_capabilities.load() result
    (else read from project). A 'no' in the record -> not_applicable with the record's reason; nothing recorded ->
    not_run naming the file and field to write. 'no_entry' (an ad role the record does not list and does not excuse)
    -> applies: the check then reports the missing entry, as before."""
    need, what = CAP_RULES[rule]
    if caps is None:
        if project is None:
            return 'not_run', '%s: no project given, so no capability record to read' % what
        import game_capabilities  # same folder; lazy so feature_policy keeps no import-time dependency
        caps = game_capabilities.load(project)
    import game_capabilities
    v, why = game_capabilities.verdict(caps, need)
    if v == 'no':
        return 'not_applicable', '%s does not apply: %s' % (what, why)
    if v == 'unknown':
        return 'not_run', '%s: %s' % (what, why)
    return 'applies', why


def applies(rule, board, project=None, caps=None):
    """'block' | 'hint' | 'not_applicable' for this rule on this board. Unknown board = remake (strictest).
    CAP_RULES rules also read the capability record: 'not_applicable' when the game lacks the thing, 'not_run' when the
    record does not say (capability() gives the reason)."""
    if rule in CAP_RULES:
        v, _ = capability(rule, project, caps)
        return {'applies': 'block'}.get(v, v)
    table = RULES[rule]
    key = board if board in BOARDS else 'remake'
    if key == 'localize' and project is not None and art_style(project) == 'remake' and 'localize_remake_art' in table:
        key = 'localize_remake_art'
    return table[key]
