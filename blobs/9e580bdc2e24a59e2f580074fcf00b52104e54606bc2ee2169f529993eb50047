'use strict';
// Pure AST evaluation of known mini-game environment constants, never game execution.
const fs=require('fs'),acorn=require('./vendor/acorn.cjs');
const input=JSON.parse(fs.readFileSync(0,'utf8')),ast=acorn.parse(input.code,{ecmaVersion:8}),UNKNOWN=Symbol('unknown');
function member(n){if(n.type==='Identifier')return n.name;if(n.type==='MemberExpression'&&!n.computed)return member(n.object)+'.'+n.property.name;return '';}
function value(n){if(n.type==='Literal')return n.value;const m=member(n);if(m==='cc.sys.isNative')return false;if(['settings.debug','window._CCSettings.debug'].includes(m))return input.debug;if(n.type==='UnaryExpression'&&n.operator==='!'){const v=value(n.argument);return v===UNKNOWN?UNKNOWN:!v;}if(n.type==='LogicalExpression'){const l=value(n.left);if(n.operator==='&&'&&l!==UNKNOWN&&!l)return l;if(n.operator==='||'&&l!==UNKNOWN&&l)return l;const r=value(n.right);return l===UNKNOWN?UNKNOWN:r;}return UNKNOWN;}
const out=[];
function walk(n){if(!n||typeof n!=='object')return;if(n.type==='Literal'&&typeof n.value==='string')out.push(n.value);if(n.type==='IfStatement'||n.type==='ConditionalExpression'){const v=value(n.test);walk(n.test);if(v===UNKNOWN){walk(n.consequent);walk(n.alternate);}else walk(v?n.consequent:n.alternate);return;}for(const v of Object.values(n))if(v&&typeof v==='object')Array.isArray(v)?v.forEach(walk):walk(v);}
walk(ast);console.log(JSON.stringify(out));
