import py
from pypy.tool import lib_pypy

def test_lib_pypy_exists():
    dirname = lib_pypy.LIB_PYPY
    assert dirname.check(dir=1)

def test_lib_python_exists():
    assert lib_pypy.LIB_PYTHON.check(dir=1)
