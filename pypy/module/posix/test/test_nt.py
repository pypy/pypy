import os
import sys

import pytest

if not sys.platform.startswith('win'):
    pytest.skip("requires Windows")

from pypy.module.posix import interp_nt as nt


def test__getfileinformation():
    with open(__file__) as fp:
        stat = os.fstat(fp.fileno())
        info = nt._getfileinformation(fp.fileno())
    serial, high, low = info
    assert type(serial) in (int, long)
    assert (high << 32) + low == stat.st_ino


def test__getfinalpathname():
    path = __file__.decode('utf-8')
    try:
        result, lgt = nt._getfinalpathname(path)
    except nt.LLNotImplemented:
        pytest.skip("_getfinalpathname not supported on this platform")
    assert os.path.exists(result)
