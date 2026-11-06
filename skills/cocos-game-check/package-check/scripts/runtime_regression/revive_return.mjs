// Shared by the ad_outcome suite and its focused regression controls.
export function reviveContractProblem(spec, resume) {
  const code = v => typeof v === 'string' && v.trim().length > 0;
  for (const key of ['run_id_js', 'reward_js', 'cancel_js', 'after_js']) {
    if (!code(spec?.[key])) return 'missing revive observation: ' + key;
  }
  if (!Array.isArray(spec.after_visible) || !spec.after_visible.length ||
      !spec.after_visible.every(code)) return 'missing visible gameplay anchors: after_visible';
  const probe = resume?.probe;
  if (!code(resume?.state_js) || !probe || probe.optional ||
      !['tap', 'tap_js', 'drag_js'].some(k => code(probe[k]))) {
    return 'revive requires a real gameplay input and action-specific state_js in revive_probe or resume_play';
  }
  return null;
}

export function sameRun(a, b) {
  return ((typeof a === 'string' && a.trim().length > 0) || Number.isFinite(a)) && a === b;
}

// Do not use disappearance of the ad button as the playability check.
// Capture the rendered state before the probe can change the board again.
export async function checkReviveReturn(spec, before, io) {
  const observed = {before, after: await io.runId(), anchors: [], review: 'inspect both frames'};
  const fail = why => ({...observed, ok: false, why});
  observed.restoredFrame = await io.shot('restored');
  if (!observed.restoredFrame) return fail('missing restored frame');
  if (!sameRun(before, observed.after)) return fail('run identity missing or changed');
  if (await io.restored() !== true) return fail('gameplay, camera or overlay did not recover');
  for (const path of spec.after_visible) {
    const visible = await io.visible(path);
    observed.anchors.push({path, visible});
    if (!visible) return fail('required gameplay anchor hidden, covered or off screen: ' + path);
  }
  observed.input = await io.play();
  observed.nextFrame = await io.shot('next-action');
  if (!observed.nextFrame) return fail('missing next-action frame');
  const pair = observed.input?.state;
  if (!observed.input?.ok || !Array.isArray(pair) || pair.length !== 2 ||
      pair.some(v => v == null || v.adapterError) || JSON.stringify(pair[0]) === JSON.stringify(pair[1])) {
    return fail('first gameplay input produced no verified business effect');
  }
  return {...observed, ok: true};
}
