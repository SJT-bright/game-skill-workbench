"""Reuse needs independent full-frame evidence, not a stable declaration."""
import json
from pathlib import Path
import subprocess
import unittest

HERE = Path(__file__).resolve().parent

class StabilityTests(unittest.TestCase):
    def test_independent_confirmation_and_fail_closed_controls(self):
        script = r"""
        import {confirmStability,confirmCurrentFixture} from MODULE;
        const state={stable:true,kind:'popup',storageSha:'fixture',externalInputs:[]};
        const a={id:'a',session:'s1',timeOrigin:1,case:'settings',caseHash:'case',round:'r',
          version:'v',env:'e',png:'pixels',reads:['index.html','shared.png'],
          storage:{supported:true,sha256:'fixture'},auxiliary:false};
        const second={...a,id:'b',session:'s2',timeOrigin:2};
        let checked=0;
        function reject(change,policy=state){
          try{confirmStability(a,{...second,...change},policy);}
          catch{checked++;return;}
          throw Error('unsafe confirmation accepted: '+JSON.stringify(change));
        }
        confirmStability(a,second,state);
        reject({png:'one-red-pixel-changed'});
        reject({session:'s1'}); reject({timeOrigin:1});
        reject({version:'v2'}); reject({round:'r2'});
        reject({env:'other'}); reject({caseHash:'other'});
        reject({reads:['index.html']}); reject({auxiliary:true});
        reject({storage:{supported:true,sha256:'changed-save'}});
        reject({storage:{supported:false,sha256:'fixture'}});
        reject({}, {...state,storageSha:null});
        reject({}, {...state,stable:false}); reject({}, {...state,kind:'gameplay'});
        reject({}, {...state,externalInputs:['clock']});
        reject({}, {...state,externalInputs:undefined});
        const anchor={env:'e',storage:{supported:true,sha256:'fixture'}};
        confirmCurrentFixture(state,a,anchor);
        for(const invalid of [{...anchor,storage:{supported:true,sha256:'new-save'}},
          {...anchor,storage:null},{...anchor,env:null}]){
          let refused=false;
          try{confirmCurrentFixture(state,a,invalid);}catch{refused=true;checked++;}
          if(!refused)throw Error('changed current fixture accepted');
        }
        console.log(JSON.stringify({positive:1,rejected:checked}));
        """.replace('MODULE', json.dumps((HERE/'art_capture_round.mjs').as_uri()))
        proc = subprocess.run(['node','--input-type=module','-e',script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {'positive':1, 'rejected':19})

if __name__ == '__main__':
    unittest.main()
