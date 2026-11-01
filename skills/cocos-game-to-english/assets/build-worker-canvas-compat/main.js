'use strict';
// Only the editor's asset serialization worker uses Canvas. Nothing is injected into game assets or exports.
var previous, wrappedSpawn;
module.exports = {
  load: function () {
    if (process.platform !== 'darwin') {
      Editor.log('Build-worker Canvas compatibility is only enabled on macOS.');
      return;
    }
    var version;
    try { version = require('electron').app.getVersion(); }
    catch (error) { Editor.warn('Could not determine Creator version; build-worker compatibility is disabled.', error); return; }
    if (version !== '2.4.3') {
      Editor.log('Build-worker Canvas compatibility is only needed for Creator 2.4.3; disabled for ' + version + '.');
      return;
    }
    if (wrappedSpawn && Editor.App.spawnWorker === wrappedSpawn) return;
    previous = Editor.App.spawnWorker;
    var originalSpawn = previous;
    wrappedSpawn = function (url, callback) {
      var rest = Array.prototype.slice.call(arguments, 2);
      var wrapped = function (worker, window) {
        if (String(url).indexOf('editor/page/build/build-worker') >= 0) {
          var send = worker.send;
          worker.send = function (channel) {
            var self = this, args = Array.prototype.slice.call(arguments);
            if (channel !== 'app:init-build-worker') return send.apply(self, args);
            var settled = false;
            var timer;
            function fail(error) {
              if (settled) return;
              settled = true; clearTimeout(timer);
              Editor.error('Could not initialize the project build-worker compatibility', error);
              var reply = args[args.length - 1];
              try { if (typeof reply === 'function') reply(error); }
              catch (callbackError) { Editor.error('Build-worker failure callback threw', callbackError); }
              // This is the dedicated, agent-created build worker window, never a scene editor or preview.
              try {
                if (worker.nativeWin && !worker.nativeWin.isDestroyed()) worker.nativeWin.close();
              } catch (closeError) { Editor.error('Could not close the failed build worker', closeError); }
            }
            var script = '(' + function () {
              var originalRequire = Editor.require;
              Editor.require = function (path) {
                var value = originalRequire.apply(this, arguments);
                if (path === 'unpack://engine-dev' && !cc.game.__assetWorkerCanvasCompatibility) {
                  cc.game.__assetWorkerCanvasCompatibility = true;
                  var run = cc.game.run;
                  cc.game.run = function (options, ready) {
                    options = Object.assign({}, options, {renderMode: 1});
                    console.log('BUILD_WORKER_CANVAS_COMPAT: original engine, asset worker only');
                    return run.call(this, options, ready);
                  };
                }
                return value;
              };
            }.toString() + ')();';
            timer = setTimeout(function () { fail(new Error('Build-worker compatibility initialization timed out')); }, 10000);
            try {
              var wc = worker.nativeWin.webContents;
              Promise.resolve(wc.executeJavaScript(script)).then(function () {
                if (settled) return;
                settled = true; clearTimeout(timer);
                try { send.apply(self, args); }
                catch (error) {
                  // Forwarding can throw synchronously too; allow the same one-time failure path.
                  settled = false; fail(error);
                }
              }, fail);
            } catch (error) { fail(error); }
          };
        }
        if (typeof callback === 'function') return callback.apply(this, arguments);
      };
      return originalSpawn.apply(this, [url, wrapped].concat(rest));
    };
    Editor.App.spawnWorker = wrappedSpawn;
    Editor.log('Project-local build-worker Canvas compatibility loaded; exported renderer unchanged.');
  },
  unload: function () {
    if (wrappedSpawn && Editor.App.spawnWorker === wrappedSpawn) Editor.App.spawnWorker = previous;
    wrappedSpawn = null;
  }
};
