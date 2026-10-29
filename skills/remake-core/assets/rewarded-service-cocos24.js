// HISTORICAL SNAPSHOT ONLY: not approved for direct reuse. cancel/timeout do not
// establish native-session termination. Apply current AD-02/03/04 gates first.
"use strict";

// Official contracts: https://developers.tiktok.com/docs/en/mini-games-sdk-iaa
// https://developers.tiktok.com/docs/en/in-app-ads
// Native runtime supplies TTMinis.game. No HTML SDK initialization is needed.
function defaultSDKProvider() {
    return typeof TTMinis !== "undefined" && TTMinis.game ? TTMinis.game : null;
}

function errorCode(error) {
    if (!error) return undefined;
    var code = error.errorCode;
    if (code === undefined) code = error.code;
    if (code === undefined) code = error.error_code;
    if (code === undefined && error.error) code = error.error.error_code;
    return typeof code === "number" || typeof code === "string" ? code : undefined;
}

function result(status, rewarded, error) {
    var value = { status: status, rewarded: rewarded };
    var code = errorCode(error);
    if (code !== undefined) value.code = code;
    return value;
}

function createRewardedService(options) {
    options = options || {};
    var sdkProvider = options.sdkProvider || defaultSDKProvider;
    var schedule = options.setTimeout || setTimeout;
    var unschedule = options.clearTimeout || clearTimeout;
    var timeoutMs = typeof options.timeoutMs === "number" &&
        isFinite(options.timeoutMs) && options.timeoutMs >= 0 ? options.timeoutMs : 180000;
    var active = null;

    function show(adUnitId) {
        if (active) return Promise.resolve(result("busy", false));
        if (typeof adUnitId !== "string" || !adUnitId.trim()) {
            return Promise.resolve(result("unavailable", false));
        }

        var sdk;
        try {
            sdk = sdkProvider();
        } catch (error) {
            return Promise.resolve(result("unavailable", false, error));
        }
        if (!sdk || typeof sdk.createRewardedVideoAd !== "function") {
            return Promise.resolve(result("unavailable", false));
        }

        return new Promise(function (resolve) {
            var ad = null;
            var timer = null;
            var settled = false;
            var attempt = { finish: finish };
            active = attempt;

            function finish(status, rewarded, error) {
                if (settled) return;
                settled = true;
                // Cleanup can throw or trigger another callback; neither may settle twice.
                if (timer !== null) {
                    try { unschedule(timer); } catch (_) {}
                    timer = null;
                }
                try { if (ad && typeof ad.offClose === "function") ad.offClose(onClose); } catch (_) {}
                try { if (ad && typeof ad.offError === "function") ad.offError(onError); } catch (_) {}
                if (active === attempt) active = null;
                resolve(result(status, rewarded, error));
            }

            function onClose(res) {
                var completed = !!(res && res.isEnded === true);
                finish(completed ? "completed" : "cancelled", completed);
            }

            function onError(error) {
                finish("ad_error", false, error);
            }

            try {
                // Instances are single-use; never cache or show an old instance again.
                ad = sdk.createRewardedVideoAd({ adUnitId: adUnitId });
                if (!ad || typeof ad.show !== "function" ||
                    typeof ad.onClose !== "function" || typeof ad.offClose !== "function" ||
                    typeof ad.onError !== "function" || typeof ad.offError !== "function") {
                    finish("create_failed", false);
                    return;
                }
                if (settled) return;
                ad.onClose(onClose);
                if (settled) return;
                ad.onError(onError);
                if (settled) return;
                timer = schedule(function () { finish("timeout", false); }, timeoutMs);
            } catch (error) {
                finish("create_failed", false, error);
                return;
            }

            try {
                // A fulfilled show promise proves display only, never reward eligibility.
                Promise.resolve(ad.show()).catch(function (error) {
                    finish("show_failed", false, error);
                });
            } catch (error) {
                finish("show_failed", false, error);
            }
        });
    }

    function cancel() {
        if (!active) return false;
        active.finish("cancelled", false);
        return true;
    }

    return { show: show, cancel: cancel };
}

module.exports = {
    createRewardedService: createRewardedService,
    isAvailable: function () {
        try {
            var sdk = defaultSDKProvider();
            return !!(sdk && typeof sdk.createRewardedVideoAd === "function");
        } catch (_) { return false; }
    }
};
