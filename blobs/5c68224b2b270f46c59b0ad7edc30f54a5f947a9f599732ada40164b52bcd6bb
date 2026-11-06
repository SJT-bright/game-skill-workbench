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
    # 简化.11.14.1 (Codex 英化会话 2026-11-05: an original game with no coins, random levels and no home page was told by
    # art_check to add a coin top bar, a level table and a map). The top resource bar and the level map are remake-board
    # designs (remake-levels). An English game keeps the original game and adds no systems (Saul 2026-10-28), so they do
    # not apply -- unless the project used those boards for new gameplay Saul asked for (a LOCALIZE_BOARD_RECORDS file
    # exists, Saul 2026-10-30; applies() then answers block). preflight.py makes the same call for its rows.
    'top_bar': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'not_applicable'},
    'level_map': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'not_applicable'},
    # R4N1 (补查2 第 5 组, SLS07 / SLS35 / 弹球传奇): four more new-game rules that an English game's original gameplay
    # does not follow. Same call as top_bar / level_map: English games get 不适用 unless the project has a record of that
    # board (RULE_RECORDS below); remake and unknown boards are checked as before.
    #   skin_min_levels     make_skin_table.py --levels needs --final-level >= 60 (SLS35: original 6 levels)
    #   econ_window_levels  make_economy_config.py needs --total-levels >= ECON-LEVEL10 window (10) (SLS35)
    #   checkin_design      CheckinFlow / DailyCheckin design rows: coin days grow, a check-in skin, a big day-7 bundle
    #                       (弹球传奇 keeps its original seven-day table)
    #   writer_coin_reward  check_kit_project.py (run by the package writer): PlatformConfig.normalLevelCoins > 0
    #                       (SLS07 has no coins; Saul 11-04 「没金币游戏的两个奖励点」 pay the no-coin replacements)
    'skin_min_levels': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'not_applicable'},
    'econ_window_levels': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'not_applicable'},
    'checkin_design': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'not_applicable'},
    'writer_coin_reward': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'not_applicable'},
    # R4Q3 (补查3 第 3 组, 火箭三消 / 弹球传奇, Saul chose 「保留原画风」 twice): art_check's 大块深色与纯色底 row does
    # not apply to the ORIGINAL pictures of an English game that keeps its art (same SHA-256 as the Chinese original,
    # original_style.py); new pictures are still checked. Remake, and English games that chose remake art, block.
    'dark_flat_original': {'remake': 'block', 'localize': 'not_applicable', 'localize_remake_art': 'block'},
}

# The records the remake boards write. Must stay equal to preflight.LOCALIZE_BOARD_RECORDS (test_localize_design_rows.py).
LOCALIZE_BOARD_RECORDS = ('docs/modules.json', 'docs/features.json', 'docs/top-bar.json', 'docs/league/decision.json',
                          'assets/resources/config/level_plan.json', 'docs/levels/level_plan.json',
                          'assets/resources/config/unlock_table.json', 'docs/economy/unlock_table.json')
BOARD_RECORD_RULES = ('top_bar', 'level_map')


def localize_board_records(project, rule=None):
    """The LOCALIZE_BOARD_RECORDS files present in project (an English game that used the remake boards).
    rule: one of RULE_RECORDS -> only the records that switch that rule on."""
    names = RULE_RECORDS.get(rule, LOCALIZE_BOARD_RECORDS) if rule else LOCALIZE_BOARD_RECORDS
    return [r for r in names if (Path(project) / r).is_file()]


# R4N1: which records switch each new rule back on for an English game. The level / economy / check-in rules are NOT
# switched on by unlock_table.json (make_skin_table.py writes it itself, so a rerun would block on its own output) or by
# a check-in config alone; they follow the remake module decision and the level plan (new levels Saul asked for).
_LEVEL_RECORDS = ('docs/modules.json', 'assets/resources/config/level_plan.json', 'docs/levels/level_plan.json')
RULE_RECORDS = {
    'skin_min_levels': _LEVEL_RECORDS,
    'econ_window_levels': _LEVEL_RECORDS,
    'checkin_design': ('docs/modules.json', 'docs/features.json'),
    'writer_coin_reward': LOCALIZE_BOARD_RECORDS,
}


def game_levels(project):
    """(real level count or None, reason) from docs/game_capabilities.json level_count (game_capabilities.py write
    --level-count N | --no-levels "why"). None = endless / not recorded."""
    if project is None:
        return None, 'no project given'
    import game_capabilities
    caps = game_capabilities.load(project)
    v = caps.get('level_count')
    if isinstance(v, int) and not isinstance(v, bool):
        return v, 'level_count=%d (%s)' % (v, caps['source'].get('level_count'))
    if isinstance(v, dict):
        return None, 'level_count none: %s' % v.get('none')
    return None, 'not recorded: docs/game_capabilities.json has no "level_count" (game_capabilities.py write --merge --level-count N)'


def rule_verdict(rule, board, project=None):
    """(applies() answer, one-line reason) for the R4N1 rules, for the CLIs to print."""
    v = applies(rule, board, project)
    if v != 'not_applicable':
        recs = localize_board_records(project, rule) if project is not None and board == 'localize' else []
        return v, ('English game with remake-board records %s: checked as a new game' % ', '.join(recs) if recs
                   else '%s board: checked as a new game' % (board or 'unknown (= remake)'))
    return v, ('English game (board localize from %s): %s does not apply to the original gameplay (feature_policy R4N1)'
               % (board_of(project)[1] if project is not None else '--board', rule))


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
    if rule in BOARD_RECORD_RULES and key != 'remake' and project is not None and localize_board_records(project):
        return 'block'
    if rule in RULE_RECORDS and key != 'remake' and project is not None:
        if localize_board_records(project, rule):
            return 'block'
        if rule == 'writer_coin_reward':
            # an English game that DOES have a coin wallet (economy_capabilities.json wallet true) must still set B
            import game_capabilities
            if game_capabilities.load(project).get('wallet') is True:
                return 'block'
    return table[key]
