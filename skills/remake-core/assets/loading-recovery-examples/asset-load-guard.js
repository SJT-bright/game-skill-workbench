'use strict';
// Settle the real Cocos downloader/parser callback, so its in-flight cache is released.
//
// v7.5 policy (MergeShot2048 v82 local-file policy, 待真机复测 / pending real-device retest):
//  - a package image that has not answered after 10 s of foreground time is requested again; the first answer wins;
//  - an error answer is retried once after 0.5 s;
//  - the image fails only after 30 s of foreground time without any answer, so Cocos releases its in-flight task and
//    the visible Retry starts a fresh request;
//  - byte progress (onFileProgress) resets the clock; time while the game is in the background does not count, and one
//    update() adds at most 1 s, so a long main-thread stall cannot fake a timeout.
// The old 10 s fatal guard without a second request dropped late answers on a real iPhone (MergeShot2048 v81: home
// logo, Add to Home Screen and Profile Revisit images never appeared). package_gates.startup G7 refuses that pattern.
//
// Contract (unchanged): install(root, engine, nativeBeforeAdapter) -> api {progress(), setBackground(hidden), update()};
// call api.update() once per frame and api.setBackground() from the hide/show events.
module.exports = function install(root, engine, nativeBeforeAdapter) {
  if (root.__mosslightImageGuard) return root.__mosslightImageGuard;
  var am = engine && engine.assetManager;
  if (!am || !am.downloader) return null;
  var REISSUE_MS = 10000, GIVE_UP_MS = 30000, ERROR_RETRY_MS = 500, MAX_STEP_MS = 1000, ATTEMPTS = 2;
  var jobs = [], hidden = false, serial = 0, mark = 0;
  var types = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.tiff', '.image', '.webp'];

  var api = {
    progress: function () { return mark; },
    setBackground: function (value) {
      hidden = !!value;
      var now = Date.now();
      jobs.forEach(function (r) { r.last = now; });
    },
    update: function () {
      var now = Date.now();
      jobs.slice().forEach(function (r) {
        var step = Math.min(MAX_STEP_MS, Math.max(0, now - r.last));
        r.last = now;
        if (hidden || r.settled) return;
        r.idle += step;
        if (r.attempts < ATTEMPTS && !r.reissued && r.idle >= REISSUE_MS) {
          r.reissued = true;
          r.start();
        }
        if (r.idle >= GIVE_UP_MS) r.finish(new Error('Image did not answer: ' + r.url), undefined, -1);
      });
    }
  };

  function abort(handle) {
    if (!handle) return;
    try {
      if (typeof handle.abort === 'function') handle.abort();
      else if ('src' in handle) handle.src = '';
    } catch (ignore) {}
  }

  function wrap(raw) {
    return function (url, options, done) {
      if (typeof options === 'function') { done = options; options = {}; }
      options = options || {};
      var self = this;
      var r = {id: ++serial, url: String(url), idle: 0, last: Date.now(), bytes: -1, settled: false,
               attempts: 0, reissued: false, handles: []};
      jobs.push(r);
      mark++;
      r.finish = function (err, value, winner) {
        if (r.settled) return;
        r.settled = true;
        var i = jobs.indexOf(r);
        if (i >= 0) jobs.splice(i, 1);
        r.handles.forEach(function (handle, index) { if (index !== winner) abort(handle); });
        done(err || null, value);
      };
      var opts = {};
      Object.keys(options).forEach(function (k) { opts[k] = options[k]; });
      var progress = opts.onFileProgress;
      opts.onFileProgress = function (a, b) {
        var n = typeof a === 'number' ? a : a && a.totalBytesWritten;
        if (typeof n === 'number' && isFinite(n) && n > r.bytes) { r.bytes = n; r.idle = 0; r.last = Date.now(); mark++; }
        if (progress) progress.apply(this, arguments);
      };
      r.start = function () {
        var mine = r.attempts++;
        try {
          r.handles[mine] = raw.call(self, url, opts, function (err, value) {
            if (r.settled) return;                                  // a late answer after the result was given
            if (!err) { r.finish(null, value, mine); return; }      // first good answer wins
            if (mine !== r.attempts - 1) return;                    // a newer attempt is still running
            if (r.attempts < ATTEMPTS) {
              setTimeout(function () { if (!r.settled) { r.reissued = true; r.start(); } }, ERROR_RETRY_MS);
              return;
            }
            r.finish(err, undefined, mine);
          });
        } catch (e) {
          if (mine === r.attempts - 1 && r.attempts < ATTEMPTS) {
            setTimeout(function () { if (!r.settled) { r.reissued = true; r.start(); } }, ERROR_RETRY_MS);
          } else {
            r.finish(e, undefined, mine);
          }
        }
      };
      r.start();
      return r.handles[0];
    };
  }

  function hook(registry) {
    if (!registry || !registry.register) return;
    var register = registry.register;
    registry.register = function (type, handler) {
      if (typeof type === 'string') return register.call(this, type, types.indexOf(type) >= 0 ? wrap(handler) : handler);
      var map = {};
      Object.keys(type).forEach(function (k) { map[k] = types.indexOf(k) >= 0 ? wrap(type[k]) : type[k]; });
      return register.call(this, map);
    };
  }

  // Do not change Native filesystem/cache handling: wrap the handlers adaptEngine actually registers.
  if (nativeBeforeAdapter) {
    hook(am.downloader);
    hook(am.parser);
  } else {
    // Web: an abortable XHR supplies real byte progress; decode with a fresh Image each attempt.
    var rawDownload = am.downloader.downloadFile;
    var webImage = function (url, opts, done) {
      var image = null, objectURL = null, xhr = null, aborted = false;
      function clearURL() { if (objectURL) { URL.revokeObjectURL(objectURL); objectURL = null; } }
      var handle = {abort: function () {
        aborted = true;
        if (xhr) xhr.abort();
        if (image) { image.onload = image.onerror = null; image.src = ''; }
        clearURL();
      }};
      var options = {};
      Object.keys(opts).forEach(function (k) { options[k] = opts[k]; });
      options.responseType = 'blob';
      xhr = rawDownload(url, options, opts.onFileProgress, function (err, blob) {
        if (aborted) return;
        if (err) return done(err);
        try {
          objectURL = URL.createObjectURL(blob);
          image = new Image();
          image.onload = function () { image.onload = image.onerror = null; clearURL(); done(null, image); };
          image.onerror = function () { image.onload = image.onerror = null; clearURL(); done(new Error('Image decode failed')); };
          image.src = objectURL;
        } catch (e) { clearURL(); done(e); }
      });
      return handle;
    };
    var map = {};
    types.forEach(function (t) { map[t] = wrap(webImage); });
    am.downloader.register(map);
  }

  // Retries belong to the guard above; Cocos' own automatic retries would keep an abandoned attempt alive behind the
  // visible Retry.
  var download = am.downloader.download;
  am.downloader.download = function (id, url, type, options, done) {
    if (types.indexOf(type) >= 0) {
      var opts = {};
      Object.keys(options || {}).forEach(function (k) { opts[k] = options[k]; });
      opts.maxRetryCount = 0;
      options = opts;
    }
    return download.call(this, id, url, type, options, done);
  };
  root.__mosslightImageGuard = api;
  return api;
};
