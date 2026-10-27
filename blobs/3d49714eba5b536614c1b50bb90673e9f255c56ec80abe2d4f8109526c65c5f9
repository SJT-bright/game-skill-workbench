"""HTTP integration checks for user phone preview versus internal raw QA."""
import importlib.util,tempfile,threading,unittest,subprocess,sys
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preview',HERE/'serve_preview.py');preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)
class PhonePreview(unittest.TestCase):
 def test_raw_root_ad_simulation_matches_explicit_index(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);original=b'<html><head></head><body>game</body></html>';(root/'index.html').write_bytes(original)
   for enabled in (False,True):
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(preview.Handler,directory=folder,phone_size=None,ad_simulator=enabled));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
    try:
     body=urlopen(base+'/').read();explicit=urlopen(base+'/index.html').read();self.assertEqual(body,explicit)
     self.assertEqual(b'/__local_ad_simulator.js' in body,enabled);self.assertEqual((root/'index.html').read_bytes(),original)
    finally:server.shutdown();thread.join();server.server_close()
 def test_ad_simulation_is_response_only_and_disabled_by_default(self):
  from urllib.error import HTTPError
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);original=b'<!doctype html><html><head><title>game</title><script src="game.js"></script></head><body></body></html>'
   (root/'index.html').write_bytes(original);(root/'nested.html').write_bytes(original)
   for enabled in (False,True):
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(preview.Handler,directory=folder,phone_size=(390,844),preview_token='candidate',ad_simulator=enabled));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
    try:
     for route in ('/__preview/candidate/index.html?__phone_game=1','/__preview/candidate/nested.html'):
      response=urlopen(base+route).read()
      if enabled:
       self.assertIn(b'/__local_ad_simulator.js',response);self.assertLess(response.index(b'/__local_ad_simulator.js'),response.index(b'game.js'))
      else:self.assertEqual(response,original)
     if enabled:self.assertIn(b'function create(opts)',urlopen(base+'/__local_ad_simulator.js').read())
     else:
      with self.assertRaises(HTTPError) as error:urlopen(base+'/__local_ad_simulator.js?enable=1')
      self.assertEqual(error.exception.code,404)
     self.assertEqual((root/'index.html').read_bytes(),original);self.assertEqual((root/'nested.html').read_bytes(),original)
    finally:server.shutdown();thread.join();server.server_close()
 def test_setup_requires_explicit_simulation(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'index.html').write_text('<html></html>');setup=root/'setup.js';setup.write_text('window.setup=true;')
   r=subprocess.run([sys.executable,str(HERE/'serve_preview.py'),'--directory',folder,'--ad-simulator-setup',str(setup)],capture_output=True,text=True)
   self.assertEqual(r.returncode,2);self.assertIn('requires --ad-simulator',r.stderr)
 def check_server(self,phone):
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);original=b'<html><canvas id="GameCanvas"></canvas></html>';asset=b'\x00\x01original-asset';(root/'index.html').write_bytes(original);(root/'game.bin').write_bytes(asset)
   server=ThreadingHTTPServer(('127.0.0.1',0),partial(preview.Handler,directory=folder,phone_size=phone));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
   try:
    body=urlopen(base+'/').read()
    if phone:self.assertIn(b'fixed-phone-v1',body);self.assertIn(b'<iframe',body)
    else:self.assertEqual(body,original)
    self.assertEqual(urlopen(base+'/index.html?__phone_game=1').read(),original)
    self.assertEqual(urlopen(base+'/game.bin').read(),asset)
    self.assertEqual((root/'index.html').read_bytes(),original)
   finally:server.shutdown();thread.join();server.server_close()
 def test_versioned_entry_isolates_all_relative_assets_and_never_304(self):
  from urllib.request import Request
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);(root/'index.html').write_text('<iframe src="game.html"></iframe>');(root/'game.html').write_text('<script src="main.js"></script>');(root/'main.js').write_text('window.currentBuild=79;');(root/'assets').mkdir();(root/'assets/index.js').write_text('bundle79');
   server=ThreadingHTTPServer(('127.0.0.1',0),partial(preview.Handler,directory=folder,phone_size=(390,844),preview_token='build79'));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
   try:
    self.assertIn(b'/__preview/build79/index.html',urlopen(base+'/').read())
    for rel,expected in [('index.html',b'<iframe src="game.html"></iframe>'),('main.js',b'window.currentBuild=79;'),('assets/index.js',b'bundle79')]:
     response=urlopen(Request(base+'/__preview/build79/'+rel,headers={'If-Modified-Since':'Wed, 01 Jan 2099 00:00:00 GMT'}));self.assertEqual(response.status,200);self.assertEqual(response.read(),expected);self.assertIn('no-store',response.headers['Cache-Control'])
   finally:server.shutdown();thread.join();server.server_close()
 def test_default_phone_keeps_actual_game_and_assets(self):self.check_server((390,844))
 def test_internal_raw_keeps_top_level_canvas(self):self.check_server(None)
 def test_raw_cannot_be_user_keep(self):
  with tempfile.TemporaryDirectory()as d:
   (Path(d)/'index.html').write_text('<html>game</html>');r=subprocess.run([sys.executable,str(HERE/'serve_preview.py'),'--directory',d,'--raw','--keep'],capture_output=True,text=True);self.assertEqual(r.returncode,2);self.assertIn('internal QA',r.stderr)
if __name__=='__main__':unittest.main()
