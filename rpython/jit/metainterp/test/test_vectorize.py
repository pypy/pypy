import py

from rpython.jit.metainterp.warmspot import ll_meta_interp, get_stats
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp import history
from rpython.rlib.jit import JitDriver, hint, set_param
from rpython.rlib.objectmodel import compute_hash
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.rawstorage import (alloc_raw_storage, raw_storage_setitem,
                                     free_raw_storage, raw_storage_getitem)

class VectorizeTest(object):
    enable_opts = ''

    def meta_interp(self, f, args, policy=None):
        return ll_meta_interp(f, args, enable_opts=self.enable_opts,
                              policy=policy,
                              CPUClass=self.CPUClass,
                              type_system=self.type_system)

    def test_vectorize_simple_load_arith_store(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i','a','b','va','vb','vc','c','d'],
                                vectorize=True)
        def f(d):
            va = alloc_raw_storage(d*rffi.sizeof(rffi.SIGNED), zero=True)
            vb = alloc_raw_storage(d*rffi.sizeof(rffi.SIGNED), zero=True)
            vc = alloc_raw_storage(d*rffi.sizeof(rffi.SIGNED), zero=True)
            for i in range(d):
                raw_storage_setitem(va, i*rffi.sizeof(rffi.SIGNED),
                                    rffi.cast(rffi.SIGNED,i))
                raw_storage_setitem(vb, i*rffi.sizeof(rffi.SIGNED),
                                    rffi.cast(rffi.SIGNED,i))
            i = 0
            a = 0
            b = 0
            c = 0
            while i < d:
                myjitdriver.can_enter_jit(i=i, a=a, b=b, va=va, vb=vb, vc=vc, d=d, c=c)
                myjitdriver.jit_merge_point(i=i, a=a, b=b, va=va, vb=vb, vc=vc, d=d, c=c)
                a = raw_storage_getitem(rffi.SIGNED,va,i*rffi.sizeof(rffi.SIGNED))
                b = raw_storage_getitem(rffi.SIGNED,va,i*rffi.sizeof(rffi.SIGNED))
                c = a+b
                raw_storage_setitem(vc, i*rffi.sizeof(rffi.SIGNED), rffi.cast(rffi.SIGNED,c))
                i += 1
            res = 0
            for i in range(d):
                res += raw_storage_getitem(rffi.SIGNED,vc,i*rffi.sizeof(rffi.SIGNED))

            free_raw_storage(va)
            free_raw_storage(vb)
            free_raw_storage(vc)
            return res
        i = 32
        res = self.meta_interp(f, [i])
        assert res == sum(range(i)) + sum(range(i))
        self.check_trace_count(1)

class TestLLtype(VectorizeTest, LLJitMixin):
    pass
