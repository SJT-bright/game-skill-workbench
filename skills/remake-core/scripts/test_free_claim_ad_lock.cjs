'use strict';
const assert = require('node:assert/strict');
const {scan} = require('./scan_free_claim_ad_lock.cjs');

const bindings = `Panel.prototype.start=function(){
  UI.setButtonClickEvents(this, this.freeButton, 'collect', 1);
  UI.setButtonClickEvents(this, this.videoButton, 'collect', 0);
};`;
const ad = `if(mode===0){
  this.waiting=true;
  var self=this;
  SDK.showVideoAd('bonus',function(){self.waiting=false;self.collect(event,2);});
  return;
}`;
const reward = 'this.save(mode===1?this.base:this.base.concat(this.bonus));';
const method = body => bindings + `Panel.prototype.collect=function(event,mode){${body}};`;
let cases = 0;
function check(name, source, expected) {
  const found = scan(source, name);
  assert.equal(found.length, expected, name + ': ' + JSON.stringify(found));
  ++cases;
}

check('early unconditional return', method('if(this.waiting)return;' + ad + reward), 1);
check('minified negative guard', method('if(!this.waiting){' + ad + reward + '}'), 1);
check('minified sequence guard', method('if(void 0===mode&&(mode=1),!this.waiting){' + ad + reward + '}'), 1);
check('renamed flag', method('if(this.waiting)return;' + ad + reward).replaceAll('waiting', 'processingVideo'), 1);
check('free path cancels its own request', method('if(this.waiting){if(mode!==1)return;this.cancelBonus();}' + ad + reward), 0);
check('only ad path guarded', method('if(mode===1){this.save(this.base);return;}if(this.waiting)return;' + ad), 0);
check('single mandatory ad button', method('if(this.waiting)return;' + ad).replace("UI.setButtonClickEvents(this, this.freeButton, 'collect', 1);", ''), 0);
check('purchase tiers without reward reentry', method('if(this.waiting)return;' + ad + reward).replace('self.collect(event,2)', 'self.purchase()'), 0);
check('quoted examples', `var example=${JSON.stringify(method('if(this.waiting)return;' + ad + reward))};`, 0);
check('unrelated classes with the same handler', bindings.replaceAll('Panel', 'Other') +
  `Panel.prototype.collect=function(event,mode){if(this.waiting)return;${ad}${reward}};`, 0);
const object = `{start:function(){UI.setButtonClickEvents(this,a,'collect',1);UI.setButtonClickEvents(this,b,'collect',0);},
 collect:function(event,mode){if(this.waiting)return;${ad}${reward}}}`;
check('object methods', 'var panel=' + object, 1);
console.log(JSON.stringify({passed: true, cases}));
