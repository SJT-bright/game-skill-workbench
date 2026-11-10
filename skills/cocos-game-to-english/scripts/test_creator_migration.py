from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import creator_migration as M


def compiled_bundle(mapping):
    return '''
window.__require = function e(table, cache, entries) {
  function load(id) {
    if (!cache[id]) {
      if (!table[id]) {
        var basename = id.split("/");
        basename = basename[basename.length - 1];
        if (!table[basename]) throw new Error(id);
        id = basename;
      }
      var instance = cache[id] = {exports:{}};
      table[id][0](function(request) { return load(table[id][1][request] || request); }, instance, instance.exports);
    }
    return cache[id].exports;
  }
  return load;
}({
  Shared: [function(require,module,exports){exports.default={};},{}],
  Writer: [function(require,module,exports){
    var shared=require("../Shared");
    exports.mount=function(node){shared.default.root=node;};
  },{"../Shared": %s}],
  Reader: [function(require,module,exports){
    var shared=require("./Shared");
    exports.mount=function(node){shared.default.root.addChild(node);};
  },{"./Shared":"Shared"}],
  Isolated: [function(require,module,exports){
    var shared=require("../Shared");
    exports.text=function(){return shared.default.caption;};
  },{"../Shared":void 0}]
},{},[]);
''' % mapping


class CreatorMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='迁移 回归 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.original = self.root / '原始工程'
        self.project = self.root / '工作 副本'
        self.original.mkdir()
        (self.project / 'assets').mkdir(parents=True)
        self.write_project(self.original, '2.1.3')
        self.write_project(self.project, M.TARGET)

    def write_project(self, project, version):
        M.write(project / 'project.json', {'id': 'same-game', 'version': version})

    def test_affected_graph_and_harmless_alias(self):
        web = self.project / 'build/web-mobile'
        bundle = web / 'assets/main/index.js'
        bundle.parent.mkdir(parents=True)
        bundle.write_text(compiled_bundle('void 0'))
        result = M.audit(web)
        self.assertEqual(result['status'], 'blocked')
        finding, = result['tables'][0]['findings']
        self.assertEqual((finding['module'], finding['field']), ('Shared', 'default.root'))
        self.assertEqual(finding['pairs'][0]['writer']['caller'], 'Writer')
        self.assertEqual(finding['pairs'][0]['reader']['caller'], 'Reader')
        bundle.write_text(compiled_bundle('"Shared"'))
        result = M.audit(web)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['tables'][0]['relative_fallbacks'], 1)

    def test_route_and_current_stage_guard(self):
        timer = Path(__file__).with_name('stage_timer.py')
        args = [sys.executable, '-B', str(timer), '--project', str(self.project), 'stage', '2']
        with patch.object(M, 'audit', side_effect=AssertionError('ordinary project scanned')):
            M.require_ready(self.project)
        (self.project / M.REPORT.parent).mkdir(parents=True)
        (self.project / M.REPORT.parent / 'engine.txt').write_text('原工程 2.1.3，升到 2.4.15', encoding='utf-8')
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('prepare', result.stderr)
        self.assertEqual(M.prepare(self.project, self.original)['status'], 'pending_build')
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('smoke', result.stderr)
        returned = args[:-2] + ['start', '--run-id', 'return-1', '--route', 'returned']
        subprocess.run(returned, capture_output=True, text=True, check=True)
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)

    def test_relocated_proof_and_changed_source_or_export(self):
        M.prepare(self.project, self.original)
        web = self.project / 'build/web-mobile'
        web.mkdir(parents=True)
        (web / 'index.html').write_text('evidence-bound fixture')
        record = M.load(self.project)
        web_hash = M.signature(web, [web / 'index.html'])
        record['status'] = 'passed'
        record['candidate'] = {'web': 'build/web-mobile', 'source_sha256': M.source_signature(self.project),
                               'tool_sha256': M.tool_signature(), 'web_sha256': web_hash, 'audit': {'status': 'passed'}}
        record['smoke'] = {'home': True, 'entered': True, 'browser_route': 'ego_taskspace', 'space_finished': True,
                           'engine': M.TARGET, 'web_sha256': web_hash}
        M.write(self.project / M.REPORT, record)
        other = self.root / '新电脑' / '项目 B'
        shutil.copytree(self.project, other)
        self.project.rename(self.root / '旧目录 已移开')
        M.require_ready(other)
        with patch.object(M.find_creator, 'busy', side_effect=AssertionError('repeat build')):
            self.assertEqual(M.build(other), record)
        (other / 'tsconfig.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, '迁移源码'):
            M.require_ready(other)
        (other / 'tsconfig.json').unlink()
        (other / 'build/web-mobile/index.html').write_text('wrong version')
        with self.assertRaisesRegex(ValueError, '已核对的文件不同'):
            M.require_ready(other)

    def test_build_command_uses_physical_working_copy(self):
        alias = self.root / 'alias'
        try:
            alias.symlink_to(self.project, target_is_directory=True)
        except OSError:
            self.skipTest('symbolic link creation unavailable on this host')
        command = M.find_creator.build_argv({'exe': 'Creator'}, alias, 2, 'web-mobile')
        self.assertEqual(command[command.index('--path') + 1], str(self.project))


if __name__ == '__main__':
    unittest.main()
