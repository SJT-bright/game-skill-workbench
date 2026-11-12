"""Actual prepare_delivery path; only the external CLI is replaced with an explicit success fixture."""
import importlib.util,json,tempfile,unittest,zipfile,sys,os
from pathlib import Path
from unittest.mock import patch
from test_upload_size_gate import payload
HERE=Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[1]/'cocos-game-check/package-check/scripts'))

class DeliveryReceipt(unittest.TestCase):
    def test_project_zip_with_green_cli_refuses_and_writes_block_not_success(self):
        spec=importlib.util.spec_from_file_location('receipt_delivery',HERE.parents[1]/'cocos-game-check/package-check/scripts/prepare_delivery.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        stable = Path(os.environ.get('SKILL_TEST_STABLE_ROOT', Path.cwd()))
        stable.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='delivery-receipt-unit-',dir=stable) as d:
            root=Path(d);archive=root/'test.zip';native=root/'native';native.mkdir();record=root/'delivery.json'
            with zipfile.ZipFile(archive,'w') as z:
                for name,data in payload().items():z.writestr(name,data)
            original=archive.read_bytes()
            with patch('tiktok_cli_gate.verify',return_value={'passed':True,'errors':[]}),patch.object(m,'audit_final_startup',side_effect=AssertionError('must reject without touching runtime')) as startup:
                with self.assertRaisesRegex(ValueError,'writer receipt'):
                    m.prepare(archive,native,'test',record,project=root)
                startup.assert_not_called()
            self.assertEqual(archive.read_bytes(),original);self.assertFalse(record.exists())
            blocked=json.loads(Path(str(record)+'.blocked.json').read_text())
            self.assertFalse(blocked['delivery_ready'])
            self.assertEqual(blocked['checks'][-1]['id'],'package.writer_receipt')
            check=json.loads(Path(str(record)+'.size.json').read_text())
            self.assertTrue(check['size_passed']);self.assertTrue(check['tiktok_cli']['passed']);self.assertFalse(check['passed'])
if __name__=='__main__':unittest.main()
