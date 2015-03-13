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

    automatic_promotion_result = {
        'int_add' : 6, 'int_gt' : 1, 'guard_false' : 1, 'jump' : 1,
        'guard_value' : 3
    }

    def meta_interp(self, f, args, policy=None):
        return ll_meta_interp(f, args, enable_opts=self.enable_opts,
                              policy=policy,
                              CPUClass=self.CPUClass,
                              type_system=self.type_system)

    def test_simple_raw_load(self):
        myjitdriver = JitDriver(greens = [],
                                reds = ['i', 'res', 'va'],
                                vectorize=True)
        def f():
            res = r_uint(0)
            va = alloc_raw_storage(32, zero=True)
            for i in range(32):
                raw_storage_setitem(va, i, rffi.cast(rffi.UCHAR,i))
            i = 0
            while i < 32:
                myjitdriver.can_enter_jit(i=i, res=res,  va=va)
                myjitdriver.jit_merge_point(i=i, res=res, va=va)
                res += raw_storage_getitem(rffi.UCHAR,va,i)
                i += 1
            free_raw_storage(va)
            return res
        res = self.meta_interp(f, [])
        assert res == sum(range(32))
        self.check_trace_count(1)

class TestLLtype(VectorizeTest, LLJitMixin):
    pass
