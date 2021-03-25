import pytest
try:
    from pyrepl.curses import setupterm, error as curses_error
except ImportError:
    pytest.skip('cannot import curses', allow_module_level=True)
import pyrepl


def test_setupterm(monkeypatch):
    assert setupterm(None, 0) is None

    with pytest.raises(
        curses_error,
        match=r"setupterm\(b?'term_does_not_exist', 0\) failed \(err=0\)",
    ):
        setupterm("term_does_not_exist", 0)

    monkeypatch.setenv('TERM', 'xterm')
    assert setupterm(None, 0) is None

    monkeypatch.delenv('TERM')
    with pytest.raises(
        curses_error,
        match=r"setupterm\(None, 0\) failed \(err=-1\)",
    ):
        setupterm(None, 0)
