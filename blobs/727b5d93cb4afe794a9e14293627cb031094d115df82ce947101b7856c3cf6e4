'use strict';

export default {
    bannerAd: null,
    interstitialAd: null,
    videoAd: null,
    recorder: null,
    videoPath: "",
    isVideoLoaded: false,
    isBannerShow: false,
    _onVideoClose: null,
    windowWidth: 100,
    windowHeight: 100,
    conf: {},
    init (conf) {
        this.conf = conf;
    },
    login (success, fail) {

    },
    initAd () {
        console.log("init tt Ad");
        this.createVideoAd();
        // this.createBannerAd();
    },
    createBannerAd () {

    },
    showBannerAd () {
        if (this.conf.banner_posid && tt.createBannerAd) {
            let id = Math.floor(Math.random() * this.conf.banner_posid.length);
            console.log("show tt banner", this.conf.banner_posid[id]);
            const { windowHeight, windowWidth } = tt.getSystemInfoSync();
            let targetBannerAdWidth = 300;
            this.bannerAd = tt.createBannerAd({
                adUnitId: this.conf.banner_posid[id],
                style: {
                    width: targetBannerAdWidth,
                    top: windowHeight - 110, // 根据系统约定尺寸计算出广告高度
                    left: (windowWidth - targetBannerAdWidth) / 2
                }
            });
        }
        let adshow = this.bannerAd.show();
        // 调用then和catch之前需要对show的结果做下判空处理，防止出错（如果没有判空，在平台版本为1052以及以下的手机上将会出现错误）
        adshow && adshow.then(() => {
            console.log("banner广告展示成功");
            // this.isBannerShow = true; this.showToast({     message: "banner广告展示成功" });
            // this.bannerAd.onClose(() => {     this.isBannerShow = false; });
        }).catch((err) => {
            switch (err.code) {
                case 30003:
                    console.log("新用户7天内不能曝光Banner，请将手机时间调整为7天后，退出游戏重新进入")
                    // this.showToast({     message: "banner广告展示失败：30003" });
                    break;
                case 30009:
                    console.log("10秒内调用广告次数超过1次，10秒后再调用")
                    // this.showToast({     message: "banner广告展示失败：30009" });
                    setTimeout(() => {
                        this.showBanner();
                    }, 10000);
                    break;
                case 30002:
                    console.log("加载广告失败，重新加载广告")
                    // this.showToast({     message: "banner广告展示失败：30002" });
                    setTimeout(() => {
                        this.showBanner()
                    }, 10000);
                    break;
                default:
                    // 参考 https://minigame.vivo.com.cn/documents/#/lesson/open-ability/ad?id=广告错误码信息
                    // 对错误码做分类处理
                    console.log("banner广告展示失败")
                    // this.showToast({     message: `banner广告展示失败${JSON.stringify(err)}` });
                    break;
            }
        });
    },
    hideBannerAd () {
        console.log("hide tt banner");
        // this.bannershow = false;
        if (this.bannerAd) {
            this.bannerAd.hide();
        }
        // this.bannerAd = null;
    },
    showInterstitialAd () {
        console.log("show tt interstitial");
        const isToutiaio = tt.getSystemInfoSync().appName === "Toutiao";
        // 插屏广告仅今日头条安卓客户端支持
        if (isToutiaio) {
            let posid = Math.floor(Math.random() * this.conf.interstitial_posid.length);
            const interstitialAd = tt.createInterstitialAd({
                adUnitId: this.conf.interstitial_posid[posid]
            });
            interstitialAd.load().then(() => {
                interstitialAd.show();
            }).catch((err) => {
                console.log(err);
            });
        }
    },
    createVideoAd () {
        // video
        if (this.conf && this.conf.video_posid && tt.createRewardedVideoAd) {
            let video_id = Math.floor(Math.random() * this.conf.video_posid.length);
            this.videoAd = tt.createRewardedVideoAd({ adUnitId: this.conf.video_posid[video_id] });
            console.log("show tt video", this.conf.video_posid[video_id]);
            this.videoAd.onError(err => {
                console.log("激励广告错误： " + JSON.stringify(err));
            });
        }
    },
    showVideoAd (onShow, onError, onClose) {
        console.log("show tt video");
        if (!this.videoAd) return;
        if (this._onVideoClose) {
            this.videoAd.offClose(this._onVideoClose);
        }

        this._onVideoClose = ((res) => {
            if (res && res.isEnded) {
                console.log('激励视频广告完成，发放奖励')
                if (onClose) {
                    onClose(true);
                }
            } else {
                console.log('激励视频广告取消关闭，不发放奖励');
                if (onClose) {
                    onClose(false)
                }
            }
            this.videoAd.offClose(this._onVideoClose);
            this._onVideoClose = null;
        });

        this.videoAd.onClose(this._onVideoClose);

        this.videoAd.show().then(() => {
            console.log("激励视频广告显示成功");
            if (onShow) {
                onShow();
            }
        }).catch((err) => {
            console.log("激励广告展示失败 ---- " + JSON.stringify(err))
            // this.showToast({     message: "激励广告展示失败"+JSON.stringify(err) });
            if (err && err.errCode) {
                this
                    .videoAd
                    .load()
                    .then(() => {
                        console.log("激励视频广告加载成功");
                        // this.isVideoLoaded = true;
                        return this
                            .videoAd
                            .show();
                    })
                    .catch((err) => {
                        console.log("激励视频广告加载失败", err);
                        if (onError) {
                            onError(err);
                        }
                    });
            }
        });
    },
    share (callback) {

        tt.shareAppMessage({
            // templateId: this.conf.share_templateId,
            title: this.conf.share_title,
            desc: this.conf.share_desc,
            imageUrl: "",
            query: "",
            extra: {
                videoPath: this.videoPath, // 可用录屏得到的视频地址
            },
            success () {
                console.log("分享成功");
                if (callback) {
                    callback(true);
                }
            },
            fail (e) {
                console.log("分享失败");
                if (callback) {
                    callback(false);
                }
            }
        });

    },
    shareVideo (callback) {
        console.log(this.videoPath, "videoPath");
        let self = this;
        if (!this.videoPath || this.videoPath == '') {
            this.showToast({ message: '没有录屏或录屏时间过短，分享失败!' });
            return;
        }
        tt.shareAppMessage({
            channel: "video",
            title: "",
            desc: "",
            extra: {
                videoPath: self.videoPath, // 可用录屏得到的视频地址
                // videoTopics: this.conf.share_topics.split(',') // ['一起来碰碰']
            },
            success () {
                console.log('分享视频成功');
                if (callback) {
                    callback(true);
                }
            },
            fail (e) {
                console.log('分享视频失败', e);
                // self.showToast({ message: '分享失败,请重新点击' });
                if (callback) {
                    callback(false);
                }
            }
        });

    },
    recordVideo (time, onStart, stop) {

        if (!this.recorder) {
            this.recorder = tt.getGameRecorderManager();
        }
        this.recorder.start({
            duration: time || 60
        });

        this.recorder.onStart(res => {
            console.log("开始录屏")
            if (onStart) {
                onStart();
            }
        });

        this.recorder.onStop(res => {
            this.videoPath = res.videoPath;
            console.log("录屏结束", res.videoPath)
            // this.showToast("录屏结束",2000); callback("end");
            if (stop) {
                stop(res);
            }
        })
    },
    stopRecord () {
        if (this.recorder) {
            this.recorder.stop();
        }
    },
    vibrate (duration) {
        if (duration === 0) {
            tt.vibrateShort();
        } else {
            tt.vibrateLong()
        }
    },
    showToast (msg) {
        tt.showToast({ icon: 'none', title: msg.message });
        // console.log("showToast", msg.message);
    },
    platform () {
        const systemInfo = tt.getSystemInfoSync();
        let system = "ios";
        // iOS 不支持，建议先检测再使用
        if (systemInfo.platform == "android") {
            system = "android";
        }
        console.log(systemInfo.platform)
        return system;
    },

    navigateToMiniGame (pkgName) {
        const systemInfo = tt.getSystemInfoSync();
        // iOS 不支持，建议先检测再使用
        if (systemInfo.platform !== "ios") {
            // 打开互跳弹窗
            tt.showMoreGamesModal({
                appLaunchOptions: [
                    {
                        appId: pkgName
                    }
                ],
                success (res) {
                    console.log("success", res.errMsg);
                },
                fail (res) {
                    console.log("fail", res.errMsg);
                }
            });
        }
    }
};