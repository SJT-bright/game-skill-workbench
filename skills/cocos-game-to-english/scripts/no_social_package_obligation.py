"""Mandatory source/export no-social obligation shared by package writers.

Resolve only project/assets or direct project/source children. Native-only wrappers
remain supported by a valid game.js/game.json pair, with explicit provenance in
the result. Never infer social clearance from absent source.
"""
import hashlib,json,tempfile
from pathlib import Path
from audit_no_social_features import audit

def resolve_source(project):
    root=Path(project).resolve(); candidates=[]
    if (root/'assets').exists():
        if not (root/'assets').is_dir():raise ValueError('assets is not a directory')
        candidates.append(root)
    source=root/'source'
    if source.is_symlink():raise ValueError('symlink source root refused')
    if source.is_dir():
        for child in sorted(source.iterdir()):
            if child.is_symlink():raise ValueError('symlink source candidate refused: '+str(child))
            if child.is_dir() and (child/'assets').is_dir() and (child/'project.json').is_file():candidates.append(child.resolve())
    if len(candidates)>1:raise ValueError('ambiguous Cocos sources: '+', '.join(map(str,candidates)))
    if not candidates:
        if source.exists():raise ValueError('source directory exists but no Cocos assets/project.json root found')
        return None
    candidate=candidates[0];assets=candidate/'assets'
    if assets.is_symlink() or not assets.resolve().is_relative_to(root):raise ValueError('assets root escapes project or is a symlink')
    return candidate

def _decisions(root,report):
    path=root/'docs/league/decision.json'
    if not path.is_file():return
    raw=path.read_bytes();report['artifacts']['workspace/decision/league']=hashlib.sha256(raw).hexdigest()
    try:record=json.loads(raw)
    except (ValueError,UnicodeDecodeError):record=None
    if not isinstance(record,dict) or record.get('decision') not in ('none','skip'):
        report['findings'].append({'file':str(path),'kind':'obsolete_enabling_decision','match':str(record)[:180]})

def verify(project,native):
    root=Path(project).resolve();native=Path(native).resolve();source=resolve_source(root)
    if not (native/'game.js').is_file() or not (native/'game.json').is_file():raise ValueError('no-social obligation requires actual Native game.js/game.json root')
    if source is not None:
        report=audit(source,native=native);provenance={'mode':'cocos_source','source_root':str(source)}
    else:
        # Use the unchanged scanner on a deliberately empty source context, not
        # a missing source root. All actual Native scripts/JSON remain scanned.
        with tempfile.TemporaryDirectory(prefix='no-social-native-only-') as td:
            empty=Path(td);(empty/'assets').mkdir();report=audit(empty,native=native)
        provenance={'mode':'native_only','source_available':False,'native_root':str(native),'entry_sha256':{n:hashlib.sha256((native/n).read_bytes()).hexdigest() for n in ('game.js','game.json')}}
    if source!=root:_decisions(root,report)
    report['passed']=not report['findings'];report['source_provenance']=provenance
    if not report['passed']:raise ValueError('forbidden social package features: '+json.dumps(report['findings'],ensure_ascii=False))
    return report
