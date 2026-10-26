"""Shared local check runner; preserves tool exit codes and records real elapsed time."""
import json,subprocess,sys,time
from pathlib import Path

def run_tool(name,args,logs,here,timeout):
    logs=Path(logs);cmd=[sys.executable,'-B',str(Path(here)/name),*map(str,args)]
    started=time.monotonic()
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
        text=(r.stdout or '')+(('\n[stderr]\n'+r.stderr) if r.stderr.strip() else '')
        code=r.returncode
    except subprocess.TimeoutExpired:
        text,code='timeout after %ss'%timeout,-1
    except OSError as exc:
        text,code='tool execution failed: '+str(exc),-2
    elapsed=round(time.monotonic()-started,6)
    (logs/(Path(name).stem+'.log')).write_text(' '.join(cmd)+'\n\nelapsed_seconds='+str(elapsed)+'\n'+text,encoding='utf-8')
    with (logs/'timings.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps({'tool':name,'elapsed_seconds':elapsed,'exit_code':code},ensure_ascii=False)+'\n')
    return code,text

def read_timings(logs):
    p=Path(logs)/'timings.jsonl'
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()] if p.is_file() else []
