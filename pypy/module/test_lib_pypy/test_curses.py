import pytest
import sys
if sys.platform == 'win32':
    #This module does not exist in windows
    pytest.skip('no curses on windows')

# Check that lib_pypy.cffi finds the correct version of _cffi_backend.
# Otherwise, the test is skipped.  It should never be skipped when run
# with "pypy py.test -A".
try:
    from lib_pypy import cffi; cffi.FFI()
except (ImportError, AssertionError), e:
    pytest.skip("no cffi module or wrong version (%s)" % (e,))

from lib_pypy import _curses


lib = _curses.lib


def test_color_content(monkeypatch):
    def lib_color_content(color, r, g, b):
        r[0], g[0], b[0] = 42, 43, 44
        return lib.OK

    monkeypatch.setattr(_curses, '_ensure_initialised_color', lambda: None)
    monkeypatch.setattr(lib, 'color_content', lib_color_content)

    assert _curses.color_content(None) == (42, 43, 44)


def test_setupterm(monkeypatch):
    def make_setupterm(err_no):
        def lib_setupterm(term, fd, err):
            err[0] = err_no

            return lib.ERR

        return lib_setupterm

    monkeypatch.setattr(_curses, '_initialised_setupterm', False)
    monkeypatch.setattr(lib, 'setupterm', make_setupterm(0))

    with pytest.raises(Exception) as exc_info:
        _curses.setupterm()

    assert "could not find terminal" in exc_info.value.args[0]

    monkeypatch.setattr(lib, 'setupterm', make_setupterm(-1))

    with pytest.raises(Exception) as exc_info:
        _curses.setupterm()

    assert "could not find terminfo database" in exc_info.value.args[0]

    monkeypatch.setattr(lib, 'setupterm', make_setupterm(42))

    with pytest.raises(Exception) as exc_info:
        _curses.setupterm()

    assert "unknown error" in exc_info.value.args[0]
