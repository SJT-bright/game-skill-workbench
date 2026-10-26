import copy
import json
import unittest
from product_contract import limited_levels, skin_counts, reward_rows, reward_errors
from make_level_plan import make
from make_skin_table import make as skin_table


class ProductContractTests(unittest.TestCase):
    def test_tail_does_not_create_limited_level_or_skin(self):
        self.assertEqual(limited_levels(10,75),list(range(10,71,10)))
        for mode,count in [('final',20),('every_10',26)]:
            self.assertEqual(skin_counts(75,mode)['total'],count)
            table=skin_table(50,'levels',75,True,'hero',limited_mode=mode)
            self.assertEqual(len([r for r in table['items'] if r['group']=='skin']),count)
            self.assertTrue(all(r['level']<=70 for r in table['items'] if r.get('limited')))

    def test_seeded_rewards_are_deterministic_and_bounded(self):
        for total in [70,75,85,121]:
            for seed in [0,1,42,999]:
                plan=make(total,50,'hero_limited',seed,'Tokens',skin_mode='every_10')
                self.assertEqual(plan,make(total,50,'hero_limited',seed,'Tokens',skin_mode='every_10'))
                self.assertEqual(reward_errors(plan),[])
                self.assertEqual(len(plan['levels']),total)
                self.assertGreaterEqual(len({r['coins'] for r in plan['levels'] if r['type']!='bonus'}),5)
                for row in plan['levels']:
                    if row['type']!='bonus':
                        self.assertLessEqual(abs(row['coins_roll']),row['coins_band'])
                        self.assertEqual(row['coins'],row['coins_base']+row['coins_roll'])
                    else:self.assertEqual(row['coins'],3*row['chapter_median'])

    def test_changed_reward_seed_or_row_refused(self):
        p=make(70,50,None,42,'Tokens')
        p['reward_seed']=41
        self.assertTrue(reward_errors(p))
        p=make(70,50,None,42,'Tokens');p['levels'][0]['coins']+=1
        self.assertTrue(reward_errors(p))
        p=make(70,50,None,42,'Tokens');p.pop('reward_policy')
        self.assertTrue(reward_errors(p))

    def test_first_clear_coin_milestone_uses_previous_five_stored_rewards(self):
        p=make(75,50,None,42,'Tokens')
        for row in p['levels']:
            if row['type']=='milestone':
                self.assertEqual(row['reward']['amount'],sum(r['coins'] for r in p['levels'][row['level']-6:row['level']-1]))


if __name__=='__main__':unittest.main()
