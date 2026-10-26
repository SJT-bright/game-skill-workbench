import json,tempfile,unittest
from pathlib import Path
from audit_league import audit

class RankingProhibitionTests(unittest.TestCase):
    def test_clean_project_passes_without_inventing_module_decisions(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'assets').mkdir();self.assertTrue(audit(p)['passed'])
    def test_old_enabling_decisions_and_source_remain_refused(self):
        for decision in ['add','keep_original']:
            with tempfile.TemporaryDirectory() as td:
                p=Path(td);(p/'assets').mkdir();(p/'docs/league').mkdir(parents=True);(p/'docs/league/decision.json').write_text(json.dumps({'decision':decision}));self.assertFalse(audit(p)['passed'])
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'assets').mkdir();(p/'assets/LeagueSim.ts').write_text('export const ranking=1;');self.assertFalse(audit(p)['passed'])
if __name__=='__main__':unittest.main()
