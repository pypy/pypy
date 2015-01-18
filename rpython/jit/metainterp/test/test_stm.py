import py, sys
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.jit import JitDriver, dont_look_inside
from rpython.rlib.rarithmetic import ovfcheck, LONG_BIT, intmask
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.rlib import rstm




class STMTests:
    def test_simple(self):
        def g():
            return rstm.should_break_transaction(1)
        res = self.interp_operations(g, [], translationoptions={"stm":True})
        assert res == False
        self.check_operations_history(stm_should_break_transaction=1)

    def test_debug_merge_points(self):
        myjitdriver = JitDriver(greens = ['a'], reds = ['x', 'res'])
        def g(a, x):
            res = 0
            while x > 0:
                myjitdriver.jit_merge_point(a=a, x=x, res=res)
                res += x
                x -= 1
                a = -a
            return res
        res = self.meta_interp(g, [42, 10], translationoptions={"stm":True})
        assert res == 55
        self.check_resops(debug_merge_point=6)
        #
        from rpython.jit.metainterp.warmspot import get_stats
        loops = get_stats().get_all_loops()
        assert len(loops) == 1
        got = []
        for op in loops[0]._all_operations():
            if op.getopname() == "debug_merge_point":
                got.append(op.getarglist()[-1].value)
        assert got == [42, -42, 42, 42, -42, 42]

    def check_stm_locations(self, operations=None, cur_location="???"):
        if operations is None:
            from rpython.jit.metainterp.warmspot import get_stats
            loop = get_stats().get_all_loops()[0]
            operations = loop.operations
        #
        for op in operations:
            if op.getopname() == "debug_merge_point":
                num_box, ref_box = op.getarglist()[-2:]
                num = num_box.getint()
                ref = ref_box.getref_base()
                assert num == op.stm_location.num
                assert ref == op.stm_location.ref
                cur_location = (num, ref)
            elif op.getopname() in ("label", "finish", "jump"):
                pass
            else:
                stmloc = op.stm_location
                assert stmloc is not None, op
                assert cur_location == (stmloc.num, stmloc.ref)
                if (op.is_guard() and
                        hasattr(op.getdescr(), '_debug_suboperations')):
                    subops = op.getdescr()._debug_suboperations
                    self.check_stm_locations(subops, cur_location)

    def test_stm_report_location(self):
        myjitdriver = JitDriver(greens = ['a', 'r'], reds = ['x', 'res'],
                                stm_report_location = [0, 1])
        class Code(object):
            pass
        def g(a, r, x):
            res = 0
            while x > 0:
                myjitdriver.jit_merge_point(a=a, r=r, x=x, res=res)
                res += x
                x -= 1
                a = -a
            return res
        def main(a, x):
            r = Code()
            res = -1
            n = 7
            while n > 0:
                res = g(a, r, x)
                n -= 1
            return res
        res = self.meta_interp(main, [42, 10], translationoptions={"stm":True})
        assert res == 55
        self.check_resops(debug_merge_point=6)
        self.check_stm_locations()

    def test_stm_report_location_2(self):
        myjitdriver = JitDriver(greens = ['a', 'r'], reds = ['x', 'res', 'n'],
                                stm_report_location = [0, 1])
        class Code(object):
            pass
        def g(a, r, x, n):
            res = 0
            while x > 0:
                myjitdriver.jit_merge_point(a=a, r=r, x=x, res=res, n=n)
                res += x
                x -= 1
                a = -a
            if n & 1:
                pass   # sub-bridge of this bridge
            return res
        def main(a, x):
            r = Code()
            res = -1
            n = 7
            while n > 0:
                res = g(a, r, x, n)
                n -= 1
            return res
        res = self.meta_interp(main, [42, 10], translationoptions={"stm":True})
        assert res == 55
        self.check_resops(debug_merge_point=6)
        self.check_stm_locations()


class TestLLtype(STMTests, LLJitMixin):
    pass
