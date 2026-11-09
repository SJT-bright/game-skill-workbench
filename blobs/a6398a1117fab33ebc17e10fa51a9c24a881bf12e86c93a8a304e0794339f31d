"""Existing art acceptance is consumed, not re-executed, at later workflow nodes."""
import json
import hashlib
from pathlib import Path

def verify_original_report(receipt):
    """A matching input digest does not recover a missing or replaced verdict."""
    proof=receipt.get('art_check') or {}
    name=proof.get('report');expected=proof.get('report_sha256')
    if not name or not expected:
        raise ValueError('原美术回执未绑定完整报告及哈希；先恢复原证据，不能视为完整通过')
    path=Path(name)
    if not path.is_file():raise ValueError('原美术报告已缺失，先恢复原证据：'+str(path))
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('原美术报告字节已变，不能沿用旧通过：'+str(path))
    report=json.loads(raw)
    if (not isinstance(report,dict) or report.get('passed') is not True
            or report.get('failed') not in (None,0)
            or any(isinstance(r,dict) and r.get('status')=='需处理' for r in report.get('rows') or [])):
        raise ValueError('原美术报告不是完整通过，不能从回执状态推定通过：'+str(path))
    return path

def resolve(args):
    import art_receipt
    project=Path(args.project).resolve()
    receipt,error=art_receipt.read(project)
    if receipt is None:
        if error:raise ValueError('原美术记录读不了；先恢复记录，不能当作首次任务重新全测：'+error)
        return None
    capture=args.capture_build or (args.build if args.build and (args.build/'index.html').exists() else None)
    current=art_receipt.check_history(project,args.board,capture_build=capture)
    # The successful original receipt must be a real full pass. A scoped approval
    # is kept as scoped approval, never promoted here.
    if receipt.get('status')=='pass' and current.get('state')=='match_pass' and current.get('level')=='ok':
        verify_original_report(receipt)
        print(json.dumps({'action':'reuse','receipt':str(art_receipt.receipt_path(project)),
            'original_at':receipt.get('created'),'message':'美术原验收仍有效；只核对记录，未重跑像素/文字/页面检查'},ensure_ascii=False))
        if args.out:
            args.out.mkdir(parents=True,exist_ok=True)
            (args.out/'reuse.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
        return 0
    if args.maintenance_scope or args.english_visual_scope:
        return None  # Existing exact-state maintenance executors own the changed units.
    changed={k:current.get(k) for k in ('changed','added','removed','display_changed','display_added','display_removed') if current.get(k)}
    print(json.dumps({'action':'scope_required','state':current.get('state'),'changed':changed,
        'message':'已有美术验收记录，禁止自动全量重检。运行 art_iteration_plan.py 定位素材/页面，'
                  '只执行对应首件、UI 合同或维护范围；原通过项保留。','receipt':str(art_receipt.receipt_path(project))},ensure_ascii=False))
    return 3
