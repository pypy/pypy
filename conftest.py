import pytest


def pytest_configure(config):
    # the vendored pytest 3.10 warns about its own deprecated APIs (resultlog,
    # get_marker, ...); newer pytests, used for -D runs, lack the category
    if hasattr(pytest, 'RemovedInPytest4Warning'):
        config.addinivalue_line(
            'filterwarnings', 'ignore::pytest.RemovedInPytest4Warning')
