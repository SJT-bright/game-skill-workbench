/* Preview-only passive Web audio observer. No play/start/resume/unlock is initiated here. */
(function (w) {
  'use strict';
  if (w.__webAudioStartupSnapshot) return;
  var installedWithEngine = !!(w.cc && w.cc.game), gestures = 0, nextId = 0;
  var media = new Map(), sources = new Map(), edges = new Map(), mediaNodes = new WeakMap();
  var bufferIds = new WeakMap(), errors = [], capabilities = {};
  function finite(x) { return typeof x === 'number' && Number.isFinite(x); }
  function id(prefix) { return prefix + (++nextId); }
  function fail(where, error) { if (errors.length < 12) errors.push(where + ': ' + String(error && error.message || error)); }
  function wrap(proto, name, make) {
    if (!proto || typeof proto[name] !== 'function') return false;
    try { var old = proto[name]; proto[name] = make(old); return proto[name] !== old; }
    catch (error) { fail(name, error); return false; }
  }
  function input(event) { if (event && event.isTrusted && !event.repeat) gestures++; }
  w.addEventListener(w.PointerEvent ? 'pointerdown' : 'touchstart', input, true);
  if (!w.PointerEvent) w.addEventListener('mousedown', input, true);
  w.addEventListener('keydown', input, true);

  function mediaRecord(element) {
    var r = media.get(element);
    if (!r) { r = {id:id('media-'), element:element, requested:false, intent:false, gesture:null, error:null}; media.set(element, r); }
    return r;
  }
  capabilities.media = wrap(w.HTMLMediaElement && w.HTMLMediaElement.prototype, 'play', function (old) {
    return function () {
      var r = mediaRecord(this); r.gesture = gestures; r.intent = true; r.requested = false; r.error = null;
      try { var value = old.apply(this, arguments); r.requested = true; return value; }
      catch (error) { r.intent = false; r.error = String(error && error.name || error); throw error; }
    };
  });
  wrap(w.HTMLMediaElement && w.HTMLMediaElement.prototype, 'pause', function (old) {
    return function () { var value = old.apply(this, arguments); mediaRecord(this).intent = false; return value; };
  });

  capabilities.connect = wrap(w.AudioNode && w.AudioNode.prototype, 'connect', function (old) {
    return function (destination, output, inputIndex) {
      var value = old.apply(this, arguments), list = edges.get(this) || [];
      list.push({to:destination, output:output || 0, input:inputIndex || 0}); edges.set(this, list); return value;
    };
  });
  capabilities.disconnect = wrap(w.AudioNode && w.AudioNode.prototype, 'disconnect', function (old) {
    return function (destination, output, inputIndex) {
      var value = old.apply(this, arguments), count = arguments.length, list = edges.get(this) || [];
      if (!count) list = [];
      else if (typeof destination === 'number') list = list.filter(function (e) { return e.output !== destination; });
      else list = list.filter(function (e) {
        return e.to !== destination || count > 1 && e.output !== output || count > 2 && e.input !== inputIndex;
      });
      edges.set(this, list); return value;
    };
  });
  function contextPrototype(name) {
    var ctor = w[name]; return ctor && ctor.prototype;
  }
  var contexts = [contextPrototype('AudioContext'), contextPrototype('webkitAudioContext')].filter(Boolean);
  var seenMethods = new Set(), mediaRoutingObserved = true;
  contexts.forEach(function (proto) {
    var owner = proto;
    while (owner && !Object.prototype.hasOwnProperty.call(owner, 'createMediaElementSource')) owner = Object.getPrototypeOf(owner);
    if (!owner) { mediaRoutingObserved = false; return; }
    if (seenMethods.has(owner)) return; seenMethods.add(owner);
    var observed = wrap(owner, 'createMediaElementSource', function (old) {
      return function (element) { var node = old.apply(this, arguments); mediaNodes.set(element, node); return node; };
    });
    mediaRoutingObserved = mediaRoutingObserved && observed;
  });
  capabilities.mediaRouting = mediaRoutingObserved;
  function bufferKey(buffer) {
    if (!buffer) return null;
    if (!bufferIds.has(buffer)) bufferIds.set(buffer, id('buffer-'));
    return bufferIds.get(buffer);
  }
  function sourceRecord(node) {
    var r = sources.get(node);
    if (!r) {
      r = {id:id('source-'), node:node, started:false, gesture:null, startAt:null, stopAt:null, endAt:null, ended:false, error:null};
      sources.set(node, r);
      node.addEventListener('ended', function () { r.ended = true; });
    }
    return r;
  }
  capabilities.webaudio = wrap(w.AudioBufferSourceNode && w.AudioBufferSourceNode.prototype, 'start', function (old) {
    return function (when, offset, duration) {
      var r = sourceRecord(this), at = this.context.currentTime;
      try {
        var value = old.apply(this, arguments);
        r.started = true; r.gesture = gestures; r.startAt = Math.max(finite(when) ? when : 0, at);
        r.endAt = finite(duration) ? r.startAt + duration / (this.playbackRate.value || 1) : null;
        r.buffer = bufferKey(this.buffer); return value;
      } catch (error) { r.error = String(error && error.name || error); throw error; }
    };
  });
  capabilities.webaudioStop = wrap(w.AudioBufferSourceNode && w.AudioBufferSourceNode.prototype, 'stop', function (old) {
    return function (when) {
      var value = old.apply(this, arguments), r = sourceRecord(this);
      r.stopAt = Math.max(finite(when) ? when : 0, this.context.currentTime); return value;
    };
  });
  function route(node, context, seen) {
    if (node === context.destination) return {known:true, gain:1};
    if (seen.has(node)) return {known:false, gain:0};
    var visited = new Set(seen); visited.add(node);
    var ownGain = 1;
    if (node !== seen.root) {
      if (!w.GainNode || !(node instanceof w.GainNode)) return {known:false, gain:0};
      ownGain = node.gain.value;
      if (!finite(ownGain)) return {known:false, gain:0};
    }
    var best = {known:false, gain:0};
    (edges.get(node) || []).forEach(function (edge) {
      var branch = new Set(visited); branch.root = seen.root;
      var found = route(edge.to, context, branch);
      if (found.known && (!best.known || Math.abs(found.gain * ownGain) > Math.abs(best.gain))) best = {known:true, gain:found.gain * ownGain};
    });
    return best;
  }
  function output(node) {
    var seen = new Set(); seen.root = node;
    return route(node, node.context, seen);
  }
  function snapMedia(r) {
    var e = r.element, node = mediaNodes.get(e), path = node ? output(node) : {known:true, gain:1};
    var state = node ? node.context.state : null, contextTime = node ? node.context.currentTime : null;
    return {kind:'html_media', id:r.id, src:e.currentSrc || e.src || null, loop:e.loop === true,
      requested:r.requested, requestGesture:r.gesture, intent:r.intent && !e.ended,
      paused:e.paused, ended:e.ended, muted:e.muted, volume:e.muted ? 0 : e.volume * Math.abs(path.gain),
      currentTime:e.currentTime, duration:e.duration, playbackRate:e.playbackRate,
      routedThroughWebAudio:!!node,
      routeKnown:path.known && capabilities.mediaRouting && (!node || capabilities.connect && capabilities.disconnect), routeGain:path.gain,
      contextState:state, contextTime:contextTime, error:r.error};
  }
  function snapSource(r) {
    var n = r.node, c = n.context, time = c.currentTime, path = output(n), rate = n.playbackRate.value;
    var stopped = r.stopAt !== null && time >= r.stopAt;
    var expired = r.endAt !== null && time >= r.endAt;
    var active = r.started && !r.ended && !stopped && !expired && time >= r.startAt;
    return {kind:'webaudio', id:r.id, src:r.buffer, loop:n.loop === true, requested:r.started,
      requestGesture:r.gesture, intent:r.started && !r.ended && !stopped && !expired,
      started:r.started, active:active, paused:!active || c.state !== 'running', ended:r.ended,
      stopped:stopped, startAt:r.startAt, stopAt:r.stopAt, endAt:r.endAt,
      muted:Math.abs(path.gain) === 0, volume:Math.abs(path.gain), routeGain:path.gain,
      routeKnown:path.known && capabilities.connect && capabilities.disconnect && capabilities.webaudioStop,
      currentTime:time, contextTime:time, contextState:c.state, playbackRate:rate,
      duration:n.buffer && n.buffer.duration || 0, hasBuffer:!!n.buffer, error:r.error};
  }
  w.__webAudioStartupSnapshot = function () {
    var tracks = [].concat(Array.from(media.values()).map(snapMedia), Array.from(sources.values()).map(snapSource));
    return {schema:'preview-audio-startup.v1', environment:'browser_web_export', gestures:gestures,
      installedWithEngine:installedWithEngine, capabilities:capabilities, observerErrors:errors.slice(),
      autoRequests:tracks.filter(function (t) { return t.requested && t.requestGesture === 0 && t.loop; }).length,
      tracks:tracks};
  };
})(window);
