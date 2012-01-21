
def pytest_runtest_makereport(__multicall__, item):
    report = __multicall__.execute()
    if 'out' in item.funcargs:
        report.sections.append(('out', item.funcargs['out'].read()))
    return report
