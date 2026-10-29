'use strict';
module.exports.install=function(cc){
 var manager=cc.internal&&cc.internal.inputManager;if(!manager||manager.__starPopTouchCoordinates)return;
 var raw=manager.getTouchesByEvent;
 function finite(n){return typeof n==='number'&&isFinite(n)}
 function convert(t){if(finite(t.clientX)&&finite(t.clientY))return t;var out={};Object.keys(t).forEach(function(k){out[k]=t[k]});out.identifier=t.identifier;out.clientX=finite(t.clientX)?t.clientX:t.screenX;out.clientY=finite(t.clientY)?t.clientY:t.screenY;return out;}
 manager.getTouchesByEvent=function(event,position){var normalized=Object.create(event);['touches','changedTouches'].forEach(function(k){if(event[k])Object.defineProperty(normalized,k,{value:Array.prototype.map.call(event[k],convert)});});return raw.call(this,normalized,position)};
 manager.__starPopTouchCoordinates=true;
};
