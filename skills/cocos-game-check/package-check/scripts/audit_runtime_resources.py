"""Compatibility import; production catalog validation is shared with the writer."""
import importlib.util
from pathlib import Path
_path=Path(__file__).resolve().parents[3]/'remake-core/scripts/audit_runtime_resources.py'
_spec=importlib.util.spec_from_file_location('_cocos_shared_runtime_resources',_path)
_module=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
audit=_module.audit
