"""Transitive exact R18->R19 visibility-only issue dependency reuse; no raw rewriting."""
from pathlib import Path
import debrand_art_successor as A

def validate(project,contract,ref,native,original_validator,context=None):
 issue_id=contract.get('id')
 if issue_id not in A.IDS:raise ValueError('issue has no debrand historical dependency bridge')
 project=Path(project).resolve();native=Path(native).resolve()
 if context is None:
  file=project/A.MANIFEST;doc=A.read(file)
  if set(doc.get('original_issue_proofs',{}))!=A.IDS:raise ValueError('exact original seven issue proof anchors required')
  context={'project':project,'native':native,'doc':doc,'manifest_sha256':A.sha(file)}
 if context['project']!=project or context['native']!=native:raise ValueError('debrand issue context belongs to another build')
 if ref!=context['doc']['original_issue_proofs'][issue_id]:raise ValueError('original registered issue proof was replaced')
 original=A.read(A.checked(ref));root=Path(original['executed_native_roots']['current']).resolve()
 # Every original proof still passes the unchanged original assertion function
 # against its actual executed Native, including current/negative/normal artifacts.
 proof=original_validator(contract,ref,root)
 oldart=A.read(A.checked(context['doc']['predecessor']['art_scope']))
 expected=oldart['predecessor']['executed_native']if issue_id!='SS-PLAY-IMAGE'else oldart['current_native']
 if str(root)!=expected:raise ValueError('historical issue Native identity was rebound')
 if 'validated'not in context:context['validated']=A.common(project,native,context['doc'])
 # Common validation includes old exact PLAY source/native proof on the read-only
 # R18 historical source view and original S789 executions; new guard proves the
 # sole R18->R19 visibility flag. No current-S or browser replay per old family.
 targets={name:A.sha(native/name)for name in contract['targets']}
 reuse={'mode':'exact_debrand_visibility_delta_with_original_PLAY_bridge','semantic_dependency_reused':True,'dependency_bytes_reused':False,'scope_manifest_sha256':context['manifest_sha256'],'original_executed_native_root':str(root),'original_target_sha256':proof['target_sha256'],'current_target_sha256':targets,'debrand_scope':str(project/A.MANIFEST),'current_debrand_report':context['validated']['shared']['current_affected_state']['report'],'boundary':'Original issue execution retained. R17-to-R18 PLAY predicates and R18-to-R19 one-boolean scene delta validated transitively; only R19 normal/logo-hidden observations are new.'}
 return proof,reuse,context
