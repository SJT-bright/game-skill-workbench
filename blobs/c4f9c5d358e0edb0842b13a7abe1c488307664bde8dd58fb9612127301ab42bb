#!/usr/bin/env python3
"""v7.8 (Saul 10-31): a local in-game ranking is allowed, so audit_ui_coverage no longer treats a button merely named
Ranking / RankList / 排名 as a removed social feature. Leaderboards, friend ranks, leagues, 排行榜, 好友榜 and 周榜 still
count as removed (W99 moved the real social-board checks to audit_no_social_features.py).

    PYTHONDONTWRITEBYTECODE=1 python3 -B test_ui_coverage_local_rank.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_ui_coverage as U  # noqa: E402


class LocalRankWords(unittest.TestCase):
    def test_local_match_places_are_not_removed_words(self):
        for name in ('Ranking', 'btn_ranking', 'RankList', 'rank_list', '排名', 'result_rank'):
            self.assertIsNone(U.REMOVED_WORDS.search(name), name)

    def test_feature_policy_uses_the_same_rule(self):
        import feature_policy as FP
        for name in ('Ranking', 'rank', 'ranked_mode', '排名'):
            self.assertIsNone(FP.LEAGUE_WORDS.search(name), name)
        for name in ('Leaderboard', 'friendRank', 'Weekly League', '排行榜', '好友榜', '周榜'):
            self.assertIsNotNone(FP.LEAGUE_WORDS.search(name), name)

    def test_social_boards_still_are(self):
        for name in ('Leaderboard', 'leader_board', 'friendRank', 'friend_rank', 'Weekly League', '排行榜', '好友榜', '周榜',
                     'more_games', 'check_in'):
            self.assertIsNotNone(U.REMOVED_WORDS.search(name), name)


if __name__ == '__main__':
    unittest.main()
