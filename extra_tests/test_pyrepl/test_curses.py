import pytest
try:
    from pyrepl.curses import setupterm
except ImportError:
    pytest.skip('cannot import curses', allow_module_level=True)
import pyrepl


def test_setupterm(monkeypatch):
    assert setupterm(None, 0) is None

    with pytest.raises(
        pyrepl._minimal_curses.error,
        match=r"setupterm\(b?'term_does_not_exist', 0\) failed \(err=0\)",
    ):
        setupterm("term_does_not_exist", 0)

    monkeypatch.setenv('TERM', 'xterm')
    assert setupterm(None, 0) is None

    monkeypatch.delenv('TERM')
    with pytest.raises(
        pyrepl._minimal_curses.error,
        match=r"setupterm\(None, 0\) failed \(err=-1\)",
    ):
        setupterm(None, 0)
