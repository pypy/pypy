import os

if os.name == 'posix':
    from pyrepl.readline import _ReadlineWrapper
else:
    import pytest
    e = pytest.raises(ImportError, "import pyrepl.readline")
    assert 'termios' in e.value.message
    pytest.skip('pyrepl.readline requires termios')


def test_raw_input():
    import pty
    master, slave = pty.openpty()
    readline_wrapper = _ReadlineWrapper(slave, slave)
    os.write(master, b'input\n')

    result = readline_wrapper.get_reader().readline()
    #result = readline_wrapper.raw_input('prompt:')
    assert result == 'input'
    # A bytes string on python2, a unicode string on python3.
    assert isinstance(result, str)
