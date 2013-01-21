import sys
import pytest
from rpython.tool.pytest import viewerplugin

class mock(object):
    view = False

    @staticmethod
    def execute():
        pass

mock.config = mock
mock.option = mock


def test_pygame_teardown_check(monkeypatch):
    monkeypatch.delitem(sys.modules, 'pygame', raising=False)
    viewerplugin.pytest_runtest_teardown(mock, mock)

    monkeypatch.setitem(sys.modules, 'pygame', None)
    with pytest.raises(AssertionError) as exc_info:
        viewerplugin.pytest_runtest_teardown(mock, mock)

    monkeypatch.setattr(mock, 'view', True)
    viewerplugin.pytest_runtest_teardown(mock, mock)



