"use strict";
// WebP decode check for Cocos Creator 3.8.8 on the TikTok native runtime.
//
// The engine decides WebP support at startup with a LOSSY 1x1 sample, the
// img.onload / img.onerror properties and a 500 ms limit. Every image in this
// game is LOSSLESS WebP (VP8L, alpha) with no PNG fallback, so a wrong "false"
// makes the texture loader skip every image and the game shows blank pages.
//
// This check decodes a lossless sample with the same SDK image object the
// engine's image loader uses (tt.createImage), listens with addEventListener
// like that loader does, and keeps the onload/onerror properties as a fallback.
// It settles exactly once: decoded, error, zero size, timeout or SDK throw.
// A failed or timed-out decode is never reported as supported.
//
// Remake Skill v7.5 platform-kit reference (from LunasJade v0.10.1, 待真机复测 - not scanned on a phone yet):
// the data: URI fallback of the original was removed (Mabel's Meadow rule: decode a real .webp file shipped in
// the main package, never a data: URI). Ship webp-check.webp next to this file in the main package.

// Decode one image source with sdk.createImage. done(ok, reason, image) is called once.
function decode(sdk, src, timeoutMs, done) {
  var settled = false, timer = null, img = null;
  function detach() {
    if (!img) return;
    try { if (typeof img.removeEventListener === 'function') { img.removeEventListener('load', onLoad); img.removeEventListener('error', onError); } } catch (e) {}
    try { img.onload = null; img.onerror = null; } catch (e) {}
  }
  function finish(ok, reason) {
    if (settled) return;
    settled = true;
    if (timer !== null) { clearTimeout(timer); timer = null; }
    detach();
    done(!!ok, reason, ok ? img : null);
  }
  function onLoad() {
    var w = img ? img.width : 0, h = img ? img.height : 0;
    if (w > 0 && h > 0) finish(true, 'decoded'); else finish(false, 'zero-size');
  }
  function onError() { finish(false, 'error'); }
  try {
    if (!sdk || typeof sdk.createImage !== 'function') { finish(false, 'no-createImage'); return; }
    img = sdk.createImage();
    if (typeof img.addEventListener === 'function') {
      img.addEventListener('load', onLoad);
      img.addEventListener('error', onError);
    }
    img.onload = onLoad;
    img.onerror = onError;
    timer = setTimeout(function () { finish(false, 'timeout'); }, timeoutMs);
    img.src = src;
  } catch (e) {
    finish(false, 'throws');
  }
}
exports.decode = decode;

// The 2x2 lossless WebP sample with alpha (VP8L, 48 bytes) shipped as a package
// file, so the check loads a local file path exactly like the engine's texture loader does.
var SAMPLE_FILE = 'webp-check.webp';
exports.SAMPLE_FILE = SAMPLE_FILE;

// Run the WebP check unless the engine already found WebP decodable.
// WebP counts as decodable only if the package file really decodes.
// done(decodable, reason) is called once.
exports.check = function (cc, sdk, timeoutMs, done) {
  var feature = cc && cc.sys && cc.sys.Feature ? cc.sys.Feature.WEBP : undefined;
  if (feature !== undefined && cc.sys.hasFeature(feature)) { done(true, 'engine'); return; }
  decode(sdk, SAMPLE_FILE, timeoutMs, function (ok, reason) { done(ok, reason + ':file'); });
};

// Tell the engine WebP decodes. Only ever turns the engine's "false" into "true"
// after a real decode; it never turns an engine "true" into "false".
// Texture2D picks image formats through cc.sys.hasFeature(cc.sys.Feature.WEBP).
exports.apply = function (cc, decodable) {
  var sys = cc && cc.sys;
  if (!sys || !sys.Feature || sys.Feature.WEBP === undefined) return false;
  var feature = sys.Feature.WEBP;
  if (!sys.__ljjWebpPatched) {
    var original = sys.hasFeature;
    sys.hasFeature = function (f) {
      if (f === feature && sys.__ljjWebpDecodes === true) return true;
      return original.call(this, f);
    };
    sys.__ljjWebpPatched = true;
  }
  sys.__ljjWebpDecodes = !!decodable;
  var result = sys.hasFeature(feature);
  if (sys.capabilities) sys.capabilities.webp = result;
  return result;
};
