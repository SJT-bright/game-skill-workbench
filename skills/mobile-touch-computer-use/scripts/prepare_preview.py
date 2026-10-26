#!/usr/bin/env python3
"""Isolated, byte-bound Web QA copy with passive browser input logging."""
import os
import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def prepare(args):
    source=Path(args.web_root).resolve(strict=True)
    output=Path(args.output).resolve()
    entry=Path(args.entry)
    if not source.is_dir() or entry.is_absolute() or '..' in entry.parts:
        raise ValueError('Web root and relative HTML entry required')
    original=(source/entry).resolve(strict=True)
    if not original.is_relative_to(source) or original.suffix.lower() not in ('.html','.htm'):
        raise ValueError('Entry must be HTML inside Web root')
    if output.exists() or output.is_relative_to(source):
        raise ValueError('Use a new output outside original Web root')
    files=sorted(p for p in source.rglob('*') if p.is_file() and p.name!='.DS_Store' and '__MACOSX' not in p.relative_to(source).parts)
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Symlinked export needs explicit review')
    manifest={str(p.relative_to(source)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}
    html=original.read_text(encoding='utf-8')
    if '<head>' not in html.lower():
        raise ValueError('HTML head absent; inspect entry without changing source')
    output.mkdir(parents=True)
    web=output/'web';shutil.copytree(source,web,ignore=shutil.ignore_patterns('.DS_Store','__MACOSX'))
    observer=Path(__file__).with_name('input_observer.js')
    shutil.copy2(observer,web/'__mobile_cua_observer.js')
    head_at=html.lower().index('<head>')+len('<head>')
    (web/entry).write_text(html[:head_at]+'\n<script src="/__mobile_cua_observer.js"></script>\n'+html[head_at:],encoding='utf-8')
    unchanged=[n for n,d in manifest.items() if n!=str(entry) and digest(web/n)==d['sha256']]
    if len(unchanged)!=len(manifest)-1:
        raise ValueError('Copied export byte mismatch')
    write_json(output/'source-manifest.json',manifest)
    write_json(output/'instrumentation.json',{'source':str(source),'entry':str(entry),'files':len(manifest),'unchanged_files':len(unchanged),'source_manifest_sha256':digest(output/'source-manifest.json'),'original_html_sha256':digest(original),'qa_html_sha256':digest(web/entry),'observer_sha256':digest(observer),'input_mode':'not_yet_observed','physical_device':False,'limitations':['HTML passive observer; other game files unchanged','moves sampled at 40ms minimum','not platform Native touch callbacks','preparation does not establish touch emulation']})
    if args.start:
        with (output/'server.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'serve','--output',str(output),'--port',str(args.port)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=(os.name != "nt"),creationflags=(getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0) if os.name=="nt" else 0),cwd=str(output))
        deadline=time.monotonic()+5
        while not (output/'server.json').exists():
            if child.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError('QA server failed; inspect server.log')
            time.sleep(.05)
        print((output/'server.json').read_text(encoding='utf-8'))
    else:
        print(json.dumps({'output':str(output),'entry':str(entry)},ensure_ascii=False))

def serve(args):
    output=Path(args.output).resolve(strict=True)
    info=json.loads((output/'instrumentation.json').read_text(encoding='utf-8'))
    web=output/'web';lock=threading.Lock()
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):
            super().__init__(*a,directory=str(web),**kw)
        def do_POST(self):
            host=self.headers.get('Host','')
            local_hosts={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}',f'10.0.2.2:{self.server.server_port}'}
            origin=f'http://{host}'
            try:
                length=int(self.headers.get('Content-Length','0'))
                if self.path!='/__mobile_cua_events__' or host not in local_hosts or self.headers.get('Origin')!=origin or not 0<length<=262144:
                    raise ValueError('Invalid local observer request')
                rows=json.loads(self.rfile.read(length))
                if not isinstance(rows,list) or not 1<=len(rows)<=48 or any(not isinstance(x,dict) or not isinstance(x.get('seq'),int) for x in rows):
                    raise ValueError('Invalid event batch')
                with lock,(output/'events.jsonl').open('a',encoding='utf-8') as f:
                    for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
                self.send_response(204);self.end_headers()
            except (ValueError,UnicodeError):
                self.send_error(400,'Invalid event batch')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    write_json(output/'server.json',{'pid':os.getpid(),'port':server.server_port,'host':'127.0.0.1','url':f'http://127.0.0.1:{server.server_port}/{info["entry"]}','output':str(output)})
    server.serve_forever()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--web-root',required=True);prep.add_argument('--entry',default='index.html');prep.add_argument('--output',required=True);prep.add_argument('--start',action='store_true');prep.add_argument('--port',type=int,default=0)
    srv=sub.add_parser('serve');srv.add_argument('--output',required=True);srv.add_argument('--port',type=int,default=0)
    args=p.parse_args()
    try:(prepare if args.mode=='prepare' else serve)(args)
    except (ValueError,RuntimeError,OSError) as e:p.exit(2,str(e)+'\n')

if __name__=='__main__':main()
