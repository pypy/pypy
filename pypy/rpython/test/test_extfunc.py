
from pypy.rpython.extfunc import ExtFuncEntry
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation.policy import AnnotatorPolicy
from pypy.rpython.test.test_llinterp import interpret

def b(x):
    return eval("x+40")

class BTestFuncEntry(ExtFuncEntry):
    _about_ = b
    name = 'b'
    signature_args = [annmodel.SomeInteger()]
    signature_result = annmodel.SomeInteger()

def test_annotation_b():
    def f():
        return b(1)
    
    policy = AnnotatorPolicy()
    policy.allow_someobjects = False
    a = RPythonAnnotator(policy=policy)
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInteger)

def test_rtyping_b():
    def f():
        return b(2)

    res = interpret(f, [])
    assert res == 42

def c(y, x):
    yyy

class CTestFuncEntry(ExtFuncEntry):
    _about_ = c
    name = 'ccc'
    signature_args = [annmodel.SomeInteger()] * 2
    signature_result = annmodel.SomeInteger()

    def lltypeimpl(y, x):
        return y + x

def test_interp_c():
    def f():
        return c(3, 4)

    res = interpret(f, [])
    assert res == 7
