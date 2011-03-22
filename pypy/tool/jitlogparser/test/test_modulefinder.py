import py
from pypy.tool.jitlogparser.module_finder import gather_all_code_objs
import re, sys

def setup_module(mod):
    if sys.version_info[:2] != (2.6):
        py.test.skip("Specific python 2.6 tests")

def test_gather_code_py():
    fname = re.__file__
    codes = gather_all_code_objs(fname)
    assert len(codes) == 21
    assert sorted(codes.keys()) == [102, 134, 139, 144, 153, 164, 169, 181, 188, 192, 197, 206, 229, 251, 266, 271, 277, 285, 293, 294, 308]

def test_load_code():
    fname = re.__file__
    code = gather_all_code_objs(fname)[144]
    assert code.co_name == 'sub'
    assert code.co_filename == '/usr/lib/python2.6/re.py'
    assert code.co_firstlineno == 144
