'use strict';
// TikTok Platform Kit v1.1 (Cocos 2.4.15) - the ONLY file each game edits.
// Every other file in assets/tiktok-platform/ and build-templates/bytedance/ is copied unchanged.
//
// gameId: lowercase English, unique per game. It prefixes the save key so games that share the
//         test App ID never share coins or reward claims.
// placementMap: placementKey -> index into rewardedPlacements. Add the keys this game uses;
//         a key that is missing (or null) returns '' and RewardedService answers 'unconfigured'.
var config = {
  kitVersion: 1.1,
  gameId: 'change-me',
  appId: '7683427172773644296',
  clientKey: 'mgq7o8c3rbhdx2kv',
  rewardedPlacements: [
    {name: 'Rewarded 2', id: 'ad7683064432721709074'},
    {name: 'Rewarded', id: 'ad7683076047361067016'},
    {name: 'Rewarded', id: 'ad7683199506230233095'}
  ],
  placementMap: {
    revive: 0, hint: 0, start_boost: 0,
    skin: 1, background: 1,
    double_coins: 2, gift: 2
  }
};
config.getAdUnitId = function (key) {
  var index = config.placementMap[key];
  return typeof index === 'number' && config.rewardedPlacements[index] ? config.rewardedPlacements[index].id : '';
};
config.saveKey = function () {
  return config.gameId + ':' + config.appId + ':save:v1';
};
module.exports = config;
