import os
import pty
import sys

import pytest
from pyrepl.readline import _ReadlineWrapper


@pytest.fixture
def readline_wrapper():
    master, slave = pty.openpty()
    return _ReadlineWrapper(slave, slave)


if sys.version_info < (3, ):
    bytes_type = str
    unicode_type = unicode  # noqa: F821
else:
    bytes_type = bytes
    unicode_type = str


def test_readline():
    master, slave = pty.openpty()
    readline_wrapper = _ReadlineWrapper(slave, slave)
    os.write(master, b'input\n')

    result = readline_wrapper.get_reader().readline()
    assert result == b'input'
    assert isinstance(result, bytes_type)


def test_readline_returns_unicode():
    master, slave = pty.openpty()
    readline_wrapper = _ReadlineWrapper(slave, slave)
    os.write(master, b'input\n')

    result = readline_wrapper.get_reader().readline(returns_unicode=True)
    assert result == 'input'
    assert isinstance(result, unicode_type)


def test_raw_input():
    master, slave = pty.openpty()
    readline_wrapper = _ReadlineWrapper(slave, slave)
    os.write(master, b'input\n')

    result = readline_wrapper.raw_input('prompt:')
    if sys.version_info < (3, ):
        assert result == b'input'
        assert isinstance(result, bytes_type)
    else:
        assert result == 'input'
        assert isinstance(result, unicode_type)


def test_read_history_file(readline_wrapper, tmp_path):
    histfile = tmp_path / "history"
    histfile.touch()

    assert readline_wrapper.reader is None

    readline_wrapper.read_history_file(str(histfile))
    assert readline_wrapper.reader.history == []

    histfile.write_bytes(b"foo\nbar\n")
    readline_wrapper.read_history_file(str(histfile))
    assert readline_wrapper.reader.history == ["foo", "bar"]


def test_write_history_file(readline_wrapper, tmp_path):
    histfile = tmp_path / "history"

    reader = readline_wrapper.get_reader()
    history = reader.history
    assert history == []
    history.extend(["foo", "bar"])

    readline_wrapper.write_history_file(str(histfile))

    with open(str(histfile), "r") as f:
        assert f.readlines() == ["foo\n", "bar\n"]


def test_write_history_file_with_exception(readline_wrapper, tmp_path):
    """The history file should not get nuked on inner exceptions.

    This was the case with unicode decoding previously."""
    histfile = tmp_path / "history"
    histfile.write_bytes(b"foo\nbar\n")

    class BadEntryException(Exception):
        pass

    class BadEntry(object):
        @classmethod
        def replace(cls, *args):
            raise BadEntryException

    history = readline_wrapper.get_reader().history
    history.extend([BadEntry])

    with pytest.raises(BadEntryException):
        readline_wrapper.write_history_file(str(histfile))

    with open(str(histfile), "r") as f:
        assert f.readlines() == ["foo\n", "bar\n"]
