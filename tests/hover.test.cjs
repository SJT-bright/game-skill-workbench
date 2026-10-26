const test=require('node:test');const assert=require('node:assert/strict');
const {hoverTrigger}=require('../src/hover.cjs');
test('hover opens once, manual close requires leaving before re-entry',()=>{
 const trigger=hoverTrigger(),bounds={x:-32,y:100,width:32,height:88},on={x:-1,y:110},off={x:1,y:110};
 assert.equal(trigger.sample(on,bounds),true);assert.equal(trigger.sample(on,bounds),false);
 trigger.closed(on,bounds);assert.equal(trigger.sample(on,bounds),false);
 assert.equal(trigger.sample(off,bounds),false);assert.equal(trigger.sample(on,bounds),true);
 trigger.closed(off,bounds);assert.equal(trigger.sample(on,bounds),true);
});

test('Token amounts use Chinese units and preserve unknown values',()=>{
 const fs=require('node:fs'),vm=require('node:vm'),source=fs.readFileSync(require('node:path').join(__dirname,'../ui/app.js'),'utf8');
 const start=source.indexOf('function tokens('),end=source.indexOf('\nfunction timestamp',start);
 const format=vm.runInNewContext('const knownNumber=n=>typeof n===\'number\'&&Number.isFinite(n)&&n>=0;'+source.slice(start,end)+';tokens');
 assert.equal(format(220000000),'2.2亿');assert.equal(format(5600000),'5.6百万');assert.equal(format(560000),'56万');
 assert.equal(format(0),'0');assert.equal(format(null),'—');assert.equal(format(1234),'1,234');
});
