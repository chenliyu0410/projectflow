"""pytest plugin: fail the run when nothing was collected or any test was skipped."""


def pytest_sessionfinish(session, exitstatus):
    # 專用 PostgreSQL 階段若因環境變數沒設好而 skip，不能被當成通過。
    reporter = session.config.pluginmanager.get_plugin('terminalreporter')
    skipped = reporter.stats.get('skipped') if reporter else None
    if session.testscollected == 0 or skipped:
        session.exitstatus = 1
