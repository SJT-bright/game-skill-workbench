'use strict';
const __cg=(()=>{try{return require(require('path').join(__dirname,'..','..','cocos-game-check','package-check','scripts','check_guard.cjs'))}catch(e){return null}})();// P20: --help / no input never reaches JSON.parse
if(__cg&&require.main===module)__cg.cli({tool:'parse_package_requires.cjs',usage:'Usage: run by its Python check script; reads one JavaScript source on stdin and prints its literal requires.'});
// acorn 8.15.0, MIT; parses code without executing any game/SDK module.
const acorn = require('./vendor/acorn.cjs');
let source = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { source += chunk; });
process.stdin.on('end', () => {
  if (__cg && !source.trim()) __cg.notRun('parse_package_requires.cjs', 'no payload on stdin: run by its Python check script');
  try {
    let ast;
    const options = {ecmaVersion:'latest', allowHashBang:true, allowReturnOutsideFunction:true, locations:true};
    try { ast = acorn.parse(source, {...options, sourceType:'script'}); }
    catch (_) { ast = acorn.parse(source, {...options, sourceType:'module'}); }
    const parents = new WeakMap(), nodes = [];
    function walk(node, parent) {
      if (!node || typeof node !== 'object' || typeof node.type !== 'string') return;
      parents.set(node, parent); nodes.push(node);
      for (const [key,value] of Object.entries(node)) {
        if (key === 'loc') continue;
        if (Array.isArray(value)) { for (const item of value) walk(item,node); }
        else if (value && typeof value.type === 'string') walk(value,node);
      }
    }
    walk(ast,null);
    const isFunction = node => /^(FunctionExpression|FunctionDeclaration|ArrowFunctionExpression)$/.test(node.type);
    function classification(node) {
      for (let fn = parents.get(node); fn; fn = parents.get(fn)) {
        if (!isFunction(fn) || !fn.params.some(p => p.type==='Identifier' && p.name==='require')) continue;
        const array = parents.get(fn), property = array && parents.get(array);
        if (array && array.type==='ArrayExpression' && array.elements[0]===fn &&
            array.elements[1] && array.elements[1].type==='ObjectExpression' &&
            property && property.type==='Property' &&
            ['require','module','exports'].every(name => fn.params.some(p=>p.type==='Identifier'&&p.name===name))) return 'bundle_internal';
        const call = parents.get(fn), index = fn.params.findIndex(p=>p.type==='Identifier'&&p.name==='require');
        if (call && call.type==='CallExpression' && call.callee===fn && call.arguments[index] &&
            call.arguments[index].type==='Identifier' && call.arguments[index].name==='require') continue;
        return 'unknown_require_binding';
      }
      return 'package';
    }
    const dependencies=[], dynamic=[], literalRequires=[]; let internal=0;
    for (const node of nodes) {
      let argument, kind;
      if (node.type==='CallExpression' && node.callee.type==='Identifier' && node.callee.name==='require') {
        const type=classification(node);
        if (type==='bundle_internal') { internal++; continue; }
        if (type==='unknown_require_binding') { dynamic.push({line:node.loc.start.line,kind:type}); continue; }
        argument=node.arguments[0]; kind='require';
      } else if (node.type==='ImportDeclaration' || node.type==='ExportNamedDeclaration' || node.type==='ExportAllDeclaration') {
        argument=node.source; kind='esm';
      } else if (node.type==='ImportExpression') { argument=node.source; kind='import'; }
      else continue;
      if (!argument) continue;
      let request = argument.type==='Literal' && typeof argument.value==='string' ? argument.value : null;
      if (argument.type==='TemplateLiteral' && argument.expressions.length===0) request=argument.quasis[0].value.cooked;
      if (request!==null) {
        dependencies.push({request,kind,line:node.loc.start.line});
        if (kind === 'require') literalRequires.push({node,request});
      }
      else dynamic.push({line:node.loc.start.line,kind});
    }
    // Only actual writes in the entry's immediately executed code declare
    // this private compatibility protocol. Comments, labels and dormant examples
    // must not turn a different game into a Bamboo boundary fixture.
    function constant(node) {
      if (!node) return {known:false};
      if (node.type==='Literal') return {known:true,value:node.value};
      if (node.type==='TemplateLiteral' && node.expressions.length===0) return {known:true,value:node.quasis[0].value.cooked};
      if (node.type==='UnaryExpression') {
        const item=constant(node.argument);if(!item.known)return item;
        if(node.operator==='!')return {known:true,value:!item.value};
        if(node.operator==='void')return {known:true,value:undefined};
        if(node.operator==='+')return {known:true,value:+item.value};
        if(node.operator==='-')return {known:true,value:-item.value};
      }
      return {known:false};
    }
    function entryExecution(node) {
      for (let child=node,parent=parents.get(node);parent;child=parent,parent=parents.get(parent)) {
        if (isFunction(parent)) {
          const call=parents.get(parent);
          if (!call || call.type!=='CallExpression' || call.callee!==parent) return false;
        }
        if (parent.type==='IfStatement'||parent.type==='ConditionalExpression') {
          const test=constant(parent.test);
          if(test.known && ((child===parent.consequent&&!test.value)||(child===parent.alternate&&test.value)))return false;
        }
        if(parent.type==='LogicalExpression'&&child===parent.right){
          const left=constant(parent.left);
          if(left.known&&((parent.operator==='&&'&&!left.value)||(parent.operator==='||'&&left.value)||(parent.operator==='??'&&left.value!=null)))return false;
        }
        if((parent.type==='WhileStatement'||parent.type==='ForStatement')&&child===parent.body){
          const test=constant(parent.test);if(test.known&&!test.value)return false;
        }
      }
      return true;
    }
    function scopeOf(node){for(let p=node;p;p=parents.get(p))if(isFunction(p)||p.type==='Program')return p;return ast;}
    const bindings=new Map();
    function declare(scope,name,init){if(!bindings.has(scope))bindings.set(scope,new Map());const table=bindings.get(scope);table.set(name,table.has(name)?null:init);}
    for(const node of nodes){
      if(node.type==='VariableDeclarator'&&node.id.type==='Identifier')declare(scopeOf(node),node.id.name,node.init);
      if(isFunction(node)){const call=parents.get(node);node.params.forEach((param,index)=>{if(param.type==='Identifier')declare(node,param.name,call?.type==='CallExpression'&&call.callee===node?call.arguments[index]:null);});}
      if(node.type==='FunctionDeclaration'&&node.id)declare(scopeOf(parents.get(node)),node.id.name,null);
    }
    function binding(name,node){for(let scope=scopeOf(node);scope;){const table=bindings.get(scope);if(table?.has(name))return {scope,init:table.get(name)};if(scope===ast)break;scope=scopeOf(parents.get(scope));}return null;}
    function globalReceiver(expression,node,seen=new Set()){
      if(!expression)return false;
      if(expression.type==='ConditionalExpression')return globalReceiver(expression.consequent,node,new Set(seen))&&globalReceiver(expression.alternate,node,new Set(seen));
      if(expression.type==='LogicalExpression')return globalReceiver(expression.left,node,new Set(seen))&&globalReceiver(expression.right,node,new Set(seen));
      if(expression.type!=='Identifier')return false;
      const name=expression.name,found=binding(name,node);
      if(!found)return ['globalThis','GameGlobal','window'].includes(name);
      if(!found.init||seen.has(found.init))return false;
      for(const candidate of nodes){
        const lhs=candidate.type==='AssignmentExpression'?candidate.left:candidate.type==='UpdateExpression'?candidate.argument:null;
        if(lhs?.type==='Identifier'&&lhs.name===name&&binding(name,candidate)?.scope===found.scope)return false;
      }
      seen.add(found.init);return globalReceiver(found.init,found.init,seen);
    }
    const writes=new Set();
    for (const node of nodes) {
      if (node.type!=='AssignmentExpression' || node.left.type!=='MemberExpression' || !entryExecution(node)) continue;
      const member=node.left;
      if(!globalReceiver(member.object,node))continue;
      const property=!member.computed ? member.property.name : member.property.type==='Literal' ? member.property.value : null;
      if (typeof property==='string') writes.add(property);
    }
    const native_entry_protocols=[];
    if (writes.has('__bambooNativeCompat') && writes.has('__bambooResolvePlatform')) native_entry_protocols.push('bamboo_native_host_v1');
    // This is a conservative startup scan. A call after a possible early
    // return, in a conditional branch, or in a dormant callback is not proof
    // that the actual startup will execute it.
    function mayExit(statement) {
      if (!statement) return false;
      switch (statement.type) {
        case 'ReturnStatement':
        case 'ThrowStatement':
          return true;
        case 'BlockStatement':
          return statement.body.some(mayExit);
        case 'IfStatement':
          return mayExit(statement.consequent) || mayExit(statement.alternate);
        case 'SwitchStatement':
          return statement.cases.some(branch => branch.consequent.some(mayExit));
        case 'TryStatement':
          return mayExit(statement.block) || mayExit(statement.handler?.body) || mayExit(statement.finalizer);
        case 'LabeledStatement':
        case 'WithStatement':
        case 'WhileStatement':
        case 'DoWhileStatement':
        case 'ForStatement':
        case 'ForInStatement':
        case 'ForOfStatement':
          return mayExit(statement.body);
        default:
          return false;
      }
    }
    const afterExit = new WeakSet(), scannedBlocks = new WeakSet();
    function precededByExit(statement, block) {
      if (!scannedBlocks.has(block)) {
        scannedBlocks.add(block);
        let possibleExit = false;
        for (const sibling of block.body) {
          if (possibleExit) afterExit.add(sibling);
          else possibleExit = mayExit(sibling);
        }
      }
      return afterExit.has(statement);
    }
    function definiteExecution(node, boundary = ast) {
      for (let child=node,parent=parents.get(node);parent;child=parent,parent=parents.get(parent)) {
        if ((parent.type === 'Program' || parent.type === 'BlockStatement') && precededByExit(child, parent)) return false;
        if (parent === boundary) return true;
        if (isFunction(parent)) {
          const call = parents.get(parent);
          if (parent.async || parent.generator || call?.type !== 'CallExpression' || call.callee !== parent) return false;
        }
        if ((parent.type === 'IfStatement' || parent.type === 'ConditionalExpression') && child !== parent.test) return false;
        if (parent.type === 'LogicalExpression' && child === parent.right) return false;
        if (parent.type === 'AssignmentExpression' && ['&&=', '||=', '??='].includes(parent.operator)) return false;
        if (/^(ChainExpression|StaticBlock|SwitchCase|TryStatement|WithStatement|WhileStatement|DoWhileStatement|ForStatement|ForInStatement|ForOfStatement)$/.test(parent.type)) return false;
      }
      return false;
    }
    function memberName(node) {
      if (node?.type !== 'MemberExpression') return null;
      return node.computed ? constant(node.property).value : node.property.name;
    }
    function globalBoot(node, site) {
      return memberName(node) === 'boot' && globalReceiver(node.object, site);
    }
    function hostRequire(node, seen = new Set()) {
      const found = binding('require', node);
      if (!found) return true;
      if (found.init?.type !== 'Identifier' || found.init.name !== 'require' || seen.has(found.init)) return false;
      seen.add(found.init);
      return hostRequire(found.init, seen);
    }
    const startup_requires = [...new Set(literalRequires.filter(({node}) =>
      definiteExecution(node) && hostRequire(node)).map(({request}) => request))];
    const bootAssignments = nodes.filter(node => node.type === 'AssignmentExpression' &&
      globalBoot(node.left, node) && entryExecution(node));
    const bootAssignment = bootAssignments.length === 1 ? bootAssignments[0] : null;
    const assignedBoot = bootAssignment?.operator === '=' && definiteExecution(bootAssignment) &&
      isFunction(bootAssignment.right) && !bootAssignment.right.async && !bootAssignment.right.generator ?
      bootAssignment.right : null;
    let calls_global_boot = false, direct_startup_resources = false, direct_boot_resources = false;
    function isCocosMember(node, names) {
      for (let index = names.length - 1; index >= 0; index--) {
        if (memberName(node) !== names[index]) return false;
        node = node.object;
      }
      return node?.type === 'Identifier' && node.name === 'cc' && !binding('cc', node);
    }
    for (const node of nodes) {
      if (node.type !== 'CallExpression' || node.optional) continue;
      if (!calls_global_boot && globalBoot(node.callee, node) && definiteExecution(node)) calls_global_boot = true;
      if (!isCocosMember(node.callee, ['assetManager', 'loadBundle'])) continue;
      const argument = node.arguments[0];
      if (constant(argument).value !== 'resources' &&
          !isCocosMember(argument, ['AssetManager', 'BuiltinBundleName', 'RESOURCES'])) continue;
      if (definiteExecution(node)) direct_startup_resources = true;
      else if (assignedBoot && definiteExecution(node, assignedBoot)) direct_boot_resources = true;
    }
    // The 2.4 platform-kit startup loads a builtin through the adapter's computed
    // module path, so literal require collection cannot see this dependency.
    const namedCall = (node, name) => node?.type === 'CallExpression' &&
      node.callee.type === 'Identifier' && node.callee.name === name;
    const boot = nodes.find(node => node.type === 'AssignmentExpression' && entryExecution(node) &&
      node.left.type === 'MemberExpression' && !node.left.computed &&
      node.left.object.name === 'window' && node.left.property.name === 'boot' && isFunction(node.right))?.right;
    const start = boot?.body.body?.find(node => node.type === 'FunctionDeclaration' && node.id.name === 'start');
    function guardedStep(variable, stage) {
      const declaration = nodes.find(node => node.type === 'VariableDeclarator' &&
        start && scopeOf(node) === start && node.id.name === variable && namedCall(node.init, 'guarded') &&
        node.init.arguments[0]?.value === stage && isFunction(node.init.arguments[1]));
      return declaration?.init.arguments[1].body.body;
    }
    const loadResources = guardedStep('loadResources', 'resources');
    const loadSubpackage = guardedStep('loadSubpackage', 'resources subpackage');
    let startup24_resources = null;
    if (loadSubpackage && loadResources?.some(statement => {
      const call = statement.expression;
      return namedCall(call, 'loadBundle') &&
        source.slice(call.arguments[0]?.start, call.arguments[0]?.end).replace(/\s/g, '') ===
          'cc.AssetManager.BuiltinBundleName.RESOURCES';
    })) {
      const first = loadSubpackage[0];
      const test = first?.test;
      const branch = first?.consequent?.body;
      const setting = test?.type === 'BinaryExpression' && test.operator === '===' && constant(test.right).value === false ? test.left :
        test?.type === 'UnaryExpression' && test.operator === '!' ? test.argument : null;
      const skipsAbsent = first?.type === 'IfStatement' && memberName(setting) === 'hasResourcesBundle' &&
        setting.object.name === 'settings' && branch?.length === 2 &&
        namedCall(branch[0].expression, 'loadEngine') && branch[1].type === 'ReturnStatement';
      startup24_resources = skipsAbsent
        ? (test.type === 'UnaryExpression' ? 'skip_falsy' : 'skip_explicitly_absent')
        : 'unconditional';
    }
    const platform_input_bindings = require('./scan_platform_input_bindings.cjs').analyze({
      nodes, parents, isGlobal: (name, node) => !binding(name, node)
    });
    process.stdout.write(JSON.stringify({dependencies,dynamic,bundle_internal_requires:internal,parser:'acorn@8.15.0',
      native_entry_protocols,startup24_resources,startup_requires,global_boot_assignments:bootAssignments.length,calls_global_boot,
      direct_startup_resources,direct_boot_resources,platform_input_bindings}));
  } catch (error) {
    process.stdout.write(JSON.stringify({error:String(error.message)})); process.exitCode=1;
  }
});
