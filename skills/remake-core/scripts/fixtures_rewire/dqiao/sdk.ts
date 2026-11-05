
import * as SdkProxy  from './sdk/SdkProxy';

/**
 * 初始化配置
 */
export function sdkInit() {
    SdkProxy.init();
    SdkProxy.initAd();
}

/*** createBannerAd*/
export function createVideoAd() {
    SdkProxy.createVideoAd();
}

/*** createBannerAd*/
export function showBannerAd() {
    SdkProxy.showBannerAd();
}

/** hideBannerAd*/
export function hideBannerAd() {
    SdkProxy.hideBannerAd();
}

/** 获取平台信息*/
export function getChannel(): string {
    return SdkProxy.getChannel();
}

/**分享  头条就分享录屏*/
export function shareApp(callback) {
    if (SdkProxy.getChannel() == 'tt') {
        stopRecord();
        SdkProxy.shareVideo((v) => {
            if (!v) {
                if (callback) {
                    callback(false);
                }
            }
            else {
                if (callback) {
                    callback(true);
                }
            }
        })

    }
    else {
        SdkProxy.share((v) => { });
    }
}


/**插屏广告*/
export function showInterstitialAd() {
    SdkProxy.showInterstitialAd();
}

/**游戏跳转*/
export function navigateToMiniGame(pkgName: string = "") {
    SdkProxy.navigateToMiniGame(pkgName);
}

/**
 * @param tip 提示信息
 */
export function showToast(tip: string) {
    SdkProxy.showToast(tip);
}

/**
 * onShow onError onClose
 * @param callback 接收视频是否看完返回的参数
 */
export function showVideoAd(callback) {
    SdkProxy.showVideoAd(() => {
        //  onShow
    }, (e) => {
        //onError
    }, (v) => {
        //onClose
        if (!v) {
            if (callback) {
                callback(false);
            }
        }
        else {
            if (callback) {
                callback(true);
            }
        }
    })
}
let isStart = false;
/**
 * @param time 录屏时间
 * @param onStart 开始回调
 * @param onStop 结束回调
 */
export function recordVideo() {
    if (isStart) return;
    SdkProxy.recordVideo(15,
        // 开始
        () => {
            isStart = true;
        },
        // 结束
        () => {
            isStart = false;
        });
}
/** 停止录屏 */
export function stopRecord() {
    SdkProxy.stopRecord();
    isStart = false;
}

/*** 振动 0较短时间的振动 */
export function vibrate(duration = 0) {
    SdkProxy.vibrate(duration);
}
