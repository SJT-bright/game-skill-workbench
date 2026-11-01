#!/usr/bin/env python3
"""Add the missing entry page to a Cocos Creator 3.x web-mobile export (English pack 10.2.10, Saul 2026-10-31).

Cube Digits (Cocos 3.7.1, 2026-10-31): a command-line web-mobile build wrote the game but no index.html, index.js or
style.css (the platform's finishing step did not run), so the trial link showed nothing. The fix that worked there was
to fill the editor's own web-mobile template (index.ejs, style.css) and add the SystemJS form of index.js.ejs. This
script does the same on any computer: it reads the template from the installed editor, writes only what is missing and
never touches the game files. It writes nothing when the template has anything it does not understand.

  python3 fix_web_entry_3x.py --export <web-mobile folder> --project <Cocos project>   (finds the editor itself)
  python3 fix_web_entry_3x.py --export <web-mobile folder> --template <editor's templates/web-mobile folder>
  options: --title <page title>  --force (rewrite even when index.html exists).  Windows: python instead of python3.
Exit 0 entry page present or written, 1 cannot write it (reason printed), 2 bad input.
"""
import argparse
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# What the 3.6 / 3.7 / 3.8 web-mobile builder puts where index.ejs says <%- include(cocosTemplate, {}) %>.
COCOS_TEMPLATE = (
    '\n<!-- Polyfills bundle. -->\n'
    '<script src="src/polyfills.bundle.js" charset="utf-8"> </script>\n\n'
    '<!-- SystemJS support. -->\n'
    '<script src="src/system.bundle.js" charset="utf-8"> </script>\n\n'
    '<!-- Import map -->\n'
    '<script src="src/import-map.json" type="systemjs-importmap" charset="utf-8"> </script>\n\n'
    '<script>\n'
    "    System.import('./index.js').catch(function(err) { console.error(err); })\n"
    '</script>\n')

# index.js.ejs of 3.6.2 / 3.7.1 / 3.8.8 (identical) in the SystemJS form the builder writes (from Cube Digits 3.7.1).
INDEX_JS = '''System.register(["./application.js"], function (_export, _context) {
  "use strict";

  var Application, canvas, $p, bcr, application;

  function topLevelImport(url) {
    return System["import"](url);
  }

  return {
    setters: [function (_applicationJs) {
      Application = _applicationJs.Application;
    }],
    execute: function () {
      canvas = document.getElementById('GameCanvas');
      $p = canvas.parentElement;
      bcr = $p.getBoundingClientRect();
      canvas.width = bcr.width;
      canvas.height = bcr.height;
      application = new Application();
      topLevelImport('cc').then(function (engine) {
        return application.init(engine);
      }).then(function () {
        return application.start();
      })["catch"](function (err) {
        console.error(err);
      });
    }
  };
});'''

KNOWN_INDEX_JS_EJS = "import { Application } from '<%= applicationJS %>';"


def template_dirs(editor_exe):
    """Candidate templates/web-mobile folders of an installed editor (macOS .app or Windows folder)."""
    exe = Path(editor_exe)
    roots = []
    for p in [exe] + list(exe.parents):
        if p.suffix == '.app':
            roots.append(p / 'Contents' / 'Resources')
            break
    roots.append(exe.parent)
    out = []
    for r in roots:
        for rel in (('resources', '3d', 'engine', 'templates', 'web-mobile'),
                    ('resources', 'resources', '3d', 'engine', 'templates', 'web-mobile'),
                    ('resources', '3d', 'engine', 'templates', 'web-mobile')):
            out.append(r.joinpath(*rel))
    return out


def find_template(project):
    import find_creator
    r = find_creator.report(project)
    if not r['editor']:
        raise ValueError('这台电脑没装这款游戏的 Cocos Creator（%s），找不到模板；先装编辑器，或用 --template 指定' % r['version'])
    if r['major'] != 3:
        raise ValueError('这是 Cocos %s 的工程：2.x 的 web-mobile 导出自带 index.html，不用补' % r['version'])
    for d in template_dirs(r['editor']['exe']):
        if (d / 'index.ejs').is_file():
            return d
    raise ValueError('在 %s 里没找到 templates/web-mobile/index.ejs，用 --template 指定' % r['editor']['exe'])


def project_title(project):
    import json
    try:
        name = json.loads((Path(project) / 'package.json').read_text(encoding='utf-8-sig')).get('name')
        if name:
            return str(name)
    except (OSError, ValueError, AttributeError):
        pass
    return Path(project).resolve().name if project else 'Game'


def render(template_dir, title):
    text = (Path(template_dir) / 'index.ejs').read_text(encoding='utf-8-sig')   # the 3.7.1 template starts with a BOM
    for tag, value in (('<%= projectName %>', title), ('<%= cssUrl %>', 'style.css'),
                       ('<%- include(cocosTemplate, {}) %>', COCOS_TEMPLATE)):
        if tag not in text:
            raise ValueError('模板 index.ejs 里没有 %s，和 3.6～3.8 的不一样，不自动补' % tag)
        text = text.replace(tag, value)
    if '<%' in text:
        raise ValueError('模板 index.ejs 里还有不认识的写法（<%% ... %%>），不自动补')
    js_ejs = Path(template_dir) / 'index.js.ejs'
    if js_ejs.is_file() and KNOWN_INDEX_JS_EJS not in js_ejs.read_text(encoding='utf-8-sig'):
        raise ValueError('模板 index.js.ejs 和 3.6～3.8 的不一样，不自动补 index.js')
    return text


def fix(export, template_dir, title, force=False):
    export = Path(export)
    if (export / 'index.html').is_file() and not force:
        return {'written': [], 'message': '导出里已经有 index.html，不用补'}
    app = export / 'application.js'
    if not app.is_file() or '_export("Application"' not in app.read_text(encoding='utf-8', errors='replace'):
        raise ValueError('%s 不像 Cocos 3.x 的 web-mobile 导出（没有导出 Application 的 application.js）' % export)
    missing = [p for p in ('src/system.bundle.js', 'src/import-map.json') if not (export / p).is_file()]
    if missing:
        raise ValueError('导出里缺 %s，是构建没做完，重新构建' % '、'.join(missing))
    html = render(template_dir, title)
    if not (export / 'src' / 'polyfills.bundle.js').is_file():
        html = html.replace('<!-- Polyfills bundle. -->\n<script src="src/polyfills.bundle.js" charset="utf-8"> </script>\n\n', '')
    css = Path(template_dir) / 'style.css'
    if not css.is_file():
        raise ValueError('模板里没有 style.css：%s' % template_dir)
    written = []
    for name, data in (('index.html', html), ('index.js', INDEX_JS)):
        if force or not (export / name).is_file():
            (export / name).write_text(data, encoding='utf-8', newline='\n')
            written.append(name)
    if force or not (export / 'style.css').is_file():
        shutil.copyfile(css, export / 'style.css')
        written.append('style.css')
    return {'written': written, 'template': str(template_dir),
            'message': '补上了 %s（模板：%s）' % ('、'.join(written) or '没有要补的', template_dir)}


def main(argv=None):
    ap = argparse.ArgumentParser(description='给 Cocos 3.x 的 web-mobile 导出补上缺的入口页（只补缺的，不碰游戏文件）')
    ap.add_argument('--export', required=True, type=Path)
    ap.add_argument('--project', type=Path, help='Cocos 工程：用来找本机编辑器自带的模板和页面标题')
    ap.add_argument('--template', type=Path, help='编辑器的 templates/web-mobile 文件夹')
    ap.add_argument('--title')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args(argv)
    if not a.export.is_dir():
        print('输入有问题：找不到导出目录 %s' % a.export)
        return 2
    if (a.export / 'index.html').is_file() and not a.force:
        print('导出里已经有 index.html，不用补。')
        return 0
    try:
        if a.template:
            template = a.template
        elif a.project:
            template = find_template(a.project)
        else:
            print('输入有问题：要给 --project（自动找模板）或 --template')
            return 2
        r = fix(a.export, template, a.title or project_title(a.project), a.force)
    except (OSError, ValueError) as error:
        print('没补：%s' % error)
        return 1
    print(r['message'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
