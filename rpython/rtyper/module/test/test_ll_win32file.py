import os

import py

from rpython.rtyper.module import ll_os

if not ll_os._WIN32:
    py.test.skip("requires Windows")


def test__getfinalpathname():
    path = __file__.decode('mbcs')
    try:
        result = ll_os._getfinalpathname(path)
    except ll_os.LLNotImplemented:
        py.test.skip("_getfinalpathname not supported on this platform")
    assert os.path.exists(result)


def test__getfileinformation():
    with open(__file__) as fp:
        stat = os.fstat(fp.fileno())
        info = ll_os._getfileinformation(fp.fileno())
    serial, high, low = info
    assert type(serial) in (int, long)
    assert (high << 32) + low == stat.st_ino
