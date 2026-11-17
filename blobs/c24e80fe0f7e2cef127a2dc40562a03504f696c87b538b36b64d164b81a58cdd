"""Fresh real-mouse start + gameplay verification before each user preview handoff."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent

def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get('schema') != 'preview_mouse_plan.v1':
        raise ValueError('需要 preview_mouse_plan.v1；先按真实画面登记开局和玩法操作，不能用触摸通过代替')
    for key in ('ready','started','operation_state','operation_ok'):
        if not isinstance(plan.get(key),str) or not plan[key].strip():raise ValueError('mouse plan missing '+key)
    def action(row):
        if not isinstance(row,dict) or len(set(row)&{'node','click','drag'}) != 1:raise ValueError('mouse action needs exactly one node/click/drag')
        if 'node' in row and (not isinstance(row['node'],str) or not row['node']):raise ValueError('invalid node target')
        for pair in ([row['click']] if 'click' in row else row.get('drag',[])):
            if not isinstance(pair,list) or len(pair)!=2 or any(type(x) not in (int,float) or not 0<=x<=4000 for x in pair):raise ValueError('invalid mouse coordinates')
        if 'drag' in row and len(row['drag'])!=2:raise ValueError('drag needs from/to coordinates')
        if type(row.get('wait_ms',0)) not in (int,float) or not 0<=row.get('wait_ms',0)<=3000:raise ValueError('invalid action wait')
    if type(plan.get('timeout_ms',45000)) is not int or not 1000<=plan.get('timeout_ms',45000)<=45000:raise ValueError('invalid timeout_ms')
    action(plan.get('start'))
    if not isinstance(plan.get('operations'),list) or not 1<=len(plan['operations'])<=12:raise ValueError('missing gameplay mouse operations')
    for row in plan['operations']:action(row)
    return plan

def check(url, plan_path, out, *, run=None, executable=None):
    parts=urlsplit(url)
    if parts.scheme!='http' or parts.hostname not in ('127.0.0.1','localhost','::1') or parts.username or parts.password:
        raise ValueError('mouse preview check only accepts a local HTTP preview')
    plan_path=Path(plan_path);plan=validate_plan(json.loads(plan_path.read_text()))
    out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise ValueError('mouse observation output must be new')
    ego=executable or shutil.which('ego-browser')
    if not ego:raise ValueError('真实鼠标检查未执行：找不到 Ego；不给试玩链接，不换触摸指令或 Chrome 代测')
    cfg={'url':url,'plan':plan,'timeout_ms':plan.get('timeout_ms',45000),'space_name':'preview-mouse-'+secrets.token_hex(8),'result_file':str(out),'screenshot':str(out.with_suffix('.png'))}
    template=HERE/'preview_mouse_runner.mjs';script=template.read_text().replace('__PREVIEW_MOUSE_CONFIG__',json.dumps(cfg,ensure_ascii=False),1)
    try:
        done=(run or subprocess.run)([ego,'nodejs','-e',script],capture_output=True,text=True,timeout=60)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('真实鼠标检查超时，保留未通过状态') from exc
    if not out.is_file():raise ValueError('真实鼠标检查未产生原始观察：'+str(done.stderr)[-500:])
    result=json.loads(out.read_text())
    if (done.returncode!=0 or result.get('passed') is not True or result.get('input_transport')!='ego_page_mouse'
            or result.get('space_closed') is not True or result.get('url')!=url or not out.with_suffix('.png').is_file()):
        raise ValueError('真实鼠标开局/玩法检查未通过：'+str(result.get('error') or result.get('cleanup_error') or done.stderr)[-500:])
    result['plan_sha256']=hashlib.sha256(plan_path.read_bytes()).hexdigest()
    result['runner_sha256']=hashlib.sha256(template.read_bytes()).hexdigest()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result

def handoff_check(url, project, plan=None, out=None, directory=None, phone_size=(390,844)):
    project=Path(project) if project else None
    plan=Path(plan) if plan else project/'docs/playtest/mouse-plan.json' if project else None
    if plan is None or not plan.is_file():raise ValueError('不给试玩链接：缺少真实鼠标操作计划；用 --mouse-plan 或 docs/playtest/mouse-plan.json 登记实际开局及玩法结果')
    out=Path(out) if out else project/'docs/checks/preview-mouse'/('mouse-'+secrets.token_hex(12)+'.json') if project else Path(tempfile.mkdtemp(prefix='preview-mouse-'))/'result.json'
    if directory is None:
        return check(url,plan,out)
    # Use the exact retained artifact on a new origin; never consume the user's save/energy.
    from functools import partial
    from serve_preview import Handler, start_check_server, stop_check_server
    server, test_url = start_check_server(partial(Handler,directory=str(Path(directory).resolve()),phone_size=phone_size,touch_bridge=True))
    try:
        result=check(test_url,plan,out)
        result['delivery_url']=url
        result['artifact_directory']=str(Path(directory).resolve())
        Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2))
        return result
    finally:
        stop_check_server(server)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(check(a.url,a.plan,a.out),ensure_ascii=False))
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:p.exit(1,str(e)+'\n')
