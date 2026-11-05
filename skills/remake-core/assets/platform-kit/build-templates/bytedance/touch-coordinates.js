'use strict';
// Platform kit standard part touch24 (Cocos 2.4, 待真机复测). Installed by tiktok_finalize; do not hand-edit.
// 1. TikTok touches carry screenX/screenY only and Cocos 2.4 reads clientX/clientY: copy them over (StarPop v50).
// 2. (v7.9 手机问题源头约束) A finger that is down when TikTok takes the game away (Control Center, a call, a rewarded
//    video) may never get touchend. Cocos 2.4 keeps that touch, and the next touchstart with the same identifier is
//    dropped (the engine forgets a touch only after 5 s): the first tap after returning is lost (甜点消消乐 R47: the
//    pause popup needed two taps; 割草 v015). On EVENT_HIDE and EVENT_SHOW the touches the engine still holds get a
//    TOUCH_CANCEL and its touch state is cleared, so the next finger starts clean (甜点消消乐 R48, accepted on a phone).
module.exports.install=function(cc){
 var manager=cc.internal&&cc.internal.inputManager;if(!manager||manager.__starPopTouchCoordinates)return;
 var raw=manager.getTouchesByEvent;
 function finite(n){return typeof n==='number'&&isFinite(n)}
 function convert(t){if(finite(t.clientX)&&finite(t.clientY))return t;var out={};Object.keys(t).forEach(function(k){out[k]=t[k]});out.identifier=t.identifier;out.clientX=finite(t.clientX)?t.clientX:t.screenX;out.clientY=finite(t.clientY)?t.clientY:t.screenY;return out;}
 manager.getTouchesByEvent=function(event,position){var normalized=Object.create(event);['touches','changedTouches'].forEach(function(k){if(event[k])Object.defineProperty(normalized,k,{value:Array.prototype.map.call(event[k],convert)});});return raw.call(this,normalized,position)};
 manager.__starPopTouchCoordinates=true;
 function cancelStale(){
  try{
   var dict=manager._touchesIntegerDict;if(!dict)return;
   var held=[];
   Object.keys(dict).forEach(function(id){var t=manager._touches&&manager._touches[dict[id]];if(t&&t._point)held.push(t);});
   // the engine's own touch objects: handleTouchesCancel reads their point and previous point
   if(held.length&&typeof manager.handleTouchesCancel==='function')manager.handleTouchesCancel(held);
   manager._touchesIntegerDict={};manager._touchesCache={};manager._indexBitsUsed=0;manager._touchCount=0;
   var events=cc.internal.eventManager;if(events&&typeof events._clearCurTouch==='function')events._clearCurTouch();
  }catch(e){try{console.warn('[touch24] stale touch reset',e)}catch(_){}}
 }
 var game=cc.game;
 if(game&&typeof game.on==='function'&&game.EVENT_HIDE&&game.EVENT_SHOW){game.on(game.EVENT_HIDE,cancelStale);game.on(game.EVENT_SHOW,cancelStale);}
};
