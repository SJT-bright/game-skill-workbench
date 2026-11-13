"""Inventory accepts only the provenance owner's exact original file set, without copying evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from art_check import capture_inventory, verified_capture_inventory
from unittest.mock import patch


class ResolvedInventory(unittest.TestCase):
    def test_complete_set_can_span_verified_original_folders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();project=root/'game';old=root/'old';fresh=root/'new'
            (project/'assets').mkdir(parents=True);(project/'docs/art').mkdir(parents=True);old.mkdir();fresh.mkdir()
            viewports=[{'name':'short','width':375,'height':667},{'name':'long','width':390,'height':844}]
            (project/'docs/art/screens.json').write_text(json.dumps({'runtime_verified':True,'screens':[{'id':'level','purpose':'gameplay'}],'required_viewports':viewports}))
            files=[]
            for folder,vp in zip([fresh,old],viewports):
                shot=folder/'shot.png';shot.write_bytes(b'synthetic same-frame placeholder: inventory only, not quality/provenance')
                dump=folder/'capture-ui-dump-level.json';dump.write_text(json.dumps({'screen':'level','kind':'gameplay','viewport':vp,'screenshot':'shot.png'}));files.append(dump)
            before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
            self.assertFalse(capture_inventory(project,fresh)['ready'])
            result=capture_inventory(project,fresh,files)
            self.assertTrue(result['ready'],result['errors'])
            self.assertEqual(set(result['dump_files']),set(files))
            self.assertEqual(before,{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
            self.assertEqual(len(list(fresh.glob('*.json'))),1)
            self.assertFalse(capture_inventory(project,fresh,[])['ready'])
            self.assertFalse(capture_inventory(project,fresh,['relative.json'])['ready'])
            self.assertFalse(capture_inventory(project,fresh,[files[0],files[0]])['ready'])

    def test_entry_resolves_provenance_once_before_inventory(self):
        project=Path('/synthetic-project');folder=Path('/new-capture');build=Path('/synthetic-web')
        files=['/old-capture/a.json','/new-capture/b.json']
        proof={'ready':True,'resolved_dumps':files,'quality_promoted':False}
        with patch('art_input_check.verify_capture',return_value=proof) as verify, patch('art_check.capture_inventory',return_value={'ready':True}) as inventory:
            result,returned=verified_capture_inventory(project,folder,build,'localize')
            verify.assert_called_once_with(project,folder,build,'localize',None,None)
            inventory.assert_called_once_with(project,folder,resolved_dumps=files)
            self.assertIs(returned,proof)
            self.assertFalse(returned['quality_promoted'])
        with patch('art_input_check.verify_capture',return_value={'ready':False,'error':'tampered','resolved_dumps':files}), patch('art_check.capture_inventory',return_value={'ready':False}) as inventory:
            verified_capture_inventory(project,folder,build,'localize')
            inventory.assert_called_once_with(project,folder,resolved_dumps=None)


if __name__=='__main__':unittest.main()
