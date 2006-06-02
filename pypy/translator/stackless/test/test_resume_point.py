from pypy.translator.stackless.transform import StacklessTransformer
from pypy.translator.stackless.test.test_transform import llinterp_stackless_function, rtype_stackless_function, one
from pypy import conftest
import py
from pypy.rpython import rstack

def transform_stackless_function(fn):
    def wrapper(argv):
        return fn()
    t = rtype_stackless_function(wrapper)
    st = StacklessTransformer(t, wrapper, False)
    st.transform_all()
    if conftest.option.view:
        t.view()

def test_no_call():
    def f(x, y):
        x = x-1
        rstack.resume_point("rp0", x, y) 
        r = x+y
        rstack.stack_unwind()
        return r
    def example():
        v1 = f(one(),one()+one())
        state = rstack.resume_state_create(None, "rp0", one(), one()+one()+one())
        v2 = rstack.resume_state_invoke(int, state)
        return v1*10 + v2
    transform_stackless_function(example)
##     res = llinterp_stackless_function(example, assert_unwind=False)
##     assert res == 24

def test_call():
    def g(x,y):
        return x*y
    def f(x, y):
        z = g(x,y)
        rstack.resume_point("rp1", y, returns=z) 
        return z+y
    def example():
        f(one(),one()+one())
        return 0
    transform_stackless_function(example)

def test_call_exception_handling():
    def g(x,y):
        if x == 0:
            raise KeyError
        return x*y
    def f(x, y):
        try:
            z = g(x,y)
            rstack.resume_point("rp1", y, returns=z)
        except KeyError:
            return 0
        return z+y
    def example():
        f(one(),one()+one())
        return 0
    transform_stackless_function(example)

def test_call_uncovered():
    def g(x,y):
        return x*y
    def f(x, y):
        z = g(x,y)
        rstack.resume_point("rp1", y, returns=z) 
        return z+y+x
    def example():
        f(one(),one()+one())
        return 0
    e = py.test.raises(Exception, transform_stackless_function, example)
    assert e.value.args == ('not covered needed value at resume_point',)

