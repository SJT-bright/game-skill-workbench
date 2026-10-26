from pathlib import Path
import tempfile,json,shutil
from audit_atlas_slices import audit,check_project
E=Path(__file__).resolve().parent
fixtures=E/'adapter-fixtures'
if not fixtures.exists():fixtures=E.parent/'examples/flat-atlas'
with tempfile.TemporaryDirectory(prefix='flat-atlas-real-controls-') as tmp:
 p=Path(tmp);(p/'assets/art').mkdir(parents=True);shutil.copy2(fixtures/'buttons.png',p/'assets/art/buttons.png')
 f=p/'assets/atlas.json';f.write_text((fixtures/'old-atlas.json').read_text());old=audit(f);bad={i['frame']for i in old['issues']};assert bad=={'btn_try','btn_nothanks'},bad
 detected=check_project(p);assert detected['applicable'] and not detected['passed']
 f.write_text((fixtures/'fixed-atlas.json').read_text());assert audit(f)['passed'];assert check_project(p)['passed']
 (p/'assets/duplicate').mkdir();shutil.copy2(fixtures/'buttons.png',p/'assets/duplicate/buttons.png')
 try:audit(f)
 except ValueError as ex:assert 'texture_not_unique' in str(ex)
 else:raise AssertionError('ambiguous texture accepted')
 print('Real flat-atlas controls: two old buttons rejected; normal PLAY/NEXT and fixed frames pass; ambiguous texture rejected.')
