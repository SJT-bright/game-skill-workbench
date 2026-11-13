// Explicit producer-only deterministic VM inputs. Standalone probes keep real defaults.
module.exports = function probeClock(env = process.env) {
  if (env.COCOS_REWARD_PROBE_NOW_MS === undefined) return {Date, Math};
  const epoch = Number(env.COCOS_REWARD_PROBE_NOW_MS);
  if (!Number.isSafeInteger(epoch) || epoch < 0) throw Error('Invalid reward probe clock');
  const RealDate = Date;
  function FixedDate(...args) {
    if (!new.target) return new RealDate(epoch).toString();
    return new RealDate(...(args.length ? args : [epoch]));
  }
  Object.setPrototypeOf(FixedDate, RealDate);
  FixedDate.prototype = RealDate.prototype;
  FixedDate.now = () => epoch;
  const seeded = Object.create(Math);
  let state = Number(env.COCOS_REWARD_PROBE_SEED || '1');
  if (!Number.isSafeInteger(state) || state < 0 || state > 0xffffffff) throw Error('Invalid reward probe seed');
  seeded.random = () => ((state = (Math.imul(state, 1664525) + 1013904223) >>> 0) / 0x100000000);
  return {Date: FixedDate, Math: seeded};
};
