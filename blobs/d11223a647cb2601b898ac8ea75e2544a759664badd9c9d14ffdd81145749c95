'use strict';
// Component-construction side effects and cross-state contracts; Node stand-ins, not device acceptance.
var assert = require('assert');
var S = require('./engine-stub-ui');
var cases = [];
function test(name, fn) { cases.push({name:name,fn:fn}); }
function opacity(env,n) { var op=n.getComponent(env.cc.UIOpacity); return op ? op.opacity : n.opacity; }
function color(env,n) { var r=n.getComponent(env.cc.Sprite)||n; return r.color; }
function fresh(kind) { var e=S.loadKit(kind);e.kind=kind;e.Kit._reset();return e; }
test('text keeps declared box when adding a Label immediately sizes its empty NONE text', function(e) {
  var add=e.cc.Node.prototype.addComponent;
  e.cc.Node.prototype.addComponent=function(C) { var c=add.call(this,C);if(C===e.cc.Label)c._forceUpdateRenderData();return c; };
  ['shrink','clamp','resize'].forEach(function(mode) {
    var t=e.Kit.text(e.canvas,{w:310,h:130,text:'A body description that wraps.',overflow:mode});
    assert.strictEqual(t.node.width,310,mode+' width');
    if(mode!=='resize')assert.strictEqual(t.node.height,130,mode+' height');
    t.set('');t.label._forceUpdateRenderData();assert.strictEqual(t.node.width,310,'empty update');
    t.set('Updated body description.');t.label._forceUpdateRenderData();assert.strictEqual(t.node.width,310,'text update');
  });
});
test('picture swaps frames inside the original declared budget with one renderer',function(e) {
  var p=e.Kit.picture(e.canvas,{name:'Caption',frame:e.frame(400,100),w:200,h:100});
  assert.strictEqual(p.node.width,200);assert.strictEqual(p.node.height,50);
  p.setFrame(e.frame(100,400));assert.strictEqual(p.node.width,25);assert.strictEqual(p.node.height,100);
  p.setFrame(e.frame(200,200));assert.strictEqual(p.node.width,100);assert.strictEqual(p.node.height,100);
  assert.strictEqual(S.renderCount(p.node),1,'one renderer after swaps');
  assert.throws(function(){e.Kit.picture(e.canvas,{frame:e.frame(200,200)});},/display/);
});
test('button disabled and busy preserve artwork colours and restore authored opacity; late press does not undo state',function(e) {
  var art=e.Kit.picture(e.canvas,{frame:e.frame(200,100),w:200,h:100}).node;
  var c=color(e,art);c.r=250;c.g=180;c.b=110;
  if(e.kind==='3x')(art.getComponent(e.cc.UIOpacity)||art.addComponent(e.cc.UIOpacity)).opacity=180;else art.opacity=180;
  var calls=0,b=e.Kit.button(art,function(){calls++;},{guardMs:0,disabledText:'',disabledOpacity:0.7});
  b.tap();b.setEnabled(false);e.clock.advance(100);
  assert.strictEqual(calls,1);assert.deepStrictEqual([color(e,art).r,color(e,art).g,color(e,art).b],[250,180,110]);
  assert.strictEqual(opacity(e,art),126,'late press must retain disabled opacity');
  b.tap();assert.strictEqual(calls,1);
  b.setEnabled(true);assert.strictEqual(opacity(e,art),180);
  b.setBusy(true);b.tap();assert.strictEqual(calls,1);assert.strictEqual(b.isBusy(),true);
  b.setBusy(false);b.tap();assert.strictEqual(calls,2);
  b.dispose();e.clock.advance(100);
});
test('result free claim is the standard text-link role while slot API remains claim',function(e) {
 var p=e.Kit.resultPage(e.canvas,{double:false,amount:5,onReward:function(){},onNext:function(){},onHome:function(){},buttons:{claim:{textFrame:e.frame(200,40),text:''}}});
 var n=p.button('claim').node;
 assert.strictEqual(n.name,'LinkClaim');assert.strictEqual(n.__gameUIRole,'result_claim_link');assert.ok(p.slot('claim'));
 assert.strictEqual(p.button('home').node.__gameUIRole,'action_button');
});
test('fontFrames carries unique source font and character identity without changing glyph rect',function(e) {
 var source=e.frame(400,100);var font={_uuid:'fixture-font-uuid',spriteFrame:source,_fntConfig:{fontDefDictionary:{'43':{rect:{x:10,y:0,width:20,height:40}}}}};
 var glyph=e.Kit.fontFrames(font,'+')['+'];assert.ok(glyph);
 assert.strictEqual(glyph.name,'glyph_fixture-font-uuid_43');assert.strictEqual(glyph.__gameUISource.font_uuid,'fixture-font-uuid');assert.strictEqual(glyph.__gameUISource.code,43);
 var rect=glyph.getRect?glyph.getRect():glyph.rect;assert.strictEqual(rect.width,20);assert.strictEqual(rect.height,40);
});
var failed=0;['24','3x'].forEach(function(k){cases.forEach(function(t){try{t.fn(fresh(k));console.log('PASS ['+k+'] '+t.name);}catch(e){failed++;console.log('FAIL ['+k+'] '+t.name+': '+e.message);}});});
console.log(JSON.stringify({cases:cases.length*2,failed:failed,environment:'Node engine stand-ins'}));process.exitCode=failed?1:0;
