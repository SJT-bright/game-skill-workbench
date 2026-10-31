'use strict';
// Finite Cocos resource domains only. Unknown expressions stay unresolved.
const acorn = require('./vendor/acorn.cjs');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const payload = JSON.parse(input), sites = [], escapes = [], settingsJs = {}, settingsWrites = [];
    const U = null, limit = 10000;
    const symbolic = name => ({symbol:name});
    const union = values => {
      if (values.some(v => v === U)) return U;
      if (values.length && values.every(v=>v && v.table)) {
        const table={}, keys=[...new Set(values.flatMap(v=>Object.keys(v.table)))];
        for (const key of keys) table[key]=union(values.map(v=>v.table[key]??U));
        return {table};
      }
      const out = [...new Set(values.flat())];
      return out.length <= limit ? out : U;
    };
    for (const [file, source] of Object.entries(payload.files)) {
      let ast;
      const options = {ecmaVersion:'latest', locations:true, allowReturnOutsideFunction:true};
      try { ast = acorn.parse(source, {...options, sourceType:'script'}); }
      catch (_) { ast = acorn.parse(source, {...options, sourceType:'module'}); }
      const env = new Map(), parents = new WeakMap(), nodes = [];
      function collect(n, p) {
        if (!n || !n.type) return;
        nodes.push(n); parents.set(n,p);
        for (const [k,v] of Object.entries(n)) {
          if (k === 'loc') continue;
          if (Array.isArray(v)) v.forEach(x => collect(x,n));
          else if (v && v.type) collect(v,n);
        }
      }
      collect(ast,null);
      // Binding by AST scope avoids merging two minified functions' locals.
      const scopeOf = n => {
        for (let p=n;p;p=parents.get(p)) if (/Function/.test(p.type) || p.type==='Program') return p;
        return ast;
      };
      const scopeId = new Map(); let serial=0;
      for (const n of nodes) if (/Function/.test(n.type) || n.type==='Program') scopeId.set(n,serial++);
      const bindingKey = (name,n) => scopeId.get(scopeOf(n))+':'+name;
      const declared = new Set();
      const declarationCounts=new Map();
      for (const n of nodes) {
        if (n.type==='VariableDeclarator' && n.id.type==='Identifier') declared.add(bindingKey(n.id.name,n));
        if (n.type==='VariableDeclarator' && n.id.type==='ObjectPattern') for (const p of n.id.properties) if (p.value?.type==='Identifier') declared.add(bindingKey(p.value.name,n));
        if (/Function/.test(n.type)) for (const p of n.params) if (p.type==='Identifier') declared.add(scopeId.get(n)+':'+p.name);
      }
      for (const n of nodes) if (n.type==='VariableDeclarator' && n.id.type==='Identifier') {
        const key=bindingKey(n.id.name,n);declarationCounts.set(key,(declarationCounts.get(key)||0)+1);
      }
      function resolvedKey(name,n) {
        let s=scopeOf(n);
        for (;;) {
          const key=scopeId.get(s)+':'+name;
          if (declared.has(key)||s===ast) return key;
          s=scopeOf(parents.get(s));
        }
      }
      function lookup(name,n) {
        for (let s=scopeOf(n);s;) {
          const key=scopeId.get(s)+':'+name;
          if (declared.has(key)) return env.has(key)?env.get(key):U;
          s=scopeOf(parents.get(s));
          if (s===ast && !parents.get(s)) {
            const k=scopeId.get(s)+':'+name;
            if (declared.has(k)) return env.has(k)?env.get(k):U;
            break;
          }
        }
        return name==='cc' ? symbolic('cc') : ['window','globalThis','GameGlobal'].includes(name) ? symbolic('global') : U;
      }
      function prop(n) {
        if (!n.computed) return n.property.name;
        const v=value(n.property);
        return Array.isArray(v) && v.length===1 ? v[0] : U;
      }
      function value(n,depth=0) {
        if (!n || depth>35) return U;
        const v=x=>value(x,depth+1);
        if (n.type==='Literal') return typeof n.value==='string'||typeof n.value==='number' ? [n.value] : U;
        if (n.type==='Identifier') return lookup(n.name,n);
        if (n.type==='ArrayExpression') {
          const items=n.elements.map(v); return items.some(x=>x===U)?U:{table:items};
        }
        if (n.type==='ObjectExpression') {
          const table={};
          for (const p of n.properties) {
            if (p.type!=='Property' || p.computed) return U;
            const key=p.key.name??p.key.value; table[key]=v(p.value);
          }
          return {table};
        }
        if (n.type==='ConditionalExpression') return union([v(n.consequent),v(n.alternate)]);
        if (n.type==='BinaryExpression' && n.operator==='+') {
          const a=v(n.left),b=v(n.right);
          if (!Array.isArray(a)||!Array.isArray(b)||a.length*b.length>limit) return U;
          return [...new Set(a.flatMap(x=>b.map(y=>x+y)))];
        }
        if (n.type==='TemplateLiteral') {
          let out=[n.quasis[0].value.cooked];
          for (let i=0;i<n.expressions.length;i++) {
            const item=v(n.expressions[i]);
            if (!Array.isArray(item)||out.length*item.length>limit) return U;
            out=out.flatMap(a=>item.map(b=>a+b+n.quasis[i+1].value.cooked));
          }
          return out;
        }
        if (n.type==='MemberExpression') {
          const obj=v(n.object), key=prop(n);
          if (obj && obj.symbol==='global' && key==='cc') return symbolic('cc');
          if (obj && obj.symbol) return symbolic(obj.symbol+'.'+(key??'?'));
          if (obj && obj.bundle) return {method:key,bundle:obj.bundle};
          if (obj && obj.table) {
            const keys=n.computed?v(n.property):[n.property.name];
            if (Array.isArray(keys) && keys.length===1) return obj.table[keys[0]]??U;
            const vals=Array.isArray(keys)?keys.map(k=>obj.table[k]??U):Object.values(obj.table);
            return union(vals);
          }
          return U;
        }
        if (n.type==='CallExpression' && n.callee.type==='MemberExpression') {
          if (n.callee.object.type==='Identifier' && n.callee.object.name==='Object' && ['keys','values'].includes(prop(n.callee))) {
            const obj=v(n.arguments[0]);
            if (obj?.table) return {table:prop(n.callee)==='keys'?Object.keys(obj.table).map(k=>[k]):Object.values(obj.table)};
          }
          const callee=v(n.callee);
          if (callee && callee.symbol==='cc.assetManager.getBundle') {
            const name=v(n.arguments[0]);return Array.isArray(name)?{bundle:name}:U;
          }
          // Imported finite JSON domains use package-local require only.
        }
        if (n.type==='CallExpression' && n.callee.type==='Identifier' && n.callee.name==='require' && n.arguments.length===1) {
          const path=v(n.arguments[0]);
          if (Array.isArray(path)&&path.length===1&&payload.json_domains?.[file]?.[path[0]]) return payload.json_domains[file][path[0]];
        }
        return U;
      }
      // Cocos 3 imports are assigned by the cc System.register setter. Bind
      // their actual lexical variables rather than guessing minified names.
      const systemSeeds=new Map(), setterAssignments=new WeakSet();
      function children(root,visit){if(!root||!root.type)return;visit(root);for(const [k,v]of Object.entries(root)){if(k==='loc')continue;if(Array.isArray(v))v.forEach(x=>children(x,visit));else if(v?.type)children(v,visit)}}
      function ccImport(expr,param){
        if(expr?.type==='Identifier'&&expr.name===param)return symbolic('cc');
        if(expr?.type==='MemberExpression') {const base=ccImport(expr.object,param),key=prop(expr);if(base?.symbol&&typeof key==='string')return symbolic(base.symbol+'.'+key)}
        return U;
      }
      for(const n of nodes)if(n.type==='CallExpression'&&n.callee.type==='MemberExpression'&&n.callee.object.name==='System'&&prop(n.callee)==='register'){
        const args=n.arguments,offset=args[0]?.type==='Literal'?1:0,deps=args[offset],factory=args[offset+1];
        if(deps?.type!=='ArrayExpression'||!/Function/.test(factory?.type))continue;
        const index=deps.elements.findIndex(x=>x?.value==='cc');if(index<0)continue;
        children(factory,ret=>{if(ret.type!=='ReturnStatement'||scopeOf(ret)!==factory||ret.argument?.type!=='ObjectExpression')return;
          const setters=ret.argument.properties.find(p=>p.key?.name==='setters'||p.key?.value==='setters')?.value;
          const setter=setters?.elements?.[index],param=setter?.params?.[0];if(!/Function/.test(setter?.type)||param?.type!=='Identifier')return;
          systemSeeds.set(scopeId.get(setter)+':'+param.name,symbolic('cc'));
          children(setter,a=>{if(a.type==='AssignmentExpression'&&a.operator==='='&&a.left.type==='Identifier'){const value=ccImport(a.right,param.name);if(value){systemSeeds.set(resolvedKey(a.left.name,a),value);setterAssignments.add(a)}}});
        });
      }
      // A method is non-resource only when its own concrete body is known.
      // Its body is still inventoried, so a wrapper cannot hide a Cocos call.
      const variableDefinitions=new Map();
      for(const n of nodes)if(n.type==='VariableDeclarator'&&n.id.type==='Identifier'){const key=bindingKey(n.id.name,n);if(!variableDefinitions.has(key))variableDefinitions.set(key,[]);variableDefinitions.get(key).push(n)}
      const ownedMethodProofs=new WeakMap();
      // v7.8 B3: a function constructor (platform kit SaveStore). `function A(){}` declared exactly once in its
      // scope, with no var/let/const/param/class of the same name there, is the owner of A.prototype, of new A()
      // and of `this` inside A and inside A.prototype.x = function(){...}. The bare name A is not an owner.
      const functionDeclarations=new Set(), declaredFunctions=new Map(), declaredClasses=new Map(), constructorCache=new WeakMap();
      for(const n of nodes)if((n.type==='FunctionDeclaration'||n.type==='ClassDeclaration')&&n.id?.type==='Identifier'){
        const key=scopeId.get(scopeOf(parents.get(n)))+':'+n.id.name,index=n.type==='ClassDeclaration'?declaredClasses:declaredFunctions;
        if(n.type==='FunctionDeclaration')functionDeclarations.add(n);
        if(!index.has(key))index.set(key,[]);index.get(key).push(n);
      }
      // Same lookup as before (a class declared in the expression's own scope), by index instead of a node scan.
      const sameScopeClasses=(name,expr)=>declaredClasses.get(scopeId.get(scopeOf(expr))+':'+name)||[];
      function constructorDeclaration(id){
        if(id?.type!=='Identifier')return null;
        if(constructorCache.has(id))return constructorCache.get(id);
        let found=null;
        for(let s=scopeOf(id);s;s=s===ast?null:scopeOf(parents.get(s))){
          const key=scopeId.get(s)+':'+id.name,fns=declaredFunctions.get(key)||[],other=declared.has(key)||declaredClasses.has(key);
          if(fns.length||other){found=fns.length===1&&!other?fns[0]:null;break}
        }
        constructorCache.set(id,found);return found;
      }
      function definition(expr,seen=new Set()){
        if(!expr||seen.has(expr))return null;seen.add(expr);
        if(expr.type==='Identifier'){
          const key=resolvedKey(expr.name,expr),defs=variableDefinitions.get(key)||[];
          return defs.length===1?definition(defs[0].init,seen):defs.length===0?expr:null;
        }
        return expr;
      }
      function objectOrigin(expr,seen=new Set()){
        expr=definition(expr,seen);if(!expr)return null;
        if(expr.type==='ObjectExpression'||expr.type==='ClassBody')return expr;
        if(expr.type==='Identifier'){const classes=sameScopeClasses(expr.name,expr);return classes.length===1?classes[0].body:null}
        if(expr.type==='NewExpression'&&expr.callee.type==='Identifier'){
          const classes=sameScopeClasses(expr.callee.name,expr);
          return classes.length===1?classes[0].body:classes.length===0?constructorDeclaration(expr.callee):null;
        }
        if(expr.type==='ThisExpression'){
          let f=parents.get(expr);while(f&&(!/Function/.test(f.type)||f.type==='ArrowFunctionExpression'))f=parents.get(f);
          const owner=parents.get(f);if(owner?.type==='Property'&&owner.value===f)return parents.get(owner);
          if(owner?.type==='MethodDefinition'&&owner.value===f)return parents.get(owner);
          if(owner?.type==='AssignmentExpression'&&owner.operator==='='&&owner.right===f&&owner.left.type==='MemberExpression'){
            const proto=owner.left.object;
            if(proto.type==='MemberExpression'&&!proto.computed&&prop(proto)==='prototype'){const c=constructorDeclaration(proto.object);if(c)return c}
          }
          if(f?.type==='FunctionDeclaration'&&functionDeclarations.has(f)&&constructorDeclaration(f.id)===f)return f;
        }
        if(expr.type==='MemberExpression'){
          if(!expr.computed&&prop(expr)==='prototype'&&expr.object.type==='Identifier'){const c=constructorDeclaration(expr.object);if(c)return c}
          const owner=objectOrigin(expr.object,seen),name=prop(expr);if(owner?.type==='ClassBody'&&name==='prototype')return owner;if(owner?.type==='ObjectExpression'&&typeof name==='string'){
            const properties=owner.properties.filter(p=>p.type==='Property'&&!p.computed&&(p.key.name??p.key.value)===name);
            return properties.length===1?objectOrigin(properties[0].value,seen):null;
          }
        }
        return null;
      }
      // The one write of A.prototype.<name>: `A.prototype.<name> = function(){...}` exactly once. Any other write
      // of that name through A.prototype, an alias of it, an instance or `this` makes the method unproved.
      const memberWrites=nodes.filter(n=>n.type==='AssignmentExpression'&&n.left.type==='MemberExpression');
      const prototypeMethods=new WeakMap();
      function prototypeMethod(owner,name){
        if(!prototypeMethods.has(owner))prototypeMethods.set(owner,new Map());
        const known=prototypeMethods.get(owner);if(known.has(name))return known.get(name);
        known.set(name,null);
        const writes=memberWrites.filter(n=>prop(n.left)===name&&objectOrigin(n.left.object)===owner);
        const w=writes.length===1?writes[0]:null,proto=w?.left.object;
        const fn=w&&w.operator==='='&&w.right.type==='FunctionExpression'&&proto.type==='MemberExpression'&&!proto.computed&&prop(proto)==='prototype'&&constructorDeclaration(proto.object)===owner?w.right:null;
        known.set(name,fn);return fn;
      }
      function ownFunction(owner,name){
        if(owner?.type==='FunctionDeclaration')return prototypeMethod(owner,name);
        const properties=owner?.type==='ObjectExpression'?owner.properties:owner?.type==='ClassBody'?owner.body:[];
        const matches=properties.filter(p=>['Property','MethodDefinition'].includes(p.type)&&!p.computed&&(p.key.name??p.key.value)===name&&/Function/.test(p.value?.type));
        return matches.length===1?matches[0].value:null;
      }
      function provedLocalMethod(member){
        const name=prop(member),owner=objectOrigin(member.object);if(typeof name!=='string'||!ownFunction(owner,name))return false;
        if(!ownedMethodProofs.has(owner))ownedMethodProofs.set(owner,new Map());
        const proofs=ownedMethodProofs.get(owner);if(proofs.has(name))return proofs.get(name);
        const reject=()=>{proofs.set(name,false);return false};
        const constructor=owner.type==='FunctionDeclaration',definingWrite=constructor?parents.get(ownFunction(owner,name)):null;
        for(const n of nodes){
          if(n===definingWrite)continue;
          const target=n.type==='AssignmentExpression'?n.left:n.type==='UpdateExpression'?n.argument:(n.type==='UnaryExpression'&&n.operator==='delete')?n.argument:null;
          if(constructor&&target?.type==='Identifier'&&constructorDeclaration(target)===owner)return reject();
          if(constructor&&target?.type==='MemberExpression'&&constructorDeclaration(target.object)===owner&&(prop(target)===null||prop(target)==='prototype'))return reject();
          if(constructor&&n.type==='CallExpression'&&n.arguments.some(a=>a.type==='Identifier'&&constructorDeclaration(a)===owner))return reject();
          if(target?.type==='Identifier'&&objectOrigin(target)===owner)return reject();
          if(target?.type==='MemberExpression'&&objectOrigin(target.object)===owner&&(prop(target)===null||prop(target)===name||prop(target)==='prototype'))return reject();
          if(n.type==='CallExpression'&&n.arguments.some(a=>objectOrigin(a)===owner)){
            if(!(n.callee.type==='MemberExpression'&&n.callee.object.name==='Object'&&['keys','values'].includes(prop(n.callee))))return reject();
          }
        }
        proofs.set(name,true);return true;
      }
      function provedAdMethod(member){
        if(prop(member)!=='load')return false;
        if(member.object.type==='Identifier'&&dirty.has(resolvedKey(member.object.name,member.object)))return false;
        const origin=definition(member.object);if(origin?.type!=='CallExpression'||origin.callee.type!=='MemberExpression'||prop(origin.callee)!=='createRewardedVideoAd')return false;
        const sdk=origin.callee.object;
        return sdk.type==='Identifier'&&['tt','wx','TTMinis'].includes(sdk.name)&&!declared.has(resolvedKey(sdk.name,sdk))&&!dirty.has(resolvedKey(sdk.name,sdk));
      }
      // Conservative finite binding propagation. Mutation invalidates a domain.
      const dirty=new Set();
      const loaderAliases=new Set();
      for (const [key,count] of declarationCounts) if (count>1) dirty.add(key);
      for (const n of nodes) if ((n.type==='AssignmentExpression'||n.type==='UpdateExpression')&&!setterAssignments.has(n)) {
        let target=n.left??n.argument;
        while (target?.type==='MemberExpression') target=target.object;
        if (target?.type==='Identifier') dirty.add(resolvedKey(target.name,n));
      }
      for (const n of nodes) if (n.type==='CallExpression') {
        const method=n.callee.type==='MemberExpression'?prop(n.callee):null;
        const safe= ['load','loadDir','loadRes','loadResDir','loadResArray','keys','values'].includes(method) || n.callee.name==='require';
        if (!safe) for (const arg of n.arguments) if (arg.type==='Identifier') dirty.add(resolvedKey(arg.name,arg));
        if (['push','pop','shift','unshift','splice','sort','reverse','set','delete','clear'].includes(method)) {
          let receiver=n.callee.object;while(receiver?.type==='MemberExpression')receiver=receiver.object;
          if(receiver?.type==='Identifier')dirty.add(resolvedKey(receiver.name,n));
        }
      }
      // A write through an alias also invalidates the original finite table.
      for(let pass=0;pass<8;pass++)for(const n of nodes)if(n.type==='VariableDeclarator'&&n.id.type==='Identifier'&&dirty.has(bindingKey(n.id.name,n))) {
        let original=n.init;while(original?.type==='MemberExpression')original=original.object;
        if(original?.type==='Identifier')dirty.add(resolvedKey(original.name,n));
      }
      for(const [key,value]of systemSeeds)if(!dirty.has(key))env.set(key,value);
      for (let pass=0;pass<8;pass++) for (const n of nodes) {
        if (n.type==='VariableDeclarator' && n.id.type==='Identifier') {
          const key=bindingKey(n.id.name,n);
          if(systemSeeds.has(key))env.set(key,dirty.has(key)?U:systemSeeds.get(key));
          else if (n.init) env.set(key,dirty.has(key)?U:value(n.init));
        }
        if (n.type==='VariableDeclarator' && n.id.type==='ObjectPattern') {
          const init=value(n.init);
          for (const p of n.id.properties) if (p.value?.type==='Identifier') {
            const key=bindingKey(p.value.name,n), name=p.key.name??p.key.value;
            if (['load','loadDir','loadRes','loadResArray','loadResDir'].includes(name) && (['cc.resources','cc.loader'].includes(init?.symbol)||init?.bundle)) loaderAliases.add(key);
            env.set(key,dirty.has(key)?U:init?.symbol?symbolic(init.symbol+'.'+name):init?.bundle?{method:name,bundle:init.bundle}:U);
          }
        }
        if ((n.type==='ForOfStatement'||n.type==='ForInStatement') && n.left.type==='VariableDeclaration') {
          const id=n.left.declarations[0]?.id, domain=value(n.right);
          if (id?.type==='Identifier' && domain?.table) {
            const key=bindingKey(id.name,n);env.set(key,dirty.has(key)?U:n.type==='ForInStatement'?Object.keys(domain.table):union(Object.values(domain.table)));
          }
        }
        if (n.type==='CallExpression') {
          const c=value(n.callee);
          if (c?.symbol==='cc.assetManager.loadBundle') {
            const names=value(n.arguments[0]);
            for (const cb of n.arguments.filter(x=>/Function/.test(x.type))) {
              const p=cb.params[1];
              if (p?.type==='Identifier') {const key=scopeId.get(cb)+':'+p.name;env.set(key,dirty.has(key)?U:Array.isArray(names)?{bundle:names}:U);}
            }
          }
          if (n.callee.type==='MemberExpression' && ['forEach','map'].includes(prop(n.callee))) {
            const domain=value(n.callee.object), cb=n.arguments[0];
            if (domain?.table && /Function/.test(cb?.type)) {
              const param=cb.params[0];
              if (param?.type==='Identifier') {const key=scopeId.get(cb)+':'+param.name;env.set(key,dirty.has(key)?U:union(Object.values(domain.table)));}
            }
          }
        }
      }
      function classify(callee) {
        const c=value(callee), name=callee.type==='MemberExpression'?prop(callee):null;
        if (callee.type==='Identifier' && loaderAliases.has(resolvedKey(callee.name,callee)) && !c) return {bundles:null,kind:'unknown_alias',unknown_receiver:true};
        if (['cc.resources.load','cc.loader.loadRes','cc.loader.loadResArray'].includes(c?.symbol)) return {bundles:['resources'],kind:'load'};
        if (c?.symbol==='cc.resources.loadDir'||c?.symbol==='cc.loader.loadResDir') return {bundles:['resources'],kind:'loadDir'};
        if (c?.bundle && ['load','loadDir'].includes(c.method)) return {bundles:c.bundle,kind:c.method};
        if (c?.symbol && /^cc\.(resources|loader|assetManager)\.(load|preload)/.test(c.symbol) && c.symbol!=='cc.assetManager.loadBundle') return {bundles:null,kind:'unsupported',unknown_receiver:true};
        if(callee.type==='MemberExpression'&&['load','loadDir','loadRes','loadResArray','loadResDir','preload','preloadDir','loadAny','loadRemote'].includes(name)&&(provedLocalMethod(callee)||provedAdMethod(callee)))return null;
        if(callee.type==='MemberExpression'&&prop(callee)===null&&value(callee.object)?.symbol?.match(/^cc\.(resources|loader|assetManager)$/))return {bundles:null,kind:'dynamic_method',unknown_receiver:true};
        if (['load','loadDir','loadRes','loadResArray','loadResDir','preload','preloadDir','loadAny','loadRemote'].includes(name)) return {bundles:null,kind:name,unknown_receiver:true};
        if (c?.bundle && c.method===null) return {bundles:c.bundle,kind:'unknown',unknown_receiver:true};
        return null;
      }
      for (const n of nodes) {
        if ((n.type==='CallExpression' && (n.callee.name==='eval'||(n.callee.name==='require'&&value(n.arguments[0])===U))) ||
            (n.type==='NewExpression'&&n.callee.name==='Function')) escapes.push({id:file+':'+n.start,source:file,line:n.loc.start.line,expression:'unsupported dynamic code/module generation'});
        if(n.type==='Identifier' && classify(n)) {
          const p=parents.get(n);
          const declaration=(p?.type==='VariableDeclarator'&&(p.id===n||p.init===n)) || (p?.type==='Property'&&parents.get(p)?.type==='ObjectPattern');
          if(!declaration && !(p?.type==='CallExpression'&&p.callee===n))escapes.push({id:file+':'+n.start,source:file,line:n.loc.start.line,expression:'resource loader alias escaped: '+n.name});
        }
        if (n.type==='CallExpression') {
          const c=classify(n.callee);
          if (!c) continue;
          let paths=value(n.arguments[0]);
          if (paths?.table) paths=union(Object.values(paths.table));
          const type=value(n.arguments[1]);
          sites.push({id:file+':'+n.start,source:file,line:n.loc.start.line,...c,
            paths:Array.isArray(paths)?paths.filter(x=>typeof x==='string'):null,
            type:type?.symbol?.startsWith('cc.')?type.symbol:null,
            expression:source.slice(n.start,n.end).slice(0,300)});
        } else if (n.type==='MemberExpression') {
          const c=classify(n),p=parents.get(n);
          if (c && !(p?.type==='CallExpression' && p.callee===n)) {
            // Direct method aliases are allowed if every use is itself a call.
            if (p?.type==='VariableDeclarator' && p.id.type==='Identifier') {
              const key=bindingKey(p.id.name,p);
              const uses=nodes.filter(x=>x.type==='Identifier'&&x.name===p.id.name&&lookup(x.name,x)===env.get(key)&&x!==p.id);
              if (uses.length && uses.every(x=>parents.get(x)?.type==='CallExpression'&&parents.get(x).callee===x)) continue;
            }
            escapes.push({id:file+':'+n.start,source:file,line:n.loc.start.line,expression:source.slice(n.start,n.end)});
          }
        }
      }
      // v7.7 W-G2: facts for the kit main.js jsList expansion (the auditor decides, by KIT_MANIFEST hash).
      // The literal jsList of the Cocos 2.4 settings script, and every write that could change it: an assignment,
      // update or delete whose target chain names jsList or _CCSettings, an array mutator on a jsList chain, or a
      // call that passes such a chain. Nothing here resolves a site; a non-literal jsList is reported as null.
      const isSettings=/^src\/settings(\.[0-9a-fA-F]+)?\.js$/.test(file);
      const chainOf=t=>{const out=[];for(;t?.type==='MemberExpression';t=t.object)out.push(prop(t));if(t?.type==='Identifier')out.push(t.name);return out};
      const names=c=>c.includes('jsList')||c.includes('_CCSettings');
      const writeRow=n=>({id:file+':'+n.start,source:file,line:n.loc.start.line,expression:source.slice(n.start,n.end).slice(0,200)});
      const declarations=[];
      // Aliases: s = window._CCSettings (settings object) and k = s.jsList (the list itself), followed transitively.
      const aliases=new Set(), listAliases=new Set();
      for(let pass=0;pass<4;pass++)for(const n of nodes)if(n.type==='VariableDeclarator'&&n.id.type==='Identifier'&&(n.init?.type==='MemberExpression'||n.init?.type==='Identifier')){
        const c=chainOf(n.init),root=c[c.length-1];
        if(c[0]==='jsList'||(c.length===1&&listAliases.has(root)))listAliases.add(n.id.name);
        else if(c[0]==='_CCSettings'||(c.length===1&&aliases.has(root)))aliases.add(n.id.name);
      }
      const named=c=>c.length>0&&(c[0]==='jsList'||c[0]==='_CCSettings'||(c.length===1&&(aliases.has(c[0])||listAliases.has(c[0]))));
      const written=c=>c.includes('jsList')||c[0]==='_CCSettings'||(c.length>1&&listAliases.has(c[c.length-1]))||(c.length>1&&(c.includes('_CCSettings')||aliases.has(c[c.length-1]))&&c.includes(null));
      const listChain=c=>c.includes('jsList')||(c.length===1&&listAliases.has(c[0]));
      for(const n of nodes){
        const target=n.type==='AssignmentExpression'?n.left:n.type==='UpdateExpression'?n.argument:(n.type==='UnaryExpression'&&n.operator==='delete')?n.argument:null;
        if(target){
          const c=chainOf(target);
          if(isSettings&&n.type==='AssignmentExpression'&&n.operator==='='&&target.type==='MemberExpression'&&prop(target)==='_CCSettings'&&c.length===2&&c[1]==='window'&&parents.get(n)?.type==='ExpressionStatement'&&parents.get(parents.get(n))===ast)declarations.push(n);
          else if(written(c))settingsWrites.push(writeRow(n));
          continue;
        }
        if(n.type==='CallExpression'){
          const method=n.callee.type==='MemberExpression'?prop(n.callee):null;
          if(['push','pop','shift','unshift','splice','sort','reverse','fill','copyWithin'].includes(method)&&listChain(chainOf(n.callee.object)))settingsWrites.push(writeRow(n));
          else if(n.arguments.some(a=>(a.type==='MemberExpression'||a.type==='Identifier')&&named(chainOf(a))))settingsWrites.push(writeRow(n));
        }
      }
      if(isSettings){
        let jsList=null,why='';
        if(declarations.length!==1)why='expected exactly one top-level window._CCSettings = {...}, found '+declarations.length;
        else if(declarations[0].right.type!=='ObjectExpression')why='window._CCSettings is not an object literal';
        else{
          const props=declarations[0].right.properties;
          const keyOf=p=>p.type==='Property'&&!p.computed?(p.key.name??p.key.value):null;
          const hits=props.filter(p=>keyOf(p)==='jsList');
          if(props.some(p=>p.type!=='Property'||p.computed))why='_CCSettings has a spread or computed key';
          else if(hits.length>1)why='jsList defined twice';
          else if(!hits.length)jsList=[];
          else if(hits[0].value.type!=='ArrayExpression'||hits[0].value.elements.some(e=>e?.type!=='Literal'||typeof e.value!=='string'))why='jsList is not an array of string literals';
          else jsList=hits[0].value.elements.map(e=>e.value);
        }
        settingsJs[file]={jsList,why};
      }
    }
    process.stdout.write(JSON.stringify({schema:'cocos_resource_sites.v1',sites,escapes,settings_js:settingsJs,settings_writes:settingsWrites}));
  } catch (error) {
    process.stdout.write(JSON.stringify({error:String(error)}));process.exitCode=1;
  }
});
