'use strict';
// Decoder capability only. Canvas encoding is deliberately not used here.
// r8: decode a real WebP file shipped in the main package (same encoder settings as
// the game art, with alpha) through TikTok's own createImage. No data: URI, because
// a mini-game image loader is not required to accept one.
// Only a real decode with non-zero size enables WebP. An error or no answer within
// 5 s leaves it off (startup shows Retry, and Retry runs this probe again).
module.exports=function(root,ready){
 var caps=root.cc.sys.capabilities;
 if(caps.webp){ready();return;}
 var done=false,timer,image;
 function finish(ok){if(done)return;done=true;clearTimeout(timer);caps.webp=ok===true;ready();}
 timer=setTimeout(function(){finish(false);},5000);
 try{
  var sdk=(root.TTMinis&&root.TTMinis.game)||root.tt||root.wx;
  image=sdk.createImage();
  var loaded=function(){finish((image.naturalWidth||image.width)>0&&(image.naturalHeight||image.height)>0);},failed=function(){finish(false);};
  if(typeof image.addEventListener==='function'){image.addEventListener('load',loaded);image.addEventListener('error',failed);}
  else{image.onload=loaded;image.onerror=failed;}
  image.src='loading/webp-probe.webp';
 }catch(e){finish(false);}
};
