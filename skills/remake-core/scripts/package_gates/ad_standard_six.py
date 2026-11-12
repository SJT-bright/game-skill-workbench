"""One six-standard ad/UI gate used by both writers and exact ZIP verification."""
from . import finding


def check(view):
    from ad_standard_scope import requirement
    project = getattr(view, 'project', None)
    scope = requirement(project, view.get_policy()[0])
    if not scope['required']:
        return [finding('AD6_scope_retained', 'warn', scope['reason'])]
    if project is None:
        return [finding('AD6_project_required', 'block',
                        '六标准广告节点检查需要 --project 指向实际工程；静态包内容不能代替项目的接线、运行和UI证据。')]
    from ad_nodes_gate import check_project
    result = check_project(project, files=view.files, native=view.root, stage='writer')
    if not result.get('passed'):
        return [finding('AD6_production_incomplete', 'block',
                        '六标准广告节点或对应新增UI未完成：' + '; '.join(result.get('problems') or ['unknown gate result']),
                        result)]
    return []
