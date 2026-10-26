import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from validate_starter import read_files,validate

EXAMPLE=Path(__file__).resolve().parents[1]/'examples/minimal-starter'


class StarterContractTests(unittest.TestCase):
    def files(self):return read_files(EXAMPLE)
    def mutate(self,files,name,operation):
        data=json.loads(files[name]);operation(data);files[name]=json.dumps(data).encode()

    def test_complete_example_passes_and_proposed_solutions_replay(self):
        files=self.files();self.assertTrue(validate(files)['passed'])
        plan=json.loads(files['levels/level_plan.json']);solutions=json.loads(files['levels/solutions.json'])['levels']
        for row,solution in zip(plan['levels'],solutions):
            layout=json.loads(files[row['layout_file']]);position=layout['start']
            for action in solution['actions']:
                self.assertEqual(action,'right');position+=1;self.assertLess(position,layout['length'])
            self.assertEqual(position,layout['target'])

    def test_two_file_inventory_is_not_semantic_acceptance(self):
        result=validate({'README.md':b'incomplete','ECONOMY.json':b'{}'})
        self.assertFalse(result['passed']);self.assertTrue(any('START_HERE' in e for e in result['errors']))

    def test_old_twenty_skin_every_ten_table_refused(self):
        files=self.files();self.mutate(files,'ECONOMY.json',lambda d:d.update(skins=d['skins'][:20]));self.assertFalse(validate(files)['passed'])

    def test_missing_layout_forged_solution_and_reward_change_refused(self):
        for name,change in [('layout',lambda f:f.pop('levels/layouts/001.json')),('solution',lambda f:self.mutate(f,'levels/solutions.json',lambda d:d['levels'][0].update(layout_sha256='0'*64))),('reward',lambda f:self.mutate(f,'levels/level_plan.json',lambda d:d['levels'][0].update(coins=10000)))]:
            with self.subTest(name=name):
                files=self.files();change(files);self.assertFalse(validate(files)['passed'])

    def test_banned_feature_route_id_and_nonenglish_rejected(self):
        changes=[lambda f:self.mutate(f,'starter.json',lambda d:d['features'].update(ranking=True)),lambda f:self.mutate(f,'starter.json',lambda d:d['pages'][0]['buttons'].append({'action':'weekly_league'})),lambda f:f.update({'COPY_EN.md':b'AppID = tt123456789abcdef'}),lambda f:f.update({'COPY_EN.md':'中文'.encode()})]
        for change in changes:
            files=self.files();change(files);self.assertFalse(validate(files)['passed'])

    def test_unsafe_zip_refused_before_reading_member(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'unsafe.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../outside.json','{}')
            with self.assertRaisesRegex(ValueError,'unsafe'):read_files(p)

    def test_endless_starter_has_no_invented_level_map(self):
        files=self.files();files={k:v for k,v in files.items() if not k.startswith('levels/')}
        self.mutate(files,'starter.json',lambda d:(d.update(mode='endless'),d['modules'].remove('levels')))
        self.mutate(files,'ECONOMY.json',lambda d:d.update(skin_module=False,skins=[],backgrounds=[]))
        self.assertTrue(validate(files)['passed'])

    def test_endless_missing_currency_is_rejected(self):
        files=self.files()
        for name in list(files):
            if name.startswith('levels/'):del files[name]
        self.mutate(files,'starter.json',lambda d:d.update(mode='endless',modules=['currency','result_x2','home_gift']))
        self.mutate(files,'ECONOMY.json',lambda d:d.update(skin_module=False,skins=[],backgrounds=[],currency=''))
        result=validate(files)
        self.assertFalse(result['passed']);self.assertTrue(any('currency required' in e for e in result['errors']))


if __name__=='__main__':unittest.main()
