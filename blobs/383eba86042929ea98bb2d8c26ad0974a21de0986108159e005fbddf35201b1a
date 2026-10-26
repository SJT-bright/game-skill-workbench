"""Compatibility entry for previously reviewed local exported-game maintenance.
New projects use the common schema-3 gate and reviewed project supplements.
"""
import project_qa

def audit(args):
    policy=project_qa.read_store().get('legacy_export_validator')
    if not policy:raise ValueError('legacy export maintenance requires its reviewed local adapter; new projects use schema 3')
    return project_qa.invoke(policy,'audit',args)
