import pytest

from .infrastructure import sane_term

import sys
from pyrepl import readline

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
        result = readline_wrapper.input('prompt:')
    assert result == 'input'
    # A bytes string on python2, a unicode string on python3.
    assert isinstance(result, str)

def test_get_line_buffer_is_str():
    from pyrepl import readline
    assert isinstance(readline.get_line_buffer(), str)

def test_nonascii_history():
    import sys
    import os
    TESTFN = "{}_{}_tmp".format("@test", os.getpid())

    is_editline = readline.__doc__ and "libedit" in readline.__doc__

    readline.clear_history()
    try:
        try:
            readline.add_history("entrée 1")
        except UnicodeEncodeError as err:
            skip("Locale cannot encode test data: " + format(err))
        readline.add_history("entrée 2")
        readline.replace_history_item(1, "entrée 22")
        readline.write_history_file(TESTFN)
        readline.clear_history()
        readline.read_history_file(TESTFN)
        if is_editline:
            # An add_history() call seems to be required for get_history_
            # item() to register items from the file
            readline.add_history("dummy")
        assert readline.get_history_item(1) ==  "entrée 1"
        assert readline.get_history_item(2) == "entrée 22"
    finally:
        try:
            os.unlink(TESTFN)
        except FileNotFoundError:
            pass

def test_insert_text_leading_tab():
    """
    A literal tab can be inserted at the beginning of a line.

    See <https://bugs.python.org/issue25660>
    """
    readline.insert_text("\t")
    assert readline.get_line_buffer() == "\t"


def test_append_history_file_only_writes_new_entries(tmpdir):
    history_file = str(tmpdir / "history")
    old_history = [
        readline.get_history_item(i)
        for i in range(1, readline.get_current_history_length() + 1)
    ]
    old_history_length = readline.get_history_length()
    old_persisted_history_length = readline._wrapper.persisted_history_length
    try:
        readline.clear_history()
        readline.set_history_length(0)

        readline.add_history("first")
        readline.append_history_file(history_file)
        readline.add_history("second\nline")
        readline.append_history_file(history_file)

        assert (tmpdir / "history").read("rb") == b"first\nsecond\r\nline\n"
    finally:
        readline.clear_history()
        for entry in old_history:
            readline.add_history(entry)
        readline.set_history_length(old_history_length)
        readline._wrapper.persisted_history_length = old_persisted_history_length
