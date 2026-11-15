(function(){
var mode=new URLSearchParams(location.search).get('mode')==='before'?'before':'after';
var errors=[];window.addEventListener('error',function(e){if(errors.length<3)errors.push(e.message);document.getElementById('result').textContent=JSON.stringify(errors);});
var script=document.createElement('script');script.src=mode+'-GameUIKit.js';script.onload=function(){window.TestUI=module.exports;var fit=document.createElement('script');fit.src=mode+'-ScreenFit.js';fit.onload=function(){window.TestFit=module.exports;start();};document.head.appendChild(fit);};document.head.appendChild(script);
function start(){cc.game.run({id:'GameCanvas',debugMode:0,frameRate:60,renderMode:2,showFPS:false,registerSystemEvent:false},function(){
 cc.view.setDesignResolutionSize(720,1280,cc.ResolutionPolicy.FIXED_WIDTH);
 var scene=new cc.Scene(),canvas=new cc.Node('Canvas');scene.addChild(canvas);var c=canvas.addComponent(cc.Canvas);c.designResolution=cc.size(720,1280);c.fitWidth=true;c.fitHeight=false;
 cc.director.runScene(scene);cc.director.once(cc.Director.EVENT_AFTER_DRAW,function(){run(canvas);});
});}
function run(canvas){var UI=window.TestUI,out=window.fixturePartial={mode:mode,engine:cc.ENGINE_VERSION,rows:[],errors:errors};function row(name,ok,data){out.rows.push({name:name,passed:!!ok,data:data});}
 ['shrink','clamp','resize'].forEach(function(m,i){var t=UI.text(canvas,{name:'Text_'+m,w:310,h:130,text:'Read a useful body description, then try the next action.',overflow:m,fontSize:26,y:360-i*140});t.label._forceUpdateRenderData();var first={width:t.node.width,height:t.node.height};t.set('');t.label._forceUpdateRenderData();var empty=t.node.width;t.set('Updated body description with more words.');t.label._forceUpdateRenderData();row('text_'+m,first.width===310&&empty===310&&t.node.width===310&&(m==='resize'||first.height===130),{first:first,empty:empty,updated:{width:t.node.width,height:t.node.height}});});
 var tx=new cc.Texture2D();var cv=document.createElement('canvas');cv.width=400;cv.height=100;var ctx=cv.getContext('2d');ctx.fillStyle='#efb770';ctx.fillRect(0,0,400,100);tx.initWithElement(cv);tx.handleLoadedTexture();var f=new cc.SpriteFrame(tx);var tall=new cc.SpriteFrame(tx,cc.rect(0,0,50,100));
 if(UI.picture){var p=UI.picture(canvas,{frame:f,w:200,h:100,y:-200});p.setFrame(tall);row('picture_swap',p.node.width===50&&p.node.height===100,{width:p.node.width,height:p.node.height});}else row('picture_swap',false,{reason:'public stable picture method absent'});
 var bn=new cc.Node('Button');canvas.addChild(bn);bn.setContentSize(200,100);bn.y=-350;var sp=bn.addComponent(cc.Sprite);sp.sizeMode=cc.Sprite.SizeMode.CUSTOM;sp.spriteFrame=f;bn.setContentSize(200,100);bn.color=cc.color(250,180,110);bn.opacity=180;
 var taps=0,b=UI.button(bn,function(){taps++;},{guardMs:0,disabledText:'',disabledOpacity:.7});b.tap();b.setEnabled(false);
 var rp=UI.resultPage(canvas,{double:false,amount:5,onReward:function(){},onNext:function(){},onHome:function(){},buttons:{claim:{textFrame:f,text:''}}});var cn=rp.button('claim').node;row('claim_semantics',cn.name==='LinkClaim'&&cn.__gameUIRole==='result_claim_link',{name:cn.name,role:cn.__gameUIRole||null});rp.close();
 setTimeout(function(){row('button_state',bn.color.r===250&&bn.color.g===180&&bn.color.b===110&&bn.opacity===126&&taps===1,{color:{r:bn.color.r,g:bn.color.g,b:bn.color.b},opacity:bn.opacity,taps:taps});
 var parent=new cc.Node('DelayedParent');canvas.addChild(parent);var bg=new cc.Node('Background');parent.addChild(bg);bg.setContentSize(720,1280);var watch=window.TestFit.cover(cc,bg,{watch:true,bleed:0});var old=bg.y;parent.y+=80;
 cc.director.once(cc.Director.EVENT_AFTER_DRAW,function(){row('cover_after_parent_layout',Math.abs(bg.y-(old-80))<.01,{before:old,after:bg.y});watch.off();bg.destroy();parent.destroy();out.passed=out.rows.every(function(r){return r.passed;})&&errors.length===0;window.fixtureResult=out;document.getElementById('result').textContent=JSON.stringify(out,null,2);});
 },150);
}
})();