from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rlib.objectmodel import specialize
from pypy.rlib import rarithmetic, jit
from pypy.rpython.lltypesystem import rffi
from pypy.interpreter.baseobjspace import InternalSpaceCache, W_Root

from pypy.module.cppyy import interp_cppyy

class FakeBase(W_Root):
    typename = None

class FakeInt(FakeBase):
    typename = "int"
    def __init__(self, val):
        self.val = val
class FakeFloat(FakeBase):
    typename = "float"
    def __init__(self, val):
        self.val = val
class FakeString(FakeBase):
    typename = "str"
    def __init__(self, val):
        self.val = val
class FakeType(FakeBase):
    typename = "type"
    def __init__(self, name):
        self.name = name
    def getname(self, space, name):
        return self.name




class FakeSpace(object):
    fake = True

    w_ValueError = FakeType("ValueError")
    w_TypeError = FakeType("TypeError")
    w_AttributeError = FakeType("AttributeError")
    w_ReferenceError = FakeType("ReferenceError")

    w_None = None
    w_str = FakeType("str")
    w_int = FakeType("int")
    w_float = FakeType("float")

    def __init__(self):
        self.fromcache = InternalSpaceCache(self).getorbuild

    def issequence_w(self, w_obj):
        return True

    @specialize.argtype(1)
    def wrap(self, obj):
        if isinstance(obj, int):
            return FakeInt(obj)
        if isinstance(obj, float):
            return FakeFloat(obj)
        if isinstance(obj, str):
            return FakeString(obj)
        if isinstance(obj, rffi.r_int):
            return FakeInt(int(obj))
        assert 0

    def float_w(self, w_obj):
        assert isinstance(w_obj, FakeFloat)
        return w_obj.val

    def interp_w(self, RequiredClass, w_obj, can_be_None=False):
        if can_be_None and w_obj is None:
            return None
        if not isinstance(w_obj, RequiredClass):
            raise TypeError
        return w_obj
    interp_w._annspecialcase_ = 'specialize:arg(1)'

    def interpclass_w(self, w_obj):
        return w_obj

    def exception_match(self, typ, sub):
        return typ is sub

    def int_w(self, w_obj):
        assert isinstance(w_obj, FakeInt)
        return w_obj.val

    def uint_w(self, w_obj):
        assert isinstance(w_obj, FakeInt)
        return rarithmetic.r_uint(w_obj.val)


    def str_w(self, w_obj):
        assert isinstance(w_obj, FakeString)
        return w_obj.val

    c_int_w = int_w

    def isinstance_w(self, w_obj, w_type):
        assert isinstance(w_obj, FakeBase)
        return w_obj.typename == w_type.name

    def type(self, w_obj):
        return FakeType("fake")

    def findattr(self, w_obj, w_name):
        return None

    def _freeze_(self):
        return True

class TestFastPathJIT(LLJitMixin):
    def test_simple(self):
        space = FakeSpace()
        drv = jit.JitDriver(greens=[], reds=["i", "inst", "addDataToInt"])
        def f():
            lib = interp_cppyy.load_lib(space, "./example01Dict.so")
            cls  = interp_cppyy.type_byname(space, "example01")
            inst = cls.construct([FakeInt(0)])
            addDataToInt = cls.get_overload("addDataToInt")
            assert isinstance(inst, interp_cppyy.W_CPPInstance)
            i = 10
            while i > 0:
                drv.jit_merge_point(inst=inst, addDataToInt=addDataToInt, i=i)
                inst.invoke(addDataToInt, [FakeInt(i)])
                i -= 1
            return 7
        f()
        space = FakeSpace()
        result = self.meta_interp(f, [], listops=True, backendopt=True, listcomp=True)
        self.check_loops(call=0, call_release_gil=1)
