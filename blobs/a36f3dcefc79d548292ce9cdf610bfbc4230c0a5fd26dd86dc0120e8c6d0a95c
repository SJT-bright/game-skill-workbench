'use strict';
// Negative-control fixture for tests/res-loader.test.js: the loading half of 甜品消除大师 (Dessert) v11
// assets/scripts/manager/ResMgr.ts (learning library 代码/06_甜品消除大师/英文), loadBundle + loadRes copied as plain JS.
// Only the imports became parameters (assetManager) and Debug.* became no-ops; the control flow is unchanged:
//   - `new Promise(async (resolve, reject) => { bundle = await this.loadBundle(...) ... })`: when the bundle fails the
//     await throws inside the async executor, the outer Promise never settles and the rejection is unhandled;
//   - no timer: a load whose callback never comes never settles; an error is never retried.
// Census evidence: all_occurrences.jsonl 04:107 (原 v11 资源加载失败时 ResMgr 不闭合，重试矩阵 6/9，3 个 unhandled rejection).
function make(assetManager) {
  var Debug = { Log: function () {}, Warn: function () {}, Error: function () {} };
  var Tag = 'ResMgr';
  var ResMgr = {
    loadBundle: function (Bundle, onComplete) {
      return new Promise(function (resolve, reject) {
        if (assetManager.getBundle(Bundle)) {
          Debug.Warn(Tag, 'already loaded');
          resolve(assetManager.getBundle(Bundle));
        } else {
          assetManager.loadBundle(Bundle, function (err, bundle) {
            if (err) {
              Debug.Error(Tag, 'bundle failed ' + err);
              reject(err);
            } else {
              onComplete && onComplete(bundle);
              resolve(bundle);
            }
          });
        }
      });
    },
    loadRes: function (Bundle, resName, relative_path) {
      var self = this;
      relative_path = relative_path || '';
      return new Promise(async function (resolve, reject) {
        var path = relative_path + resName;
        var bundle = assetManager.getBundle(Bundle);
        if (!bundle) {
          bundle = await self.loadBundle(Bundle);
        }
        bundle.load(path, function (err, asset) {
          if (err) {
            Debug.Error(Tag, 'load failed ' + err);
            reject(err);
          } else {
            resolve(asset);
          }
        });
      });
    }
  };
  return ResMgr;
}
module.exports = { make: make };
