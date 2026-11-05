"use strict";
// Native SDK contracts: developers.tiktok.com/docs/en/mini-games-sdk-iaa
// One module-wide transport lease prevents overlap across UI/service instances.
var active = null, sequence = 0, logCount = 0;
function resolveSDK(methods, capability) {
    var providers = [function () { return typeof TTMinis !== "undefined" && TTMinis.game; },
        function () { return typeof tt !== "undefined" && tt; },
        function () { return typeof wx !== "undefined" && wx; }];
    for (var i = 0; i < providers.length; i++) {
        try {
            var api = providers[i]();
            if (!api || !methods.every(function (m) { return typeof api[m] === "function"; })) continue;
            if (capability && (typeof api.canIUse !== "function" || !methods.every(function (m) { return api.canIUse(m) === true; }))) continue;
            return api;
        } catch (_) { /* Broken optional namespaces cannot hide later providers. */ }
    }
    return null;
}
function diagnostic(stage, id, error) {
    if (logCount++ >= 32) return;
    var code;
    try { code = error && (error.errorCode || error.errCode || error.code); } catch (_) {}
    if (typeof code !== "number" && !(typeof code === "string" && /^-?\d{1,10}$/.test(code))) code = undefined;
    console.info("[hex-ad]", stage, id, code === undefined ? "" : code);
}
function rewarded(adUnitId, options) {
    options = options || {};
    var set = options.setTimeout || setTimeout, clear = options.clearTimeout || clearTimeout;
    var resolve, promise = new Promise(function (r) { resolve = r; });
    var ad, timer, done = false, terminal = false, started = false;
    var session = { id: ++sequence };
    function finish(status, completed) {
        if (done) return;
        done = true; clear(timer);
        var callback = resolve; resolve = null;
        diagnostic(status, session.id);
        callback({ status: status, completed: completed === true,
            receipt: completed === true ? "video:" + Date.now() + ":" + session.id : null });
    }
    function release() {
        if (terminal) return;
        terminal = true; clear(timer);
        if (active === session) active = null;
        try { if (ad && ad.offClose) ad.offClose(close); } catch (_) {}
        try { if (ad && ad.offError) ad.offError(error); } catch (_) {}
    }
    function close(result) {
        if (terminal) return;
        var complete = false;
        try { complete = started && result && result.isEnded === true; } catch (_) {}
        release(); finish(complete ? "completed" : "cancelled", complete);
    }
    function error(value) {
        if (terminal) return;
        diagnostic("sdk-error", session.id, value);
        release(); finish("failed", false);
    }
    function cancel() {
        if (done) return;
        if (!started) release();
        // Cancelling business/UI cannot close the native video. Retain its lease
        // and only the terminal listeners until close/onError/show rejection.
        finish("cancelled", false);
    }
    if (active) { finish("busy", false); return { promise: promise, cancel: cancel }; }
    var api = (options.resolveSDK || resolveSDK)(["createRewardedVideoAd"]);
    if (!api || !adUnitId) { finish("unavailable", false); return { promise: promise, cancel: cancel }; }
    active = session;
    try {
        ad = api.createRewardedVideoAd({ adUnitId: adUnitId });
        if (!ad || !["show", "onClose", "offClose", "onError", "offError"].every(function (m) { return typeof ad[m] === "function"; })) throw Error("Unsupported ad instance");
        ad.onClose(close);
        if (!terminal && !done) ad.onError(error);
        if (!terminal && !done) {
            started = true;
            timer = set(function () { finish("timeout", false); }, options.timeoutMs || 180000);
            diagnostic("show", session.id);
            // A resolved show promise is display acknowledgement, never reward.
            Promise.resolve(ad.show()).catch(error);
        }
    } catch (e) { error(e); }
    return { promise: promise, cancel: cancel };
}
function Growth(provider, deadline) { this.provider = provider || resolveSDK; this.deadline = deadline || 15000; this.pending = {}; }
Growth.prototype.call = function (method, reward) {
    var self = this;
    if (self.pending[method]) return Promise.resolve({ status: "busy" });
    var api = self.provider([method], true);
    if (!api) return Promise.resolve({ status: "unavailable" });
    return new Promise(function (resolve) {
        var done = false;
        function finish(value) { if (done) return; done = true; clearTimeout(timer); delete self.pending[method]; resolve(value); }
        var timer = setTimeout(function () { finish({ status: "timeout" }); }, self.deadline);
        self.pending[method] = finish;
        try {
            api[method]({ success: function (r) { finish({ status: reward ? r && r.canReceiveReward === true ? "eligible" : "ineligible" : "done" }); },
                fail: function () { finish({ status: "failed" }); }, complete: function () {} });
        } catch (_) { finish({ status: "failed" }); }
    });
};
Growth.prototype.start = function (kind) { return this.call(kind === "shortcut" ? "addShortcut" : "startEntranceMission", false); };
Growth.prototype.verify = function (kind) { return this.call(kind === "shortcut" ? "getShortcutMissionReward" : "getEntranceMissionReward", true); };
Growth.prototype.cancel = function () { var self = this; Object.keys(self.pending).forEach(function (k) { self.pending[k]({ status: "cancelled" }); }); };
module.exports = { resolveSDK: resolveSDK, rewarded: rewarded, Growth: Growth };
