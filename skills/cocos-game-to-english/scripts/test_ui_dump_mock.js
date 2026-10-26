// Self-test fixture: a minimal fake Cocos (2.x or 3.x API shape) so ui_dump.js can be exercised in Node.
// Usage: node test_ui_dump_mock.js 3|2 <scene: menu|play|pause|copy> > dump.json
//        or in a browser page: <script src="test_ui_dump_mock.js"></script> then window.cc = buildMockCc(3, 'pause', canvasEl)
// Not an engine: it only reproduces the APIs ui_dump.js calls (getComponent, contentSize/anchor or width/anchorX,
// convertToWorldSpaceAR, children, active, opacity/UIOpacity, Sprite insets).
function buildMockCc(api, sceneName, canvasEl) {

class Comp { constructor(props) { Object.assign(this, props || {}); this.enabled = true; } }
// labels are styled like the rules want (game font, white with an outline) unless a scene says otherwise
const STYLED = { font: { name: 'Fredoka-Bold' }, useSystemFont: false, color: { r: 255, g: 255, b: 255 },
                 enableOutline: true, outlineWidth: 3, outlineColor: { r: 80, g: 40, b: 10 } };
class Canvas extends Comp {} class Button extends Comp {} class RichText extends Comp {}
class Label extends Comp { constructor(props) { super(Object.assign({}, props && 'useSystemFont' in props ? {} : STYLED, props)); } }
class Sprite extends Comp {} class Graphics extends Comp {} class BlockInputEvents extends Comp {} class UIOpacity extends Comp {} class ProgressBar extends Comp {}
// Render camera: world (0..750 x 0..1624) -> canvas backing pixels (750 x 1624), optionally shifted (camera offset bug)
const CAM_SHIFT = sceneName.indexOf('offset_') === 0 ? 60 : 0;
class Camera extends Comp {
  worldToScreen(p, out) { out = out || {}; out.x = p.x + CAM_SHIFT; out.y = p.y; out.z = 0; return out; }
  getWorldToScreenPoint(p, out) { out = out || {}; out.x = p.x + CAM_SHIFT; out.y = p.y; return out; }
}
Camera.findCamera = () => MAIN_CAM;
let MAIN_CAM = null;
class UITransform extends Comp {
  convertToWorldSpaceAR(v) { const w = this.node.worldPos(); return { x: w.x + v.x * w.s, y: w.y + v.y * w.s, z: 0 }; }
}
Sprite.Type = { SIMPLE: 0, SLICED: 1 };

class Node {
  constructor(name, x, y, w, h, opts) {
    opts = opts || {};
    this.name = name; this.x = x; this.y = y; this.scale = opts.scale || 1; this.children = []; this.parent = null;
    this.active = opts.active !== false; this.components = []; this.uuid = name + Math.random().toString(16).slice(2, 6);
    this.w = w; this.h = h; this.ax = opts.ax === undefined ? 0.5 : opts.ax; this.ay = opts.ay === undefined ? 0.5 : opts.ay;
    if (api === 3) { this.add(new UITransform({ contentSize: { width: w, height: h }, anchorPoint: { x: this.ax, y: this.ay } })); this.layer = 33554432; }
    else { this.width = w; this.height = h; this.anchorX = this.ax; this.anchorY = this.ay; this.opacity = opts.opacity === undefined ? 255 : opts.opacity; }
    if (api === 3 && opts.opacity !== undefined) this.add(new UIOpacity({ opacity: opts.opacity }));
  }
  add(c) {
    c.node = this; this.components.push(c);
    const sf = c instanceof Sprite && c.spriteFrame;      // the picture is 2x the node unless a scene says otherwise
    if (sf && !sf.originalSize) { sf.originalSize = { width: this.w * 2, height: this.h * 2 }; sf.rect = { x: 0, y: 0, width: this.w * 2, height: this.h * 2 }; }   // drawn at half its size: 2x sharp (ART-04)
    return this;
  }
  kid(n) { n.parent = this; this.children.push(n); return n; }
  getComponent(ctor) { return this.components.find((c) => c instanceof ctor) || null; }
  worldPos() { // parent space: position relative to parent's anchor point, uniform scale
    if (!this.parent || this.parent.isScene) return { x: this.x, y: this.y, s: this.scale };
    const p = this.parent.worldPos();
    return { x: p.x + this.x * p.s, y: p.y + this.y * p.s, s: p.s * this.scale };
  }
  convertToWorldSpaceAR(v) { const w = this.worldPos(); return { x: w.x + v.x * w.s, y: w.y + v.y * w.s }; }
}

const scene = new Node('Scene', 0, 0, 0, 0); scene.isScene = true; scene.components = [];
const canvas = scene.kid(new Node('Canvas', 375, 812, 750, 1624)).add(new Canvas());
MAIN_CAM = new Camera({ visibility: 0xffffffff, priority: 0 });
canvas.kid(new Node('Main Camera', 0, 0, 1, 1)).add(MAIN_CAM);
sceneName = sceneName.replace(/^offset_/, '');
// "<scene>+bar": add the top resource bar (references/top-bar-and-level-map.md); "+coinbar": same with a plain coin icon
const BAR = sceneName.indexOf('+') > 0 ? sceneName.split('+')[1] : '';
sceneName = sceneName.split('+')[0];
const plainBg = ['bad_result', 'bad_home_flat'].indexOf(sceneName) >= 0;
const bg = canvas.kid(new Node('Background', 0, 0, 750, 1624)).add(new Sprite(plainBg
  ? { spriteFrame: { name: 'default_sprite_splash' }, type: 0, color: { r: 80, g: 128, b: 196 } }
  : { spriteFrame: { name: 'bg' }, type: 0 }));
const FONT = { font: { name: 'Fredoka-Bold' }, useSystemFont: false, color: { r: 255, g: 255, b: 255 },
               enableOutline: true, outlineWidth: 3, outlineColor: { r: 80, g: 40, b: 10 } };
const SYS = { font: null, useSystemFont: true };
// user 2026-10-23: numbers (coins, energy, level, prices, percentages) are generated digit pictures -> a bitmap font
const BMFONT = { font: { name: 'num_candy', fntConfig: { commonHeight: 64 } }, useSystemFont: false, color: { r: 255, g: 255, b: 255 } };
// user 2026-10-22: fixed words are picture text generated with the art (frame txt_<words>); numbers use the bitmap font.
// user 2026-10-23: a button is ONE generated picture with its word baked in (frame btn_<words>, icon captions baked into
// icon_*): no label or txt_ word on top of a plate. A scene that passes font 'spliced' puts txt_ picture text on the plate,
// an explicit font object puts a font label there (the negative examples).
const WORDY = (t) => /[A-Za-z]{2,}/.test(t);
const picText = (parent, name, x, y, w, h, t) => parent.kid(new Node(name, x, y, w, h)).add(new Sprite({ spriteFrame: { name: 'txt_' + t.replace(/ /g, '_') }, type: 0 }));
const numLabel = (parent, name, x, y, w, h, t, size) => parent.kid(new Node(name, x, y, w, h)).add(new Label(Object.assign({ string: t, fontSize: size || 30, overflow: 2 }, BMFONT)));
const plateBtn = (parent, name, x, y, w, h, text, font) => {
  const baked = text && WORDY(text) && !font;
  const b = parent.kid(new Node(name, x, y, w, h)).add(new Button({ interactable: true }))
    .add(new Sprite({ spriteFrame: { name: baked ? 'btn_' + text.replace(/ /g, '_') : 'btn_' + name }, type: 1 }));
  if (baked) return b;
  if (text && font === 'spliced') picText(b, 'Txt', 0, 0, w * 0.8, h * 0.6, text);
  else if (text && !WORDY(text) && !font) numLabel(b, 'Txt', 0, 0, w * 0.8, h * 0.6, text, 36);
  else if (text) b.kid(new Node('Txt', 0, 0, w * 0.8, h * 0.6)).add(new Label(Object.assign({ string: text, fontSize: 36, overflow: 2 }, font || FONT)));
  return b;
};
const iconBtn = (parent, name, x, y, label, font) => {
  const b = parent.kid(new Node(name, x, y, 110, 110)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'icon_' + name }, type: 0 }));
  if (!label || (WORDY(label) && !font)) return b;                    // caption baked into the icon picture
  if (font === 'spliced') picText(b, 'Txt', 0, -75, label.length > 8 ? 200 : 110, 36, label);
  else b.kid(new Node('Txt', 0, -75, label.length > 8 ? 200 : 110, 36)).add(new Label(Object.assign({ string: label, fontSize: 26, overflow: 2 }, font || FONT)));
  return b;
};
const sprite = (parent, name, x, y, w, h, sliced) => parent.kid(new Node(name, x, y, w, h)).add(new Sprite({ spriteFrame: { name: name }, type: sliced ? 1 : 0 }));
const fontLabel = (parent, name, x, y, w, h, text, size) => parent.kid(new Node(name, x, y, w, h)).add(new Label(Object.assign({ string: text, fontSize: size || 30, overflow: 2 }, FONT)));
const label = (parent, name, x, y, w, h, text, size) => WORDY(text) ? picText(parent, name, x, y, w, h, text) : numLabel(parent, name, x, y, w, h, text, size);
if (sceneName === 'bold_api') {
  fontLabel(canvas, 'EnableBold', 0, 200, 200, 50, '2.4', 32).components.find(c => c instanceof Label).enableBold = true;
  fontLabel(canvas, 'IsBold', 0, 100, 200, 50, '3.x', 32).components.find(c => c instanceof Label).isBold = true;
  fontLabel(canvas, 'Plain', 0, 0, 200, 50, 'plain', 32);
} else if (sceneName === 'bad_result') {                 // user 2026-10-21 negative example: flat blue page, one NEXT LEVEL button
  plateBtn(canvas, 'BtnNext', 0, -300, 270, 100, 'NEXT LEVEL');
} else if (sceneName === 'good_result') {
  canvas.kid(new Node('Mask', 0, 0, 750, 1624, { opacity: 150 })).add(new BlockInputEvents()).add(new Sprite({ spriteFrame: { name: 'mask' }, type: 0 }));
  const panel = sprite(canvas, 'Panel', 0, 40, 620, 1000, true);
  sprite(panel, 'Ribbon', 0, 440, 560, 150);
  label(panel, 'Level', 0, 330, 300, 50, 'Level 12', 34);
  for (let i = 0; i < 3; i++) sprite(panel, 'Star' + i, -160 + i * 160, 180, 130, 130);
  sprite(panel, 'CoinIcon', -90, 10, 80, 80);
  label(panel, 'Coins', 40, 10, 180, 60, '+50', 40);
  sprite(panel, 'Mascot', 0, -130, 220, 160);
  // user 2026-10-23: every level end offers "watch an ad, x2 coins" (one generated button picture)
  plateBtn(panel, 'BtnDouble', 0, -262, 320, 90, 'x2 COINS');
  plateBtn(panel, 'BtnNext', 0, -372, 220, 100, 'NEXT');
  iconBtn(panel, 'BtnHome', -180, -372, '');
  iconBtn(panel, 'BtnRetry', 180, -372, '');
} else if (sceneName === 'bad_home') {            // user 2026-10-21 negative example: PLAY is bare text, labels in the system font
  sprite(canvas, 'Logo', 0, 500, 460, 280);
  sprite(canvas, 'Mascots', 0, -20, 600, 460);
  canvas.kid(new Node('BtnPlay', 0, -420, 200, 70)).add(new Button({ interactable: true })).add(new Label(Object.assign({ string: 'PLAY', fontSize: 44, overflow: 0 }, FONT)));
  iconBtn(canvas, 'BtnShortcut', -250, -620, 'Home Screen', SYS);
  iconBtn(canvas, 'BtnRevisit', 250, -620, 'Profile Revisit', SYS);
} else if (sceneName === 'good_home') {
  sprite(canvas, 'Logo', 0, 520, 480, 280);
  sprite(canvas, 'Mascots', 0, 20, 560, 420);
  plateBtn(canvas, 'BtnPlay', 0, -420, 380, 130, 'PLAY');
  // user 2026-10-23: settings in a top corner (below the platform capsule), currency at the top; current rule puts real features on both sides above PLAY
  iconBtn(canvas, 'BtnSettings', 310, 590, '');
  iconBtn(canvas, 'BtnSkins', -300, -240, '');
  iconBtn(canvas, 'BtnGift', 300, -240, '');             // user 2026-10-23: animated gift box -> ad -> coins
  iconBtn(canvas, 'BtnShortcut', 65, -640, 'Home');
  iconBtn(canvas, 'BtnRevisit', 195, -640, 'Revisit');
} else if (sceneName === 'scattered_home') {      // user 2026-10-23 negative example (Hazel's Shelf Scramble home)
  sprite(canvas, 'Logo', 0, 560, 480, 260);
  sprite(canvas, 'Mascots', 0, 250, 560, 300);
  const bar = canvas.kid(new Node('CoinBar', 0, 0, 420, 80)).add(new Sprite({ spriteFrame: { name: 'capsule' }, type: 1 }));
  sprite(bar, 'CoinIcon', -150, 0, 60, 60).getComponent(Sprite).spriteFrame.name = 'icon_coin';
  label(bar, 'CoinCount', -80, 0, 80, 44, '0', 30);
  sprite(bar, 'ItemIcon', 60, 0, 60, 60).getComponent(Sprite).spriteFrame.name = 'icon_magnet';
  label(bar, 'ItemCount', 130, 0, 80, 44, '1', 30);
  plateBtn(canvas, 'BtnPlay', 0, -380, 380, 130, 'PLAY');
  iconBtn(canvas, 'BtnSettings', 310, 590, '');
  iconBtn(canvas, 'BtnMap', -300, -150, '');
  iconBtn(canvas, 'BtnSkins', 300, -150, '');
  iconBtn(canvas, 'BtnHelp', -300, -700, '');
  iconBtn(canvas, 'BtnVideo', 300, -700, '');
} else if (sceneName === 'plain_popup' || sceneName === 'reward_popup') {   // user 2026-10-23: "Home screen reward" popup
  canvas.kid(new Node('Mask', 0, 0, 750, 1624, { opacity: 150 })).add(new BlockInputEvents()).add(new Sprite({ spriteFrame: { name: 'mask' }, type: 0 }));
  const panel = sprite(canvas, 'Panel', 0, 0, 620, 860, true);
  label(panel, 'Title', 0, 380, 420, 70, 'Home Screen Reward', 40);
  label(panel, 'Body', 0, 200, 520, 120, 'Add the game to your home screen', 28);
  if (sceneName === 'reward_popup') {
    sprite(panel, 'Ribbon', 0, 380, 560, 120);
    sprite(panel, 'PhoneArt', -110, 0, 220, 260);
    sprite(panel, 'GiftChest', 120, 0, 220, 200);
    sprite(panel, 'CoinIcon', 60, -140, 60, 60);
    label(panel, 'Reward', 140, -140, 120, 50, '+100', 36);
  }
  plateBtn(panel, 'BtnAdd', 0, -250, 300, 100, 'ADD NOW');
  iconBtn(panel, 'BtnCheck', -150, -370, '');
  iconBtn(panel, 'BtnClose', 270, 390, '');
} else if (sceneName === 'button_home') {         // user 2026-10-21: buttons fill the screen (> 40%), small title, no cover art
  sprite(canvas, 'Logo', 0, 560, 300, 160);
  plateBtn(canvas, 'BtnPlay', 0, 150, 680, 300, 'PLAY');
  plateBtn(canvas, 'BtnLevels', 0, -150, 680, 240, 'LEVELS');
  plateBtn(canvas, 'BtnSkins', 0, -420, 680, 240, 'SKINS');
  iconBtn(canvas, 'BtnSettings', -300, 740, '');
  iconBtn(canvas, 'BtnShortcut', -280, -640, 'Add to Home');
  iconBtn(canvas, 'BtnRevisit', 280, -640, 'Revisit');
} else if (sceneName === 'round2_home') {         // user 2026-10-21 round 2: Scissors Master home
  sprite(canvas, 'Logo', 0, 460, 640, 300);
  const play = canvas.kid(new Node('BtnPlay', 0, -300, 600, 130)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn_play' }, type: 1 }));
  play.kid(new Node('Txt', 0, 0, 300, 80)).add(new Label(Object.assign({}, FONT, { string: 'PLAY', fontSize: 64, overflow: 0, isBold: true, color: { r: 25, g: 35, b: 50 }, enableOutline: false })));
  plateBtn(canvas, 'BtnLevels', -150, -470, 250, 50, 'LEVELS', 'spliced');
  plateBtn(canvas, 'BtnSkins', 150, -470, 250, 50, 'SKINS', 'spliced');
  const hs = canvas.kid(new Node('BtnShortcut', -180, -580, 280, 90)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn_shortcut' }, type: 1 }));
  hs.kid(new Node('Txt', 0, -20, 340, 40)).add(new Label(Object.assign({ string: 'HOME SCREEN', fontSize: 30, overflow: 0 }, FONT)));
  iconBtn(canvas, 'BtnSettings', 300, 740, '');
} else if (sceneName === 'typed_home') {         // user 2026-10-23 negative example: Scissors Master home, everything typed
  canvas.kid(new Node('Title', 0, 560, 600, 110)).add(new Label(Object.assign({}, FONT, { string: 'Scissors Master', fontSize: 72, overflow: 0 })));
  canvas.kid(new Node('Subtitle', 0, 470, 520, 50)).add(new Label(Object.assign({}, FONT, { string: 'Cut the paper, win the round', fontSize: 30, overflow: 0 })));
  sprite(canvas, 'Mascots', 0, -60, 600, 520);
  const bar = canvas.kid(new Node('CoinBar', -150, 730, 260, 70)).add(new Sprite({ spriteFrame: { name: 'capsule' }, type: 1 }));
  sprite(bar, 'CoinIcon', -90, 0, 56, 56).getComponent(Sprite).spriteFrame.name = 'icon_coin';
  bar.kid(new Node('CoinCount', 20, 0, 100, 44)).add(new Label(Object.assign({ string: '0', fontSize: 32, overflow: 0 }, FONT)));
  canvas.kid(new Node('LevelCount', 150, 730, 120, 44)).add(new Label(Object.assign({ string: '0/9', fontSize: 32, overflow: 0 }, FONT)));
  plateBtn(canvas, 'BtnPlay', 0, -420, 380, 120, 'PLAY', FONT);
  iconBtn(canvas, 'BtnLevels', -270, -620, 'LEVELS', 'spliced');
  iconBtn(canvas, 'BtnSkins', -90, -620, 'SKINS', 'spliced');
  iconBtn(canvas, 'BtnShortcut', 90, -620, 'Add to Home', 'spliced');
  iconBtn(canvas, 'BtnRevisit', 270, -620, 'Revisit', 'spliced');
  iconBtn(canvas, 'BtnSettings', 310, 600, '');
} else if (sceneName === 'round2_map') {          // round 2: level select with three blank cards and a placeholder
  sprite(canvas, 'Title', 0, 700, 300, 60);
  label(canvas, 'Levels', 0, 700, 280, 50, 'Levels 1-10', 30);
  iconBtn(canvas, 'BtnBack', -310, 720, '');
  for (let i = 0; i < 3; i++) {
    const b = canvas.kid(new Node('Level' + (i + 1), i === 2 ? -160 : -160 + i * 320, i === 2 ? -80 : 220, 190, 250)).add(new Button({ interactable: true }));
    b.add(new Sprite({ spriteFrame: { name: 'level_card' }, type: 1 }));
    label(b, 'Num', 0, 160, 60, 40, String(i + 1), 28);
  }
  canvas.kid(new Node('Preview', 160, -80, 200, 180)).add(new Sprite({ spriteFrame: { name: 'default_sprite_splash' }, type: 0 }));
} else if (sceneName === 'mixed_captions' || sceneName === 'ribbon_captions') {
  // user 2026-10-23: five home feature buttons, captions made four different ways (bad) / one way for all (good)
  sprite(canvas, 'Logo', 0, 520, 480, 280);
  const spots = [['BtnLevels', -250, -300, 'LEVELS'], ['BtnSouvenirs', 0, -300, 'SOUVENIRS'], ['BtnSettings', 250, -300, 'SETTINGS'],
                 ['BtnShortcut', -150, -560, 'HOME SCREEN +2'], ['BtnRevisit', 150, -560, 'PROFILE REVISIT +2']];
  spots.forEach(([n, x, y, cap], i) => {
    canvas.kid(new Node(n, x, y, 130, 130)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'icon_' + n }, type: 0 }));
    if (sceneName === 'ribbon_captions') {
      sprite(canvas, 'CapPlate' + i, x, y - 95, 210, 56).getComponent(Sprite).spriteFrame.name = 'caption_ribbon';
      picText(canvas, 'Cap' + i, x, y - 95, 180, 40, cap);
    } else if (i < 2) {
      picText(canvas, 'Cap' + i, x, y - 95, 200, 50, cap);                              // separate picture-text ribbons
    } else if (i === 2) {
      fontLabel(canvas, 'Cap' + i, x, y - 95, 200, 44, cap, 28);                         // typed, no plate
    } else {
      sprite(canvas, 'CapPlate' + i, x, y - 95, 280, 60).getComponent(Sprite).spriteFrame.name = 'caption_cloud';
      fontLabel(canvas, 'Cap' + i, x, y - 95, 260, 44, cap, 26);                         // typed on a cloud plate
    }
  });
} else if (sceneName === 'good_map') {           // user 2026-10-22: path map, total shown, bonus gift and a boss level
  sprite(canvas, 'Title', 0, 640, 520, 150);
  picText(canvas, 'ProgressTxt', -90, 545, 160, 50, 'Level');
  label(canvas, 'Progress', 80, 545, 180, 50, '12 / 70', 32);
  iconBtn(canvas, 'BtnBack', -300, 540, '');
  for (let i = 0; i < 12; i++) {
    const n = 9 + i, boss = n === 20;
    const b = canvas.kid(new Node('Level' + n, (i % 4 - 1.5) * 170, -650 + i * 95, boss ? 170 : 120, boss ? 170 : 90)).add(new Button({ interactable: true }));
    b.add(new Sprite({ spriteFrame: { name: boss ? 'node_boss' : n === 14 ? 'node_bonus' : 'node' }, type: 0 }));
    label(b, 'Num', 0, 0, 60, 40, String(n), 28);
    if (n === 14) sprite(b, 'GiftMark', 50, 40, 50, 50);
    if (boss) sprite(b, 'BossMark', 0, 70, 90, 70);
    if (n < 12) sprite(b, 'Stars', 0, -50, 90, 30);
  }
} else if (sceneName === 'teal_shop') {          // user 2026-10-22: font text in dark teal, typed arrows on flat boxes
  const TEAL = Object.assign({}, FONT, { color: { r: 38, g: 74, b: 86 }, enableOutline: false, isBold: true });
  const panel = sprite(canvas, 'Panel', 0, 0, 680, 1400, true);
  picText(panel, 'Title', 0, 560, 420, 120, 'Collection');
  panel.kid(new Node('Wallet', 0, 450, 520, 50)).add(new Label(Object.assign({}, TEAL, { string: 'COINS 47   PEARLS 17', fontSize: 34 })));
  panel.kid(new Node('Name', 0, 360, 500, 70)).add(new Label(Object.assign({}, TEAL, { string: 'Buttercup Mini', fontSize: 44 })));
  sprite(panel, 'Skin', 0, 50, 360, 260);
  panel.kid(new Node('Price', 0, -170, 420, 50)).add(new Label(Object.assign({}, TEAL, { string: 'Price · 250 coins', fontSize: 36 })));
  ['Prev', 'Next'].forEach((n, i) => {
    const b = canvas.kid(new Node('Btn' + n, i ? 300 : -300, 50, 140, 140)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'arrow_box' }, type: 1 }));
    b.kid(new Node('Txt', 0, 0, 60, 60)).add(new Label(Object.assign({}, TEAL, { string: i ? '>' : '<', fontSize: 40 })));
  });
  const u = plateBtn(panel, 'BtnUnlock', 0, -330, 300, 90, 'Unlock');
} else if (sceneName === 'checkin' || sceneName === 'checkin_small7') {   // user 2026-10-22: 7-day Daily Reward
  canvas.kid(new Node('Mask', 0, 0, 750, 1624, { opacity: 150 })).add(new BlockInputEvents()).add(new Sprite({ spriteFrame: { name: 'mask' }, type: 0 }));
  const panel = sprite(canvas, 'Panel', 0, 0, 640, 1000, true);
  label(panel, 'Title', 0, 420, 320, 60, 'Daily Reward', 40);
  iconBtn(panel, 'BtnClose', 220, 400, '');
  for (let i = 0; i < 6; i++) {
    const card = sprite(panel, 'Day' + (i + 1), -190 + (i % 3) * 190, 230 - Math.floor(i / 3) * 210, 170, 190, true);
    card.kid(new Node('CardSurface', 0, 0, 170, 190)).add(new Graphics({ lineWidth: 3 }));
    label(card, 'Num', -60, 70, 40, 36, String(i + 1), 26);
    sprite(card, 'Icon', 0, 10, 90, 90);
    label(card, 'Amount', 0, -65, 150, 30, i % 2 ? 'Energy x' + (i + 1) : 'Coins x' + (100 * (i + 1)), 24);
  }
  const big = sceneName === 'checkin';
  const c7 = sprite(panel, 'Day7', big ? 0 : 0, -230, big ? 560 : 170, big ? 200 : 150, true);
  c7.kid(new Node('CardSurface', 0, 0, big ? 560 : 170, big ? 200 : 150)).add(new Graphics({ lineWidth: 3 }));
  label(c7, 'Num', big ? -250 : -60, 70, 40, 36, '7', 26);
  sprite(c7, 'Chest', big ? 160 : 0, 0, big ? 200 : 80, big ? 170 : 80);
  label(c7, 'Gift', big ? -60 : 0, 0, big ? 300 : 150, 40, 'Mystery Gift', big ? 34 : 22);
  panel.kid(new Node('btn_claim', 0, -400, 260, 90)).add(new Button({ interactable: true }))
    .add(new Sprite({ spriteFrame: { name: 'btn_claim' }, type: 0 })); // actual generated plate has no live text label
} else if (sceneName === 'plain_text_result') {   // user 2026-10-22: thin system-font text on a cream panel, white RETRY
  const PLAIN = { font: null, useSystemFont: true, color: { r: 40, g: 60, b: 80 } };
  const panel = sprite(canvas, 'Panel', 0, 0, 640, 1100, true);
  panel.kid(new Node('Title', 0, 420, 400, 70)).add(new Label(Object.assign({ string: 'NEW BEST!', fontSize: 44, overflow: 0 }, PLAIN)));
  panel.kid(new Node('Saved', 0, 120, 400, 40)).add(new Label(Object.assign({ string: 'Saved to your collection', fontSize: 26, overflow: 0 }, PLAIN)));
  const retry = panel.kid(new Node('BtnRetry', 0, -100, 300, 70)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn_retry' }, type: 1 }));
  retry.kid(new Node('Txt', 0, 0, 200, 50)).add(new Label({ string: 'RETRY', fontSize: 36, overflow: 0, font: null, useSystemFont: true, color: { r: 250, g: 248, b: 240 } }));
} else if (sceneName === 'empty_league') {        // the "Weekly Rankings" screenshot: a big blank panel
  canvas.kid(new Node('Mask', 0, 0, 750, 1624, { opacity: 150 })).add(new BlockInputEvents()).add(new Sprite({ spriteFrame: { name: 'mask' }, type: 0 }));
  const panel = sprite(canvas, 'Panel', 0, 0, 660, 1200, true);
  label(panel, 'Title', 0, 520, 420, 70, 'Weekly Rankings', 44);
  label(panel, 'Mine', 0, -480, 300, 40, 'Your rank: 5432', 28);
  iconBtn(panel, 'BtnClose', 290, 560, '');
} else if (sceneName === 'league') {
  const panel = sprite(canvas, 'Panel', 0, -20, 680, 1300, true);
  sprite(panel, 'TierBadge', 0, 560, 200, 160);
  label(panel, 'Title', 0, 450, 420, 60, 'Weekly League', 42);
  label(panel, 'Ends', 0, 395, 300, 36, 'Ends in 2d 5h', 26);
  for (let i = 0; i < 9; i++) {
    const row = sprite(panel, 'Row' + i, 0, 300 - i * 95, 620, 85, true);
    label(row, 'Rank', -260, 0, 70, 40, String(84 + i), 30);
    sprite(row, 'Avatar', -180, 0, 64, 64);
    fontLabel(row, 'Name', -20, 0, 240, 40, i === 5 ? 'You' : 'SunnyFox' + (20 + i), 28);   // rival names change at run time
    label(row, 'Score', 230, 0, 130, 40, String(1200 - i * 9), 28);
  }
  sprite(panel, 'NextSkin', -180, -560, 140, 140);
  label(panel, 'Reward', 60, -560, 320, 40, 'Top 1,000: League skin', 26);
  iconBtn(panel, 'BtnInfo', -290, 600, '');
  iconBtn(panel, 'BtnClose', 290, 600, '');
} else if (sceneName === 'squashed') {    // user 2026-10-23: words.png cells 570x345 forced into 234x49 (DETAILS 2.89x), RasterText.ts
  const sized = (node, w, h, extra) => { Object.assign(node.getComponent(Sprite).spriteFrame, { originalSize: { width: w, height: h }, rect: { x: 0, y: 0, width: w, height: h } }, extra || {}); return node; };
  const det = canvas.kid(new Node('BtnDetails', 0, 300, 468, 98)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'plate_green' }, type: 1 }));
  sized(det.kid(new Node('Word', 0, 0, 468, 98)).add(new Sprite({ spriteFrame: { name: 'words' }, type: 0 })), 570, 345);
  sized(canvas.kid(new Node('SkinsTitle', 0, 500, 300, 110)).add(new Sprite({ spriteFrame: { name: 'txt_skins' }, type: 0 })), 300, 200);
  sized(canvas.kid(new Node('MapTitle', 0, 650, 300, 110)).add(new Sprite({ spriteFrame: { name: 'txt_map' }, type: 0 })), 600, 220);   // uniform: fine
  sized(canvas.kid(new Node('ProgressFill', 0, 100, 500, 30)).add(new Sprite({ spriteFrame: { name: 'bar_fill' }, type: 0 })), 100, 30);   // a bar may stretch
  sized(canvas.kid(new Node('Mascot', 0, -200, 300, 300)).add(new Sprite({ spriteFrame: { name: 'mascot' }, type: 0 })), 300, 500);
  const raster = canvas.kid(new Node('CoinsRaster', 0, -500, 400, 80)).add(new Sprite({ spriteFrame: { name: 'raster_coins' }, type: 0 }));
  raster.getComponent(Sprite).spriteFrame.texture = { image: { canvas_drawn: true } };
} else if (sceneName === 'blurry') {    // user 2026-10-23 ART-04: source pixels vs CSS pixels: gameplay:10 140x126 for 82.5x90; background 550x1190 for 375x812
  const own = (node, w, h) => { Object.assign(node.getComponent(Sprite).spriteFrame, { originalSize: { width: w, height: h }, rect: { x: 0, y: 0, width: w, height: h } }); return node; };
  own(canvas.kid(new Node('GameBg', 0, 0, 750, 1624)).add(new Sprite({ spriteFrame: { name: 'bg_spa' }, type: 0 })), 550, 1190);
  own(canvas.kid(new Node('Robot', -150, 0, 165, 180)).add(new Sprite({ spriteFrame: { name: 'gameplay:10' }, type: 0 })), 140, 126);
  own(canvas.kid(new Node('OldShelf', 150, 0, 200, 200)).add(new Sprite({ spriteFrame: { name: 'orig_shelf' }, type: 0 })), 100, 100);
  canvas.kid(new Node('Tray', 0, -400, 310, 210)).add(new Sprite({ spriteFrame: { name: 'plates-tray' }, type: 0 }));   // 2x: sharp
} else if (sceneName === 'daily_overlap') {   // user 2026-10-23 Daily Rewards: "100" printed as "10" over "100", day-7 car out of its card
  canvas.kid(new Node('Mask', 0, 0, 750, 1624, { opacity: 150 })).add(new BlockInputEvents()).add(new Sprite({ spriteFrame: { name: 'mask' }, type: 0 }));
  const panel = sprite(canvas, 'Panel', 0, 0, 660, 1100, true);
  picText(panel, 'Title', 0, 470, 360, 70, 'Daily Rewards');
  const c1 = sprite(panel, 'Day1', -200, 280, 180, 230, true);
  sprite(c1, 'Coin', 0, 25, 90, 90).getComponent(Sprite).spriteFrame.name = 'icon_coin';
  const digits = c1.kid(new Node('Reward', 0, -65, 130, 50));
  ['1', '0', '0'].forEach((g, i) => { sprite(digits, 'D' + i, -24 + i * 24, 0, 44, 50).getComponent(Sprite).spriteFrame.name = 'num_' + g; });   // 44 px glyphs every 24 px
  const c2 = sprite(panel, 'Day2', 0, 280, 180, 230, true);
  sprite(c2, 'Coin', 0, 25, 90, 90).getComponent(Sprite).spriteFrame.name = 'icon_coin';
  const amt = numLabel(c2, 'Amount', 0, -65, 130, 44, '150', 30);
  numLabel(amt, 'Copy', -10, 0, 90, 44, '15', 30);                     // a second label printed on top of the first
  const c3 = sprite(panel, 'Day3', 200, 280, 180, 230, true);
  sprite(c3, 'Coin', 0, 25, 90, 90).getComponent(Sprite).spriteFrame.name = 'icon_coin';
  c3.kid(new Node('Amount', 0, -65, 130, 44)).add(new Label(Object.assign({ string: '200', fontSize: 30, overflow: 2, spacingX: -14 }, BMFONT)));
  sprite(panel, 'Day7', 0, -120, 560, 220, true);
  sprite(panel, 'Car', 150, -60, 200, 420).getComponent(Sprite).spriteFrame.name = 'reward_car';   // drawn on the card, sticks far out of it
  plateBtn(panel, 'BtnClaim', 0, -420, 260, 90, 'Claim');
} else if (sceneName === 'clipping') {    // user 2026-10-23: "20" on the lightning icon, coin pile off WATCH AD, action caption
  const cap = canvas.kid(new Node('EnergyBar', -150, 700, 260, 70)).add(new Sprite({ spriteFrame: { name: 'capsule' }, type: 1 }));
  sprite(cap, 'EnergyIcon', -110, 0, 90, 90).getComponent(Sprite).spriteFrame.name = 'icon_lightning';
  cap.kid(new Node('EnergyCount', -60, 0, 70, 44)).add(new Label(Object.assign({ string: '20', fontSize: 32, overflow: 0 }, BMFONT)));
  const ad = canvas.kid(new Node('BtnWatchAd', 0, 200, 420, 140)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn_watch_ad' }, type: 0 }));
  sprite(ad, 'CoinPile', -230, 0, 160, 140).getComponent(Sprite).spriteFrame.name = 'coin_pile';
  canvas.kid(new Node('AdCaption', 0, 100, 420, 40)).add(new Sprite({ spriteFrame: { name: 'txt_WATCH_AD_DOUBLE_COINS' }, type: 0 }));
  canvas.kid(new Node('BtnHome', -100, -300, 260, 120)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn_home' }, type: 0 }));
  canvas.kid(new Node('BtnShop', 50, -300, 260, 120)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn_shop' }, type: 0 }));
} else if (sceneName === 'settings' || sceneName === 'settings_sound') {   // references/common-game-components.md
  canvas.kid(new Node('Mask', 0, 0, 750, 1624, { opacity: 150 })).add(new BlockInputEvents()).add(new Sprite({ spriteFrame: { name: 'mask' }, type: 0 }));
  const panel = sprite(canvas, 'Panel', 0, 0, 640, 900, true);
  label(panel, 'Title', 0, 350, 280, 60, 'Settings', 40);
  plateBtn(panel, 'TabGeneral', -120, 220, 210, 70, 'General');
  plateBtn(panel, 'TabSound', 120, 220, 210, 70, 'Sound');
  iconBtn(panel, 'BtnClose', 210, 330, '');
  if (sceneName === 'settings') {
    [['Vibration', 'ON'], ['How to Play', ''], ['Credits', ''], ['About', '']].forEach(([t, v], i) => {
      const row = sprite(panel, 'Row' + i, 0, 120 - i * 112, 520, 95, true);
      sprite(row, 'Icon', -220, 0, 70, 70);
      label(row, 'Name', -40, 0, 260, 44, t, 30);
      plateBtn(row, 'Btn', 190, 0, 140, 70, v || 'Open');
    });
    label(panel, 'Version', 0, -380, 200, 30, 'v1.0.3', 24);
  } else {
    [['Music', '70%'], ['Sound Effects', '100%']].forEach(([t, v], i) => {
      const row = sprite(panel, 'Row' + i, 0, 60 - i * 250, 520, 210, true);
      sprite(row, 'Icon', -230, 50, 70, 70);
      label(row, 'Name', -60, 50, 260, 44, t, 30);
      plateBtn(row, 'Switch', 200, 50, 120, 64, 'ON');
      iconBtn(row, 'Minus', -230, -50, '');
      for (let k = 0; k < 10; k++) sprite(row, 'Seg' + k, -150 + k * 32, -50, 26, 40);
      iconBtn(row, 'Plus', 200, -50, '');
      label(row, 'Pct', 120, 50, 90, 40, v, 28);
    });
  }
} else if (sceneName === 'copy') {
  const b = canvas.kid(new Node('BtnClaim', 0, -300, 160, 60)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn' }, type: 1 }));
  b.kid(new Node('Txt', 0, 0, 260, 40)).add(new Label({ string: 'Claim Reward Now', fontSize: 30, overflow: 0 }));
  const b2 = canvas.kid(new Node('BtnPlay', 0, -450, 300, 90)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'btn' }, type: 1 }));
  b2.kid(new Node('Txt', 0, 0, 200, 50)).add(new Label({ string: 'PLAY', fontSize: 40, overflow: 0 }));
  const plaque = canvas.kid(new Node('InfoPlaque', 0, 200, 400, 80)).add(new Sprite({ spriteFrame: { name: 'plaque' }, type: 1 }));
  plaque.kid(new Node('Info', 0, 0, 380, 60)).add(new Label({ string: 'Watch a short video to get double coins for this level', fontSize: 28, overflow: 1 }));
} else if (sceneName === 'menu') {
  canvas.kid(new Node('Title', 0, 450, 600, 180)).add(new Sprite({ spriteFrame: { name: 'title' }, type: 0 }));
  canvas.kid(new Node('BtnPlay', 0, -380, 360, 110)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'play' }, type: 0 }));
  const icons = [['BtnSettings', -320, 740], ['BtnShop', 320, 740], ['BtnSkins', -320, 0], ['BtnMap', 320, 0], ['BtnHelp', -320, -740]];
  for (const [n, x, y] of icons) {
    const b = canvas.kid(new Node(n, x, y, 90, 90)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: n }, type: 0 }));
    if (n === 'BtnShop') b.kid(new Node('Txt', 0, -55, 80, 26)).add(new Label({ string: 'Shop', fontSize: 22, overflow: 0 }));
  }
} else {
  const board = canvas.kid(new Node('Board', 0, -40, 700, 900));
  for (let i = 0; i < 6; i++) board.kid(new Node('Tile' + i, -250 + i * 100, 0, 90, 90)).add(new Sprite({ spriteFrame: { name: 'tile' }, type: 0 }));
  const top = canvas.kid(new Node('TopBar', 0, 740, 750, 120)).add(new Sprite({ spriteFrame: { name: 'topbar' }, type: 1 }));
  top.kid(new Node('CoinIcon', -300, 0, 60, 60)).add(new Sprite({ spriteFrame: { name: 'coin' }, type: 0 }));
  top.kid(new Node('CoinText', -220, 0, 120, 50)).add(new Label(Object.assign({ string: '1,250', fontSize: 36, overflow: 0 }, BMFONT)));
  canvas.kid(new Node('BtnPause', 310, 600, 80, 80)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'pause' }, type: 0 }));
  canvas.kid(new Node('Hidden', 0, 0, 300, 300, { active: false })).add(new Label({ string: 'SECRET', fontSize: 30, overflow: 0 }));
  canvas.kid(new Node('Faded', 0, 300, 300, 100, { opacity: 0 })).add(new Label({ string: 'GONE', fontSize: 30, overflow: 0 }));
  canvas.kid(new Node('TipBubble', 0, 600, 300, 80)).add(new Sprite({ spriteFrame: { name: 'txt_Tap_two_tiles' }, type: 0 }));
  if (sceneName === 'pause') {
    const pop = canvas.kid(new Node('PausePopup', 0, 0, 750, 1624));
    pop.kid(new Node('Mask', 0, 0, 750, 1624, { opacity: 150 })).add(new BlockInputEvents()).add(new Sprite({ spriteFrame: { name: 'mask' }, type: 0 }));
    const panel = pop.kid(new Node('Panel', 0, 0, 560, 720)).add(new Sprite({ spriteFrame: { name: 'panel', insetLeft: 40, insetRight: 40, insetTop: 60, insetBottom: 40 }, type: 1 }));
    panel.kid(new Node('Title', 0, 270, 320, 80)).add(new Label({ string: 'PAUSED', fontSize: 48, overflow: 0 }));
    panel.kid(new Node('CornerTL', -270, 350, 80, 80)).add(new Sprite({ spriteFrame: { name: 'corner' }, type: 0 }));
    panel.kid(new Node('BtnResume', 0, -150, 360, 100)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'resume' }, type: 0 }));
    panel.kid(new Node('BtnHome', 0, -270, 360, 100)).add(new Button({ interactable: true })).add(new Sprite({ spriteFrame: { name: 'home' }, type: 0 }));
  }
}
if (BAR) {
  const top = canvas.kid(new Node('TopBar', 0, 760, 750, 90));
  [['Energy', -270, 'icon_lightning', '5/5'], ['Pearls', -100, BAR === 'coinbar' ? 'icon_coin' : 'icon_pearl', '1,250'], ['Level', 70, 'icon_flag', '12']]
    .forEach(([n, x, icon, v]) => {
      const c = top.kid(new Node(n, x, 0, 150, 64)).add(new Sprite({ spriteFrame: { name: 'capsule' }, type: 1 }));
      sprite(c, 'Icon', -60, 0, 64, 64).getComponent(Sprite).spriteFrame.name = icon;
      label(c, 'Count', 15, 0, 90, 44, v, 30);
    });
}
if (api === 2) for (const n of [scene]) n.opacity = 255;

const cc = {
  director: { getScene: () => scene }, ENGINE_VERSION: api === 3 ? '3.8.8' : '2.4.13',
  Canvas, Button, Label, RichText, Sprite, Graphics, BlockInputEvents, ProgressBar, Toggle: null, ScrollView: null, EditBox: null, Mask: null, Widget: null,
  game: { canvas: { width: 750, height: 1624, getBoundingClientRect: () => ({ x: 0, y: 0, width: 375, height: 812 }) } },
  view: { getVisibleSize: () => ({ width: 750, height: 1624 }), getVisibleOrigin: () => ({ x: 0, y: 0 }) }, Camera,
};
if (api === 3) { cc.UITransform = UITransform; cc.UIOpacity = UIOpacity; cc.Vec3 = function (x, y, z) { this.x = x; this.y = y; this.z = z; }; }
else { cc.v2 = (x, y) => ({ x, y }); }
if (canvasEl) cc.game.canvas = canvasEl;
return cc;
}

if (typeof module !== 'undefined' && typeof require !== 'undefined' && require.main === module) {
const fs = require('fs');
const path = require('path');
const api = process.argv[2] === '2' ? 2 : 3;
const sceneName = process.argv[3] || 'play';
const cc = buildMockCc(api, sceneName);
global.window = { cc, innerWidth: 375, innerHeight: 812, devicePixelRatio: 2 };
global.document = { querySelector: () => cc.game.canvas };
const dump = eval(fs.readFileSync(path.join(__dirname, 'ui_dump.js'), 'utf8'))({});
const baseScene = sceneName.replace(/^offset_/, '').split('+')[0];
dump.screen = { menu: 'home_9x19', play: 'play_9x19', pause: 'pause_9x19' }[sceneName] || sceneName;
dump.kind = { menu: 'home', play: 'gameplay', pause: 'popup', bad_home: 'home', good_home: 'home', typed_home: 'home', button_home: 'home', scattered_home: 'home', plain_popup: 'popup', reward_popup: 'popup', round2_home: 'home', good_result: 'popup',
  empty_league: 'popup', settings: 'popup', settings_sound: 'popup', checkin: 'popup', checkin_small7: 'popup' }[baseScene] || 'page';
dump.purpose = { menu: 'home', bad_home: 'home', good_home: 'home', typed_home: 'home', button_home: 'home', scattered_home: 'home', plain_popup: 'reward', reward_popup: 'reward', bad_result: 'result_win', good_result: 'result_win',
  empty_league: 'league', league: 'league', pause: 'pause', settings: 'settings', settings_sound: 'settings_sound', checkin: 'checkin', checkin_small7: 'checkin', good_map: 'map' }[baseScene] || 'other';
dump.producer = 'chrome_touch.dump_ui';
process.stdout.write(JSON.stringify(dump, null, 1));
}
