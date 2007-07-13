from pypy.rpython.memory.gctransform.boehm import BoehmGCTransformer
from pypy.rpython.memory.gctransform.test.test_transform import rtype_and_transform, getops
from pypy.rpython.memory.gctransform.test.test_refcounting import make_deallocator
from pypy.rpython.lltypesystem import lltype
from pypy.translator.translator import graphof
from pypy.translator.c.gc import BoehmGcPolicy
from pypy.rpython.memory.gctransform.test.test_transform import LLInterpedTranformerTests
from pypy import conftest
import py

class TestLLInterpedBoehm(LLInterpedTranformerTests):
    gcpolicy = BoehmGcPolicy

def make_boehm_finalizer(TYPE):
    return make_deallocator(TYPE, attr="finalizer_funcptr_for_type",
                            cls=BoehmGCTransformer)

def test_boehm_simple():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c.x
    t, transformer = rtype_and_transform(
        f, [], BoehmGCTransformer, check=False)
    ops = getops(graphof(t, f))
    assert len(ops.get('direct_call', [])) <= 1
    gcs = [k for k in ops if k.startswith('gc')]
    assert len(gcs) == 0

def test_boehm_finalizer_simple():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    f, t = make_boehm_finalizer(S)
    assert f is None

def test_boehm_finalizer_pyobj():
    S = lltype.GcStruct("S", ('x', lltype.Ptr(lltype.PyObject)))
    f, t = make_boehm_finalizer(S)
    assert f is not None

def test_boehm_finalizer___del__():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(s):
        s.x = 1
    def type_info_S(p):
        return lltype.getRuntimeTypeInfo(S)
    qp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Ptr(lltype.RuntimeTypeInfo)),
                            "type_info_S",
                            _callable=type_info_S)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void),
                            "destructor_funcptr",
                            _callable=f)
    pinf = lltype.attachRuntimeTypeInfo(S, qp, destrptr=dp)
    f, t = make_boehm_finalizer(S)
    assert f is not None

def test_boehm_finalizer_nomix___del___and_pyobj():
    S = lltype.GcStruct("S", ('x', lltype.Signed), ('y', lltype.Ptr(lltype.PyObject)))
    def f(s):
        s.x = 1
    def type_info_S(p):
        return lltype.getRuntimeTypeInfo(S)
    qp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Ptr(lltype.RuntimeTypeInfo)),
                            "type_info_S",
                            _callable=type_info_S)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void),
                            "destructor_funcptr",
                            _callable=f)
    pinf = lltype.attachRuntimeTypeInfo(S, qp, destrptr=dp)
    py.test.raises(Exception, "make_boehm_finalizer(S)")
