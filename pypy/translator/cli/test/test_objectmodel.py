import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_objectmodel import BaseTestObjectModel

from pypy.rpython.objectmodel import cast_object_to_weakgcaddress,\
     cast_weakgcaddress_to_object

def skip_r_dict(self):
    py.test.skip('r_dict support is still incomplete')

class TestCliObjectModel(CliTest, BaseTestObjectModel):
    test_rtype_r_dict_bm = skip_r_dict

    # this test is copied from TestLLtype in
    # rpython/test_objectmodel.py. It is not in TestOOtype because at
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
        py.test.skip('Skip due to a mono bug')
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
