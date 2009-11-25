from pypy.rpython.rtyper import RPythonTyper
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation import policy
from pypy.rpython.test.test_llinterp import interpret, interpret_raises

import py
from pypy.rpython.test.tool import LLRtypeMixin, OORtypeMixin

class BaseRGenericTest:
    def test_some_generic_function_call(self):
        def h(x):
            return int(x)

        def c(x):
            return int(x) + 1

        def default(x):
            return int(x) + 3
        
        def g(a, x):
            if x == -1:
                a = None
            if x > 0:
                if x == 1:
                    a = h
                else:
                    a = c
                x = x + 0.01
            return a(x)

        def f(x):
            return g(default, x)

        g._annenforceargs_ = policy.Sig(annmodel.SomeGenericCallable(
            args=[annmodel.SomeFloat()], result=annmodel.SomeInteger()),
                                        float)

        assert interpret(f, [1.]) == 1
        assert interpret(f, [10.]) == 11
        assert interpret(f, [-3.]) == 0

class TestLLRgeneric(BaseRGenericTest, LLRtypeMixin):
    pass

class TestOORgeneric(BaseRGenericTest, OORtypeMixin):
    pass
