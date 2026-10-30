/* Served only by serve_preview.py --ad-simulator; never copy into game builds. */
(function (root) {
  'use strict';
  if (root.__adSimulator || !/^(127\.0\.0\.1|localhost|\[::1\])$/.test(root.location.hostname)) return;
  var active = null, serial = 0, records = [], host, box, badge, observer = null;
  // Optional cases (v7.5, Basil problem 1.2). Simulation only: they change WHEN the SDK answers, never what the
  // game should reward. video60 / video130: the video lasts 60 / 130 s, then the viewer closes it (isEnded true);
  // start16: show() resolves only 16 s after it is called (playback starts late); background: 2 s into playback
  // the app goes to the background for 3 s (onHide, then onShow). Pick with ?adsim=video60,background or
  // __adSimulator.mode('video130'); several may be combined; '' or 'normal' restores the default.
  var MODES = {video60: 60000, video130: 130000, start16: 16000, background: 3000}, modes = {};
  var hideListeners = [], showListeners = [];
  function setModes(value) {
    var next = {};
    String(value || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean).forEach(function (name) {
      if (name === 'normal') return;
      if (!MODES.hasOwnProperty(name)) throw Error('unknown simulation mode: ' + name);
      next[name] = true;
    });
    if (next.video60 && next.video130) throw Error('choose video60 or video130, not both');
    modes = next; return Object.keys(modes);
  }
  try { var query = /[?&]adsim=([^&#]*)/.exec(root.location.search); if (query) setModes(decodeURIComponent(query[1])); } catch (e) { modes = {}; }
  function videoMs() { return modes.video130 ? MODES.video130 : modes.video60 ? MODES.video60 : 0; }
  function lifecycle(kind, record) {
    record[kind === 'hide' ? 'hiddenAt' : 'shownAt'] = Date.now();
    (kind === 'hide' ? hideListeners : showListeners).slice().forEach(function (fn) { try { fn({}); } catch (e) { record.lifecycleError = String(e); } });
    try { if (root.cc && root.cc.game && root.cc.game.emit) root.cc.game.emit(kind === 'hide' ? root.cc.game.EVENT_HIDE : root.cc.game.EVENT_SHOW); } catch (e) { record.lifecycleError = String(e); }
  }
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
    var picker = document.createElement('p'); picker.textContent = '下一次广告的可选情况（当前：' + (Object.keys(modes).join(', ') || '普通') + '）：'; box.appendChild(picker);
    [['普通', ''], ['视频 60 秒', 'video60'], ['视频 130 秒', 'video130'], ['16 秒后才开始播放', 'start16'], ['播放中切后台再回来', 'background']].forEach(function (m) {
      box.appendChild(button(m[0], function () { setModes(m[1] && modes[m[1]] ? Object.keys(modes).filter(function (k) { return k !== m[1]; }).join(',') : m[1] ? Object.keys(modes).filter(function (k) { return !(m[1].indexOf('video') === 0 && k.indexOf('video') === 0); }).concat(m[1]).join(',') : ''); history(); }));
    });
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
    var length = videoMs(), unlock = length || 2000;
    var complete = button(length ? '视频 ' + length / 1000 + ' 秒 · 播完后自动关闭（isEnded=true）' : '模拟看完 · 2 秒后可点', function () { finish(attempt, 'completed'); }); complete.disabled=true; actions.appendChild(complete);
    attempt.timer = setTimeout(function () {
      if (length) { finish(attempt, 'completed'); return; }
      complete.disabled=false; complete.textContent='模拟看完（应发一次奖励）';
    }, unlock);
    if (modes.background) {
      attempt.hideTimer = setTimeout(function () {
        if (active !== attempt) return;
        lifecycle('hide', attempt.record);
        attempt.showTimer = setTimeout(function () { if (active === attempt) lifecycle('show', attempt.record); }, MODES.background);
      }, 2000);
    }
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
    clearTimeout(attempt.timer); clearTimeout(attempt.hideTimer); clearTimeout(attempt.showTimer); // startTimer keeps running: a late start after give-up is part of start16
    if (attempt.record.hiddenAt && !attempt.record.shownAt) lifecycle('show', attempt.record);
    active=null; attempt.record.outcome=outcome; attempt.record.finishedAt=Date.now();
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
        var record={simulation:true,id:++serial,entry:root.__adSimulator.entry||'未标注入口，请按实际按钮核对',adUnitId:opts&&opts.adUnitId||'',modes:Object.keys(modes),startedAt:Date.now(),before:snapshot()};
        records.push(record);
        var attempt={record:record,entry:record.entry,adUnitId:record.adUnitId,close:close,error:error};active=attempt;
        if(!modes.start16){present(attempt);return Promise.resolve();} // Display only; reward requires an explicit complete action.
        // start16: playback (and the show() promise) starts only 16 s later. If the game gave up and destroyed the
        // ad meanwhile, the promise still resolves late and its listeners are gone: a late start must never grant.
        ui(); badge.textContent='广告模拟 · 16 秒后才开始播放…';
        return new Promise(function(resolve){
          attempt.startTimer=setTimeout(function(){
            record.playbackStartedAt=Date.now();
            if(active===attempt)present(attempt);else record.lateStartAfterFinish=true;
            resolve();
          },MODES.start16);
        });
      },
      destroy:function(){if(active&&active.close===close)finish(active,'cancelled');destroyed=true;close.splice(0);error.splice(0);load.splice(0);}
    };
  }
  root.__adSimulator={version:1,entry:'',records:records,createRewardedVideoAd:create,
    observe:function(fn){if(typeof fn!=='function')throw Error('state reader required');observer=fn;},
    label:function(name){root.__adSimulator.entry=String(name);},
    mode:function(value){return setModes(value);}, modes:function(){return Object.keys(modes);},
    finish:function(outcome){if(['completed','cancelled','failed','no-fill'].indexOf(outcome)<0)throw Error('unknown simulation outcome');return active?finish(active,outcome):false;}
  };
  // background mode: listeners the game registers with onHide/onShow are called by the simulation; an existing
  // implementation is kept and still receives the registration.
  function wrapLifecycle(target){
    [['onHide',hideListeners],['onShow',showListeners]].forEach(function(pair){
      var original=target[pair[0]],list=pair[1],offName='off'+pair[0].slice(2),originalOff=target[offName];
      target[pair[0]]=function(fn){if(typeof fn==='function'&&list.indexOf(fn)<0)list.push(fn);if(typeof original==='function')return original.apply(target,arguments);};
      target[offName]=function(fn){var i=list.indexOf(fn);if(i>=0)list.splice(i,1);if(typeof originalOff==='function')return originalOff.apply(target,arguments);};
    });
  }
  // Preserve unrelated platform methods and refuse to overwrite a real ad implementation.
  var targets=[];
  root.TTMinis=root.TTMinis||{};root.TTMinis.game=root.TTMinis.game||{};targets.push(root.TTMinis.game);
  root.tt=root.tt||{};targets.push(root.tt);
  var existing=targets.some(function(target){return typeof target.createRewardedVideoAd==='function';});
  if(!existing)targets.forEach(function(target){
    target.createRewardedVideoAd=create;
    wrapLifecycle(target);
    var originalCanIUse=target.canIUse;
    target.canIUse=function(name){return name==='createRewardedVideoAd'||(typeof originalCanIUse==='function'&&originalCanIUse.call(target,name)===true);};
  });
  else root.__adSimulator.integration='existing-sdk-preserved: bind preview sdkProvider explicitly';
  function initialUI(){if(!document.querySelector('iframe'))ui();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialUI);else initialUI();
})(window);
