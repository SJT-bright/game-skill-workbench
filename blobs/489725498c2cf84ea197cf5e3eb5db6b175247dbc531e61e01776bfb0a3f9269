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
            self.assertTrue(all(r.get('award_level',r.get('level'))<=70 for r in table['items'] if r.get('limited')))

    def test_seeded_rewards_are_deterministic_and_bounded(self):
        for total in [70,75,85,121]:
            for seed in [0,1,42,999]:
                plan=make(total,50,'hero_limited',seed,'Tokens',skin_mode='every_10')
                self.assertEqual(plan,make(total,50,'hero_limited',seed,'Tokens',skin_mode='every_10'))
                self.assertEqual(reward_errors(plan),[])
                self.assertEqual(len(plan['levels']),total)
                self.assertGreaterEqual(len({r['coins'] for r in plan['levels'] if r['type']!='bonus'}),2)
                normal=[r for r in plan['levels']if r['type']!='bonus']
                for start in range(0,len(normal)-9,10):self.assertEqual(sum(r['coins']for r in normal[start:start+10]),500)
                for row in plan['levels']:
                    if row['type']!='bonus':
                        self.assertLessEqual(abs(row['coins_roll']),row['coins_band'])
                        self.assertEqual(row['coins'],row['coins_base']+row['coins_roll'])
                    else:self.assertEqual(row['coins'],3*row['normal_level_coins'])

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

    def test_actual_normal_wins_afford_exact_tier_boundaries(self):
        from product_contract import PRICE_LEVEL_TARGETS
        for base in (1,9,10,37,50,100):
            plan=make(100,base,None,57,'Tokens')
            income=[r['coins']for r in plan['levels']if r['type']!='bonus']
            for wins in PRICE_LEVEL_TARGETS.values():
                self.assertEqual(sum(income[:wins]),wins*base)
                self.assertLess(sum(income[:wins-1]),wins*base)

    def test_current_budget_rejects_wrong_prices_ad_or_cooldown(self):
        from product_contract import budget_errors
        table=skin_table(50,'levels',70,True,'hero')
        self.assertEqual(budget_errors(table),[])
        for key,value in [('coins_per_ad',50),('gift_multiplier',4),('gift_cooldown_ms',60_000)]:
            broken=copy.deepcopy(table);broken[key]=value;self.assertTrue(budget_errors(broken))
        broken=copy.deepcopy(table);broken['items'][0]['coins']+=1;self.assertTrue(budget_errors(broken))

    def test_original_level_scope_preserves_or_extends_actual_maps(self):
        from audit_level_plan import audit_original_levels
        def rows(count):return [dict(level=i,layout=[i,i+1,i+2])for i in range(1,count+1)]
        # 英化不补关 (Saul 2026-10-28; replaces the 2026-10-24 rule "pad to 70"): production keeps the original count.
        for count in (1,40,69,70,75,121):
            checks=[];audit_original_levels(rows(count),rows(count),lambda i,ok,d:checks.append((i,ok)))
            self.assertTrue(all(ok for _,ok in checks),checks)
        for original,current in [(rows(40),rows(70)),(rows(69),rows(70)),(rows(75),rows(70)),(rows(75),rows(80)),(rows(70),rows(71)),(rows(40),rows(69)),(rows(40),rows(71)),(rows(40),rows(75))]:
            checks=[];audit_original_levels(original,current,lambda i,ok,d:checks.append(ok));self.assertFalse(all(checks))
        # Levels the user asked for (explicit_total) must still be distinct actual maps.
        ask={'count':70,'authorized_by':'Saul 2026-10-30','reason':'Saul asked for one more real level in this English game'}
        duplicate=rows(69)+[dict(level=70,layout=rows(69)[0]['layout'])]
        checks=[];audit_original_levels(rows(69),duplicate,lambda i,ok,d:checks.append(ok),ask);self.assertFalse(all(checks))
        # Shared grid with a materially different puzzle target is not just a renamed map.
        changed_goal=rows(69)+[dict(level=70,layout=rows(69)[0]['layout'],goal={'target':42})]
        checks=[];audit_original_levels(rows(69),changed_goal,lambda i,ok,d:checks.append(ok),ask);self.assertTrue(all(checks))
        checks=[];audit_original_levels(rows(69),changed_goal,lambda i,ok,d:checks.append(ok));self.assertFalse(all(checks))
        shuffled=rows(75);shuffled[0],shuffled[1]=shuffled[1],shuffled[0]
        checks=[];audit_original_levels(rows(75),shuffled,lambda i,ok,d:checks.append(ok));self.assertFalse(all(checks))

    def test_localize_cli_reads_actual_inputs_without_new_design_gates(self):
        import tempfile,subprocess,sys
        from pathlib import Path
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'assets/resources/config').mkdir(parents=True)
            plan=root/'assets/resources/config/level_plan.json';plan.write_text(json.dumps({'mode':'levels','total_levels':75}))
            original=root/'original.json';current=root/'assets/levels.json';report=root/'report.json'
            rows=[{'level':n,'layout':[n,n+1],'difficulty':76-n}for n in range(1,76)]
            original.write_text(json.dumps(rows));current.write_text(json.dumps(rows))
            cmd=[sys.executable,str(Path(__file__).with_name('audit_level_plan.py')),'--project',str(root),'--board','localize','--original-levels',str(original),'--current-levels',str(current),'--out',str(report)]
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            checks=json.loads(report.read_text())['checks'];self.assertFalse(any(c['id'].startswith(('limited','bonus','difficulty'))for c in checks))
            rows[0]['layout']=[999];current.write_text(json.dumps(rows))
            self.assertNotEqual(subprocess.run(cmd,capture_output=True,text=True).returncode,0)

    def test_non_skin_item_shop_uses_same_five_tier_budget(self):
        import tempfile,subprocess,sys
        from pathlib import Path
        from product_contract import PRICE_LEVEL_TARGETS,ECONOMY_POLICY,GIFT_COOLDOWN_MS
        table={'economy_policy':ECONOMY_POLICY,'normal_level_coins':20,'coins_per_level':20,'coins_per_ad':100,'gift_multiplier':5,'gift_cooldown_ms':GIFT_COOLDOWN_MS,'price_level_targets':PRICE_LEVEL_TARGETS,'price_profile':'ordinary-levels','items':[]}
        for i,(rarity,count)in enumerate(PRICE_LEVEL_TARGETS.items(),1):table['items'].append({'id':rarity,'group':'tools','order':i,'rarity':rarity,'limited':rarity=='limited','unlock':'coins','coins':20*count,'ads':0})
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);path=root/'table.json';report=root/'report.json';path.write_text(json.dumps(table))
            cmd=[sys.executable,str(Path(__file__).with_name('audit_acquisition_progression.py')),'--table',str(path),'--report',str(report)]
            result=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            table['items'][-1]['coins']=980;path.write_text(json.dumps(table))
            self.assertNotEqual(subprocess.run(cmd,capture_output=True,text=True).returncode,0)


if __name__=='__main__':unittest.main()
