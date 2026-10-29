'use strict';
// Public shared-test configuration only. Backend activation is unverified.
var config = {
  profile: 'felix-shared-test', applicationMode: 'shared-test',
  appId: '7683427172773644296', clientKey: 'mgq7o8c3rbhdx2kv',
  rewardedPlacements: [
    {name: 'Rewarded 2', id: 'ad7683064432721709074'},
    {name: 'Rewarded', id: 'ad7683076047361067016'},
    {name: 'Rewarded', id: 'ad7683199506230233095'}
  ],
  placementMap: {
    revive: 0, revive_coins: 0, skill_coins: 0, start_shield: 0, shield: 0,
    prop_chest: 1, timed_skin_normal: 1, timed_skin_rare: 1,
    skin_coins: 1, skin_help_coins: 1, unlock_background: 1,
    result_double_coins: 2, daily_double: 2, welfare_coins: 2,
    fortune_card: null // Removed in the approved plan; never request this placement.
  }
};
config.getAdUnitId = function (key) {
  var index = config.placementMap[key];
  return typeof index === 'number' && config.rewardedPlacements[index] ? config.rewardedPlacements[index].id : '';
};
module.exports = config;
