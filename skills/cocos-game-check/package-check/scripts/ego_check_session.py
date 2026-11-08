"""Finish only the owned session recorded by this check batch, through Ego's supported API."""
import json
from pathlib import Path
import subprocess

def finish(browser,file):
    module=Path(__file__).with_name('runtime_regression')/'session.mjs'
    script='const S=await import(%s); console.log(JSON.stringify(await S.finish(%s)));'%(json.dumps(module.as_uri()),json.dumps(str(file)))
    done=subprocess.run([browser,'nodejs','-e',script],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=40)
    if done.returncode:raise ValueError('Ego 检查空间尚未收尾：'+done.stderr[-600:])
    return done.stdout
