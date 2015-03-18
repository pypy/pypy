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

    def test_simple_raw_load(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'res', 'va','c'],
                                vectorize=True)
        def f(c):
            res = 0
            va = alloc_raw_storage(c*rffi.sizeof(rffi.SIGNED), zero=True)
            for i in range(c):
                raw_storage_setitem(va, i*rffi.sizeof(rffi.SIGNED),
                                    rffi.cast(rffi.SIGNED,i))
            i = 0
            while i < c:
                myjitdriver.can_enter_jit(i=i, res=res,  va=va, c=c)
                myjitdriver.jit_merge_point(i=i, res=res, va=va, c=c)
                res += raw_storage_getitem(rffi.SIGNED,va,i*rffi.sizeof(rffi.SIGNED))
                i += 1
            free_raw_storage(va)
            return res
        i = 32
        res = self.meta_interp(f, [i])
        assert res == sum(range(i))
        self.check_trace_count(1)

class TestLLtype(VectorizeTest, LLJitMixin):
    pass
