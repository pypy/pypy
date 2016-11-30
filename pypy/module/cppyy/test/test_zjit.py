import py, os, sys
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.objectmodel import specialize, instantiate
from rpython.rlib import rarithmetic, jit
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.baseobjspace import InternalSpaceCache, W_Root

from pypy.module.cppyy import interp_cppyy, capi
# These tests are for the backend that support the fast path only.
if capi.identify() == 'CINT':
    py.test.skip("CINT does not support fast path")
elif capi.identify() == 'loadable_capi':
    py.test.skip("can not currently use FakeSpace with _cffi_backend")

# load cpyext early, or its global vars are counted as leaks in the test
# (note that the module is not otherwise used in the test itself)
import pypy.module.cpyext

# change capi's direct_ptradd and exchange_address to being jit-opaque
@jit.dont_look_inside
def _opaque_direct_ptradd(ptr, offset):
    address = rffi.cast(rffi.CCHARP, ptr)
    return rffi.cast(capi.C_OBJECT, lltype.direct_ptradd(address, offset))
capi.direct_ptradd = _opaque_direct_ptradd

@jit.dont_look_inside
def _opaque_exchange_address(ptr, cif_descr, index):
    offset = rffi.cast(rffi.LONG, cif_descr.exchange_args[index])
    return rffi.ptradd(ptr, offset)
capi.exchange_address = _opaque_exchange_address

currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("example01Dict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make example01Dict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")


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
        self.__name__ = name
    def getname(self, space, name):
        return unicode(self.name)
class FakeBuffer(FakeBase):
    typedname = "buffer"
    def __init__(self, val):
        self.val = val
    def get_raw_address(self):
        raise ValueError("no raw buffer")
class FakeException(FakeType):
    def __init__(self, name):
        FakeType.__init__(self, name)
        self.message = name

class FakeUserDelAction(object):
    def __init__(self, space):
        pass

    def register_callback(self, w_obj, callback, descrname):
        pass

    def perform(self, executioncontext, frame):
        pass

class FakeSpace(object):
    fake = True

    w_ValueError = FakeException("ValueError")
    w_TypeError = FakeException("TypeError")
    w_AttributeError = FakeException("AttributeError")
    w_ReferenceError = FakeException("ReferenceError")
    w_NotImplementedError = FakeException("NotImplementedError")
    w_RuntimeError = FakeException("RuntimeError")

    w_None = None
    w_str = FakeType("str")
    w_int = FakeType("int")
    w_float = FakeType("float")

    def __init__(self):
        self.fromcache = InternalSpaceCache(self).getorbuild
        self.user_del_action = FakeUserDelAction(self)
        class dummy: pass
        self.config = dummy()
        self.config.translating = False

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

    def float_w(self, w_obj, allow_conversion=True):
        assert isinstance(w_obj, FakeFloat)
        return w_obj.val

    @specialize.arg(1)
    def interp_w(self, RequiredClass, w_obj, can_be_None=False):
        if can_be_None and w_obj is None:
            return None
        if not isinstance(w_obj, RequiredClass):
            raise TypeError
        return w_obj

    def getarg_w(self, code, w_obj):    # for retrieving buffers
        return FakeBuffer(w_obj)

    def exception_match(self, typ, sub):
        return typ is sub

    def is_w(self, w_one, w_two):
        return w_one is w_two

    def int_w(self, w_obj, allow_conversion=True):
        assert isinstance(w_obj, FakeInt)
        return w_obj.val

    def uint_w(self, w_obj):
        assert isinstance(w_obj, FakeInt)
        return rarithmetic.r_uint(w_obj.val)

    def str_w(self, w_obj):
        assert isinstance(w_obj, FakeString)
        return w_obj.val

    def str(self, obj):
        assert isinstance(obj, str)
        return obj

    c_int_w = int_w
    r_longlong_w = int_w
    r_ulonglong_w = uint_w

    def is_(self, w_obj1, w_obj2):
        return w_obj1 is w_obj2

    def isinstance_w(self, w_obj, w_type):
        assert isinstance(w_obj, FakeBase)
        return w_obj.typename == w_type.name

    def is_true(self, w_obj):
        return not not w_obj

    def type(self, w_obj):
        return FakeType("fake")

    def getattr(self, w_obj, w_name):
        assert isinstance(w_obj, FakeException)
        assert self.str_w(w_name) == "__name__"
        return FakeString(w_obj.name)

    def findattr(self, w_obj, w_name):
        return None

    def allocate_instance(self, cls, w_type):
        return instantiate(cls)

    def call_function(self, w_func, *args_w):
        return None

    def _freeze_(self):
        return True

class TestFastPathJIT(LLJitMixin):
    def _run_zjit(self, method_name):
        space = FakeSpace()
        drv = jit.JitDriver(greens=[], reds=["i", "inst", "cppmethod"])
        def f():
            lib = interp_cppyy.load_dictionary(space, "./example01Dict.so")
            cls  = interp_cppyy.scope_byname(space, "example01")
            inst = cls.get_overload("example01").call(None, [FakeInt(0)])
            cppmethod = cls.get_overload(method_name)
            assert isinstance(inst, interp_cppyy.W_CPPInstance)
            i = 10
            while i > 0:
                drv.jit_merge_point(inst=inst, cppmethod=cppmethod, i=i)
                cppmethod.call(inst, [FakeInt(i)])
                i -= 1
            return 7
        f()
        space = FakeSpace()
        result = self.meta_interp(f, [], listops=True, backendopt=True, listcomp=True)
        self.check_jitcell_token_count(1)

    def test01_simple(self):
        """Test fast path being taken for methods"""

        self._run_zjit("addDataToInt")

    def test02_overload(self):
        """Test fast path being taken for overloaded methods"""

        self._run_zjit("overloadedAddDataToInt")

    def test03_const_ref(self):
        """Test fast path being taken for methods with const ref arguments"""

        self._run_zjit("addDataToIntConstRef")
