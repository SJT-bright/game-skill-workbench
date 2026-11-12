"""Continue one failed delivery step through a registered repair and its original gate.

``repair_and_resume`` runs at most one named Python callback, one replan callback,
and the original resume callback. It never imports handlers or launches commands
from a task document. Callers must register the authorized callbacks themselves.
The replan callback must call the original scope gate and return ``plan``,
``plan_path`` and its ``preflight`` result as ``verification``. The resume callback
receives that exact, verified plan and must retain its usual execution gate.
"""

import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
from functools import wraps
from types import MappingProxyType


SCHEMA = 'cocos-delivery-continuation.v1'
PLAN_SCHEMA = 'cocos-regression-scope.v1'
STARTUP = 'startup.native.renderer'


def repair_context(stage):
    return {
        'repair_status': 'repair_required',
        'task_terminal': False,
        'owner': 'current_agent',
        'requires_user_continue': False,
        'resume_at': stage,
        'next_action': 'repair_exact_gap_then_resume_authorized_step',
        'verification_scope': 'affected_or_missing_only',
        'retry_condition': 'corrected_input_or_new_evidence',
    }


def failure(error, *, stage, status='refuse'):
    return {'status': status, 'error': str(error), **repair_context(stage)}


def _copy(value):
    """Keep task data separate from mutable callback arguments and caller inputs."""
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _frozen(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def _ids(values):
    if not isinstance(values, (list, tuple)):
        raise ValueError('approved_run_ids 必须是明确用例 ID 列表')
    if any(not isinstance(item, str) or not item.strip()
           or any(char in item for char in '*?[]') for item in values):
        raise ValueError('授权必须对应具体用例 ID，不能使用通配符')
    if len(values) != len(set(values)):
        raise ValueError('授权用例 ID 不能重复')
    return sorted(values)


def continuation_task(*, stage, original_failure, approved_run_ids, mode='scoped',
                      next_action='diagnose_exact_failure_and_register_a_bounded_repair'):
    """Snapshot original authorization, stage and unmodified failure output.

    For a missing plan, IDs come from the already authorized user objective;
    they must not be inferred by approving every currently failing check.
    """
    if not isinstance(stage, str) or not stage.strip():
        raise ValueError('续跑任务需要原失败阶段')
    if mode not in ('scoped', 'reuse-only', 'full'):
        raise ValueError('无效执行模式')
    run_ids = _ids(approved_run_ids)
    if mode == 'reuse-only' and run_ids:
        raise ValueError('纯沿用任务不能包含重跑授权')
    return {
        **repair_context(stage), 'schema': SCHEMA, 'status': 'repair_required',
        'original_failure': _copy(original_failure), 'approved_run_ids': run_ids,
        'mode': mode, 'next_action': str(next_action),
    }


def _fingerprint(observe):
    value = observe()
    if value is None or value == {} or value == [] or value == '':
        raise ValueError('缺少原失败输入/证据的内容指纹，不能判断是否已修复')
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


def _verified_plan(result, task):
    if not isinstance(result, dict):
        raise ValueError('replan 必须返回原 gate 核准的 plan、plan_path 和 verification')
    plan, verified = result.get('plan'), result.get('verification')
    if not isinstance(plan, dict) or not isinstance(verified, dict) or not result.get('plan_path'):
        raise ValueError('replan 缺少原 gate 核准的 plan、plan_path 或 verification')
    raw = Path(result['plan_path']).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not re.fullmatch(r'[a-f0-9]{64}', str(verified.get('plan_sha256', ''))):
        raise ValueError('verification 缺少原 preflight 核准的计划 SHA-256')
    if digest != verified['plan_sha256'] or json.loads(raw) != plan:
        raise ValueError('修复后的实际计划与原 gate 核准的计划或 SHA-256 不一致')
    if plan.get('schema') != PLAN_SCHEMA or verified.get('schema') != PLAN_SCHEMA:
        raise ValueError('修复后的计划未经过原回归 gate 核准')
    mode = plan.get('mode')
    if mode != verified.get('mode') or mode not in ('scoped', 'reuse-only', 'full'):
        raise ValueError('计划模式与原 gate 核准结果不一致')
    if mode == 'full' and task['mode'] != 'full':
        raise ValueError('修复不能把原授权提升为 full 或退回全量')
    if task['mode'] == 'reuse-only' and mode != 'reuse-only':
        raise ValueError('修复不能把纯沿用授权提升为重跑模式')
    if not isinstance(plan.get('actions'), dict):
        raise ValueError('核准计划缺少具体用例清单')
    run_ids = []
    for group in plan['actions'].values():
        if not isinstance(group, dict):
            raise ValueError('核准计划的用例清单无效')
        for check_id, item in group.items():
            if not isinstance(item, dict):
                raise ValueError('核准计划缺少用例动作')
            if item.get('action') == 'run':
                run_ids.append(check_id)
    run_ids = _ids(run_ids)
    if run_ids != _ids(verified.get('allowed')):
        raise ValueError('计划 run 用例与原 preflight 核准 ID 不一致')
    if bool(plan.get('startup_run')) != bool(verified.get('startup_run')):
        raise ValueError('启动检查与原 preflight 核准结果不一致')
    if plan.get('startup_run') and STARTUP not in run_ids:
        run_ids.append(STARTUP)
    run_ids = sorted(run_ids)
    if mode == 'reuse-only' and run_ids:
        raise ValueError('纯沿用计划不能恢复任何实际重跑')
    unexpected = sorted(set(run_ids) - set(task['approved_run_ids']))
    if unexpected:
        raise ValueError('修复后的计划扩大原授权 run IDs：' + ', '.join(unexpected))
    return _copy(plan), run_ids, digest


def repair_and_resume(task, *, repair_action=None, actions=None, observe=None,
                      replan=None, resume=None):
    """Repair once, replan through the original gate, and resume its exact step.

    ``actions`` is a registry of explicitly supplied Python callables. An action
    and ``replan`` each receive an immutable original task. ``observe()`` returns
    content identities of the actual failed inputs/evidence, including a missing
    plan if plan regeneration is the repair. Noise such as report timestamps is
    not a repair identity. ``resume(plan)`` remains the original gated entrypoint.

    No loop or fallback is performed. All incomplete outcomes retain
    ``task_terminal=False`` with a concrete next action for the owning agent.
    """
    task = _copy(task)
    if task.get('schema') != SCHEMA:
        raise ValueError('不是有效的 delivery continuation 任务')
    # Re-validate a serialized task before invoking any supplied callback.
    original = continuation_task(stage=task['resume_at'], original_failure=task['original_failure'],
                                 approved_run_ids=task['approved_run_ids'], mode=task['mode'],
                                 next_action=task['next_action'])
    report = {**original, 'repair_action': repair_action, 'repair_calls': 0,
              'replan_calls': 0, 'resume_calls': 0}

    def pending(why, next_action, *, status='repair_required', phase=None):
        report.update(status=status, repair_status=status, why=str(why),
                      next_action=str(next_action), task_terminal=False)
        if phase:
            report['continuation_phase'] = phase
        return report

    if not repair_action or not isinstance(actions, dict) or repair_action not in actions:
        return pending('没有为此缺口登记修复 callback，当前任务仍由 Agent 诊断。',
                       task['next_action'], status='needs_agent_action', phase='diagnose')
    if not all(callable(item) for item in (actions[repair_action], observe, replan, resume)):
        return pending('修复、内容指纹、原 gate 核准或原入口 callback 未完整登记。',
                       'register_the_missing_observer_gate_or_original_entrypoint',
                       status='needs_agent_action', phase='diagnose')
    frozen = _frozen(original)
    phase = 'observe'
    try:
        before = _fingerprint(observe)
        report['before_sha256'] = before
        phase = 'repair'
        report['repair_calls'] = 1
        result = actions[repair_action](frozen)
        if isinstance(result, dict):
            report['repair_result'] = _copy(result)
            if result.get('status') in ('needs_agent_action', 'diagnosis_required', 'repair_required', 'blocked'):
                return pending(result.get('why') or result.get('error') or '修复仍需要语义诊断。',
                               result.get('next_action') or task['next_action'],
                               status='needs_agent_action', phase='repair')
        phase = 'replan'
        report['replan_calls'] = 1
        planned = replan(frozen)
        after = _fingerprint(observe)
        report['after_sha256'] = after
        plan, run_ids, plan_sha = _verified_plan(planned, original)
        if before == after:
            return pending('原失败输入或证据没有内容变化，禁止无变化续跑。',
                           'repair_the_recorded_failed_input_or_supply_new_bound_evidence',
                           phase='verify_repair')
        report.update(plan_sha256=plan_sha, resumed_run_ids=run_ids)
        phase = 'resume'
        report['resume_calls'] = 1
        resumed = resume(plan)
        if isinstance(resumed, int) and not isinstance(resumed, bool) and resumed != 0:
            report['resume_exit_code'] = resumed
            return pending('原入口恢复后仍返回非零退出码。',
                           'diagnose_the_new_original_entrypoint_failure_without_expanding_scope', phase='resume')
        if resumed is False:
            return pending('原入口返回失败，仍需修复。',
                           'diagnose_the_new_original_entrypoint_failure_without_expanding_scope', phase='resume')
        if isinstance(resumed, dict):
            report['resume_result'] = _copy(resumed)
            if resumed.get('status') in ('repair_required', 'scope_required', 'needs_agent_action',
                                         'refuse', 'failed', 'blocked', 'not_run', 'environment_incomplete') \
                    or resumed.get('blocked') is True or resumed.get('passed') is False \
                    or resumed.get('exit_code', 0):
                details = resumed.get('why') or resumed.get('error') or resumed.get('problems')
                return pending(details or '原入口仍有待修复缺口。',
                               resumed.get('next_action') or task['next_action'], phase='resume')
        report.update(status='resumed', repair_status='resumed', task_terminal=False,
                      continuation_phase='resumed',
                      why='修复已改变失败输入/证据，原 gate 核准后已调用原入口。',
                      next_action='continue_delivery_from_the_original_entrypoint_result')
        return report
    except Exception as error:
        report['continuation_error'] = {'type': type(error).__name__, 'error': str(error)}
        return pending(str(error), 'repair_the_' + phase + '_gap_then_resume_the_same_authorized_step',
                       phase=phase)


def continuing_cli(stage):
    """Retain command output and exit codes while marking failed tasks resumable."""
    def decorate(command):
        @wraps(command)
        def execute(*args, **kwargs):
            try:
                code = command(*args, **kwargs)
            except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as error:
                print(json.dumps(failure(error, stage=stage, status='repair_required'), ensure_ascii=False), file=sys.stderr)
                return 1
            if code:
                context = failure('处理本次命令上方原始失败原因，修复后续跑当前节点。',
                                  stage=stage, status='repair_required')
                print(json.dumps(context, ensure_ascii=False), file=sys.stderr)
            return code
        return execute
    return decorate
