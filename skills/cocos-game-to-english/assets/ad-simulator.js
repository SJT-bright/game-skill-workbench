/* Served only by serve_preview.py --ad-simulator; never copy into game builds. */
(function (root) {
  'use strict';
  if (root.__adSimulator || !/^(127\.0\.0\.1|localhost|\[::1\])$/.test(root.location.hostname)) return;
  var active = null, serial = 0, records = [], host, box, badge, observer = null;
  function snapshot() {
    try {
      if (observer) return JSON.parse(JSON.stringify(observer()));
      var state = {};
      for (var i = 0; i < root.localStorage.length; i++) {
        var key = root.localStorage.key(i); state[key] = root.localStorage.getItem(key);
      }
      return state;
    } catch (e) { return { readError: String(e) }; }
  }
  function changes(before, after) {
    var out = {};
    Object.keys(Object.assign({}, before, after)).forEach(function (key) {
      if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) out[key] = { before: before[key], after: after[key] };
    });
    return out;
  }
  function ui() {
    if (host || !document.body) return;
    host = document.createElement('div'); host.id = '__ad-simulator';
    host.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none';
    var shadow = host.attachShadow({mode:'open'});
    shadow.innerHTML = '<style>*{box-sizing:border-box}button{font:14px sans-serif;padding:10px;border:1px solid #70839a;border-radius:8px;background:#fff;color:#132132;cursor:pointer}#badge{position:absolute;top:3px;left:3px;padding:4px 8px;font:11px sans-serif;background:#fff4c7;color:#292513;pointer-events:auto}#box{display:none;position:absolute;inset:0;background:#142235ed;color:white;pointer-events:auto;overflow:auto;padding:35px 20px;font:15px/1.5 sans-serif}h2{font-size:21px}#actions{display:grid;gap:10px}pre{font:12px/1.5 monospace;white-space:pre-wrap;overflow-wrap:anywhere}</style><button id="badge">广告模拟 · 查看记录</button><section id="box"></section>';
    badge = shadow.getElementById('badge'); box = shadow.getElementById('box');
    badge.onclick = function () { if (!active) history(); };
    document.body.appendChild(host);
  }
  function button(text, action) { var b = document.createElement('button'); b.textContent = text; b.onclick = action; return b; }
  function history() {
    ui(); box.replaceChildren(); box.style.display = 'block';
    var title = document.createElement('h2'); title.textContent = '模拟记录（不自动判定奖励通过）'; box.appendChild(title);
    var label = document.createElement('input'); label.placeholder='正在测试的入口，如：首页礼盒'; label.value=root.__adSimulator.entry;
    label.style.cssText='width:100%;padding:10px;margin-bottom:12px';
    label.oninput=function(){root.__adSimulator.label(label.value);}; box.appendChild(label);
    var pre = document.createElement('pre'); pre.textContent = JSON.stringify(records, null, 2); box.appendChild(pre);
    box.appendChild(button('返回游戏', function () { box.style.display = 'none'; }));
    box.appendChild(button('下载本次记录', function () {
      var url = URL.createObjectURL(new Blob([JSON.stringify(records, null, 2)], {type:'application/json'}));
      var a = document.createElement('a'); a.href = url; a.download = 'ad-simulation.json'; a.click(); setTimeout(function(){URL.revokeObjectURL(url);},1000);
    }));
  }
  function present(attempt) {
    ui(); box.replaceChildren(); box.style.display = 'block';
    var h = document.createElement('h2'); h.textContent = '模拟激励广告'; box.appendChild(h);
    var p = document.createElement('p'); p.textContent = '入口：' + attempt.entry + '\n广告位：' + attempt.adUnitId + '\n选择结果后，由游戏原有流程处理奖励。'; p.style.whiteSpace='pre-wrap'; box.appendChild(p);
    var actions = document.createElement('div'); actions.id='actions'; box.appendChild(actions);
    var complete = button('模拟看完 · 2 秒后可点', function () { finish(attempt, 'completed'); }); complete.disabled=true; actions.appendChild(complete);
    attempt.timer = setTimeout(function () { complete.disabled=false; complete.textContent='模拟看完（应发一次奖励）'; },2000);
    actions.appendChild(button('中途关闭（不应发奖）', function () { finish(attempt,'cancelled'); }));
    actions.appendChild(button('模拟加载／播放失败（不应发奖）', function () { finish(attempt,'failed'); }));
    actions.appendChild(button('模拟暂无广告（不应发奖）', function () { finish(attempt,'no-fill'); }));
    actions.appendChild(button('一直等待（观察游戏自己的超时）', function () {
      attempt.record.waiting=true; box.style.display='none'; badge.textContent='广告模拟 · 等待中，点此终止';
      badge.onclick=function(){ if(active===attempt) finish(attempt,'cancelled'); };
    }));
  }
  function finish(attempt, outcome) {
    if (active !== attempt || attempt.record.outcome) return false;
    clearTimeout(attempt.timer); active=null; attempt.record.outcome=outcome; attempt.record.finishedAt=Date.now();
    box.style.display='none'; badge.textContent='广告模拟 · '+outcome+' · 查看记录'; badge.onclick=function(){if(!active)history();};
    var handlers = outcome==='completed'||outcome==='cancelled' ? attempt.close.slice() : attempt.error.slice();
    var payload = outcome==='completed'||outcome==='cancelled' ? {isEnded:outcome==='completed'} : {errorCode:'SIM_'+outcome.toUpperCase(),errMsg:'Local ad simulation: '+outcome};
    handlers.forEach(function(fn){try{fn(payload);}catch(e){attempt.record.callbackError=String(e);}});
    // Observe actual business writes after callbacks; never add currency or write a save here.
    setTimeout(function(){attempt.record.after=snapshot();attempt.record.changes=changes(attempt.record.before,attempt.record.after);attempt.record.rewardVerdict='manual-check-required';},350);
    return true;
  }
  function create(opts) {
    var close=[],error=[],load=[],used=false,destroyed=false;
    function on(list,fn){if(typeof fn==='function'&&list.indexOf(fn)<0)list.push(fn);}
    function off(list,fn){if(!fn)list.splice(0);else{var i=list.indexOf(fn);if(i>=0)list.splice(i,1);}}
    return {
      onClose:function(fn){on(close,fn);}, offClose:function(fn){off(close,fn);},
      onError:function(fn){on(error,fn);}, offError:function(fn){off(error,fn);},
      onLoad:function(fn){on(load,fn);}, offLoad:function(fn){off(load,fn);},
      load:function(){return Promise.resolve().then(function(){load.slice().forEach(function(fn){fn();});});},
      show:function(){
        if(destroyed||used||active)return Promise.reject({errorCode:'SIM_BUSY_OR_USED',errMsg:'Simulation instance unavailable'});
        used=true;
        var record={simulation:true,id:++serial,entry:root.__adSimulator.entry||'未标注入口，请按实际按钮核对',adUnitId:opts&&opts.adUnitId||'',startedAt:Date.now(),before:snapshot()};
        records.push(record);
        active={record:record,entry:record.entry,adUnitId:record.adUnitId,close:close,error:error};present(active);
        return Promise.resolve(); // Display only; reward requires an explicit complete action.
      },
      destroy:function(){if(active&&active.close===close)finish(active,'cancelled');destroyed=true;close.splice(0);error.splice(0);load.splice(0);}
    };
  }
  root.__adSimulator={version:1,entry:'',records:records,createRewardedVideoAd:create,
    observe:function(fn){if(typeof fn!=='function')throw Error('state reader required');observer=fn;},
    label:function(name){root.__adSimulator.entry=String(name);},
    finish:function(outcome){if(['completed','cancelled','failed','no-fill'].indexOf(outcome)<0)throw Error('unknown simulation outcome');return active?finish(active,outcome):false;}
  };
  // Preserve unrelated platform methods and refuse to overwrite a real ad implementation.
  var targets=[];
  root.TTMinis=root.TTMinis||{};root.TTMinis.game=root.TTMinis.game||{};targets.push(root.TTMinis.game);
  root.tt=root.tt||{};targets.push(root.tt);
  var existing=targets.some(function(target){return typeof target.createRewardedVideoAd==='function';});
  if(!existing)targets.forEach(function(target){
    target.createRewardedVideoAd=create;
    var originalCanIUse=target.canIUse;
    target.canIUse=function(name){return name==='createRewardedVideoAd'||(typeof originalCanIUse==='function'&&originalCanIUse.call(target,name)===true);};
  });
  else root.__adSimulator.integration='existing-sdk-preserved: bind preview sdkProvider explicitly';
  function initialUI(){if(!document.querySelector('iframe'))ui();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialUI);else initialUI();
})(window);
