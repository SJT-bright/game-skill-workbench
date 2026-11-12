"""Test-only isolation for pre-existing non-advertisement gate fixtures.

No production module imports this helper. Strict six-family behavior is exercised
by test_ad_nodes_gate and the formal entry refusal tests with real auditors.
"""
import importlib
from pathlib import Path
import sys
from unittest.mock import patch

def isolate(module):
    prior_setup=module.get('setUpModule')
    prior_teardown=module.get('tearDownModule')
    active=[]
    def setup():
        own=next(p/'remake-core/scripts' for p in Path(module['__file__']).resolve().parents
                 if (p/'remake-core/scripts/ad_standard_scope.py').is_file())
        sys.path.insert(0,str(own))
        scope=importlib.import_module('ad_standard_scope')
        item=patch.object(scope,'requirement',return_value={'required':False,
            'reason':'test-only isolation of pre-existing non-advertisement fixture'})
        item.start();active.append(item)
        try:
            if prior_setup:prior_setup()
        except BaseException:
            active.pop().stop();raise
    def teardown():
        try:
            if prior_teardown:prior_teardown()
        finally:
            while active:active.pop().stop()
    module['setUpModule']=setup
    module['tearDownModule']=teardown
