// PageRegistry (总表 P19 ①): every popup()/open() of the dev build records the page it showed, so the page list the
// checks read comes from what the game really opens, not from what someone remembered to type in.
//
// Hook (A2 批 adds it to GameUIKit.js; this file only holds the record function):
//   var PageRegistry = require('PageRegistry');
//   // at the end of UI.popup(parent, opts) and of each page template's open():
//   PageRegistry.record({id: opts.pageId, name: opts.pageName, kind: 'popup', node: PageRegistry.pathOf(panel),
//                        close: closeNode && PageRegistry.pathOf(closeNode),
//                        buttons: buttonNodes.map(PageRegistry.pathOf), ad: adNodes.map(PageRegistry.pathOf)});
//
// Read back: remake-core/scripts/ui_dump.js returns window.__pageRegistry.list() as "pages" in every dump;
// page_registry.py merge-dumps marks those pages seen_at_runtime in docs/logic/pages.json and lists pages the game
// opened that pages.json does not have. Release builds: record() does nothing unless CC_DEBUG or
// window.__QA_PAGES is true, and it never throws (a broken record must not break a popup).
(function (root) {
  var store = {};
  var order = [];

  function enabled() {
    try {
      if (typeof CC_DEBUG !== 'undefined' && CC_DEBUG) return true;
    } catch (e) { /* not a Cocos build */ }
    return !!(root && root.__QA_PAGES);
  }

  function pathOf(node) {
    var names = [];
    try {
      for (var n = node; n && n.parent; n = n.parent) names.unshift(n.name);
    } catch (e) { return ''; }
    return names.join('/');
  }

  function list() {
    return order.map(function (id) { return store[id]; });
  }

  function record(info) {
    if (!enabled() || !info) return null;
    try {
      var id = String(info.id || info.name || info.node || '').trim();
      if (!id) return null;
      var row = store[id];
      if (!row) {
        row = store[id] = {id: id, name: info.name || id, kind: info.kind || 'popup', node: info.node || '',
          close: info.close || null, buttons: [], ad: [], opened: 0};
        order.push(id);
      }
      row.opened += 1;
      ['buttons', 'ad'].forEach(function (key) {
        (info[key] || []).forEach(function (p) { if (p && row[key].indexOf(p) < 0) row[key].push(p); });
      });
      if (info.close) row.close = info.close;
      return row;
    } catch (e) {
      return null;
    }
  }

  var api = {record: record, list: list, pathOf: pathOf, reset: function () { store = {}; order = []; }};
  if (root) root.__pageRegistry = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null));
