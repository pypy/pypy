import py
from pypy.rlib.test.test_objectmodel import BaseTestObjectModel as RLibBase

from pypy.rlib.objectmodel import cast_object_to_weakgcaddress,\
     cast_weakgcaddress_to_object

class BaseTestObjectModel(RLibBase):
    def test_rdict_of_void_copy(self):
        from pypy.rlib.test.test_objectmodel import r_dict, strange_key_eq, strange_key_hash
        def fn():
            d = r_dict(strange_key_eq, strange_key_hash)
            d['hello'] = None
            d['world'] = None
            d1 = d.copy()
            return len(d1)
        assert self.interpret(fn, []) == 2

    # this test is copied from TestLLtype in
    # rlib/test_objectmodel.py. It is not in TestOOtype because at
    # the moment llinterpret can't handle cast_*weakadr*
    def test_cast_to_and_from_weakaddress(self):
        class A(object):
            pass
        class B(object):
            pass
        def f():
            a = A()
            addr = cast_object_to_weakgcaddress(a)
            return a is cast_weakgcaddress_to_object(addr, A)
        res = self.interpret(f, [])
        assert res
##        def g():
##            a = A()
##            addr = cast_object_to_weakgcaddress(a)
##            return cast_weakgcaddress_to_int(addr)
##        assert isinstance(self.interpret(f, []), int)

    def test_weakref_const(self):
        class A(object):
            def __init__(self):
                self.x = 42
        a = A()
        weak = cast_object_to_weakgcaddress(a)
        def f():
            a.x = 10
            b = cast_weakgcaddress_to_object(weak, A)
            return b.x
        assert self.interpret(f, []) == 10

    def test_weakref_const_null(self):
        class A(object):
            pass
        weak = cast_object_to_weakgcaddress(None)
        def f():
            b = cast_weakgcaddress_to_object(weak, A)
            return b
        assert self.interpret(f, []) is None
