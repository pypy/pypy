
from pypy.translator.c.dlltool import DLLDef
from ctypes import CDLL
import py

class TestDLLTool(object):
    def test_basic(self):
        # XXX abusing get_entry_point to get a so name makes no sense
        def f(x):
            return x

        def b(x):
            return x + 2

        d = DLLDef('lib', [(f, [int]), (b, [int])])
        so = d.compile()
        dll = CDLL(str(so))
        assert dll.pypy_g_f(3) == 3
        assert dll.pypy_g_b(10) == 12

    def test_split_criteria(self):
        def f(x):
            return x

        def b(x):
            return x + 2

        d = DLLDef('lib', [(f, [int]), (b, [int])])
        so = d.compile()
        dirpath = py.path.local(so).dirpath()
        assert dirpath.join('translator_c_test_test_dlltool.c').check()
