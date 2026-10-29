// Synthetic browser DOM contract only; no browser or game is started.
const fs = require('fs'), assert = require('assert'), vm = require('vm'), path = require('path');
const source = fs.readFileSync(path.join(__dirname, 'ui_dump.js'), 'utf8');
function capture(options={}) {
  const rootStyle={display:'block',visibility:'visible',opacity:'1',backgroundColor:'rgb(23, 23, 23)',
    backgroundImage:'url("splash.png")',backgroundSize:options.size||'45%',backgroundPosition:'50% 50%',fontSize:'12px',fontWeight:'400',color:'rgb(255,255,255)'};
  function element(tag,box,style={}) {return {tagName:tag,style:{...rootStyle,backgroundImage:'none',...style},
    childNodes:[],parentElement:null,firstElementChild:null,disabled:false,
    classList:{contains:n=>n==='progress-bar'&&tag==='PROGRESSDIV'},getAttribute:()=>null,hasAttribute:()=>false,
    getBoundingClientRect:()=>box};}
  const root=element('DIV',{x:0,y:0,width:390,height:844},rootStyle);
  const bar=element('PROGRESSDIV',{x:107.25,y:675.2,width:175.5,height:7});
  const span=element('SPAN',{x:109.25,y:677.2,width:87.75,height:3},{backgroundColor:'rgb(61,197,222)'});
  root.firstElementChild=bar;bar.firstElementChild=span;bar.parentElement=root;span.parentElement=bar;
  root.querySelectorAll=()=>[bar,span];
  if(options.hidden)root.style.display='none';
  const context={window:{innerWidth:390,innerHeight:844,devicePixelRatio:1,getComputedStyle:el=>el.style},
    document:{querySelector:()=>root,querySelectorAll:()=>[]},console};
  return vm.runInNewContext(source,context)({});
}
if(process.argv.includes('--dump')) process.stdout.write(JSON.stringify(capture()));
else {
  const good=capture();assert.equal(good.api,'dom-loading');assert.equal(good.errors.length,0);
  assert(good.nodes.some(n=>n.path==='DOMLoading/Logo'&&n.comps.sprite.frame_size[0]===547));
  assert(good.nodes.some(n=>n.comps.progress&&n.comps.progress.value===0.5));
  assert(capture({size:'cover'}).errors.includes('unsupported splash background fit'));
  assert(capture({hidden:true}).error.includes('cc.director'));
  console.log('3 DOM capture controls passed');
}
