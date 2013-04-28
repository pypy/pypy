import pytest


@pytest.mark.skipif("os.name != 'posix' or 'darwin' in sys.platform")
def test_raw_input():
    import os
    import pty
    from pyrepl.readline import _ReadlineWrapper

    master, slave = pty.openpty()
    readline_wrapper = _ReadlineWrapper(slave, slave)
    os.write(master, b'input\n')

    result = readline_wrapper.get_reader().readline()
    #result = readline_wrapper.raw_input('prompt:')
    assert result == 'input'
    # A bytes string on python2, a unicode string on python3.
    assert isinstance(result, str)
