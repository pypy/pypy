from rpython.tool.descriptor import InstanceMethod
from rpython.tool.descriptor import normalize_method as norm

class X(object):
    def f(self, *args, **kwds):
        return args, kwds

def test_bound():
    obj = X()
    obj.x = 12
    meth = InstanceMethod(X.f.im_func, obj, X)
    assert meth(1, z=2) == ((1,), {'z': 2})

def test_unbound():
    obj = X()
    obj.x = 12
    meth = InstanceMethod(X.f.im_func, None, X)
    assert meth(obj, 1, z=2) == ((1,), {'z': 2})

def test_eq_hash():
    obj1 = X()
    obj1.x = 12
    meth1 = InstanceMethod(X.f.im_func, obj1, X)
    meth1bis = InstanceMethod(X.f.im_func, obj1, X)
    obj2 = X()
    obj2.x = 12
    meth2 = InstanceMethod(X.f.im_func, obj2, X)
    d = {meth1: 123, meth2: 456}
    assert len(d) == 2
    assert d[meth1bis] == 123

def test_normalize_unbound_method():
    class A(object):
        pass
    class B(A):
        def __init__(self):
            pass

    assert norm(A.__init__) == norm(object.__init__)
    assert norm(A().__init__).im_func == norm(object().__init__).im_func
    assert norm(A.__init__) != norm(B.__init__)

    class C(str):
        pass

    assert norm(C.join) == norm(str.join)
    assert norm(C().join).im_func == norm(str().join).im_func

    class D(object):
        def foo(self):
            pass

    class E(D):
        pass

    assert norm(E.foo) == norm(D.foo)
    assert norm(E().foo).im_func == norm(D().foo).im_func
