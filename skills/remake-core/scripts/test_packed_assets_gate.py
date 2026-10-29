#!/usr/bin/env python3
"""Calibrate missing-path/atlas gates with independent broken and normal fixtures."""
from pathlib import Path
import tempfile,json,struct,hashlib
from audit_packed_assets import audit

def run():
 results={}
 with tempfile.TemporaryDirectory(prefix='asset gate calibration ') as td:
  r=Path(td);(r/'preview-ui/art').mkdir(parents=True);png=b'\x89PNG\r\n\x1a\n'+b'\0'*8+struct.pack('>II',16,16)
  (r/'preview-ui/art/icons.png').write_bytes(png);m={'textures':{'icons':{'width':16,'height':16,'sha256':hashlib.sha256(png).hexdigest()}},'frames':{'button':{'texture':'icons','rect':[0,0,16,16]}}};p=r/'preview-ui/art/frames.json';p.write_text(json.dumps(m));(r/'game.js').write_text("const art='preview-ui/art/icons.png';")
  results['normal']=audit(r)['passed']
  (r/'game.js').write_text("const art='preview-ui/art/old-path.png';");results['moved_path_refused']=not audit(r)['passed'];(r/'game.js').write_text("require('./missing-entry');");results['missing_entry_refused']=not audit(r)['passed'];(r/'game.js').write_text('')
  m['frames']['button']['rect']=[0,0,17,16];p.write_text(json.dumps(m));results['crop_outside_atlas_refused']=not audit(r)['passed'];m['frames']['button']['rect']=[0,0,16,16];m['textures']['icons']['sha256']='0'*64;p.write_text(json.dumps(m));results['stale_compressed_texture_refused']=not audit(r)['passed']
 print(json.dumps({'passed':all(results.values()),'cases':results}));return 0 if all(results.values()) else 1
if __name__=='__main__':raise SystemExit(run())
