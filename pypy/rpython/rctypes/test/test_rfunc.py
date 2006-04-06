from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.rctypes.test.test_rctypes import mylib
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy import conftest

from ctypes import c_long


labs = mylib.labs
labs.restype = c_long
labs.argtypes = [c_long]

def ll_labs(n):
    return abs(n)

labs.llinterp_friendly_version = ll_labs


def test_labs(n=6):
    assert labs(n) == abs(n)
    assert labs(c_long(0)) == 0
    assert labs(-42) == 42
    return labs(n)

class Test_annotation:
    def test_annotate_labs(self):
        a = RPythonAnnotator()
        s = a.build_types(test_labs, [int])
        assert s.knowntype == int
        if conftest.option.view:
            a.translator.view()

class Test_specialization:
    def test_specialize_labs(self):
        res = interpret(test_labs, [-11])
        assert res == 11

class Test_compile:
    def test_compile_labs(self):
        fn = compile(test_labs, [int])
        res = fn(-11)
        assert res == 11
