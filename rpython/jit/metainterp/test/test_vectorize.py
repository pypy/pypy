import py

from rpython.jit.metainterp.warmspot import ll_meta_interp, get_stats
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp import history
from rpython.rlib.jit import JitDriver, hint, set_param
from rpython.rlib.objectmodel import compute_hash
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib.rawstorage import (alloc_raw_storage, raw_storage_setitem,
                                     free_raw_storage, raw_storage_getitem)

class VectorizeTest(object):
    enable_opts = 'all'

    def meta_interp(self, f, args, policy=None):
        return ll_meta_interp(f, args, enable_opts=self.enable_opts,
                              policy=policy,
                              CPUClass=self.CPUClass,
                              type_system=self.type_system)

    @py.test.mark.parametrize('i',[3,4,5,6,7,8,9,50])
    def test_vectorize_simple_load_arith_store_int_add_index(self,i):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i','d','bc','va','vb','vc'],
                                vectorize=True)
        def f(d):
            bc = d*rffi.sizeof(rffi.SIGNED)
            va = alloc_raw_storage(bc, zero=True)
            vb = alloc_raw_storage(bc, zero=True)
            vc = alloc_raw_storage(bc, zero=True)
            for i in range(d):
                j = i*rffi.sizeof(rffi.SIGNED)
                raw_storage_setitem(va, j, rffi.cast(rffi.SIGNED,i))
                raw_storage_setitem(vb, j, rffi.cast(rffi.SIGNED,i))
            i = 0
            while i < bc:
                myjitdriver.can_enter_jit(i=i, d=d, va=va, vb=vb, vc=vc, bc=bc)
                myjitdriver.jit_merge_point(i=i, d=d, va=va, vb=vb, vc=vc, bc=bc)
                a = raw_storage_getitem(rffi.SIGNED,va,i)
                b = raw_storage_getitem(rffi.SIGNED,vb,i)
                c = a+b
                raw_storage_setitem(vc, i, rffi.cast(rffi.SIGNED,c))
                i += 1*rffi.sizeof(rffi.SIGNED)
            res = 0
            for i in range(d):
                res += raw_storage_getitem(rffi.SIGNED,vc,i*rffi.sizeof(rffi.SIGNED))

            free_raw_storage(va)
            free_raw_storage(vb)
            free_raw_storage(vc)
            return res
        res = self.meta_interp(f, [i])
        assert res == f(i)
        if i > 3:
            self.check_trace_count(1)

    def test_guard(self):
        py.test.skip('abc')
        myjitdriver = JitDriver(greens = [],
                                reds = ['a','b','c'],
                                vectorize=True)
        def f(a,c):
            b = 0
            while b < c:
                myjitdriver.can_enter_jit(a=a, b=b, c=c)
                myjitdriver.jit_merge_point(a=a, b=b, c=c)

                if a:
                    a = not a
                b += 1

            return 42

        i = 32
        res = self.meta_interp(f, [True,i])
        assert res == 42
        self.check_trace_count(1)

    @py.test.mark.parametrize('i',[1,2,3,8,17,128,500])
    def test_vectorize_array_get_set(self,i):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i','d','va','vb','vc'],
                                vectorize=True)
        ET = rffi.SIGNED
        T = lltype.Array(ET, hints={'nolength': True})
        def f(d):
            i = 0
            va = lltype.malloc(T, d, flavor='raw', zero=True)
            vb = lltype.malloc(T, d, flavor='raw', zero=True)
            vc = lltype.malloc(T, d, flavor='raw', zero=True)
            for j in range(d):
                va[j] = j
                vb[j] = j
            while i < d:
                myjitdriver.can_enter_jit(i=i, d=d, va=va, vb=vb, vc=vc)
                myjitdriver.jit_merge_point(i=i, d=d, va=va, vb=vb, vc=vc)

                a = va[i]
                b = vb[i]
                vc[i] = a+b

                i += 1
            res = 0
            for j in range(d):
                res += intmask(vc[j])
            lltype.free(va, flavor='raw')
            lltype.free(vb, flavor='raw')
            lltype.free(vc, flavor='raw')
            return res
        res = self.meta_interp(f, [i])
        assert res == f(i)
        if i > 4:
            self.check_trace_count(1)

class TestLLtype(VectorizeTest, LLJitMixin):
    pass
