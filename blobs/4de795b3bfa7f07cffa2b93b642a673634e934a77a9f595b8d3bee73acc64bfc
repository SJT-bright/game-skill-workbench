'use strict';
// Local geometry/event stand-ins; must not be called real-engine or device acceptance.
var assert=require('assert');var Fit=require(process.env.SCREEN_FIT_FILE||'../parts/ScreenFit');
function emitter(o){var events={};o.on=function(e,f){(events[e]=events[e]||[]).push(f);};o.off=function(e,f){events[e]=(events[e]||[]).filter(function(x){return x!==f;});};o.once=function(e,f){function once(){o.off(e,once);f();}o.on(e,once);};o.emit=function(e){(events[e]||[]).slice().forEach(function(f){f();});};o.count=function(){return Object.keys(events).reduce(function(n,k){return n+events[k].length;},0);};return o;}
function environment(kind){
 var cc={};cc.Component=function(){};cc.Class=function(def){function C(){}C.prototype=Object.create(cc.Component.prototype);C.prototype.onDestroy=def.onDestroy;return C;};
 cc.Node={EventType:{POSITION_CHANGED:'position-changed',SCALE_CHANGED:'scale-changed',SIZE_CHANGED:'size-changed',ANCHOR_CHANGED:'anchor-changed',PARENT_CHANGED:'parent-changed',TRANSFORM_CHANGED:kind==='3x'?'transform-changed':null}};
 cc.Director={EVENT_BEFORE_DRAW:'before-draw',EVENT_BEFORE_SCENE_LAUNCH:'scene'};cc.director=emitter({});cc.isValid=function(n){return !!n&&n.valid!==false;};cc.v2=function(x,y){return{x:x,y:y};};cc.Vec3=function(x,y,z){this.x=x;this.y=y;this.z=z;};
 cc.view=emitter({getVisibleSize:function(){return{width:720,height:1280};},getVisibleOrigin:function(){return{x:0,y:0};}});
 if(kind==='3x')cc.UITransform=function(){};
 function node(parent,w,h){var n=emitter({parent:parent,width:w,height:h,anchorX:.5,anchorY:.5,x:0,y:0,scaleX:1,scaleY:1,valid:true,_comps:[]});
  function wx(){return n.x+(parent?parent.x:0);}function wy(){return n.y+(parent?parent.y:0);}
  n.convertToWorldSpaceAR=function(p){return{x:wx()+p.x,y:wy()+p.y};};n.convertToNodeSpaceAR=function(p){return{x:p.x-wx(),y:p.y-wy()};};n.setPosition=function(x,y){n.x=x;n.y=y;};n.setScale=function(x,y){n.scaleX=x;n.scaleY=y;};
  Object.defineProperty(n,'scale',{get:function(){return{x:n.scaleX,y:n.scaleY,z:1};}});Object.defineProperty(n,'worldPosition',{get:function(){return{x:wx(),y:wy(),z:0};}});
  var t={width:w,height:h,anchorX:.5,anchorY:.5,convertToWorldSpaceAR:n.convertToWorldSpaceAR,convertToNodeSpaceAR:n.convertToNodeSpaceAR};
  n.getComponent=function(C){if(C===cc.UITransform)return t;return n._comps.filter(function(c){return c instanceof C;})[0]||null;};n.addComponent=function(C){var c=new C();n._comps.push(c);return c;};n.destroy=function(){n.valid=false;n._comps.forEach(function(c){if(c.onDestroy)c.onDestroy();});};return n;
 }
 return{cc:cc,node:node};
}
['24','3x'].forEach(function(k){var e=environment(k),cc=e.cc,p=e.node(null,720,1280),bg=e.node(p,720,1280);p.x=360;p.y=640;
 var r=Fit.cover(cc,bg,{watch:true,bleed:0});assert.strictEqual(bg.x,0);
 p.y=720;p.emit(k==='3x'?'transform-changed':'position-changed');assert.ok(cc.director.count()>0,'layout event queued');cc.director.emit('before-draw');assert.strictEqual(bg.y,-80,'late parent move covered');
 p.y=800;p.emit('position-changed');r.off();cc.director.emit('before-draw');assert.strictEqual(bg.y,-80,'off cancels queued refresh');assert.strictEqual(cc.view.count(),0);assert.strictEqual(p.count(),0);
 r=Fit.cover(cc,bg,{watch:true,bleed:0});assert.strictEqual(bg.y,-160);bg.destroy();assert.strictEqual(cc.view.count(),0,'destroy detaches view');assert.strictEqual(p.count(),0,'destroy detaches ancestors');
 console.log('PASS ['+k+'] late layout, off, queued cancellation and owner destroy');
});
