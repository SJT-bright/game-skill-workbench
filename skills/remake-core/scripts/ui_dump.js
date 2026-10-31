(opts) => {
  // Reads the live Cocos scene (Creator 2.4 and 3.x) and returns every active UI node with its real on-screen box.
  // Used by chrome_touch.py {"type":"dump_ui"}; extract_ui_layout.py turns dumps into docs/ui-layout.json and
  // audit_copy_quality.py reads the label texts. Nothing here is typed in by hand (user rule 2026-10-21).
  opts = opts || {};
  // A developer-controlled pre-engine DOM splash has no Cocos scene yet.
  // This captures it, but never grants the official-loading exception. The
  // Python consumers still verify original source bytes and actual pixels.
  if (typeof window.getComputedStyle === 'function' && typeof document.querySelectorAll === 'function') {
    const root = document.querySelector('[data-cocos-official-loading], #splash');
    const visible = el => { const st = window.getComputedStyle(el); const r = el.getBoundingClientRect();
      return st.display !== 'none' && st.visibility !== 'hidden' && Number(st.opacity || 1) > 0.05 && r.width > 0 && r.height > 0; };
    let sceneReady = false;
    try { sceneReady = !!(window.cc && window.cc.director && window.cc.director.getScene && window.cc.director.getScene()); } catch (_) {}
    const wrapsGame = root && sceneReady && [...root.querySelectorAll('canvas')].some(visible);
    if (root && visible(root) && !wrapsGame) {
      const cr = root.getBoundingClientRect(), nodes = [], failures = [];
      const rgb = value => { const n = String(value || '').match(/[\d.]+/g); return n ? n.slice(0, 3).map(Number) : null; };
      const rect = r => [(r.x-cr.x)/cr.width,(r.y-cr.y)/cr.height,r.width/cr.width,r.height/cr.height];
      const add = (path, r, comps, depth=1) => nodes.push({path,name:path.split('/').pop(),depth,order:nodes.length,
        opacity:1,rect:rect(r),screen:rect(r),comps});
      const style = window.getComputedStyle(root);
      if (cr.x !== 0 || cr.y !== 0 || Math.abs(cr.width-window.innerWidth)>1 || Math.abs(cr.height-window.innerHeight)>1)
        failures.push('DOM splash must cover the actual phone viewport');
      add('DOMLoading', cr, {graphics:{fillColor:rgb(style.backgroundColor)}} ,0);
      const bg = style.backgroundImage;
      if (bg && bg !== 'none') {
        // Official Creator 2.4 template: original 547x200 splash at a percentage
        // width and centered. A different asset/style must not inherit this fit.
        const m = String(style.backgroundSize).match(/^([\d.]+)%(?: auto)?$/);
        if (!m || !['50% 50%','center center'].includes(style.backgroundPosition)) failures.push('unsupported splash background fit');
        else { const width = cr.width * Number(m[1])/100, height = width*200/547;
          add('DOMLoading/Logo',{x:cr.x+(cr.width-width)/2,y:cr.y+(cr.height-height)/2,width,height},
            {sprite:{frame:'cocos_official_logo',frame_size:[547,200],display_size:[width,height],css_display_size:[width,height],source_url:bg}}); }
      }
      const elements = [root,...root.querySelectorAll('*')];
      for (let i=0;i<elements.length;i++) {
        const el=elements[i];if(!visible(el))continue;
        const st=window.getComputedStyle(el),r=el.getBoundingClientRect(),path='DOMLoading/E'+i,comps={};
        if(el.tagName==='CANVAS') {failures.push('visible canvas under DOM splash cannot be omitted');continue;}
        if(el.tagName==='IMG') {
          if(!el.complete || !el.naturalWidth || !el.naturalHeight)failures.push('splash image not decoded');
          comps.sprite={frame:'cocos_official_logo',frame_size:[el.naturalWidth,el.naturalHeight],
            display_size:[r.width,r.height],css_display_size:[r.width,r.height],source_url:el.currentSrc||el.src};
        }
        const progress=el.tagName==='PROGRESS'||el.getAttribute('role')==='progressbar'||el.classList.contains('progress-bar');
        if(progress) {const child=el.firstElementChild;const value=el.tagName==='PROGRESS'?el.value/el.max:
          el.hasAttribute('aria-valuenow')?Number(el.getAttribute('aria-valuenow'))/100:child?child.getBoundingClientRect().width/r.width:0;
          comps.progress={value};comps.graphics={fillColor:rgb(st.backgroundColor)||[23,23,23]};}
        const progressParent=el.parentElement;
        const progressFill=progressParent && (progressParent.tagName==='PROGRESS'||progressParent.getAttribute('role')==='progressbar'||progressParent.classList.contains('progress-bar'));
        if(progressFill)comps.graphics={fillColor:rgb(st.backgroundColor)};
        if(el!==root && st.backgroundImage && st.backgroundImage!=='none' && !/^linear-gradient/.test(st.backgroundImage))failures.push('nonofficial DOM background picture');
        const text=[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim();
        if(text)comps.label={string:text,fontSize:parseFloat(st.fontSize),actualFontSize:parseFloat(st.fontSize),height:r.height,
          color:rgb(st.color),bold:Number(st.fontWeight)>=600,system_font:true,font_kind:'system'};
        if(el.tagName==='BUTTON'||el.getAttribute('role')==='button')comps.button={interactable:!el.disabled,enabled:!el.disabled};
        if(Object.keys(comps).length) {
          // Keep actual DOM ancestry so Retry labels and progress fills stay bound.
          let parent=el.parentElement;const ancestors=[];while(parent&&parent!==root){ancestors.unshift(elements.indexOf(parent));parent=parent.parentElement;}
          const prefix='DOMLoading/'+ancestors.map(n=>'E'+n).join('/');
          add((prefix.endsWith('/')?prefix:prefix+'/')+'E'+i,r,comps,ancestors.length+1);
        }
      }
      return {tool:'ui_dump',schema:1,api:'dom-loading',engine:'',scene:'DOMLoading',page:{width:window.innerWidth,height:window.innerHeight,dpr:window.devicePixelRatio||1},
        canvas_css:[cr.x,cr.y,cr.width,cr.height],canvases:0,errors:failures,nodes};
    }
  }
  const cc = window.cc;
  const fail = (msg) => ({ tool: 'ui_dump', schema: 1, error: msg });
  if (!cc || !cc.director || typeof cc.director.getScene !== 'function') {
    return fail('cc.director not found: this page is not a running Cocos game yet (wait until the first scene is shown)');
  }
  const scene = cc.director.getScene();
  if (!scene) return fail('no running scene yet');
  const is3 = !!cc.UITransform;
  const T = {};
  for (const k of ['Canvas', 'Button', 'Toggle', 'Label', 'RichText', 'Sprite', 'Graphics', 'ProgressBar', 'BlockInputEvents',
                   'ScrollView', 'UIOpacity', 'EditBox', 'Mask', 'Widget', 'LabelOutline', 'LabelShadow', 'Camera']) T[k] = cc[k] || null;
  const errors = [];
  const get = (node, ctor) => { if (!ctor) return null; try { return node.getComponent(ctor); } catch (e) { return null; } };
  const sizeOf = (node) => {
    if (is3) {
      const ut = get(node, cc.UITransform);
      if (!ut) return null;
      return { w: ut.contentSize.width, h: ut.contentSize.height, ax: ut.anchorPoint.x, ay: ut.anchorPoint.y, ut };
    }
    return { w: node.width, h: node.height, ax: node.anchorX, ay: node.anchorY };
  };
  const toWorld = (node, s, x, y) => {
    if (is3) { const v = s.ut.convertToWorldSpaceAR(new cc.Vec3(x, y, 0)); return [v.x, v.y]; }
    const v = node.convertToWorldSpaceAR(cc.v2(x, y)); return [v.x, v.y];
  };
  // World box of the node itself (children not included), optionally shrunk by local insets.
  const box = (node, s, l, b, r, t) => {
    const x0 = -s.ax * s.w + l, x1 = (1 - s.ax) * s.w - r, y0 = -s.ay * s.h + b, y1 = (1 - s.ay) * s.h - t;
    const pts = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].map((p) => toWorld(node, s, p[0], p[1]));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
  };
  // Normalised [x, y, w, h] inside the Canvas, top-left origin (0..1 = the whole game canvas).
  const norm = (wb, cb) => {
    const cw = cb.maxX - cb.minX, ch = cb.maxY - cb.minY;
    const r = [(wb.minX - cb.minX) / cw, 1 - (wb.maxY - cb.minY) / ch, (wb.maxX - wb.minX) / cw, (wb.maxY - wb.minY) / ch];
    return r.map((v) => Math.round(v * 100000) / 100000);
  };
  const ownOpacity = (node) => {
    if (is3) { const o = get(node, T.UIOpacity); return o ? o.opacity / 255 : 1; }
    return typeof node.opacity === 'number' ? node.opacity / 255 : 1;
  };
  const canvasEl = (cc.game && cc.game.canvas) || document.querySelector('canvas');
  if (!canvasEl) return fail('no game <canvas> element');
  // Where the render camera really draws each node (user 2026-10-22: a camera offset once made buttons look fine but
  // not react). 3.x: Camera component worldToScreen -> canvas backing pixels; 2.x: Camera.findCamera + visible size.
  const cams = [];
  const findCams = (n) => { if (!n || n.active === false) return; const c = get(n, T.Camera); if (c && c.enabled !== false) cams.push(c);
                           (n.children || []).forEach(findCams); };
  try { findCams(scene); } catch (e) { /* camera lookup is best effort */ }
  const camFor = (node) => {
    if (!is3) { try { return cc.Camera && cc.Camera.findCamera ? cc.Camera.findCamera(node) : null; } catch (e) { return null; } }
    const seen = cams.filter((c) => typeof c.visibility !== 'number' || typeof node.layer !== 'number' || (c.visibility & node.layer));
    return seen.sort((a, b) => (b.priority || 0) - (a.priority || 0))[0] || null;
  };
  const toScreen = (cam, wx, wy) => {
    if (is3) {
      const v = cam.worldToScreen(new cc.Vec3(wx, wy, 0), new cc.Vec3());
      const bw = canvasEl.width || cr.width, bh = canvasEl.height || cr.height;
      return [v.x / bw, 1 - v.y / bh];
    }
    const v = cam.getWorldToScreenPoint(cc.v2(wx, wy), cc.v2());
    const vs = cc.view.getVisibleSize(), vo = cc.view.getVisibleOrigin ? cc.view.getVisibleOrigin() : { x: 0, y: 0 };
    return [(v.x - vo.x) / vs.width, 1 - (v.y - vo.y) / vs.height];
  };
  const screenBox = (node, s) => {
    const cam = camFor(node);
    if (!cam) return null;
    const x0 = -s.ax * s.w, x1 = (1 - s.ax) * s.w, y0 = -s.ay * s.h, y1 = (1 - s.ay) * s.h;
    const pts = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].map((p) => { const w = toScreen(cam, ...toWorld(node, s, p[0], p[1])); return w; });
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const r = [Math.min(...xs), Math.min(...ys), Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
    return r.every((v) => isFinite(v)) ? r.map((v) => Math.round(v * 100000) / 100000) : null;
  };
  const rawCanvasRect=canvasEl.getBoundingClientRect();const cr={x:rawCanvasRect.x??rawCanvasRect.left??0,y:rawCanvasRect.y??rawCanvasRect.top??0,width:rawCanvasRect.width,height:rawCanvasRect.height};
  const SLICED = T.Sprite && T.Sprite.Type ? T.Sprite.Type.SLICED : 1;
  const maxNodes = opts.maxNodes || 4000;
  const nodes = [];
  let order = 0, canvases = 0;
  const fontKind = (lab) => {
    const f = lab.font;
    if (!f) return lab.useSystemFont === false ? '' : 'system';
    const ctor = String((f.constructor && f.constructor.name) || f.__classname__ || '');
    if (/Bitmap|LabelAtlas|BMFont/i.test(ctor) || f.fntConfig || f._fntConfig || typeof f.fntDataStr === 'string' || f.spriteFrame) return 'bitmap';
    return 'ttf';
  };
  let rootBox = null;
  if (!is3) {
    const firstCanvas = (function find(n) { for (const c of (n.children || [])) { if (get(c, T.Canvas)) return c; const r = find(c); if (r) return r; } return null; })(scene);
    const fs = firstCanvas && sizeOf(firstCanvas);
    if (fs && fs.w > 0 && fs.h > 0) rootBox = box(firstCanvas, fs, 0, 0, 0, 0);
  }
  const walk = (node, path, depth, canvasBox, opacity) => {
    if (!node || nodes.length >= maxNodes) return;
    if (node !== scene && node.active === false) return;
    const name = node.name || '?';
    const here = node === scene ? '' : (path ? path + '/' + name : name);
    let cb = canvasBox;
    // 2.x panels added straight to the scene root (outside Canvas) are drawn and take touches too; measure them in
    // the first Canvas's box (指尖麻将 v55: the result panel lived there and no dump ever listed its buttons).
    const outside = !is3 && !cb && node !== scene && node.parent === scene && rootBox && !get(node, T.Canvas);
    if (outside) cb = rootBox;
    const op = opacity * (node === scene ? 1 : ownOpacity(node));
    try {
      if (node !== scene && get(node, T.Canvas)) {
        const s = sizeOf(node);
        if (s && s.w > 0 && s.h > 0) { cb = box(node, s, 0, 0, 0, 0); canvases += 1; }
        else if(is3 && camFor(node)) {
          // Manual Cocos3 UI may use a zero-width Canvas parent. Measure the
          // actual rendering camera viewport; a zero parent is not an empty UI.
          const cam=camFor(node),lo=cam.screenToWorld(new cc.Vec3(0,0,0)),hi=cam.screenToWorld(new cc.Vec3(canvasEl.width,canvasEl.height,0));
          if(hi.x>lo.x && hi.y>lo.y){cb={minX:lo.x,maxX:hi.x,minY:lo.y,maxY:hi.y};canvases+=1;}
        }
      }
      if (node !== scene && cb) {
        const s = sizeOf(node);
        if (s && s.w > 0 && s.h > 0) {
          const rec = { path: here, id: node.uuid || node._id || '', name, depth, order: order++, opacity: Math.round(op * 1000) / 1000,
                        rect: norm(box(node, s, 0, 0, 0, 0), cb), comps: {} };
          rec.ancestor_ids=[];for(let parent=node.parent;parent;parent=parent.parent){const id=parent.uuid||parent._id;if(id)rec.ancestor_ids.push(id);}
          if (get(node, T.Canvas)) rec.comps.canvas = true;
          if (rootBox && cb === rootBox) rec.outside_canvas = true;
          // Keep the local sprite orientation in the dump. The screen rect is an axis-aligned box;
          // comparing that box directly to an unrotated SpriteFrame falsely reports stretch at 90°.
          const angle = is3 ? (node.eulerAngles && node.eulerAngles.z) : node.angle;
          if (typeof angle === 'number') rec.angle = Math.round(angle * 100) / 100;
          if (is3 && typeof node.layer === 'number') rec.layer = node.layer;
          try { const sb = screenBox(node, s); if (sb) rec.screen = sb; } catch (e) { /* no camera */ }
          const progress = get(node, T.ProgressBar);
          if (progress && progress.enabled !== false) rec.loading_progress = { value: progress.progress };
          const btn = get(node, T.Button) || get(node, T.Toggle);
          if (btn) rec.comps.button = { interactable: btn.interactable !== false, enabled: btn.enabled !== false };
          const graphics = get(node, T.Graphics);
          if (graphics && graphics.enabled !== false) rec.comps.graphics = { lineWidth: typeof graphics.lineWidth === 'number' ? graphics.lineWidth : null, fillColor: graphics.fillColor ? [graphics.fillColor.r, graphics.fillColor.g, graphics.fillColor.b, graphics.fillColor.a] : null, strokeColor: graphics.strokeColor ? [graphics.strokeColor.r, graphics.strokeColor.g, graphics.strokeColor.b, graphics.strokeColor.a] : null };
          const lab = get(node, T.Label);
          if (lab && lab.enabled !== false) {
            rec.comps.label = { string: String(lab.string == null ? '' : lab.string).slice(0, 500), fontSize: lab.fontSize,
                                width: s.w, height: s.h,
                                overflow: typeof lab.overflow === 'number' ? lab.overflow : null,
                                actualFontSize: lab.actualFontSize || lab._actualFontSize || null,
                                // user 2026-10-23: digits printed over each other ("10" over "100"): spacing < 0 squeezes them
                                spacingX: typeof lab.spacingX === 'number' ? lab.spacingX : null,
                                font: lab.font ? String(lab.font.name || lab.font._name || 'custom') : '',
                                system_font: typeof lab.useSystemFont === 'boolean' ? lab.useSystemFont : null,
                                // user 2026-10-23: numbers are generated digit pictures (BitmapFont .fnt / LabelAtlas), not a TTF
                                font_kind: fontKind(lab),
                                bold: lab.enableBold === true || lab.isBold === true };
            const tc = is3 ? lab.color : node.color;                  // text colour: dark thick text is banned UI
            if (tc && typeof tc.r === 'number') rec.comps.label.color = [tc.r, tc.g, tc.b];
            const ol = T.LabelOutline ? get(node, T.LabelOutline) : null;          // 2.x component / 3.x Label fields
            const olOn = (ol && ol.enabled !== false) || lab.enableOutline === true;
            if (olOn) {
              const oc = ol ? ol.color : lab.outlineColor;
              rec.comps.label.outline = { width: (ol ? ol.width : lab.outlineWidth) || 0,
                                          color: oc && typeof oc.r === 'number' ? [oc.r, oc.g, oc.b] : null };
            }
            const sh = T.LabelShadow ? get(node, T.LabelShadow) : null;
            if ((sh && sh.enabled !== false) || lab.enableShadow === true) rec.comps.label.shadow = true;
          }
          const rich = get(node, T.RichText);
          if (rich && rich.enabled !== false) rec.comps.richtext = { string: String(rich.string || '').slice(0, 500), fontSize: rich.fontSize };
          const spr = get(node, T.Sprite);
          if (spr && spr.enabled !== false && spr.spriteFrame) {
            const sf = spr.spriteFrame;
            const TILED = T.Sprite && T.Sprite.Type ? T.Sprite.Type.TILED : 2;
            rec.comps.sprite = { whole_text_part: node.__wholeTextPart===true, frame: sf ? sf.name || '' : '', sliced: spr.type === SLICED, tiled: spr.type === TILED };
            // Clarity is measured against the phone's visible CSS size, not Cocos design units.
            // Keep display_size for geometry; screen is normalized to the camera output.
            if (rec.screen && cr.width > 0 && cr.height > 0) {
              rec.comps.sprite.css_display_size = [Math.round(rec.screen[2] * cr.width * 10) / 10,
                                                    Math.round(rec.screen[3] * cr.height * 10) / 10];
            }
            if (sf) {
              // user 2026-10-23: a word picture cropped 570x345 was forced into 234x49 (DETAILS squashed 2.89x). Record the
              // picture's own size and the size it is drawn at, so a non-uniform stretch is measured, not guessed.
              try {
                const fr = sf.rect || (sf.getRect && sf.getRect()) || sf._rect;
                const os = sf.originalSize || (sf.getOriginalSize && sf.getOriginalSize()) || sf._originalSize;
                const useRect = spr.trim !== false && fr && fr.width > 0;
                const fw = useRect ? fr.width : (os && os.width), fh = useRect ? fr.height : (os && os.height);
                if (fw > 0 && fh > 0) {
                  // Measure the two transformed local axes, not their rotated AABB. A 90° arrow
                  // has a wider AABB than its source but its image itself remains undistorted.
                  const origin = toWorld(node, s, 0, 0);
                  const xEnd = toWorld(node, s, s.w, 0);
                  const yEnd = toWorld(node, s, 0, s.h);
                  const axisW = Math.hypot(xEnd[0] - origin[0], xEnd[1] - origin[1]);
                  const axisH = Math.hypot(yEnd[0] - origin[0], yEnd[1] - origin[1]);
                  rec.comps.sprite.frame_size = [Math.round(fw), Math.round(fh)];
                  rec.comps.sprite.display_size = [Math.round(axisW * 10) / 10, Math.round(axisH * 10) / 10];
                }
                const tex = sf.texture || sf._texture || (sf.getTexture && sf.getTexture());
                const img = tex && (tex.image ? (tex.image.data || tex.image._data || tex.image) : (tex._image || tex._htmlElement));
                if (typeof HTMLCanvasElement !== 'undefined' && img instanceof HTMLCanvasElement) rec.comps.sprite.canvas_drawn = true;
                else if (img && img.canvas_drawn) rec.comps.sprite.canvas_drawn = true;      // test fixture
              } catch (e) { /* sizes are best effort */ }
            }
            const col = is3 ? spr.color : node.color;                 // tint: a white frame tinted blue is a flat colour
            if (col && typeof col.r === 'number') rec.comps.sprite.color = [col.r, col.g, col.b];
            // v7.8 U7: a 3.x sprite colour alpha dims the picture (2.x draws node.opacity, already in rec.opacity)
            if (is3 && col && typeof col.a === 'number' && col.a < 255) rec.comps.sprite.alpha = col.a;
            if (sf && spr.type === SLICED) {
              const ins = [sf.insetLeft || 0, sf.insetRight || 0, sf.insetTop || 0, sf.insetBottom || 0];
              rec.comps.sprite.insets = ins;
              if (ins.some((v) => v > 0) && ins[0] + ins[1] < s.w && ins[2] + ins[3] < s.h) {
                rec.comps.sprite.inner = norm(box(node, s, ins[0], ins[3], ins[1], ins[2]), cb);
              }
            }
          }
          if (get(node, T.BlockInputEvents)) rec.comps.block_input = true;
          if (T.Mask && get(node,T.Mask)) rec.comps.clip_mask=true;
          if (get(node, T.ProgressBar)) rec.comps.progress = true;
          if (get(node, T.ScrollView)) rec.comps.scroll = true;
          if (get(node, T.EditBox)) rec.comps.editbox = true;
          const imageState=node.__wholeText;
          if(imageState&&imageState.value){
            const pieces=(node.children||[]).filter(child=>{const sprite=get(child,T.Sprite);return child.activeInHierarchy!==false&&sprite&&sprite.enabled!==false&&sprite.spriteFrame;});
            const complete=imageState.complete===true&&pieces.length===imageState.expectedParts;
            rec.comps.image_text={string:complete?String(imageState.rendered||''):'',desired:String(imageState.value),complete,source_frames:pieces.map(child=>get(child,T.Sprite).spriteFrame.name)};
            if(pieces.length){
              const union=rects=>{const x=Math.min(...rects.map(r=>r[0])),y=Math.min(...rects.map(r=>r[1]));return[x,y,Math.max(...rects.map(r=>r[0]+r[2]))-x,Math.max(...rects.map(r=>r[1]+r[3]))-y];};
              const layouts=pieces.map(child=>norm(box(child,sizeOf(child),0,0,0,0),cb));rec.rect=union(layouts);
              const drawn=pieces.map(child=>screenBox(child,sizeOf(child))).filter(Boolean);if(drawn.length)rec.screen=union(drawn);
            }
          }
          nodes.push(rec);
        }
      }
    } catch (e) {
      if (errors.length < 50) errors.push(here + ': ' + (e && e.message ? e.message : String(e)));
    }
    const kids = node.children || [];
    for (let i = 0; i < kids.length; i++) walk(kids[i], here, depth + 1, cb, op);
  };
  walk(scene, '', 0, null, 1);
  if (!canvases) return fail('no Canvas component found in the running scene');
  const clips=nodes.filter(n=>n.comps.clip_mask);
  const intersect=(a,b)=>{const x=Math.max(a[0],b[0]),y=Math.max(a[1],b[1]);return[x,y,Math.max(0,Math.min(a[0]+a[2],b[0]+b[2])-x),Math.max(0,Math.min(a[1]+a[3],b[1]+b[3])-y)]};
  for(const n of nodes)for(const m of clips)if((n.ancestor_ids||[]).includes(m.id)){n.unclipped_rect=n.unclipped_rect||n.rect;n.rect=intersect(n.rect,m.rect);if(n.screen&&m.screen){n.unclipped_screen=n.unclipped_screen||n.screen;n.screen=intersect(n.screen,m.screen)}}

  return {
    tool: 'ui_dump', schema: 1, engine: cc.ENGINE_VERSION || '', api: is3 ? '3.x' : '2.x', scene: scene.name || '',
    page: { width: window.innerWidth, height: window.innerHeight, dpr: window.devicePixelRatio || 1 },
    canvas_css: [cr.x, cr.y, cr.width, cr.height], canvases, cameras: cams.length, truncated: nodes.length >= maxNodes, errors, nodes,
  };
}
