# spaceconfig = {"usemodules" : ["_rawffi"]}

import pytest
_rawffi = pytest.importorskip("_rawffi")
from _rawffi import Array

def test_array_view_format():
    ffiarray = Array('c')
    assert memoryview(ffiarray(1, autofree=True)).format == 'c'

def test_sizeof_time_t():
    # CPython 3.12's ctypes/__init__.py does "from _ctypes import SIZEOF_TIME_T"
    assert _rawffi.SIZEOF_TIME_T in (4, 8)
