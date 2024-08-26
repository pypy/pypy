import pytest

from .infrastructure import sane_term


@pytest.mark.skipif("os.name != 'posix' or 'darwin' in sys.platform or "
                    "'freebsd' in sys.platform")
def test_raw_input():
    import os
    import pty
    from pyrepl.readline import _ReadlineWrapper

    master, slave = pty.openpty()
    readline_wrapper = _ReadlineWrapper(slave, slave)
    os.write(master, b'input\n')

    with sane_term():
        result = readline_wrapper.raw_input('prompt:')
    assert result == 'input'
    # A bytes string on python2, a unicode string on python3.
    assert isinstance(result, str)

def test_get_line_buffer_is_str():
    from pyrepl import readline
    assert isinstance(readline.get_line_buffer(), str)
