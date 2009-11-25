
from pypy.rpython.extfunc import ExtFuncEntry, register_external,\
     is_external, lazy_register
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
    lltypeimpl = staticmethod(lltypeimpl)

def test_interp_c():
    def f():
        return c(3, 4)

    res = interpret(f, [])
    assert res == 7

def d(y):
    return eval("y()")

class DTestFuncEntry(ExtFuncEntry):
    _about_ = d
    name = 'd'
    signature_args = [annmodel.SomeGenericCallable(args=[], result=
                                                   annmodel.SomeFloat())]
    signature_result = annmodel.SomeFloat()

def test_callback():
    def callback():
        return 2.5

    def f():
        return d(callback)

    policy = AnnotatorPolicy()
    policy.allow_someobjects = False
    a = RPythonAnnotator(policy=policy)
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeFloat)
    assert a.translator._graphof(callback)

def dd():
    pass

register_external(dd, [int], int)

def test_register_external_signature():
    def f():
        return dd(3)

    policy = AnnotatorPolicy()
    policy.allow_someobjects = False
    a = RPythonAnnotator(policy=policy)
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInteger)


def function_with_tuple_arg():
    """
    Dummy function which is declared via register_external to take a tuple as
    an argument so that register_external's behavior for tuple-taking functions
    can be verified.
    """
register_external(function_with_tuple_arg, [(int,)], int)

def test_register_external_tuple_args():
    """
    Verify the annotation of a registered external function which takes a tuple
    argument.
    """
    def f():
        return function_with_tuple_arg((1,))

    policy = AnnotatorPolicy()
    policy.allow_someobjects = False
    a = RPythonAnnotator(policy=policy)
    s = a.build_types(f, [])

    # Not a very good assertion, but at least it means _something_ happened.
    assert isinstance(s, annmodel.SomeInteger)

def function_with_list():
    pass
register_external(function_with_list, [[int]], int)

def function_returning_list():
    pass
register_external(function_returning_list, [], [int])

def test_register_external_return_goes_back():
    """
    Check whether it works to pass the same list from one external
    fun to another
    [bookkeeper and list joining issues]
    """
    def f():
        return function_with_list(function_returning_list())

    policy = AnnotatorPolicy()
    policy.allow_someobjects = False
    a = RPythonAnnotator(policy=policy)
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInteger)

def function_withspecialcase(arg):
    return repr(arg)
register_external(function_withspecialcase, args=None, result=str)

def test_register_external_specialcase():
    def f():
        x = function_withspecialcase
        return x(33) + x("aaa") + x([]) + "\n"

    policy = AnnotatorPolicy()
    policy.allow_someobjects = False
    a = RPythonAnnotator(policy=policy)
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeString)
