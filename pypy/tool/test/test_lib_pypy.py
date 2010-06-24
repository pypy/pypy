import py
from pypy.tool import lib_pypy

def test_lib_pypy_exists():
    dirname = lib_pypy.LIB_PYPY
    assert dirname.check(dir=1)

def test_lib_python_exists():
    assert lib_pypy.LIB_PYTHON.check(dir=1)
    assert lib_pypy.LIB_PYTHON_VANILLA.check(dir=1)
    assert lib_pypy.LIB_PYTHON_MODIFIED.check(dir=1)

def test_import_from_lib_pypy():
    binascii = lib_pypy.import_from_lib_pypy('binascii')
    assert type(binascii) is type(lib_pypy)
    assert binascii.__name__ == 'lib_pypy.binascii'
    assert hasattr(binascii, 'crc_32_tab')
