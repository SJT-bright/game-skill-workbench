'use strict';
// Exact edits only for direct legacy resource methods; aliases stay a mapping task.
if (process.argv.slice(2).some(x=>x==='--help'||x==='-h')) {
  process.stdout.write('Usage: node resource_package_prepare.cjs < input.json\nRead source files and optional actual bootstrap projections as JSON; no game code is executed.\n');
  process.exit(0);
}
const acorn = require('./vendor/acorn.cjs');
let input = ''; process.stdin.on('data', x => input += x); process.stdin.on('end', () => {
  if (!input.trim()) {
    process.stdout.write(JSON.stringify({status:'not_run',checked:0,reason:'JSON input is required'}));
    process.exitCode=2; return;
  }
  try {
    const payload=JSON.parse(input);
    const out = {sites: [], errors: [], bundle_loads: []};
    function chain(n) { if (n.type === 'Identifier') return n.name;
      if (n.type === 'MemberExpression' && !n.computed) return chain(n.object) + '.' + n.property.name; return ''; }
    for (const [file, code] of Object.entries(payload.files || {})) {
      let ast; try { ast = acorn.parse(code, {ecmaVersion:'latest', sourceType:'module', locations:true}); }
      catch (e) {out.errors.push({source:file, reason:e.message}); continue;}
      function walk(n) {
        if (!n || !n.type) return;
        if (n.type === 'CallExpression') {
          const c = chain(n.callee), m = /^(cc\.resources\.(load|loadDir|preload|preloadDir)|cc\.loader\.(loadRes|loadResDir))$/.exec(c);
          if (m) out.sites.push({source:file, start:n.callee.start, end:n.callee.end,
            method:m[2] || m[3], line:n.loc.start.line, completion: n.arguments.length>=3 || /FunctionExpression|ArrowFunctionExpression|Identifier/.test(n.arguments[1]?.type || '')});
          if (c === 'cc.assetManager.loadBundle') out.bundle_loads.push({source:file,start:n.start,line:n.loc.start.line,name:typeof n.arguments[0]?.value === 'string' ? n.arguments[0].value : null});
        }
        for (const [k,v] of Object.entries(n)) if(k !== 'loc') {
          if(Array.isArray(v)) v.forEach(x => {if(x && x.type) walk(x);}); else if(v && v.type) walk(v);
        }
      } walk(ast);
    }
    if(payload.bootstrap) {
      const parse=s=>acorn.parse(s,{ecmaVersion:'latest',sourceType:'script'});
      const chain=n=>n?.type==='Identifier'?n.name:n?.type==='MemberExpression'&&!n.computed?chain(n.object)+'.'+n.property.name:'';
      const directCall=s=>s?.type==='ExpressionStatement'&&s.expression.type==='CallExpression'?s.expression:null;
      const entry=parse(payload.bootstrap.entry), main=parse(payload.bootstrap.main);
      out.entry_main=entry.body.some(s=>{const c=directCall(s);return c?.callee.name==='require'&&/^\.\/main(?:\.js)?$/.test(c.arguments[0]?.value || '');});
      out.editor_resources_chain=main.body.some(s=>{
        const c=directCall(s);if(!c||!['tt.loadSubpackage','platform.loadSubpackage'].includes(chain(c.callee)))return false;
        const obj=c.arguments[0];if(obj?.type!=='ObjectExpression')return false;
        const prop=k=>obj.properties.find(p=>(p.key.name||p.key.value)===k)?.value;
        if(prop('name')?.value!=='resources')return false;
        const cb=prop('success');if(!['FunctionExpression','ArrowFunctionExpression'].includes(cb?.type)||cb.body.type!=='BlockStatement')return false;
        return cb.body.body.some(s=>{const load=directCall(s);return load&&chain(load.callee)==='cc.assetManager.loadBundle'&&load.arguments[0]?.value==='resources';});
      });
    }

    if(payload.native3) {
      const fs=payload.native3, graph={},settings=new Set(), start=new Set();
      const path=require('path').posix;
      function method(n){return n?.type==='MemberExpression'&&!n.computed?n.property.name:'';}
      for(const [file,code] of Object.entries(fs)) {
        if(!file.endsWith('.js'))continue;
        let ast;try{ast=acorn.parse(code,{ecmaVersion:'latest',sourceType:'module'});}catch(e){graph[file]=[];continue;}
        const deps=[];
        function visit(n,active=true) {
          if(!n||!n.type||!active)return;
          if(n.type==='IfStatement'&&n.test.type==='Literal'&&n.test.value===false){visit(n.alternate);return;}
          if(n.type==='CallExpression') {
            const literal=n.arguments[0]?.value;
            if(typeof literal==='string'&&(n.callee.name==='require'||method(n.callee)==='import'))deps.push(literal);
            if(['init','initialize','loadSettings'].includes(method(n.callee))&&typeof literal==='string'&&/^src\/settings(?:\.[0-9a-fA-F]+)?\.json$/.test(literal))settings.add(file);
            if(method(n.callee)==='start')start.add(file);
          }
          if(n.type==='ImportDeclaration'&&typeof n.source.value==='string')deps.push(n.source.value);
          for(const [k,v] of Object.entries(n)){if(k==='loc')continue;if(Array.isArray(v))v.forEach(x=>visit(x));else if(v&&v.type)visit(v);}
        }visit(ast);
        graph[file]=deps.map(x=>path.normalize(path.join(path.dirname(file),x))).map(x=>fs[x]!==undefined?x:fs[x+'.js']!==undefined?x+'.js':null).filter(Boolean);
      }
      const seen=new Set(),todo=['game.js'];while(todo.length){const f=todo.pop();if(seen.has(f))continue;seen.add(f);todo.push(...(graph[f]||[]));}
      out.native3={supported:seen.has('game.js')&&start.has('game.js')&&[...settings].some(x=>seen.has(x))&&[...seen].some(x=>x.startsWith('cocos-js/')),
        entry:'game.js',closure:[...seen].sort(),settings_callers:[...settings].filter(x=>seen.has(x)).sort()};
    }
    process.stdout.write(JSON.stringify(out));
  } catch(e) {
    process.stdout.write(JSON.stringify({status:'not_run',checked:0,reason:e.message}));
    process.exitCode=2;
  }
});
