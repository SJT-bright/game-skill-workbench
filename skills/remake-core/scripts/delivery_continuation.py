"""Common continuation context for a failed delivery command.

The caller retains its error and exit code. The current agent owns the repair
and resumes the named step after correcting its actual inputs or evidence.
"""

import json
import sys
import zipfile
from functools import wraps


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


def continuing_cli(stage):
    """Retain the command source and exit codes while marking failed tasks resumable."""
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
