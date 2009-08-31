
from pypy.translator.c.dlltool import DLLDef
from ctypes import CDLL
import py

class TestDLLTool(object):
    def test_basic(self):
        def f(x):
            return x

        def b(x):
            return x + 2

        d = DLLDef('lib', [(f, [int]), (b, [int])])
        so = d.compile()
        dll = CDLL(str(so))
        assert dll.f(3) == 3
        assert dll.b(10) == 12

    def test_split_criteria(self):
        def f(x):
            return x

        def b(x):
            return x + 2

        d = DLLDef('lib', [(f, [int]), (b, [int])])
        so = d.compile()
        assert py.path.local(so).dirpath().join('implement.c').check()
