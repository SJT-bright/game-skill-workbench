// GameAudioManager.ts —— 全局音频管理（Cocos Creator 3.x）
// 放在 assets/scripts/audio/，和自动生成的 GameAudioConfig.ts 同目录。
// 游戏逻辑只调用这里的方法，不要自己 new AudioSource 播放声音。
//
// 设置面板需要的接口（对应检查项 AUDIO-01）：
//   音乐 / 音效两个独立开关：setMusic(on)、setSFX(on)
//   两个独立音量，0–10 共 11 档（每档 10%）：setMusicLevel(0..10)、setSFXLevel(0..10)
//   OFF 显示和有效音量均为 0；另存上次非零档，ON 恢复。所有设置自动保存。
// 暂停按"原因"记录：广告和切后台分别 pause('ad') / pause('hide')，全部原因都解除才恢复，
// 所以看广告时切后台再切回来，不会在广告还没关时就响起来。

import { _decorator, Component, AudioSource, AudioClip, resources, director,
         game, Game, sys, tween, Tween, Node, input, Input } from 'cc';
import { BGM, SFX, AudioEntry } from './GameAudioConfig';
const { ccclass } = _decorator;

const KEY = 'game_audio_settings_v1';
const BGM_BASE = 0.5;            // BGM 一定要比音效小
const SFX_BASE = 0.8;
const JINGLE_BASE = 0.8;         // 过关/失败短音乐属于"音乐"，跟音乐开关和音乐音量
const SFX_MIN_INTERVAL = 50;     // 同一音效两次播放最小间隔（毫秒）
const SFX_MAX_CONCURRENT = 6;    // 同时播放的音效上限
const DUCK_LEVEL = 0.25;         // 播放 jingle 时 BGM 压低到的比例

// 可选音效没做时，自动用相近的音效代替，游戏代码可以放心调用标准 ID
const FALLBACK: Record<string, string> = {
    sfx_ui_back: 'sfx_ui_click', sfx_ui_toggle: 'sfx_ui_click', sfx_ui_locked: 'sfx_invalid',
    sfx_ui_popup_close: 'sfx_ui_popup_open', sfx_ui_popup_open: 'sfx_ui_click',
    sfx_swap: 'sfx_select', sfx_hint: 'sfx_reward', sfx_shuffle: 'sfx_swap',
    sfx_booster: 'sfx_reward', sfx_clear_big: 'sfx_match', sfx_reward_ad: 'sfx_reward',
    sfx_unlock: 'sfx_reward', sfx_time_up: 'sfx_invalid', sfx_heart_lose: 'sfx_invalid',
    sfx_level_start: 'sfx_ui_popup_open', sfx_spin: 'sfx_coin', sfx_select: 'sfx_ui_click',
    sfx_place: 'sfx_select',
};

interface Settings { musicOn: boolean; sfxOn: boolean; musicLevel: number; sfxLevel: number; lastMusicLevel: number; lastSFXLevel: number; }
interface Transient { source: AudioSource; kind: 'music' | 'sfx'; gain: number; started: boolean; cleanup: () => void; onStarted: (source: AudioSource) => void; onEnded: (source: AudioSource) => void; }

@ccclass('GameAudioManager')
export class GameAudioManager extends Component {
    static instance: GameAudioManager;

    private bgmSource!: AudioSource;
    private transients: Transient[] = [];
    private musicEpoch = 0;
    private jingleEpoch = 0;
    private sfxEpoch = 0;
    private alive = true;
    private saved = true;
    private loadedBgm = '';
    private clips = new Map<string, AudioClip>();
    private lastPlayTime = new Map<string, number>();
    private lastVariant = new Map<string, number>();
    private activeSfx = 0;
    private currentBgm = '';
    private pendingBgm = '';
    private unlocked = false;
    private pauseReasons = new Set<string>();
    private fade = { v: 0 };
    private settings: Settings = { musicOn: true, sfxOn: true, musicLevel: 10, sfxLevel: 10, lastMusicLevel: 10, lastSFXLevel: 10 };

    /** 在启动场景调用一次；没有挂在场景里时会自动创建常驻节点 */
    static init(): GameAudioManager {
        if (GameAudioManager.instance) return GameAudioManager.instance;
        const node = new Node('GameAudioManager');
        director.getScene()!.addChild(node);
        return node.addComponent(GameAudioManager);
    }

    onLoad() {
        if (GameAudioManager.instance && GameAudioManager.instance !== this) { this.node.destroy(); return; }
        GameAudioManager.instance = this;
        director.addPersistRootNode(this.node);

        this.bgmSource = this.node.addComponent(AudioSource);
        this.bgmSource.loop = true;
        this.bgmSource.playOnAwake = false;
        this.loadSettings();

        // 浏览器要求第一次点击后才能出声；TikTok/原生环境可以直接播
        this.unlocked = !sys.isBrowser;
        game.on(Game.EVENT_HIDE, this.onHide, this);
        game.on(Game.EVENT_SHOW, this.onShow, this);
        input.once(Input.EventType.TOUCH_START, this.unlock, this);
    }

    onDestroy() {
        this.alive = false; this.musicEpoch++; this.jingleEpoch++; this.sfxEpoch++;
        Tween.stopAllByTarget(this.fade);
        if (this.bgmSource) this.bgmSource.stop();
        this.stopTransients();
        if (GameAudioManager.instance === this) GameAudioManager.instance = undefined!;
        game.off(Game.EVENT_HIDE, this.onHide, this);
        game.off(Game.EVENT_SHOW, this.onShow, this);
    }

    /** 玩家第一次点击屏幕时自动调用；按钮音组件也会调用，保证第一下就能出声 */
    unlock() {
        if (this.unlocked) return;
        this.unlocked = true;
        if (this.pendingBgm) { const id = this.pendingBgm; this.pendingBgm = ''; this.playBGM(id); }
    }

    // ---------------------------------------------------------- 设置（开关 + 11 档音量，自动保存）

    private loadSettings() {
        try {
            const raw = sys.localStorage.getItem(KEY);
            if (raw) {
                const s = JSON.parse(raw);
                const music = this.clampLevel(s.musicLevel, 10), sfx = this.clampLevel(s.sfxLevel, 10);
                this.settings.lastMusicLevel = this.clampLevel(s.lastMusicLevel, music || 10) || music || 10;
                this.settings.lastSFXLevel = this.clampLevel(s.lastSFXLevel, sfx || 10) || sfx || 10;
                this.settings.musicOn = s.musicOn !== false && music > 0;
                this.settings.sfxOn = s.sfxOn !== false && sfx > 0;
                this.settings.musicLevel = this.settings.musicOn ? music : 0;
                this.settings.sfxLevel = this.settings.sfxOn ? sfx : 0;
            }
        } catch (e) { console.warn('[Audio] 设置读取失败，使用默认值', e); }
    }

    private saveSettings() {
        try { sys.localStorage.setItem(KEY, JSON.stringify(this.settings)); this.saved = true; return true; }
        catch (e) { this.saved = false; console.warn('[Audio] 设置保存失败；当前设置仅本次运行有效，可重试保存', e); return false; }
    }

    private clampLevel(v: any, def: number): number {
        const n = Math.round(Number(v));
        return isFinite(n) ? Math.max(0, Math.min(10, n)) : def;
    }

    get settingsSaved() { return this.saved; }
    retrySaveSettings() { return this.saveSettings(); }

    get musicOn() { return this.settings.musicOn; }
    get sfxOn() { return this.settings.sfxOn; }
    get musicLevel() { return this.settings.musicLevel; }   // 0–10，界面显示为 0%–100%
    get sfxLevel() { return this.settings.sfxLevel; }

    setMusic(on: boolean) {
        this.settings.musicOn = !!on;
        this.settings.musicLevel = on ? this.settings.lastMusicLevel : 0;
        this.applyMusicSettings();
    }

    setSFX(on: boolean) {
        this.settings.sfxOn = !!on;
        this.settings.sfxLevel = on ? this.settings.lastSFXLevel : 0;
        this.applySFXSettings();
    }

    /** 绝对档位（点格）；正档开启，0 档静音并保留上次非零档。 */
    setMusicLevel(level: number) {
        const value = this.clampLevel(level, this.settings.musicLevel);
        this.settings.musicLevel = value; this.settings.musicOn = value > 0;
        if (value > 0) this.settings.lastMusicLevel = value;
        this.applyMusicSettings();
    }

    setSFXLevel(level: number) {
        const value = this.clampLevel(level, this.settings.sfxLevel);
        this.settings.sfxLevel = value; this.settings.sfxOn = value > 0;
        if (value > 0) this.settings.lastSFXLevel = value;
        this.applySFXSettings();
    }

    increaseMusicLevel() { this.setMusicLevel(this.musicLevel + 1); }
    decreaseMusicLevel() { this.setMusicLevel(this.musicLevel - 1); }
    increaseSFXLevel() { this.setSFXLevel(this.sfxLevel + 1); }
    decreaseSFXLevel() { this.setSFXLevel(this.sfxLevel - 1); }

    private applyMusicSettings() {
        this.saveSettings(); this.musicEpoch++; Tween.stopAllByTarget(this.fade);
        this.refreshTransients('music');
        if (!this.musicScale()) { this.jingleEpoch++; this.bgmSource.volume = 0; this.bgmSource.stop(); return; }
        if (this.pauseReasons.size) { this.currentBgm = this.currentBgm || this.pendingBgm || 'bgm_menu'; return; }
        if (this.bgmSource.playing && this.loadedBgm === this.currentBgm) this.bgmSource.volume = this.bgmTarget(BGM[this.currentBgm]);
        else this.playBGM(this.currentBgm || this.pendingBgm || 'bgm_menu');
    }

    private applySFXSettings() {
        this.saveSettings(); this.sfxEpoch++; this.refreshTransients('sfx');
    }

    private musicScale() { return this.settings.musicOn ? this.settings.musicLevel / 10 : 0; }
    private sfxScale() { return this.settings.sfxOn ? this.settings.sfxLevel / 10 : 0; }

    // ---------------------------------------------------------- 加载

    private pathsOf(e: AudioEntry): string[] {
        if (e.variants && e.variants > 1) {
            const list: string[] = [];
            for (let i = 1; i <= e.variants; i++) list.push(`${e.path}_${i}`);
            return list;
        }
        return [e.path];
    }

    /** 预加载全部音效（体积小），BGM 只预加载 bgm_menu，其余用到再加载 */
    preload(onDone?: () => void) {
        const paths: string[] = [];
        Object.values(SFX).forEach(e => paths.push(...this.pathsOf(e)));
        if (BGM['bgm_menu']) paths.push(BGM['bgm_menu'].path);
        if (!paths.length) { onDone && onDone(); return; }
        resources.load(paths, AudioClip, (err, list) => {
            if (err) console.warn('[Audio] 预加载有失败项', err);
            (list || []).forEach((c, i) => c && this.clips.set(paths[i], c));
            onDone && onDone();
        });
    }

    private getClip(path: string, cb: (c: AudioClip | null) => void) {
        const cached = this.clips.get(path);
        if (cached) { cb(cached); return; }
        resources.load(path, AudioClip, (err, clip) => {
            if (err || !clip) { console.warn('[Audio] 加载失败', path); cb(null); return; }
            this.clips.set(path, clip);
            cb(clip);
        });
    }

    /** 多版本随机播放，且不连续两次播同一个版本 */
    private pickVariant(id: string, e: AudioEntry): string {
        if (!e.variants || e.variants <= 1) return e.path;
        let i = 1 + Math.floor(Math.random() * e.variants);
        if (i === this.lastVariant.get(id)) i = (i % e.variants) + 1;
        this.lastVariant.set(id, i);
        return `${e.path}_${i}`;
    }

    // ---------------------------------------------------------- BGM

    playBGM(id: string, fadeIn = 0.5) {
        const e = BGM[id];
        if (!e) { console.warn('[Audio] 未知 BGM', id); return; }
        if (!this.unlocked) { this.pendingBgm = id; return; }
        const ticket = ++this.musicEpoch; this.jingleEpoch++;
        if (!this.musicScale() || this.pauseReasons.size) { this.currentBgm = id; return; }
        if (this.currentBgm === id && this.loadedBgm === id && this.bgmSource.playing) { this.fadeTo(this.bgmTarget(e), 0.3); return; }
        this.currentBgm = id;
        if (!this.settings.musicOn || this.pauseReasons.size) return;

        const start = () => this.getClip(e.path, clip => {
            if (!clip || !this.alive || ticket !== this.musicEpoch || this.currentBgm !== id || !this.musicScale() || this.pauseReasons.size) return;
            this.bgmSource.stop();
            this.loadedBgm = id;
            this.bgmSource.clip = clip;
            this.bgmSource.loop = true;
            this.bgmSource.volume = 0;
            this.bgmSource.play();
            this.fadeTo(this.bgmTarget(e), fadeIn);
        });
        // 有正在播的 BGM：先淡出再切，不会两首叠在一起
        if (this.bgmSource.playing) this.fadeTo(0, 0.3, start); else start();
    }

    /** 关卡 BGM 轮换：有 bgm_game_2 时奇偶关交替，减少听腻 */
    playLevelBGM(level: number) {
        const id = BGM['bgm_game_2'] && level % 2 === 0 ? 'bgm_game_2' : 'bgm_game';
        this.playBGM(BGM[id] ? id : 'bgm_menu');
    }

    stopBGM(fadeOut = 0.3) {
        this.musicEpoch++; this.jingleEpoch++; this.currentBgm = ''; this.pendingBgm = '';
        this.fadeTo(0, fadeOut, () => this.bgmSource.stop());
    }

    /** 胜利 / 失败短音乐：BGM 压低，jingle 播到一半后 BGM 淡出停下；结算界面出现后再调用 playBGM('bgm_menu') */
    playJingle(id: string) {
        const e = BGM[id];
        if (!e) { console.warn('[Audio] 未知 jingle', id); return; }
        if (!this.musicScale() || this.pauseReasons.size || !this.unlocked) return;
        const ticket = ++this.musicEpoch, jingleTicket = ++this.jingleEpoch;
        this.fadeTo(this.bgmTarget(BGM[this.currentBgm]) * DUCK_LEVEL, 0.15);
        this.getClip(e.path, clip => {
            if (!clip || !this.alive || ticket !== this.musicEpoch || !this.musicScale() || this.pauseReasons.size) return;
            this.playTransient(clip, 'music', JINGLE_BASE * (e.volume ?? 1), () => {
                this.scheduleOnce(() => {
                    if (!this.alive || jingleTicket !== this.jingleEpoch || !this.musicScale() || this.pauseReasons.size) return;
                    this.fadeTo(0, 0.4, () => { this.bgmSource.stop(); this.currentBgm = ''; });
                }, clip.getDuration() * 0.6);
            });
        });
    }

    private bgmTarget(e?: AudioEntry) { return BGM_BASE * this.musicScale() * (e?.volume ?? 1); }

    private fadeTo(to: number, duration: number, done?: () => void) {
        Tween.stopAllByTarget(this.fade);
        this.fade.v = this.bgmSource.volume;
        tween(this.fade)
            .to(duration, { v: to }, { onUpdate: () => { this.bgmSource.volume = this.musicScale() ? this.fade.v : 0; } })
            .call(() => done && done())
            .start();
    }

    // playOneShot 无法停止；短音使用独立受控源，静音/暂停立即停止且不排队补播。
    private removeTransient(entry: Transient) {
        const index = this.transients.indexOf(entry);
        if (index < 0) return;
        entry.source.node.off(AudioSource.EventType.STARTED, entry.onStarted);
        entry.source.node.off(AudioSource.EventType.ENDED, entry.onEnded);
        entry.source.volume = 0; entry.source.stop(); entry.source.clip = null; entry.source.destroy();
        this.unschedule(entry.cleanup); this.transients.splice(index, 1);
        if (entry.kind === 'sfx' && entry.started) this.activeSfx--;
    }

    private stopTransients(kind?: 'music' | 'sfx') {
        this.transients.slice().forEach(entry => { if (!kind || entry.kind === kind) this.removeTransient(entry); });
    }

    private refreshTransients(kind: 'music' | 'sfx') {
        const scale = kind === 'music' ? this.musicScale() : this.sfxScale();
        if (!scale) { this.stopTransients(kind); return; }
        this.transients.forEach(entry => { if (entry.kind === kind) entry.source.volume = entry.gain * scale; });
    }

    private makeSFXRoom() {
        const slots = this.transients.filter(entry => entry.kind === 'sfx');
        if (slots.length < SFX_MAX_CONCURRENT) return true;
        // AudioSource 公开 API 不区分内部加载失败与仍在加载；只在原预算满时替换旧未启动槽。
        const pending = slots.find(entry => !entry.started);
        if (!pending) return false;
        this.removeTransient(pending);
        return true;
    }

    private playTransient(clip: AudioClip, kind: 'music' | 'sfx', gain: number, onStarted?: () => void) {
        const scale = kind === 'music' ? this.musicScale() : this.sfxScale();
        if (!this.alive || !scale || this.pauseReasons.size) return;
        if (kind === 'music') this.transients.slice().forEach(entry => { if (entry.kind === 'music' && !entry.started) this.removeTransient(entry); });
        const source = this.node.addComponent(AudioSource);
        source.playOnAwake = false; source.loop = false; source.clip = clip; source.volume = gain * scale;
        const entry: Transient = { source, kind, gain, started: false,
            // 解码/播放起点可能晚于资源回调；定时收尾不得截断仍在播放的短音。
            cleanup: () => {
                if (source.playing) { this.scheduleOnce(entry.cleanup, Math.max(clip.getDuration(), 0.1)); return; }
                this.removeTransient(entry);
            },
            onStarted: started => {
                if (started !== source || entry.started || this.transients.indexOf(entry) < 0) return;
                entry.started = true;
                if (kind === 'sfx') this.activeSfx++;
                this.scheduleOnce(entry.cleanup, Math.max(clip.getDuration(), 0.1));
                if (onStarted) onStarted();
            },
            onEnded: ended => { if (ended === source) this.removeTransient(entry); },
        };
        source.node.on(AudioSource.EventType.STARTED, entry.onStarted);
        source.node.on(AudioSource.EventType.ENDED, entry.onEnded);
        this.transients.push(entry);
        source.play();
    }

    // ---------------------------------------------------------- 音效

    playSFX(id: string, volumeScale = 1) {
        if (!this.sfxScale() || !this.unlocked || this.pauseReasons.size) return;
        const ticket = this.sfxEpoch;
        let guard = 0;
        while (!SFX[id] && FALLBACK[id] && guard++ < 4) id = FALLBACK[id];
        const e = SFX[id];
        if (!e) { console.warn('[Audio] 未知音效', id); return; }
        const now = Date.now();
        if (now - (this.lastPlayTime.get(id) ?? 0) < SFX_MIN_INTERVAL) return;
        if (!this.makeSFXRoom()) return;
        this.lastPlayTime.set(id, now);

        this.getClip(this.pickVariant(id, e), clip => {
            if (!clip || !this.alive || ticket !== this.sfxEpoch || !this.sfxScale() || this.pauseReasons.size || !this.makeSFXRoom()) return;
            this.playTransient(clip, 'sfx', SFX_BASE * (e.volume ?? 1) * volumeScale);
        });
    }

    /** 连击：level 从 1 开始；超过最高级就一直用最高级 */
    playCombo(level: number) {
        let max = 0;
        while (SFX[`sfx_combo_${max + 1}`]) max++;
        if (max === 0) { this.playSFX('sfx_match'); return; }
        this.playSFX(`sfx_combo_${Math.min(Math.max(level, 1), max)}`);
    }

    /** 结算星星：index 从 1 开始，跟着星星动画逐个调用 */
    playStar(index: number) {
        this.playSFX(SFX[`sfx_star_${index}`] ? `sfx_star_${index}` : 'sfx_star_1');
    }

    /** 连续获得多个金币：依次播放，不叠在一起 */
    playCoins(count: number) {
        const n = Math.min(count, 8), ticket = this.sfxEpoch;
        for (let i = 0; i < n; i++) this.scheduleOnce(() => { if (this.alive && ticket === this.sfxEpoch) this.playSFX('sfx_coin', 1 - i * 0.05); }, i * 0.06);
    }

    // ---------------------------------------------------------- 暂停（按原因记录）

    /** 激励视频播放前调用 pause('ad')，关闭后调用 resume('ad')；其他原因（如暂停菜单）自定名字 */
    pause(reason: string) {
        this.pauseReasons.add(reason);
        this.musicEpoch++; this.jingleEpoch++; this.sfxEpoch++; Tween.stopAllByTarget(this.fade); this.stopTransients();
        this.bgmSource.volume = 0; // 内部播放器迟到时，排队 PLAY/PAUSE 也必须保持零增益。
        this.bgmSource.pause();
    }

    resume(reason: string) {
        this.pauseReasons.delete(reason);
        if (this.pauseReasons.size) return;
        if (this.musicScale() && this.currentBgm && this.unlocked) {
            if (!this.bgmSource.clip || this.loadedBgm !== this.currentBgm) { const id = this.currentBgm; this.currentBgm = ''; this.playBGM(id); return; }
            this.bgmSource.play();
            this.fadeTo(this.bgmTarget(BGM[this.currentBgm]), 0.3);
        }
    }

    /** 旧接口：等同 pause('ad') / resume('ad') */
    pauseAll() { this.pause('ad'); }
    resumeAll() { this.resume('ad'); }

    private onHide() { this.pause('hide'); }
    private onShow() { this.resume('hide'); }
}
