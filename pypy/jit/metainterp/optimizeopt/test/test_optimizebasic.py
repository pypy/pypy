import py
from pypy.rlib.objectmodel import instantiate
from pypy.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, FakeMetaInterpStaticData)
from pypy.jit.metainterp.test.test_compile import FakeLogger
import pypy.jit.metainterp.optimizeopt.optimizer as optimizeopt
import pypy.jit.metainterp.optimizeopt.virtualize as virtualize
from pypy.jit.metainterp.optimize import InvalidLoop
from pypy.jit.metainterp.history import AbstractDescr, ConstInt, BoxInt
from pypy.jit.metainterp import executor, compile, resume, history
from pypy.jit.metainterp.resoperation import rop, opname, ResOperation
from pypy.rlib.rarithmetic import LONG_BIT


def test_store_final_boxes_in_guard():
    from pypy.jit.metainterp.compile import ResumeGuardDescr
    from pypy.jit.metainterp.resume import tag, TAGBOX
    b0 = BoxInt()
    b1 = BoxInt()
    opt = optimizeopt.Optimizer(FakeMetaInterpStaticData(LLtypeMixin.cpu),
                                None)
    fdescr = ResumeGuardDescr()
    op = ResOperation(rop.GUARD_TRUE, ['dummy'], None, descr=fdescr)
    # setup rd data
    fi0 = resume.FrameInfo(None, "code0", 11)
    fdescr.rd_frame_info_list = resume.FrameInfo(fi0, "code1", 33)
    snapshot0 = resume.Snapshot(None, [b0])
    fdescr.rd_snapshot = resume.Snapshot(snapshot0, [b1])
    #
    opt.store_final_boxes_in_guard(op)
    if op.getfailargs() == [b0, b1]:
        assert list(fdescr.rd_numb.nums)      == [tag(1, TAGBOX)]
        assert list(fdescr.rd_numb.prev.nums) == [tag(0, TAGBOX)]
    else:
        assert op.getfailargs() == [b1, b0]
        assert list(fdescr.rd_numb.nums)      == [tag(0, TAGBOX)]
        assert list(fdescr.rd_numb.prev.nums) == [tag(1, TAGBOX)]
    assert fdescr.rd_virtuals is None
    assert fdescr.rd_consts == []

def test_sharing_field_lists_of_virtual():
    class FakeOptimizer(object):
        class optimizer(object):
            class cpu(object):
                pass
    opt = FakeOptimizer()
    virt1 = virtualize.AbstractVirtualStructValue(opt, None)
    lst1 = virt1._get_field_descr_list()
    assert lst1 == []
    lst2 = virt1._get_field_descr_list()
    assert lst1 is lst2
    virt1.setfield(LLtypeMixin.valuedescr, optimizeopt.OptValue(None))
    lst3 = virt1._get_field_descr_list()
    assert lst3 == [LLtypeMixin.valuedescr]
    lst4 = virt1._get_field_descr_list()
    assert lst3 is lst4

    virt2 = virtualize.AbstractVirtualStructValue(opt, None)
    lst5 = virt2._get_field_descr_list()
    assert lst5 is lst1
    virt2.setfield(LLtypeMixin.valuedescr, optimizeopt.OptValue(None))
    lst6 = virt1._get_field_descr_list()
    assert lst6 is lst3

def test_reuse_vinfo():
    class FakeVInfo(object):
        def set_content(self, fieldnums):
            self.fieldnums = fieldnums
        def equals(self, fieldnums):
            return self.fieldnums == fieldnums
    class FakeVirtualValue(virtualize.AbstractVirtualValue):
        def _make_virtual(self, *args):
            return FakeVInfo()
    v1 = FakeVirtualValue(None, None)
    vinfo1 = v1.make_virtual_info(None, [1, 2, 4])
    vinfo2 = v1.make_virtual_info(None, [1, 2, 4])
    assert vinfo1 is vinfo2
    vinfo3 = v1.make_virtual_info(None, [1, 2, 6])
    assert vinfo3 is not vinfo2
    vinfo4 = v1.make_virtual_info(None, [1, 2, 6])
    assert vinfo3 is vinfo4

def test_descrlist_dict():
    from pypy.jit.metainterp.optimizeopt import util as optimizeutil
    h1 = optimizeutil.descrlist_hash([])
    h2 = optimizeutil.descrlist_hash([LLtypeMixin.valuedescr])
    h3 = optimizeutil.descrlist_hash(
            [LLtypeMixin.valuedescr, LLtypeMixin.nextdescr])
    assert h1 != h2
    assert h2 != h3
    assert optimizeutil.descrlist_eq([], [])
    assert not optimizeutil.descrlist_eq([], [LLtypeMixin.valuedescr])
    assert optimizeutil.descrlist_eq([LLtypeMixin.valuedescr],
                                     [LLtypeMixin.valuedescr])
    assert not optimizeutil.descrlist_eq([LLtypeMixin.valuedescr],
                                         [LLtypeMixin.nextdescr])
    assert optimizeutil.descrlist_eq([LLtypeMixin.valuedescr, LLtypeMixin.nextdescr],
                                     [LLtypeMixin.valuedescr, LLtypeMixin.nextdescr])
    assert not optimizeutil.descrlist_eq([LLtypeMixin.nextdescr, LLtypeMixin.valuedescr],
                                         [LLtypeMixin.valuedescr, LLtypeMixin.nextdescr])

    # descrlist_eq should compare by identity of the descrs, not by the result
    # of sort_key
    class FakeDescr(object):
        def sort_key(self):
            return 1

    assert not optimizeutil.descrlist_eq([FakeDescr()], [FakeDescr()])


# ____________________________________________________________


class BaseTestBasic(BaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap"

    def optimize_loop(self, ops, optops, call_pure_results=None):

        loop = self.parse(ops)
        expected = self.parse(optops)
        self._do_optimize_loop(loop, call_pure_results)
        print '\n'.join([str(o) for o in loop.operations])
        self.assert_equal(loop, expected)

    def setup_method(self, meth=None):
        class FailDescr(compile.ResumeGuardDescr):
            oparse = None
            def _oparser_uses_descr_of_guard(self, oparse, fail_args):
                # typically called 3 times: once when parsing 'ops',
                # once when parsing 'preamble', once when parsing 'expected'.
                self.oparse = oparse
                self.rd_frame_info_list, self.rd_snapshot = snapshot(fail_args)
            def _clone_if_mutable(self):
                assert self is fdescr
                return fdescr2
            def __repr__(self):
                if self is fdescr:
                    return 'fdescr'
                if self is fdescr2:
                    return 'fdescr2'
                return compile.ResumeGuardDescr.__repr__(self)
        #
        def snapshot(fail_args, got=[]):
            if not got:    # only the first time, i.e. when parsing 'ops'
                rd_frame_info_list = resume.FrameInfo(None, "code", 11)
                rd_snapshot = resume.Snapshot(None, fail_args)
                got.append(rd_frame_info_list)
                got.append(rd_snapshot)
            return got
        #
        fdescr = instantiate(FailDescr)
        self.namespace['fdescr'] = fdescr
        fdescr2 = instantiate(FailDescr)
        self.namespace['fdescr2'] = fdescr2

    def teardown_method(self, meth):
        self.namespace.pop('fdescr', None)
        self.namespace.pop('fdescr2', None)



class BaseTestOptimizeBasic(BaseTestBasic):

    def test_simple(self):
        ops = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0) [i0]
        jump(i)
        """
        expected = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0) [i0]
        jump(1)
        """
        self.optimize_loop(ops, expected)

    def test_constant_propagate(self):
        ops = """
        []
        i0 = int_add(2, 3)
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_zero(i1)
        guard_false(i2) []
        guard_value(i0, 5) []
        jump()
        """
        expected = """
        []
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_constant_propagate_ovf(self):
        ops = """
        []
        i0 = int_add_ovf(2, 3)
        guard_no_overflow() []
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_zero(i1)
        guard_false(i2) []
        guard_value(i0, 5) []
        jump()
        """
        expected = """
        []
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_constfold_all(self):
        from pypy.jit.backend.llgraph.llimpl import TYPES     # xxx fish
        from pypy.jit.metainterp.executor import execute_nonspec
        from pypy.jit.metainterp.history import BoxInt
        import random
        for opnum in range(rop.INT_ADD, rop.SAME_AS+1):
            try:
                op = opname[opnum]
            except KeyError:
                continue
            if 'FLOAT' in op:
                continue
            argtypes, restype = TYPES[op.lower()]
            args = []
            for argtype in argtypes:
                assert argtype in ('int', 'bool')
                args.append(random.randrange(1, 20))
            assert restype in ('int', 'bool')
            ops = """
            []
            i1 = %s(%s)
            escape(i1)
            jump()
            """ % (op.lower(), ', '.join(map(str, args)))
            argboxes = [BoxInt(a) for a in args]
            expected_value = execute_nonspec(self.cpu, None, opnum,
                                             argboxes).getint()
            expected = """
            []
            escape(%d)
            jump()
            """ % expected_value
            self.optimize_loop(ops, expected)

    # ----------

    def test_remove_guard_class_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_class_2(self):
        ops = """
        [i0]
        p0 = new_with_vtable(ConstClass(node_vtable))
        escape(p0)
        guard_class(p0, ConstClass(node_vtable)) []
        jump(i0)
        """
        expected = """
        [i0]
        p0 = new_with_vtable(ConstClass(node_vtable))
        escape(p0)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_class_constant(self):
        ops = """
        [i0]
        p0 = same_as(ConstPtr(myptr))
        guard_class(p0, ConstClass(node_vtable)) []
        jump(i0)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_constant_boolrewrite_lt(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        i2 = int_ge(i0, 0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_constant_boolrewrite_gt(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = int_le(i0, 0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_constant_boolrewrite_reflex(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = int_lt(0, i0)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_constant_boolrewrite_reflex_invers(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = int_ge(0, i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_consecutive_guard_value_constfold(self):
        ops = """
        []
        i0 = escape()
        guard_value(i0, 0) []
        i1 = int_add(i0, 1)
        guard_value(i1, 1) []
        i2 = int_add(i1, 2)
        escape(i2)
        jump()
        """
        expected = """
        []
        i0 = escape()
        guard_value(i0, 0) []
        escape(3)
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_value_if_constant(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        expected = """
        []
        jump()
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Constant(myptr)', expected)

    def test_ooisnull_oononnull_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        guard_nonnull(p0) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_true_1(self):
        ops = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_true(i0)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_true_is_zero(self):
        py.test.skip("XXX implement me")
        ops = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_zero(i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_zero_int_is_true(self):
        ops = """
        [i0]
        i1 = int_is_zero(i0)
        guard_true(i1) []
        i2 = int_is_true(i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_is_zero(i0)
        guard_true(i1) []
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_ooisnull_oononnull_2(self):
        ops = """
        [p0]
        guard_nonnull(p0) []
        guard_nonnull(p0) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_ooisnull_on_null_ptr_1(self):
        ops = """
        []
        p0 = escape()
        guard_isnull(p0) []
        guard_isnull(p0) []
        jump()
        """
        expected = """
        []
        p0 = escape()
        guard_isnull(p0) []
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_ooisnull_oononnull_via_virtual(self):
        ops = """
        [p0]
        pv = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(pv, p0, descr=valuedescr)
        guard_nonnull(p0) []
        p1 = getfield_gc(pv, descr=valuedescr)
        guard_nonnull(p1) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_oois_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        i0 = instance_ptr_ne(p0, NULL)
        guard_true(i0) []
        i1 = instance_ptr_eq(p0, NULL)
        guard_false(i1) []
        i2 = instance_ptr_ne(NULL, p0)
        guard_true(i0) []
        i3 = instance_ptr_eq(NULL, p0)
        guard_false(i1) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_nonnull_1(self):
        ops = """
        [p0]
        setfield_gc(p0, 5, descr=valuedescr)     # forces p0 != NULL
        i0 = ptr_ne(p0, NULL)
        guard_true(i0) []
        i1 = ptr_eq(p0, NULL)
        guard_false(i1) []
        i2 = ptr_ne(NULL, p0)
        guard_true(i0) []
        i3 = ptr_eq(NULL, p0)
        guard_false(i1) []
        guard_nonnull(p0) []
        jump(p0)
        """
        expected = """
        [p0]
        setfield_gc(p0, 5, descr=valuedescr)
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_const_guard_value(self):
        ops = """
        []
        i = int_add(5, 3)
        guard_value(i, 8) []
        jump()
        """
        expected = """
        []
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_constptr_guard_value(self):
        ops = """
        []
        p1 = escape()
        guard_value(p1, ConstPtr(myptr)) []
        jump()
        """
        self.optimize_loop(ops, ops)

    def test_guard_value_to_guard_true(self):
        ops = """
        [i]
        i1 = int_lt(i, 3)
        guard_value(i1, 1) [i]
        jump(i)
        """
        expected = """
        [i]
        i1 = int_lt(i, 3)
        guard_true(i1) [i]
        jump(i)
        """
        self.optimize_loop(ops, expected)

    def test_guard_value_to_guard_false(self):
        ops = """
        [i]
        i1 = int_is_true(i)
        guard_value(i1, 0) [i]
        jump(i)
        """
        expected = """
        [i]
        i1 = int_is_true(i)
        guard_false(i1) [i]
        jump(i)
        """
        self.optimize_loop(ops, expected)

    def test_guard_value_on_nonbool(self):
        ops = """
        [i]
        i1 = int_add(i, 3)
        guard_value(i1, 0) [i]
        jump(i)
        """
        expected = """
        [i]
        i1 = int_add(i, 3)
        guard_value(i1, 0) [i]
        jump(-3)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_true_of_bool(self):
        ops = """
        [i0, i1]
        i2 = int_gt(i0, i1)
        i3 = int_is_true(i2)
        i4 = int_is_true(i3)
        guard_value(i4, 0) [i0, i1]
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_gt(i0, i1)
        guard_false(i2) [i0, i1]
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)




    def test_p123_simple(self):
        ops = """
        [i1, p2, p3]
        i3 = getfield_gc(p3, descr=valuedescr)
        escape(i3)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.optimize_loop(ops, ops)

    def test_p123_nested(self):
        ops = """
        [i1, p2, p3]
        i3 = getfield_gc(p3, descr=valuedescr)
        escape(i3)
        p1 = new_with_vtable(ConstClass(node_vtable))
        p1sub = new_with_vtable(ConstClass(node_vtable2))
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p1sub, i1, descr=valuedescr)
        setfield_gc(p1, p1sub, descr=nextdescr)
        jump(i1, p1, p2)
        """
        # The same as test_p123_simple, but with a virtual containing another
        # virtual.
        self.optimize_loop(ops, ops)

    def test_p123_anti_nested(self):
        ops = """
        [i1, p2, p3]
        p3sub = getfield_gc(p3, descr=nextdescr)
        i3 = getfield_gc(p3sub, descr=valuedescr)
        escape(i3)
        p1 = new_with_vtable(ConstClass(node_vtable))
        p2sub = new_with_vtable(ConstClass(node_vtable2))
        setfield_gc(p2sub, i1, descr=valuedescr)
        setfield_gc(p2, p2sub, descr=nextdescr)
        jump(i1, p1, p2)
        """
        # The same as test_p123_simple, but in the end the "old" p2 contains
        # a "young" virtual p2sub.  Make sure it is all forced.
        self.optimize_loop(ops, ops)

    # ----------

    def test_fold_guard_no_exception(self):
        ops = """
        [i]
        guard_no_exception() []
        i1 = int_add(i, 3)
        guard_no_exception() []
        i2 = call(i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        guard_no_exception() []
        i3 = call(i2, descr=nonwritedescr)
        jump(i1)       # the exception is considered lost when we loop back
        """
        expected = """
        [i]
        i1 = int_add(i, 3)
        i2 = call(i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        i3 = call(i2, descr=nonwritedescr)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    # ----------

    def test_call_loopinvariant(self):
        ops = """
        [i1]
        i2 = call_loopinvariant(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i2, 1) []
        i3 = call_loopinvariant(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i3, 1) []
        i4 = call_loopinvariant(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i4, 1) []
        jump(i1)
        """
        expected = """
        [i1]
        i2 = call(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i2, 1) []
        jump(i1)
        """
        self.optimize_loop(ops, expected)


    # ----------

    def test_virtual_1(self):
        ops = """
        [i, p0]
        i0 = getfield_gc(p0, descr=valuedescr)
        i1 = int_add(i0, i)
        setfield_gc(p0, i1, descr=valuedescr)
        jump(i, p0)
        """
        expected = """
        [i, i2]
        i1 = int_add(i2, i)
        jump(i, i1)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, Virtual(node_vtable, valuedescr=Not)',
                           expected)

    def test_virtual_float(self):
        ops = """
        [f, p0]
        f0 = getfield_gc(p0, descr=floatdescr)
        f1 = float_add(f0, f)
        setfield_gc(p0, f1, descr=floatdescr)
        jump(f, p0)
        """
        expected = """
        [f, f2]
        f1 = float_add(f2, f)
        jump(f, f1)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, Virtual(node_vtable, floatdescr=Not)',
                           expected)

    def test_virtual_2(self):
        ops = """
        [i, p0]
        i0 = getfield_gc(p0, descr=valuedescr)
        i1 = int_add(i0, i)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i, p1)
        """
        expected = """
        [i, i2]
        i1 = int_add(i2, i)
        jump(i, i1)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, Virtual(node_vtable, valuedescr=Not)',
                           expected)

    def test_virtual_oois(self):
        ops = """
        [p0, p1, p2]
        guard_nonnull(p0) []
        i3 = ptr_ne(p0, NULL)
        guard_true(i3) []
        i4 = ptr_eq(p0, NULL)
        guard_false(i4) []
        i5 = ptr_ne(NULL, p0)
        guard_true(i5) []
        i6 = ptr_eq(NULL, p0)
        guard_false(i6) []
        i7 = ptr_ne(p0, p1)
        guard_true(i7) []
        i8 = ptr_eq(p0, p1)
        guard_false(i8) []
        i9 = ptr_ne(p0, p2)
        guard_true(i9) []
        i10 = ptr_eq(p0, p2)
        guard_false(i10) []
        i11 = ptr_ne(p2, p1)
        guard_true(i11) []
        i12 = ptr_eq(p2, p1)
        guard_false(i12) []
        jump(p0, p1, p2)
        """
        expected = """
        [p2]
        # all constant-folded :-)
        jump(p2)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, '''Virtual(node_vtable),
                                   Virtual(node_vtable),
                                   Not''',
                           expected)
        #
        # to be complete, we also check the no-opt case where most comparisons
        # are not removed.  The exact set of comparisons removed depends on
        # the details of the algorithm...
        expected2 = """
        [p0, p1, p2]
        guard_nonnull(p0) []
        i7 = ptr_ne(p0, p1)
        guard_true(i7) []
        i9 = ptr_ne(p0, p2)
        guard_true(i9) []
        i11 = ptr_ne(p2, p1)
        guard_true(i11) []
        jump(p0, p1, p2)
        """
        self.optimize_loop(ops, expected2)

    def test_virtual_default_field(self):
        ops = """
        [p0]
        i0 = getfield_gc(p0, descr=valuedescr)
        guard_value(i0, 0) []
        p1 = new_with_vtable(ConstClass(node_vtable))
        # the field 'value' has its default value of 0
        jump(p1)
        """
        expected = """
        [i]
        guard_value(i, 0) []
        jump(0)
        """
        # the 'expected' is sub-optimal, but it should be done by another later
        # optimization step.  See test_find_nodes_default_field() for why.
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Virtual(node_vtable, valuedescr=Not)',
                           expected)

    def test_virtual_3(self):
        ops = """
        [i]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i, descr=valuedescr)
        i0 = getfield_gc(p1, descr=valuedescr)
        i1 = int_add(i0, 1)
        jump(i1)
        """
        expected = """
        [i]
        i1 = int_add(i, 1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_4(self):
        ops = """
        [i0, p0]
        guard_class(p0, ConstClass(node_vtable)) []
        i1 = getfield_gc(p0, descr=valuedescr)
        i2 = int_sub(i1, 1)
        i3 = int_add(i0, i1)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i2, descr=valuedescr)
        jump(i3, p1)
        """
        expected = """
        [i0, i1]
        i2 = int_sub(i1, 1)
        i3 = int_add(i0, i1)
        jump(i3, i2)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, Virtual(node_vtable, valuedescr=Not)',
                           expected)

    def test_virtual_5(self):
        ops = """
        [i0, p0]
        guard_class(p0, ConstClass(node_vtable)) []
        i1 = getfield_gc(p0, descr=valuedescr)
        i2 = int_sub(i1, 1)
        i3 = int_add(i0, i1)
        p2 = new_with_vtable(ConstClass(node_vtable2))
        setfield_gc(p2, i1, descr=valuedescr)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i2, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        jump(i3, p1)
        """
        expected = """
        [i0, i1, i1bis]
        i2 = int_sub(i1, 1)
        i3 = int_add(i0, i1)
        jump(i3, i2, i1)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops,
            '''Not, Virtual(node_vtable,
                            valuedescr=Not,
                            nextdescr=Virtual(node_vtable2,
                                              valuedescr=Not))''',
                           expected)

    def test_virtual_constant_isnull(self):
        ops = """
        [i0]
        p0 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p0, NULL, descr=nextdescr)
        p2 = getfield_gc(p0, descr=nextdescr)
        i1 = ptr_eq(p2, NULL)
        jump(i1)
        """
        expected = """
        [i0]
        jump(1)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_constant_isnonnull(self):
        ops = """
        [i0]
        p0 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p0, ConstPtr(myptr), descr=nextdescr)
        p2 = getfield_gc(p0, descr=nextdescr)
        i1 = ptr_eq(p2, NULL)
        jump(i1)
        """
        expected = """
        [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_array_of_struct(self):
        ops = """
        [f0, f1, f2, f3]
        p0 = new_array(2, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, f0, descr=complexrealdescr)
        setinteriorfield_gc(p0, 0, f1, descr=compleximagdescr)
        setinteriorfield_gc(p0, 1, f2, descr=complexrealdescr)
        setinteriorfield_gc(p0, 1, f3, descr=compleximagdescr)
        f4 = getinteriorfield_gc(p0, 0, descr=complexrealdescr)
        f5 = getinteriorfield_gc(p0, 1, descr=complexrealdescr)
        f6 = float_mul(f4, f5)
        f7 = getinteriorfield_gc(p0, 0, descr=compleximagdescr)
        f8 = getinteriorfield_gc(p0, 1, descr=compleximagdescr)
        f9 = float_mul(f7, f8)
        f10 = float_add(f6, f9)
        finish(f10)
        """
        expected = """
        [f0, f1, f2, f3]
        f4 = float_mul(f0, f2)
        f5 = float_mul(f1, f3)
        f6 = float_add(f4, f5)
        finish(f6)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_array_of_struct_forced(self):
        ops = """
        [f0, f1]
        p0 = new_array(1, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, f0, descr=complexrealdescr)
        setinteriorfield_gc(p0, 0, f1, descr=compleximagdescr)
        f2 = getinteriorfield_gc(p0, 0, descr=complexrealdescr)
        f3 = getinteriorfield_gc(p0, 0, descr=compleximagdescr)
        f4 = float_mul(f2, f3)
        i0 = escape(f4, p0)
        finish(i0)
        """
        expected = """
        [f0, f1]
        f2 = float_mul(f0, f1)
        p0 = new_array(1, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, f0, descr=complexrealdescr)
        setinteriorfield_gc(p0, 0, f1, descr=compleximagdescr)
        i0 = escape(f2, p0)
        finish(i0)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_1(self):
        ops = """
        [i]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i, descr=valuedescr)
        i0 = getfield_gc(p1, descr=valuedescr)
        i1 = int_add(i0, 1)
        escape(p1)
        escape(p1)
        jump(i1)
        """
        expected = """
        [i]
        i1 = int_add(i, 1)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i, descr=valuedescr)
        escape(p1)
        escape(p1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_2(self):
        ops = """
        [i, p0]
        i0 = getfield_gc(p0, descr=valuedescr)
        escape(p0)
        i1 = int_add(i0, i)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i, p1)
        """
        expected = ops
        self.optimize_loop(ops, expected)

    def test_nonvirtual_later(self):
        ops = """
        [i]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i, descr=valuedescr)
        i1 = getfield_gc(p1, descr=valuedescr)
        escape(p1)
        i2 = getfield_gc(p1, descr=valuedescr)
        i3 = int_add(i1, i2)
        jump(i3)
        """
        expected = """
        [i]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i, descr=valuedescr)
        escape(p1)
        i2 = getfield_gc(p1, descr=valuedescr)
        i3 = int_add(i, i2)
        jump(i3)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_dont_write_null_fields_on_force(self):
        ops = """
        [i]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i, descr=valuedescr)
        i1 = getfield_gc(p1, descr=valuedescr)
        setfield_gc(p1, 0, descr=valuedescr)
        escape(p1)
        i2 = getfield_gc(p1, descr=valuedescr)
        jump(i2)
        """
        expected = """
        [i]
        p1 = new_with_vtable(ConstClass(node_vtable))
        escape(p1)
        i2 = getfield_gc(p1, descr=valuedescr)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_gc_pure_1(self):
        ops = """
        [i]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i, descr=valuedescr)
        i1 = getfield_gc_pure(p1, descr=valuedescr)
        jump(i1)
        """
        expected = """
        [i]
        jump(i)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_gc_pure_2(self):
        ops = """
        [i]
        i1 = getfield_gc_pure(ConstPtr(myptr), descr=valuedescr)
        jump(i1)
        """
        expected = """
        [i]
        jump(5)
        """
        self.node.value = 5
        self.optimize_loop(ops, expected)

    def test_getfield_gc_nonpure_2(self):
        ops = """
        [i]
        i1 = getfield_gc(ConstPtr(myptr), descr=valuedescr)
        jump(i1)
        """
        expected = ops
        self.optimize_loop(ops, expected)

    def test_varray_1(self):
        ops = """
        [i1]
        p1 = new_array(3, descr=arraydescr)
        i3 = arraylen_gc(p1, descr=arraydescr)
        guard_value(i3, 3) []
        setarrayitem_gc(p1, 1, i1, descr=arraydescr)
        setarrayitem_gc(p1, 0, 25, descr=arraydescr)
        i2 = getarrayitem_gc(p1, 1, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_varray_alloc_and_set(self):
        ops = """
        [i1]
        p1 = new_array(2, descr=arraydescr)
        setarrayitem_gc(p1, 0, 25, descr=arraydescr)
        i2 = getarrayitem_gc(p1, 1, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_varray_float(self):
        ops = """
        [f1]
        p1 = new_array(3, descr=floatarraydescr)
        i3 = arraylen_gc(p1, descr=floatarraydescr)
        guard_value(i3, 3) []
        setarrayitem_gc(p1, 1, f1, descr=floatarraydescr)
        setarrayitem_gc(p1, 0, 3.5, descr=floatarraydescr)
        f2 = getarrayitem_gc(p1, 1, descr=floatarraydescr)
        jump(f2)
        """
        expected = """
        [f1]
        jump(f1)
        """
        self.optimize_loop(ops, expected)

    def test_array_non_optimized(self):
        ops = """
        [i1, p0]
        setarrayitem_gc(p0, 0, i1, descr=arraydescr)
        guard_nonnull(p0) []
        p1 = new_array(i1, descr=arraydescr)
        jump(i1, p1)
        """
        expected = """
        [i1, p0]
        p1 = new_array(i1, descr=arraydescr)
        setarrayitem_gc(p0, 0, i1, descr=arraydescr)
        jump(i1, p1)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_array_dont_write_null_fields_on_force(self):
        ops = """
        [i1]
        p1 = new_array(5, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        setarrayitem_gc(p1, 1, 0, descr=arraydescr)
        escape(p1)
        jump(i1)
        """
        expected = """
        [i1]
        p1 = new_array(5, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        escape(p1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_varray_2(self):
        ops = """
        [i0, p1]
        i1 = getarrayitem_gc(p1, 0, descr=arraydescr)
        i2 = getarrayitem_gc(p1, 1, descr=arraydescr)
        i3 = int_sub(i1, i2)
        guard_value(i3, 15) []
        p2 = new_array(2, descr=arraydescr)
        setarrayitem_gc(p2, 1, i0, descr=arraydescr)
        setarrayitem_gc(p2, 0, 20, descr=arraydescr)
        jump(i0, p2)
        """
        expected = """
        [i0, i1, i2]
        i3 = int_sub(i1, i2)
        guard_value(i3, 15) []
        jump(i0, 20, i0)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, VArray(arraydescr, Not, Not)', expected)

    def test_p123_array(self):
        ops = """
        [i1, p2, p3]
        i3 = getarrayitem_gc(p3, 0, descr=arraydescr)
        escape(i3)
        p1 = new_array(1, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.optimize_loop(ops, ops)

    def test_varray_forced_1(self):
        ops = """
        []
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, 3, descr=valuedescr)
        i1 = getfield_gc(p2, descr=valuedescr)    # i1 = const 3
        p1 = new_array(i1, descr=arraydescr)
        escape(p1)
        i2 = arraylen_gc(p1)
        escape(i2)
        jump()
        """
        expected = """
        []
        p1 = new_array(3, descr=arraydescr)
        escape(p1)
        i2 = arraylen_gc(p1)
        escape(i2)
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_vstruct_1(self):
        ops = """
        [i1, p2]
        i2 = getfield_gc(p2, descr=adescr)
        escape(i2)
        p3 = new(descr=ssize)
        setfield_gc(p3, i1, descr=adescr)
        jump(i1, p3)
        """
        expected = """
        [i1, i2]
        escape(i2)
        jump(i1, i1)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, VStruct(ssize, adescr=Not)', expected)

    def test_p123_vstruct(self):
        ops = """
        [i1, p2, p3]
        i3 = getfield_gc(p3, descr=adescr)
        escape(i3)
        p1 = new(descr=ssize)
        setfield_gc(p1, i1, descr=adescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.optimize_loop(ops, ops)

    def test_duplicate_getfield_1(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = getfield_gc(p2, descr=valuedescr)
        i3 = getfield_gc(p1, descr=valuedescr)
        i4 = getfield_gc(p2, descr=valuedescr)
        escape(i1)
        escape(i2)
        escape(i3)
        escape(i4)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = getfield_gc(p2, descr=valuedescr)
        escape(i1)
        escape(i2)
        escape(i1)
        escape(i2)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_after_setfield(self):
        ops = """
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i2 = getfield_gc(p1, descr=valuedescr)
        escape(i2)
        jump(p1, i1)
        """
        expected = """
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        escape(i1)
        jump(p1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_setfield_of_different_type_does_not_clear(self):
        ops = """
        [p1, p2, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, p1, descr=nextdescr)
        i2 = getfield_gc(p1, descr=valuedescr)
        escape(i2)
        jump(p1, p2, i1)
        """
        expected = """
        [p1, p2, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, p1, descr=nextdescr)
        escape(i1)
        jump(p1, p2, i1)
        """
        self.optimize_loop(ops, expected)

    def test_setfield_of_same_type_clears(self):
        ops = """
        [p1, p2, i1, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=valuedescr)
        i3 = getfield_gc(p1, descr=valuedescr)
        escape(i3)
        jump(p1, p2, i1, i3)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_getfield_mergepoint_has_no_side_effects(self):
        ops = """
        [p1]
        i1 = getfield_gc(p1, descr=valuedescr)
        debug_merge_point(15, 0)
        i2 = getfield_gc(p1, descr=valuedescr)
        escape(i1)
        escape(i2)
        jump(p1)
        """
        expected = """
        [p1]
        i1 = getfield_gc(p1, descr=valuedescr)
        debug_merge_point(15, 0)
        escape(i1)
        escape(i1)
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_ovf_op_does_not_clear(self):
        ops = """
        [p1]
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = int_add_ovf(i1, 14)
        guard_no_overflow() []
        i3 = getfield_gc(p1, descr=valuedescr)
        escape(i2)
        escape(i3)
        jump(p1)
        """
        expected = """
        [p1]
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = int_add_ovf(i1, 14)
        guard_no_overflow() []
        escape(i2)
        escape(i1)
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_setarrayitem_does_not_clear(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=valuedescr)
        setarrayitem_gc(p2, 0, p1, descr=arraydescr2)
        i3 = getfield_gc(p1, descr=valuedescr)
        escape(i1)
        escape(i3)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=valuedescr)
        setarrayitem_gc(p2, 0, p1, descr=arraydescr2)
        escape(i1)
        escape(i1)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_constant(self):
        ops = """
        []
        i1 = getfield_gc(ConstPtr(myptr), descr=valuedescr)
        i2 = getfield_gc(ConstPtr(myptr), descr=valuedescr)
        escape(i1)
        escape(i2)
        jump()
        """
        expected = """
        []
        i1 = getfield_gc(ConstPtr(myptr), descr=valuedescr)
        escape(i1)
        escape(i1)
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_guard_value_const(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = getfield_gc(ConstPtr(myptr), descr=valuedescr)
        escape(i1)
        escape(i2)
        jump(p1)
        """
        expected = """
        []
        i1 = getfield_gc(ConstPtr(myptr), descr=valuedescr)
        escape(i1)
        escape(i1)
        jump()
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Constant(myptr)', expected)

    def test_duplicate_getfield_sideeffects_1(self):
        ops = """
        [p1]
        i1 = getfield_gc(p1, descr=valuedescr)
        escape()
        i2 = getfield_gc(p1, descr=valuedescr)
        escape(i1)
        escape(i2)
        jump(p1)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_getfield_sideeffects_2(self):
        ops = """
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        escape()
        i2 = getfield_gc(p1, descr=valuedescr)
        escape(i2)
        jump(p1, i1)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_1(self):
        ops = """
        [p1, i1, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        expected = """
        [p1, i1, i2]
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_2(self):
        ops = """
        [p1, i1, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        i2 = getfield_gc(p1, descr=valuedescr)
        setfield_gc(p1, i3, descr=valuedescr)
        escape(i2)
        jump(p1, i1, i3)
        """
        expected = """
        [p1, i1, i3]
        setfield_gc(p1, i3, descr=valuedescr)
        escape(i1)
        jump(p1, i1, i3)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_3(self):
        ops = """
        [p1, p2, i1, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        i2 = getfield_gc(p2, descr=valuedescr)
        setfield_gc(p1, i3, descr=valuedescr)
        escape(i2)
        jump(p1, p2, i1, i3)
        """
        # potential aliasing of p1 and p2 means that we cannot kill the
        # the setfield_gc
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_4(self):
        ops = """
        [p1, i1, i2, p3]
        setfield_gc(p1, i1, descr=valuedescr)
        #
        # some operations on which the above setfield_gc cannot have effect
        i3 = getarrayitem_gc_pure(p3, 1, descr=arraydescr)
        i4 = getarrayitem_gc(p3, i3, descr=arraydescr)
        i5 = int_add(i3, i4)
        setarrayitem_gc(p3, 0, i5, descr=arraydescr)
        setfield_gc(p1, i4, descr=nextdescr)
        #
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        #
        i3 = getarrayitem_gc_pure(p3, 1, descr=arraydescr)
        i4 = getarrayitem_gc(p3, i3, descr=arraydescr)
        i5 = int_add(i3, i4)
        #
        setfield_gc(p1, i2, descr=valuedescr)
        setarrayitem_gc(p3, 0, i5, descr=arraydescr)
        setfield_gc(p1, i4, descr=nextdescr)
        jump(p1, i1, i2, p3)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_5(self):
        ops = """
        [p0, i1]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p0, p1, descr=nextdescr)
        setfield_raw(i1, i1, descr=valuedescr)    # random op with side-effects
        p2 = getfield_gc(p0, descr=nextdescr)
        i2 = getfield_gc(p2, descr=valuedescr)
        setfield_gc(p0, NULL, descr=nextdescr)
        escape(i2)
        jump(p0, i1)
        """
        expected = """
        [p0, i1]
        setfield_raw(i1, i1, descr=valuedescr)
        setfield_gc(p0, NULL, descr=nextdescr)
        escape(i1)
        jump(p0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_sideeffects_1(self):
        ops = """
        [p1, i1, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        escape()
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_residual_guard_1(self):
        ops = """
        [p1, i1, i2, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2, i4)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_residual_guard_2(self):
        # the difference with the previous test is that the field value is
        # a virtual, which we try hard to keep virtual
        ops = """
        [p1, i2, i3]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, p2, descr=nextdescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        expected = """
        [p1, i2, i3]
        guard_true(i3) [p1]
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_residual_guard_3(self):
        ops = """
        [p1, i2, i3]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        expected = """
        [p1, i2, i3]
        guard_true(i3) [i2, p1]
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_residual_guard_4(self):
        # test that the setfield_gc does not end up between int_eq and
        # the following guard_true
        ops = """
        [p1, i1, i2, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        i5 = int_eq(i3, 5)
        guard_true(i5) []
        i4 = int_neg(i2)
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2, i4)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_aliasing(self):
        # a case where aliasing issues (and not enough cleverness) mean
        # that we fail to remove any setfield_gc
        ops = """
        [p1, p2, i1, i2, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, p2, i1, i2, i3)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_guard_value_const(self):
        ops = """
        [p1, i1, i2]
        guard_value(p1, ConstPtr(myptr)) []
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(ConstPtr(myptr), i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        expected = """
        [i1, i2]
        setfield_gc(ConstPtr(myptr), i2, descr=valuedescr)
        jump(i1, i2)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Constant(myptr), Not, Not', expected)

    def test_duplicate_getarrayitem_1(self):
        ops = """
        [p1]
        p2 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p3 = getarrayitem_gc(p1, 1, descr=arraydescr2)
        p4 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p5 = getarrayitem_gc(p1, 1, descr=arraydescr2)
        escape(p2)
        escape(p3)
        escape(p4)
        escape(p5)
        jump(p1)
        """
        expected = """
        [p1]
        p2 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p3 = getarrayitem_gc(p1, 1, descr=arraydescr2)
        escape(p2)
        escape(p3)
        escape(p2)
        escape(p3)
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_1(self):
        ops = """
        [p1, p2]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        p3 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        escape(p3)
        jump(p1, p3)
        """
        expected = """
        [p1, p2]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        escape(p2)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_2(self):
        py.test.skip("setarrayitem with variable index")
        ops = """
        [p1, p2, p3, i1]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        p4 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p5 = getarrayitem_gc(p1, i1, descr=arraydescr2)
        escape(p4)
        escape(p5)
        jump(p1, p2, p3, i1)
        """
        expected = """
        [p1, p2, p3, i1]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        p4 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        escape(p4)
        escape(p3)
        jump(p1, p2, p3, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_3(self):
        ops = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, i1, p2, descr=arraydescr2)
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p1, 1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc(p1, i1, descr=arraydescr2)
        p6 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p7 = getarrayitem_gc(p1, 1, descr=arraydescr2)
        escape(p5)
        escape(p6)
        escape(p7)
        jump(p1, p2, p3, p4, i1)
        """
        expected = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, i1, p2, descr=arraydescr2)
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p1, 1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc(p1, i1, descr=arraydescr2)
        escape(p5)
        escape(p3)
        escape(p4)
        jump(p1, p2, p3, p4, i1)
        """
        self.optimize_loop(ops, expected)

    def test_getarrayitem_pure_does_not_invalidate(self):
        ops = """
        [p1, p2]
        p3 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        i4 = getfield_gc_pure(ConstPtr(myptr), descr=valuedescr)
        p5 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        escape(p3)
        escape(i4)
        escape(p5)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        p3 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        escape(p3)
        escape(5)
        escape(p3)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_two_arrays(self):
        ops = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p2, 1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p6 = getarrayitem_gc(p2, 1, descr=arraydescr2)
        escape(p5)
        escape(p6)
        jump(p1, p2, p3, p4, i1)
        """
        expected = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p2, 1, p4, descr=arraydescr2)
        escape(p3)
        escape(p4)
        jump(p1, p2, p3, p4, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_bug(self):
        ops = """
        [p0, i0, i1]
        setarrayitem_gc(p0, 0, i0, descr=arraydescr)
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i0)
        jump(p0, i11, i1)
        """
        expected = """
        [p0, i0, i1]
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, 0, i0, descr=arraydescr)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i0)
        jump(p0, i11, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_bug2(self):
        ops = """
        [p0, i0, i1]
        i2 = getarrayitem_gc(p0, 0, descr=arraydescr)
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i2)
        jump(p0, i11, i1)
        """
        expected = """
        [p0, i0, i1]
        i2 = getarrayitem_gc(p0, 0, descr=arraydescr)
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i2)
        jump(p0, i11, i1)
        """
        self.optimize_loop(ops, expected)

    def test_bug_1(self):
        ops = """
        [i0, p1]
        p4 = getfield_gc(p1, descr=nextdescr)
        guard_nonnull(p4) []
        escape(p4)
        #
        p2 = new_with_vtable(ConstClass(node_vtable))
        p3 = escape()
        setfield_gc(p2, p3, descr=nextdescr)
        jump(i0, p2)
        """
        expected = """
        [i0, p4]
        guard_nonnull(p4) []
        escape(p4)
        #
        p3 = escape()
        jump(i0, p3)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, Virtual(node_vtable, nextdescr=Not)',
                           expected)

    def test_bug_2(self):
        ops = """
        [i0, p1]
        p4 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        guard_nonnull(p4) []
        escape(p4)
        #
        p2 = new_array(1, descr=arraydescr2)
        p3 = escape()
        setarrayitem_gc(p2, 0, p3, descr=arraydescr2)
        jump(i0, p2)
        """
        expected = """
        [i0, p4]
        guard_nonnull(p4) []
        escape(p4)
        #
        p3 = escape()
        jump(i0, p3)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Not, VArray(arraydescr2, Not)',
                           expected)

    def test_bug_3(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        guard_class(p1, ConstClass(node_vtable2)) []
        p2 = getfield_gc(p1, descr=nextdescr)
        guard_nonnull(12) []
        guard_class(p2, ConstClass(node_vtable)) []
        p3 = getfield_gc(p1, descr=otherdescr)
        guard_nonnull(12) []
        guard_class(p3, ConstClass(node_vtable)) []
        setfield_gc(p3, p2, descr=otherdescr)
        p1a = new_with_vtable(ConstClass(node_vtable2))
        p2a = new_with_vtable(ConstClass(node_vtable))
        p3a = new_with_vtable(ConstClass(node_vtable))
        escape(p3a)
        setfield_gc(p1a, p2a, descr=nextdescr)
        setfield_gc(p1a, p3a, descr=otherdescr)
        jump(p1a)
        """
        expected = """
        [p2, p3]
        guard_class(p2, ConstClass(node_vtable)) []
        guard_class(p3, ConstClass(node_vtable)) []
        setfield_gc(p3, p2, descr=otherdescr)
        p3a = new_with_vtable(ConstClass(node_vtable))
        escape(p3a)
        p2a = new_with_vtable(ConstClass(node_vtable))
        jump(p2a, p3a)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Virtual(node_vtable2, nextdescr=Not, otherdescr=Not)', expected)

    def test_bug_3bis(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        guard_class(p1, ConstClass(node_vtable2)) []
        p2 = getfield_gc(p1, descr=nextdescr)
        guard_nonnull(12) []
        guard_class(p2, ConstClass(node_vtable)) []
        p3 = getfield_gc(p1, descr=otherdescr)
        guard_nonnull(12) []
        guard_class(p3, ConstClass(node_vtable)) []
        p1a = new_with_vtable(ConstClass(node_vtable2))
        p2a = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p3, p2a, descr=otherdescr)
        p3a = new_with_vtable(ConstClass(node_vtable))
        escape(p3a)
        setfield_gc(p1a, p2a, descr=nextdescr)
        setfield_gc(p1a, p3a, descr=otherdescr)
        jump(p1a)
        """
        expected = """
        [p2, p3]
        guard_class(p2, ConstClass(node_vtable)) []
        guard_class(p3, ConstClass(node_vtable)) []
        p2a = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p3, p2a, descr=otherdescr)
        p3a = new_with_vtable(ConstClass(node_vtable))
        escape(p3a)
        jump(p2a, p3a)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, 'Virtual(node_vtable2, nextdescr=Not, otherdescr=Not)', expected)

    def test_invalid_loop_1(self):
        ops = """
        [p1]
        guard_isnull(p1) []
        #
        p2 = new_with_vtable(ConstClass(node_vtable))
        jump(p2)
        """
        py.test.skip("XXX")
        py.test.raises(InvalidLoop, self.optimize_loop,
                       ops, 'Virtual(node_vtable)', None)

    def test_invalid_loop_2(self):
        py.test.skip("this would fail if we had Fixed again in the specnodes")
        ops = """
        [p1]
        guard_class(p1, ConstClass(node_vtable2)) []
        #
        p2 = new_with_vtable(ConstClass(node_vtable))
        escape(p2)      # prevent it from staying Virtual
        jump(p2)
        """
        py.test.raises(InvalidLoop, self.optimize_loop,
                       ops, '...', None)

    def test_invalid_loop_3(self):
        ops = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr)
        guard_isnull(p2) []
        #
        p3 = new_with_vtable(ConstClass(node_vtable))
        p4 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p3, p4, descr=nextdescr)
        jump(p3)
        """
        py.test.skip("XXX")
        py.test.raises(InvalidLoop, self.optimize_loop, ops,
                       'Virtual(node_vtable, nextdescr=Virtual(node_vtable))',
                       None)

    def test_merge_guard_class_guard_value(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_class(p1, ConstClass(node_vtable)) [i0]
        i3 = int_add(i1, i2)
        guard_value(p1, ConstPtr(myptr)) [i1]
        jump(p2, i0, i1, i3, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_value(p1, ConstPtr(myptr)) [i0]
        i3 = int_add(i1, i2)
        jump(p2, i0, i1, i3, p2)
        """
        self.optimize_loop(ops, expected)

    def test_merge_guard_nonnull_guard_class(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_nonnull(p1, descr=fdescr) [i0]
        i3 = int_add(i1, i2)
        guard_class(p1, ConstClass(node_vtable)) [i1]
        jump(p2, i0, i1, i3, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_nonnull_class(p1, ConstClass(node_vtable), descr=fdescr) [i0]
        i3 = int_add(i1, i2)
        jump(p2, i0, i1, i3, p2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr("i0", rop.GUARD_NONNULL_CLASS)

    def test_merge_guard_nonnull_guard_value(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_nonnull(p1, descr=fdescr) [i0]
        i3 = int_add(i1, i2)
        guard_value(p1, ConstPtr(myptr)) [i1]
        jump(p2, i0, i1, i3, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_value(p1, ConstPtr(myptr), descr=fdescr) [i0]
        i3 = int_add(i1, i2)
        jump(p2, i0, i1, i3, p2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr("i0", rop.GUARD_VALUE)

    def test_merge_guard_nonnull_guard_class_guard_value(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_nonnull(p1, descr=fdescr) [i0]
        i3 = int_add(i1, i2)
        guard_class(p1, ConstClass(node_vtable)) [i2]
        i4 = int_sub(i3, 1)
        guard_value(p1, ConstPtr(myptr)) [i1]
        jump(p2, i0, i1, i4, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_value(p1, ConstPtr(myptr), descr=fdescr) [i0]
        i3 = int_add(i1, i2)
        i4 = int_sub(i3, 1)
        jump(p2, i0, i1, i4, p2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr("i0", rop.GUARD_VALUE)

    def test_guard_class_oois(self):
        ops = """
        [p1]
        guard_class(p1, ConstClass(node_vtable2)) []
        i = instance_ptr_ne(ConstPtr(myptr), p1)
        guard_true(i) []
        jump(p1)
        """
        expected = """
        [p1]
        guard_class(p1, ConstClass(node_vtable2)) []
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_oois_of_itself(self):
        ops = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        p2 = getfield_gc(p0, descr=nextdescr)
        i1 = ptr_eq(p1, p2)
        guard_true(i1) []
        i2 = ptr_ne(p1, p2)
        guard_false(i2) []
        jump(p0)
        """
        expected = """
        [p0]
        p1 = getfield_gc(p0, descr=nextdescr)
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_duplicate_pure_op(self):
        ops = """
        [p1, p2]
        i1 = ptr_eq(p1, p2)
        i2 = ptr_eq(p1, p2)
        i3 = int_add(i1, 1)
        i3b = int_is_true(i3)
        guard_true(i3b) []
        i4 = int_add(i2, 1)
        i4b = int_is_true(i4)
        guard_true(i4b) []
        escape(i3)
        escape(i4)
        guard_true(i1) []
        guard_true(i2) []
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = ptr_eq(p1, p2)
        i3 = int_add(i1, 1)
        i3b = int_is_true(i3)
        guard_true(i3b) []
        escape(i3)
        escape(i3)
        guard_true(i1) []
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_remove_duplicate_pure_op_with_descr(self):
        ops = """
        [p1]
        i0 = arraylen_gc(p1, descr=arraydescr)
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = arraylen_gc(p1, descr=arraydescr)
        i3 = int_gt(i0, 0)
        guard_true(i3) []
        jump(p1)
        """
        expected = """
        [p1]
        i0 = arraylen_gc(p1, descr=arraydescr)
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_remove_duplicate_pure_op_ovf(self):
        ops = """
        [i1]
        i3 = int_add_ovf(i1, 1)
        guard_no_overflow() []
        i3b = int_is_true(i3)
        guard_true(i3b) []
        i4 = int_add_ovf(i1, 1)
        guard_no_overflow() []
        i4b = int_is_true(i4)
        guard_true(i4b) []
        escape(i3)
        escape(i4)
        jump(i1)
        """
        expected = """
        [i1]
        i3 = int_add_ovf(i1, 1)
        guard_no_overflow() []
        i3b = int_is_true(i3)
        guard_true(i3b) []
        escape(i3)
        escape(i3)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_int_and_or_with_zero(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 0)
        i3 = int_and(0, i2)
        i4 = int_or(i2, i1)
        i5 = int_or(i0, i3)
        jump(i4, i5)
        """
        expected = """
        [i0, i1]
        jump(i1, i0)
        """
        self.optimize_loop(ops, expected)

    def test_fold_partially_constant_ops(self):
        ops = """
        [i0]
        i1 = int_sub(i0, 0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add(i0, 0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add(0, i0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_floordiv(0, i0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_fold_partially_constant_ops_ovf(self):
        ops = """
        [i0]
        i1 = int_sub_ovf(i0, 0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add_ovf(i0, 0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add_ovf(0, i0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_fold_constant_partial_ops_float(self):
        ops = """
        [f0]
        f1 = float_mul(f0, 1.0)
        f2 = escape(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f2 = escape(f0)
        jump(f2)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [f0]
        f1 = float_mul(1.0, f0)
        f2 = escape(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f2 = escape(f0)
        jump(f2)
        """
        self.optimize_loop(ops, expected)


        ops = """
        [f0]
        f1 = float_mul(f0, -1.0)
        f2 = escape(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f1 = float_neg(f0)
        f2 = escape(f1)
        jump(f2)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [f0]
        f1 = float_mul(-1.0, f0)
        f2 = escape(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f1 = float_neg(f0)
        f2 = escape(f1)
        jump(f2)
        """
        self.optimize_loop(ops, expected)

    def test_fold_repeated_float_neg(self):
        ops = """
        [f0]
        f1 = float_neg(f0)
        f2 = float_neg(f1)
        f3 = float_neg(f2)
        f4 = float_neg(f3)
        escape(f4)
        jump(f4)
        """
        expected = """
        [f0]
        # The backend removes this dead op.
        f1 = float_neg(f0)
        escape(f0)
        jump(f0)
        """
        self.optimize_loop(ops, expected)

    # ----------

    def _verify_fail_args(self, boxes, oparse, text):
        import re
        r = re.compile(r"\bwhere\s+(\w+)\s+is a\s+(\w+)")
        parts = list(r.finditer(text))
        ends = [match.start() for match in parts] + [len(text)]
        #
        virtuals = {}
        for match, end in zip(parts, ends[1:]):
            pvar = match.group(1)
            fieldstext = text[match.end():end]
            if match.group(2) == 'varray':
                arrayname, fieldstext = fieldstext.split(':', 1)
                tag = ('varray', self.namespace[arrayname.strip()])
            elif match.group(2) == 'vstruct':
                if ',' in fieldstext:
                    structname, fieldstext = fieldstext.split(',', 1)
                else:
                    structname, fieldstext = fieldstext, ''
                tag = ('vstruct', self.namespace[structname.strip()])
            else:
                tag = ('virtual', self.namespace[match.group(2)])
            virtuals[pvar] = (tag, None, fieldstext)
        #
        r2 = re.compile(r"([\w\d()]+)[.](\w+)\s*=\s*([\w\d()]+)")
        pendingfields = []
        for match in r2.finditer(text):
            pvar = match.group(1)
            pfieldname = match.group(2)
            pfieldvar = match.group(3)
            pendingfields.append((pvar, pfieldname, pfieldvar))
        #
        def _variables_equal(box, varname, strict):
            if varname not in virtuals:
                if strict:
                    assert box.same_box(oparse.getvar(varname))
                else:
                    assert box.value == oparse.getvar(varname).value
            else:
                tag, resolved, fieldstext = virtuals[varname]
                if tag[0] == 'virtual':
                    assert self.get_class_of_box(box) == tag[1]
                elif tag[0] == 'varray':
                    pass    # xxx check arraydescr
                elif tag[0] == 'vstruct':
                    pass    # xxx check typedescr
                else:
                    assert 0
                if resolved is not None:
                    assert resolved.value == box.value
                else:
                    virtuals[varname] = tag, box, fieldstext
        #
        basetext = text.splitlines()[0]
        varnames = [s.strip() for s in basetext.split(',')]
        if varnames == ['']:
            varnames = []
        assert len(boxes) == len(varnames)
        for box, varname in zip(boxes, varnames):
            _variables_equal(box, varname, strict=True)
        for pvar, pfieldname, pfieldvar in pendingfields:
            box = oparse.getvar(pvar)
            fielddescr = self.namespace[pfieldname.strip()]
            fieldbox = executor.execute(self.cpu, None,
                                        rop.GETFIELD_GC,
                                        fielddescr,
                                        box)
            _variables_equal(fieldbox, pfieldvar, strict=True)
        #
        for match in parts:
            pvar = match.group(1)
            tag, resolved, fieldstext = virtuals[pvar]
            assert resolved is not None
            index = 0
            for fieldtext in fieldstext.split(','):
                fieldtext = fieldtext.strip()
                if not fieldtext:
                    continue
                if tag[0] in ('virtual', 'vstruct'):
                    fieldname, fieldvalue = fieldtext.split('=')
                    fielddescr = self.namespace[fieldname.strip()]
                    fieldbox = executor.execute(self.cpu, None,
                                                rop.GETFIELD_GC,
                                                fielddescr,
                                                resolved)
                elif tag[0] == 'varray':
                    fieldvalue = fieldtext
                    fieldbox = executor.execute(self.cpu, None,
                                                rop.GETARRAYITEM_GC,
                                                tag[1],
                                                resolved, ConstInt(index))
                else:
                    assert 0
                _variables_equal(fieldbox, fieldvalue.strip(), strict=False)
                index += 1

    def check_expanded_fail_descr(self, expectedtext, guard_opnum):
        from pypy.jit.metainterp.test.test_resume import ResumeDataFakeReader
        from pypy.jit.metainterp.test.test_resume import MyMetaInterp
        guard_op, = [op for op in self.loop.operations if op.is_guard()]
        fail_args = guard_op.getfailargs()
        fdescr = guard_op.getdescr()
        assert fdescr.guard_opnum == guard_opnum
        reader = ResumeDataFakeReader(fdescr, fail_args,
                                      MyMetaInterp(self.cpu))
        boxes = reader.consume_boxes()
        self._verify_fail_args(boxes, fdescr.oparse, expectedtext)

    def test_expand_fail_1(self):
        ops = """
        [i1, i3]
        # first rename i3 into i4
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i3, descr=valuedescr)
        i4 = getfield_gc(p1, descr=valuedescr)
        #
        i2 = int_add(10, 5)
        guard_true(i1, descr=fdescr) [i2, i4]
        jump(i1, i4)
        """
        expected = """
        [i1, i3]
        guard_true(i1, descr=fdescr) [i3]
        jump(1, i3)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('15, i3', rop.GUARD_TRUE)

    def test_expand_fail_2(self):
        ops = """
        [i1, i2]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i2, descr=valuedescr)
        setfield_gc(p1, p1, descr=nextdescr)
        guard_true(i1, descr=fdescr) [p1]
        jump(i1, i2)
        """
        expected = """
        [i1, i2]
        guard_true(i1, descr=fdescr) [i2]
        jump(1, i2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''ptr
            where ptr is a node_vtable, valuedescr=i2
            ''', rop.GUARD_TRUE)

    def test_expand_fail_3(self):
        ops = """
        [i1, i2, i3, p3]
        p1 = new_with_vtable(ConstClass(node_vtable))
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, 1, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p2, p3, descr=nextdescr)
        guard_true(i1, descr=fdescr) [i3, p1]
        jump(i2, i1, i3, p3)
        """
        expected = """
        [i1, i2, i3, p3]
        guard_true(i1, descr=fdescr) [i3, i2, p3]
        jump(i2, 1, i3, p3)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''i3, p1
            where p1 is a node_vtable, valuedescr=1, nextdescr=p2
            where p2 is a node_vtable, valuedescr=i2, nextdescr=p3
            ''', rop.GUARD_TRUE)

    def test_expand_fail_4(self):
        for arg in ['p1', 'i2,p1', 'p1,p2', 'p2,p1',
                    'i2,p1,p2', 'i2,p2,p1']:
            self.setup_method() # humpf
            ops = """
            [i1, i2, i3]
            p1 = new_with_vtable(ConstClass(node_vtable))
            setfield_gc(p1, i3, descr=valuedescr)
            i4 = getfield_gc(p1, descr=valuedescr)   # copy of i3
            p2 = new_with_vtable(ConstClass(node_vtable))
            setfield_gc(p1, i2, descr=valuedescr)
            setfield_gc(p1, p2, descr=nextdescr)
            setfield_gc(p2, i2, descr=valuedescr)
            guard_true(i1, descr=fdescr) [i4, i3, %s]
            jump(i1, i2, i3)
            """
            expected = """
            [i1, i2, i3]
            guard_true(i1, descr=fdescr) [i3, i2]
            jump(1, i2, i3)
            """
            self.optimize_loop(ops % arg, expected)
            self.check_expanded_fail_descr('''i3, i3, %s
                where p1 is a node_vtable, valuedescr=i2, nextdescr=p2
                where p2 is a node_vtable, valuedescr=i2''' % arg,
                                           rop.GUARD_TRUE)

    def test_expand_fail_5(self):
        ops = """
        [i1, i2, i3, i4]
        p1 = new_with_vtable(ConstClass(node_vtable))
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i4, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p2, p1, descr=nextdescr)      # a cycle
        guard_true(i1, descr=fdescr) [i3, i4, p1, p2]
        jump(i2, i1, i3, i4)
        """
        expected = """
        [i1, i2, i3, i4]
        guard_true(i1, descr=fdescr) [i3, i4, i2]
        jump(i2, 1, i3, i4)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''i3, i4, p1, p2
            where p1 is a node_vtable, valuedescr=i4, nextdescr=p2
            where p2 is a node_vtable, valuedescr=i2, nextdescr=p1
            ''', rop.GUARD_TRUE)

    def test_expand_fail_6(self):
        ops = """
        [p0, i0, i1]
        guard_true(i0, descr=fdescr) [p0]
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1, i1, descr=valuedescr)
        jump(p1, i1, i1)
        """
        expected = """
        [i1b, i0, i1]
        guard_true(i0, descr=fdescr) [i1b]
        jump(i1, i1, i1)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, '''Virtual(node_vtable, valuedescr=Not),
                                   Not, Not''', expected)
        self.check_expanded_fail_descr('''p0
            where p0 is a node_vtable, valuedescr=i1b
            ''', rop.GUARD_TRUE)

    def test_expand_fail_varray(self):
        ops = """
        [i1]
        p1 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 1, i1, descr=arraydescr)
        setarrayitem_gc(p1, 0, 25, descr=arraydescr)
        guard_true(i1, descr=fdescr) [p1]
        i2 = getarrayitem_gc(p1, 1, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        guard_true(i1, descr=fdescr) [i1]
        jump(1)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''p1
            where p1 is a varray arraydescr: 25, i1
            ''', rop.GUARD_TRUE)

    def test_expand_fail_vstruct(self):
        ops = """
        [i1, p1]
        p2 = new(descr=ssize)
        setfield_gc(p2, i1, descr=adescr)
        setfield_gc(p2, p1, descr=bdescr)
        guard_true(i1, descr=fdescr) [p2]
        i3 = getfield_gc(p2, descr=adescr)
        p3 = getfield_gc(p2, descr=bdescr)
        jump(i3, p3)
        """
        expected = """
        [i1, p1]
        guard_true(i1, descr=fdescr) [i1, p1]
        jump(1, p1)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''p2
            where p2 is a vstruct ssize, adescr=i1, bdescr=p1
            ''', rop.GUARD_TRUE)

    def test_expand_fail_v_all_1(self):
        ops = """
        [i1, p1a, i2]
        p6s = getarrayitem_gc(p1a, 0, descr=arraydescr2)
        p7v = getfield_gc(p6s, descr=bdescr)
        p5s = new(descr=ssize)
        setfield_gc(p5s, i2, descr=adescr)
        setfield_gc(p5s, p7v, descr=bdescr)
        setarrayitem_gc(p1a, 1, p5s, descr=arraydescr2)
        guard_true(i1, descr=fdescr) [p1a]
        p2s = new(descr=ssize)
        p3v = new_with_vtable(ConstClass(node_vtable))
        p4a = new_array(2, descr=arraydescr2)
        setfield_gc(p2s, i1, descr=adescr)
        setfield_gc(p2s, p3v, descr=bdescr)
        setfield_gc(p3v, i2, descr=valuedescr)
        setarrayitem_gc(p4a, 0, p2s, descr=arraydescr2)
        jump(i1, p4a, i2)
        """
        expected = """
        [i1, ia, iv, pnull, i2]
        guard_true(i1, descr=fdescr) [ia, iv, i2]
        jump(1, 1, i2, NULL, i2)
        """
        py.test.skip("XXX")
        self.optimize_loop(ops, '''
            Not,
            VArray(arraydescr2,
                   VStruct(ssize,
                           adescr=Not,
                           bdescr=Virtual(node_vtable,
                                          valuedescr=Not)),
                   Not),
            Not''', expected)
        self.check_expanded_fail_descr('''p1a
            where p1a is a varray arraydescr2: p6s, p5s
            where p6s is a vstruct ssize, adescr=ia, bdescr=p7v
            where p5s is a vstruct ssize, adescr=i2, bdescr=p7v
            where p7v is a node_vtable, valuedescr=iv
            ''', rop.GUARD_TRUE)

    def test_expand_fail_lazy_setfield_1(self):
        ops = """
        [p1, i2, i3]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        guard_true(i3, descr=fdescr) []
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        expected = """
        [p1, i2, i3]
        guard_true(i3, descr=fdescr) [p1, i2]
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        self.optimize_loop(ops, expected)
        self.loop.inputargs[0].value = self.nodebox.value
        self.check_expanded_fail_descr('''
            p1.nextdescr = p2
            where p2 is a node_vtable, valuedescr=i2
            ''', rop.GUARD_TRUE)

    def test_expand_fail_lazy_setfield_2(self):
        ops = """
        [i2, i3]
        p2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(ConstPtr(myptr), p2, descr=nextdescr)
        guard_true(i3, descr=fdescr) []
        i4 = int_neg(i2)
        setfield_gc(ConstPtr(myptr), NULL, descr=nextdescr)
        jump(i2, i4)
        """
        expected = """
        [i2, i3]
        guard_true(i3, descr=fdescr) [i2]
        i4 = int_neg(i2)
        setfield_gc(ConstPtr(myptr), NULL, descr=nextdescr)
        jump(i2, i4)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''
            ConstPtr(myptr).nextdescr = p2
            where p2 is a node_vtable, valuedescr=i2
            ''', rop.GUARD_TRUE)

    def test_residual_call_does_not_invalidate_caches(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = call(i1, descr=nonwritedescr)
        i3 = getfield_gc(p1, descr=valuedescr)
        escape(i1)
        escape(i3)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=valuedescr)
        i2 = call(i1, descr=nonwritedescr)
        escape(i1)
        escape(i1)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidate_some_caches(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=adescr)
        i2 = getfield_gc(p1, descr=bdescr)
        i3 = call(i1, descr=writeadescr)
        i4 = getfield_gc(p1, descr=adescr)
        i5 = getfield_gc(p1, descr=bdescr)
        escape(i1)
        escape(i2)
        escape(i4)
        escape(i5)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc(p1, descr=adescr)
        i2 = getfield_gc(p1, descr=bdescr)
        i3 = call(i1, descr=writeadescr)
        i4 = getfield_gc(p1, descr=adescr)
        escape(i1)
        escape(i2)
        escape(i4)
        escape(i2)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidate_arrays(self):
        ops = """
        [p1, p2, i1]
        p3 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p4 = getarrayitem_gc(p2, 1, descr=arraydescr2)
        i3 = call(i1, descr=writeadescr)
        p5 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p6 = getarrayitem_gc(p2, 1, descr=arraydescr2)
        escape(p3)
        escape(p4)
        escape(p5)
        escape(p6)
        jump(p1, p2, i1)
        """
        expected = """
        [p1, p2, i1]
        p3 = getarrayitem_gc(p1, 0, descr=arraydescr2)
        p4 = getarrayitem_gc(p2, 1, descr=arraydescr2)
        i3 = call(i1, descr=writeadescr)
        escape(p3)
        escape(p4)
        escape(p3)
        escape(p4)
        jump(p1, p2, i1)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidate_some_arrays(self):
        ops = """
        [p1, p2, i1]
        p3 = getarrayitem_gc(p2, 0, descr=arraydescr2)
        p4 = getarrayitem_gc(p2, 1, descr=arraydescr2)
        i2 = getarrayitem_gc(p1, 1, descr=arraydescr)
        i3 = call(i1, descr=writearraydescr)
        p5 = getarrayitem_gc(p2, 0, descr=arraydescr2)
        p6 = getarrayitem_gc(p2, 1, descr=arraydescr2)
        i4 = getarrayitem_gc(p1, 1, descr=arraydescr)
        escape(p3)
        escape(p4)
        escape(p5)
        escape(p6)
        escape(i2)
        escape(i4)
        jump(p1, p2, i1)
        """
        expected = """
        [p1, p2, i1]
        p3 = getarrayitem_gc(p2, 0, descr=arraydescr2)
        p4 = getarrayitem_gc(p2, 1, descr=arraydescr2)
        i2 = getarrayitem_gc(p1, 1, descr=arraydescr)
        i3 = call(i1, descr=writearraydescr)
        i4 = getarrayitem_gc(p1, 1, descr=arraydescr)
        escape(p3)
        escape(p4)
        escape(p3)
        escape(p4)
        escape(i2)
        escape(i4)
        jump(p1, p2, i1)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidates_some_read_caches_1(self):
        ops = """
        [p1, i1, p2, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=adescr)
        i3 = call(i1, descr=readadescr)
        setfield_gc(p1, i3, descr=valuedescr)
        setfield_gc(p2, i3, descr=adescr)
        jump(p1, i1, p2, i2)
        """
        expected = """
        [p1, i1, p2, i2]
        setfield_gc(p2, i2, descr=adescr)
        i3 = call(i1, descr=readadescr)
        setfield_gc(p1, i3, descr=valuedescr)
        setfield_gc(p2, i3, descr=adescr)
        jump(p1, i1, p2, i2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidates_some_read_caches_2(self):
        ops = """
        [p1, i1, p2, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=adescr)
        i3 = call(i1, descr=writeadescr)
        setfield_gc(p1, i3, descr=valuedescr)
        setfield_gc(p2, i3, descr=adescr)
        jump(p1, i1, p2, i2)
        """
        expected = """
        [p1, i1, p2, i2]
        setfield_gc(p2, i2, descr=adescr)
        i3 = call(i1, descr=writeadescr)
        setfield_gc(p1, i3, descr=valuedescr)
        setfield_gc(p2, i3, descr=adescr)
        jump(p1, i1, p2, i2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidates_some_read_caches_3(self):
        ops = """
        [p1, i1, p2, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=adescr)
        i3 = call(i1, descr=plaincalldescr)
        setfield_gc(p1, i3, descr=valuedescr)
        setfield_gc(p2, i3, descr=adescr)
        jump(p1, i1, p2, i2)
        """
        self.optimize_loop(ops, ops)

    def test_call_assembler_invalidates_caches(self):
        ops = '''
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i3 = call_assembler(i1, descr=asmdescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i3)
        '''
        self.optimize_loop(ops, ops)

    def test_call_pure_invalidates_caches(self):
        # CALL_PURE should still force the setfield_gc() to occur before it
        ops = '''
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i3 = call_pure(p1, descr=plaincalldescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i3)
        '''
        expected = '''
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i3 = call(p1, descr=plaincalldescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i3)
        '''
        self.optimize_loop(ops, expected)

    def test_call_pure_constant_folding(self):
        # CALL_PURE is not marked as is_always_pure(), because it is wrong
        # to call the function arbitrary many times at arbitrary points in
        # time.  Check that it is either constant-folded (and replaced by
        # the result of the call, recorded as the first arg), or turned into
        # a regular CALL.
        arg_consts = [ConstInt(i) for i in (123456, 4, 5, 6)]
        call_pure_results = {tuple(arg_consts): ConstInt(42)}
        ops = '''
        [i0, i1, i2]
        escape(i1)
        escape(i2)
        i3 = call_pure(123456, 4, 5, 6, descr=plaincalldescr)
        i4 = call_pure(123456, 4, i0, 6, descr=plaincalldescr)
        jump(i0, i3, i4)
        '''
        expected = '''
        [i0, i1, i2]
        escape(i1)
        escape(i2)
        i4 = call(123456, 4, i0, 6, descr=plaincalldescr)
        jump(i0, 42, i4)
        '''
        self.optimize_loop(ops, expected, call_pure_results)

    def test_vref_nonvirtual_nonescape(self):
        ops = """
        [p1]
        p2 = virtual_ref(p1, 5)
        virtual_ref_finish(p2, p1)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = force_token()
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_vref_nonvirtual_escape(self):
        ops = """
        [p1]
        p2 = virtual_ref(p1, 5)
        escape(p2)
        virtual_ref_finish(p2, p1)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = force_token()
        p2 = new_with_vtable(ConstClass(jit_virtual_ref_vtable))
        setfield_gc(p2, i0, descr=virtualtokendescr)
        escape(p2)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        setfield_gc(p2, -3, descr=virtualtokendescr)
        jump(p1)
        """
        # XXX we should optimize a bit more the case of a nonvirtual.
        # in theory it is enough to just do 'p2 = p1'.
        self.optimize_loop(ops, expected)

    def test_vref_virtual_1(self):
        ops = """
        [p0, i1]
        #
        p1 = new_with_vtable(ConstClass(node_vtable))
        p1b = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1b, 252, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        #
        p2 = virtual_ref(p1, 3)
        setfield_gc(p0, p2, descr=nextdescr)
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        virtual_ref_finish(p2, p1)
        setfield_gc(p0, NULL, descr=nextdescr)
        jump(p0, i1)
        """
        expected = """
        [p0, i1]
        i3 = force_token()
        #
        p2 = new_with_vtable(ConstClass(jit_virtual_ref_vtable))
        setfield_gc(p2, i3, descr=virtualtokendescr)
        setfield_gc(p0, p2, descr=nextdescr)
        #
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        #
        setfield_gc(p0, NULL, descr=nextdescr)
        p1 = new_with_vtable(ConstClass(node_vtable))
        p1b = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1b, 252, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        setfield_gc(p2, -3, descr=virtualtokendescr)
        jump(p0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_vref_virtual_2(self):
        ops = """
        [p0, i1]
        #
        p1 = new_with_vtable(ConstClass(node_vtable))
        p1b = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1b, i1, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        #
        p2 = virtual_ref(p1, 2)
        setfield_gc(p0, p2, descr=nextdescr)
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced(descr=fdescr) [p2, p1]
        virtual_ref_finish(p2, p1)
        setfield_gc(p0, NULL, descr=nextdescr)
        jump(p0, i1)
        """
        expected = """
        [p0, i1]
        i3 = force_token()
        #
        p2 = new_with_vtable(ConstClass(jit_virtual_ref_vtable))
        setfield_gc(p2, i3, descr=virtualtokendescr)
        setfield_gc(p0, p2, descr=nextdescr)
        #
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced(descr=fdescr) [p2, i1]
        #
        setfield_gc(p0, NULL, descr=nextdescr)
        p1 = new_with_vtable(ConstClass(node_vtable))
        p1b = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1b, i1, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        setfield_gc(p2, -3, descr=virtualtokendescr)
        jump(p0, i1)
        """
        # the point of this test is that 'i1' should show up in the fail_args
        # of 'guard_not_forced', because it was stored in the virtual 'p1b'.
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''p2, p1
            where p1 is a node_vtable, nextdescr=p1b
            where p1b is a node_vtable, valuedescr=i1
            ''', rop.GUARD_NOT_FORCED)

    def test_vref_virtual_and_lazy_setfield(self):
        ops = """
        [p0, i1]
        #
        p1 = new_with_vtable(ConstClass(node_vtable))
        p1b = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p1b, i1, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        #
        p2 = virtual_ref(p1, 2)
        setfield_gc(p0, p2, descr=refdescr)
        call(i1, descr=nonwritedescr)
        guard_no_exception(descr=fdescr) [p2, p1]
        virtual_ref_finish(p2, p1)
        setfield_gc(p0, NULL, descr=refdescr)
        jump(p0, i1)
        """
        expected = """
        [p0, i1]
        i3 = force_token()
        call(i1, descr=nonwritedescr)
        guard_no_exception(descr=fdescr) [i3, i1, p0]
        setfield_gc(p0, NULL, descr=refdescr)
        jump(p0, i1)
        """
        self.optimize_loop(ops, expected)
        # the fail_args contain [i3, i1, p0]:
        #  - i3 is from the virtual expansion of p2
        #  - i1 is from the virtual expansion of p1
        #  - p0 is from the extra pendingfields
        self.loop.inputargs[0].value = self.nodeobjvalue
        self.check_expanded_fail_descr('''p2, p1
            p0.refdescr = p2
            where p2 is a jit_virtual_ref_vtable, virtualtokendescr=i3
            where p1 is a node_vtable, nextdescr=p1b
            where p1b is a node_vtable, valuedescr=i1
            ''', rop.GUARD_NO_EXCEPTION)

    def test_vref_virtual_after_finish(self):
        ops = """
        [i1]
        p1 = new_with_vtable(ConstClass(node_vtable))
        p2 = virtual_ref(p1, 7)
        escape(p2)
        virtual_ref_finish(p2, p1)
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced() []
        jump(i1)
        """
        expected = """
        [i1]
        i3 = force_token()
        p2 = new_with_vtable(ConstClass(jit_virtual_ref_vtable))
        setfield_gc(p2, i3, descr=virtualtokendescr)
        escape(p2)
        p1 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p2, p1, descr=virtualforceddescr)
        setfield_gc(p2, -3, descr=virtualtokendescr)
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced() []
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_vref_nonvirtual_and_lazy_setfield(self):
        ops = """
        [i1, p1]
        p2 = virtual_ref(p1, 23)
        escape(p2)
        virtual_ref_finish(p2, p1)
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        jump(i1, p1)
        """
        expected = """
        [i1, p1]
        i3 = force_token()
        p2 = new_with_vtable(ConstClass(jit_virtual_ref_vtable))
        setfield_gc(p2, i3, descr=virtualtokendescr)
        escape(p2)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        setfield_gc(p2, -3, descr=virtualtokendescr)
        call_may_force(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        jump(i1, p1)
        """
        self.optimize_loop(ops, expected)

    def test_arraycopy_1(self):
        ops = '''
        [i0]
        p1 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 1, 1, descr=arraydescr)
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p2, 1, 3, descr=arraydescr)
        call(0, p1, p2, 1, 1, 2, descr=arraycopydescr)
        i2 = getarrayitem_gc(p2, 1, descr=arraydescr)
        jump(i2)
        '''
        expected = '''
        [i0]
        jump(1)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_2(self):
        ops = '''
        [i0]
        p1 = new_array(3, descr=arraydescr)
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 0, i0, descr=arraydescr)
        setarrayitem_gc(p2, 0, 3, descr=arraydescr)
        call(0, p1, p2, 1, 1, 2, descr=arraycopydescr)
        i2 = getarrayitem_gc(p2, 0, descr=arraydescr)
        jump(i2)
        '''
        expected = '''
        [i0]
        jump(3)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_not_virtual(self):
        ops = '''
        [p0]
        p1 = new_array(3, descr=arraydescr)
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 2, 10, descr=arraydescr)
        setarrayitem_gc(p2, 2, 13, descr=arraydescr)
        call(0, p1, p2, 0, 0, 3, descr=arraycopydescr)
        jump(p2)
        '''
        expected = '''
        [p0]
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p2, 2, 10, descr=arraydescr)
        jump(p2)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_no_elem(self):
        """ this was actually observed in the wild
        """
        ops = '''
        [p1]
        p0 = new_array(0, descr=arraydescr)
        call(0, p0, p1, 0, 0, 0, descr=arraycopydescr)
        jump(p1)
        '''
        expected = '''
        [p1]
        jump(p1)
        '''
        self.optimize_loop(ops, expected)

    def test_bound_lt(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_noguard(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        i2 = int_lt(i0, 5)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        i2 = int_lt(i0, 5)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_noopt(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(4)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_rev(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        i2 = int_gt(i0, 3)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_tripple(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        i2 = int_lt(i0, 7)
        guard_true(i2) []
        i3 = int_lt(i0, 5)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_add(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add(i0, 10)
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add(i0, 10)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_add_before(self):
        ops = """
        [i0]
        i2 = int_add(i0, 10)
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        i1 = int_lt(i0, 6)
        guard_true(i1) []
        jump(i0)
        """
        expected = """
        [i0]
        i2 = int_add(i0, 10)
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_add_ovf(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add(i0, 10)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_add_ovf_before(self):
        ops = """
        [i0]
        i2 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        i1 = int_lt(i0, 6)
        guard_true(i1) []
        jump(i0)
        """
        expected = """
        [i0]
        i2 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_sub(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i1p = int_gt(i0, -4)
        guard_true(i1p) []
        i2 = int_sub(i0, 10)
        i3 = int_lt(i2, -5)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i1p = int_gt(i0, -4)
        guard_true(i1p) []
        i2 = int_sub(i0, 10)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_sub_before(self):
        ops = """
        [i0]
        i2 = int_sub(i0, 10)
        i3 = int_lt(i2, -5)
        guard_true(i3) []
        i1 = int_lt(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        expected = """
        [i0]
        i2 = int_sub(i0, 10)
        i3 = int_lt(i2, -5)
        guard_true(i3) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_ltle(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_le(i0, 3)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lelt(self):
        ops = """
        [i0]
        i1 = int_le(i0, 4)
        guard_true(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_le(i0, 4)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_gt(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        i2 = int_gt(i0, 4)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_gtge(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        i2 = int_ge(i0, 6)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_gegt(self):
        ops = """
        [i0]
        i1 = int_ge(i0, 5)
        guard_true(i1) []
        i2 = int_gt(i0, 4)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_ge(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_ovf(self):
        ops = """
        [i0]
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_add_ovf(i0, 1)
        guard_no_overflow() []
        jump(i3)
        """
        expected = """
        [i0]
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_add(i0, 1)
        jump(i3)
        """
        self.optimize_loop(ops, expected)

    def test_bound_arraylen(self):
        ops = """
        [i0, p0]
        p1 = new_array(i0, descr=arraydescr)
        i1 = arraylen_gc(p1)
        i2 = int_gt(i1, -1)
        guard_true(i2) []
        setarrayitem_gc(p0, 0, p1)
        jump(i0, p0)
        """
        # The dead arraylen_gc will be eliminated by the backend.
        expected = """
        [i0, p0]
        p1 = new_array(i0, descr=arraydescr)
        i1 = arraylen_gc(p1)
        setarrayitem_gc(p0, 0, p1)
        jump(i0, p0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_strlen(self):
        ops = """
        [p0]
        i0 = strlen(p0)
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        jump(p0)
        """
        # The dead strlen will be eliminated be the backend.
        expected = """
        [p0]
        i0 = strlen(p0)
        jump(p0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_addsub_const(self):
        ops = """
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_sub(i1, 1)
        i3 = int_add(i2, 1)
        i4 = int_mul(i2, i3)
        jump(i4)
        """
        expected = """
        [i0]
        i1 = int_add(i0, 1)
        i4 = int_mul(i0, i1)
        jump(i4)
        """
        self.optimize_loop(ops, expected)

    def test_addsub_int(self):
        ops = """
        [i0, i10]
        i1 = int_add(i0, i10)
        i2 = int_sub(i1, i10)
        i3 = int_add(i2, i10)
        i4 = int_add(i2, i3)
        jump(i4, i10)
        """
        expected = """
        [i0, i10]
        i1 = int_add(i0, i10)
        i4 = int_add(i0, i1)
        jump(i4, i10)
        """
        self.optimize_loop(ops, expected)

    def test_addsub_int2(self):
        ops = """
        [i0, i10]
        i1 = int_add(i10, i0)
        i2 = int_sub(i1, i10)
        i3 = int_add(i10, i2)
        i4 = int_add(i2, i3)
        jump(i4, i10)
        """
        expected = """
        [i0, i10]
        i1 = int_add(i10, i0)
        i4 = int_add(i0, i1)
        jump(i4, i10)
        """
        self.optimize_loop(ops, expected)

    def test_framestackdepth_overhead(self):
        ops = """
        [p0, i22]
        i1 = getfield_gc(p0, descr=valuedescr)
        i2 = int_gt(i1, i22)
        guard_false(i2) []
        i3 = int_add(i1, 1)
        setfield_gc(p0, i3, descr=valuedescr)
        i4 = int_sub(i3, 1)
        setfield_gc(p0, i4, descr=valuedescr)
        i5 = int_gt(i4, i22)
        guard_false(i5) []
        i6 = int_add(i4, 1)
        i331 = force_token()
        i7 = int_sub(i6, 1)
        setfield_gc(p0, i7, descr=valuedescr)
        jump(p0, i22)
        """
        expected = """
        [p0, i22]
        i1 = getfield_gc(p0, descr=valuedescr)
        i2 = int_gt(i1, i22)
        guard_false(i2) []
        i3 = int_add(i1, 1)
        i331 = force_token()
        jump(p0, i22)
        """
        self.optimize_loop(ops, expected)

    def test_addsub_ovf(self):
        ops = """
        [i0]
        i1 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_sub_ovf(i1, 5)
        guard_no_overflow() []
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_sub(i1, 5)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_subadd_ovf(self):
        ops = """
        [i0]
        i1 = int_sub_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_add_ovf(i1, 5)
        guard_no_overflow() []
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_sub_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_add(i1, 5)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_bound_and(self):
        ops = """
        [i0]
        i1 = int_and(i0, 255)
        i2 = int_lt(i1, 500)
        guard_true(i2) []
        i3 = int_le(i1, 255)
        guard_true(i3) []
        i4 = int_gt(i1, -1)
        guard_true(i4) []
        i5 = int_ge(i1, 0)
        guard_true(i5) []
        i6 = int_lt(i1, 0)
        guard_false(i6) []
        i7 = int_le(i1, -1)
        guard_false(i7) []
        i8 = int_gt(i1, 255)
        guard_false(i8) []
        i9 = int_ge(i1, 500)
        guard_false(i9) []
        i12 = int_lt(i1, 100)
        guard_true(i12) []
        i13 = int_le(i1, 90)
        guard_true(i13) []
        i14 = int_gt(i1, 10)
        guard_true(i14) []
        i15 = int_ge(i1, 20)
        guard_true(i15) []
        jump(i1)
        """
        expected = """
        [i0]
        i1 = int_and(i0, 255)
        i12 = int_lt(i1, 100)
        guard_true(i12) []
        i13 = int_le(i1, 90)
        guard_true(i13) []
        i14 = int_gt(i1, 10)
        guard_true(i14) []
        i15 = int_ge(i1, 20)
        guard_true(i15) []
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_subsub_ovf(self):
        ops = """
        [i0]
        i1 = int_sub_ovf(1, i0)
        guard_no_overflow() []
        i2 = int_gt(i1, 1)
        guard_true(i2) []
        i3 = int_sub_ovf(1, i0)
        guard_no_overflow() []
        i4 = int_gt(i3, 1)
        guard_true(i4) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_sub_ovf(1, i0)
        guard_no_overflow() []
        i2 = int_gt(i1, 1)
        guard_true(i2) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_eq(self):
        ops = """
        [i0, i1]
        i2 = int_le(i0, 4)
        guard_true(i2) []
        i3 = int_eq(i0, i1)
        guard_true(i3) []
        i4 = int_lt(i1, 5)
        guard_true(i4) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_le(i0, 4)
        guard_true(i2) []
        i3 = int_eq(i0, i1)
        guard_true(i3) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_bound_eq_const(self):
        ops = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_true(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_true(i1) []
        jump(10)

        """
        self.optimize_loop(ops, expected)

    def test_bound_eq_const_not(self):
        ops = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_false(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_false(i1) []
        i2 = int_add(i0, 3)
        jump(i2)

        """
        self.optimize_loop(ops, expected)

    def test_bound_ne_const(self):
        ops = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_false(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_false(i1) []
        jump(10)

        """
        self.optimize_loop(ops, expected)

    def test_bound_ne_const_not(self):
        ops = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_true(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_true(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_bound_ltne(self):
        ops = """
        [i0, i1]
        i2 = int_lt(i0, 7)
        guard_true(i2) []
        i3 = int_ne(i0, 10)
        guard_true(i2) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_lt(i0, 7)
        guard_true(i2) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lege_const(self):
        ops = """
        [i0]
        i1 = int_ge(i0, 7)
        guard_true(i1) []
        i2 = int_le(i0, 7)
        guard_true(i2) []
        i3 = int_add(i0, 3)
        jump(i3)
        """
        expected = """
        [i0]
        i1 = int_ge(i0, 7)
        guard_true(i1) []
        i2 = int_le(i0, 7)
        guard_true(i2) []
        jump(10)

        """
        self.optimize_loop(ops, expected)

    def test_mul_ovf(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_lt(i1, 5)
        guard_true(i3) []
        i4 = int_gt(i1, -10)
        guard_true(i4) []
        i5 = int_mul_ovf(i2, i1)
        guard_no_overflow() []
        i6 = int_lt(i5, -2550)
        guard_false(i6) []
        i7 = int_ge(i5, 1276)
        guard_false(i7) []
        i8 = int_gt(i5, 126)
        guard_true(i8) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_lt(i1, 5)
        guard_true(i3) []
        i4 = int_gt(i1, -10)
        guard_true(i4) []
        i5 = int_mul(i2, i1)
        i8 = int_gt(i5, 126)
        guard_true(i8) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_mul_ovf_before(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i22 = int_add(i2, 1)
        i3 = int_mul_ovf(i22, i1)
        guard_no_overflow() []
        i4 = int_lt(i3, 10)
        guard_true(i4) []
        i5 = int_gt(i3, 2)
        guard_true(i5) []
        i6 = int_lt(i1, 0)
        guard_false(i6) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i22 = int_add(i2, 1)
        i3 = int_mul_ovf(i22, i1)
        guard_no_overflow() []
        i4 = int_lt(i3, 10)
        guard_true(i4) []
        i5 = int_gt(i3, 2)
        guard_true(i5) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_sub_ovf_before(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_sub_ovf(i2, i1)
        guard_no_overflow() []
        i4 = int_le(i3, 10)
        guard_true(i4) []
        i5 = int_ge(i3, 2)
        guard_true(i5) []
        i6 = int_lt(i1, -10)
        guard_false(i6) []
        i7 = int_gt(i1, 253)
        guard_false(i7) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_sub_ovf(i2, i1)
        guard_no_overflow() []
        i4 = int_le(i3, 10)
        guard_true(i4) []
        i5 = int_ge(i3, 2)
        guard_true(i5) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    # ----------
    def optimize_strunicode_loop(self, ops, optops):
        # check with the arguments passed in
        self.optimize_loop(ops, optops)
        # check with replacing 'str' with 'unicode' everywhere
        self.optimize_loop(ops.replace('str','unicode').replace('s"', 'u"'),
                           optops.replace('str','unicode').replace('s"', 'u"'))

    def test_newstr_1(self):
        ops = """
        [i0]
        p1 = newstr(1)
        strsetitem(p1, 0, i0)
        i1 = strgetitem(p1, 0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_newstr_2(self):
        ops = """
        [i0, i1]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        i2 = strgetitem(p1, 1)
        i3 = strgetitem(p1, 0)
        jump(i2, i3)
        """
        expected = """
        [i0, i1]
        jump(i1, i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_1(self):
        ops = """
        [p1, p2]
        p3 = call(0, p1, p2, descr=strconcatdescr)
        jump(p2, p3)
        """
        expected = """
        [p1, p2]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i3 = int_add(i1, i2)
        p3 = newstr(i3)
        copystrcontent(p1, p3, 0, 0, i1)
        copystrcontent(p2, p3, 0, i1, i2)
        jump(p2, p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_vstr2_str(self):
        ops = """
        [i0, i1, p2]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        p3 = call(0, p1, p2, descr=strconcatdescr)
        jump(i1, i0, p3)
        """
        expected = """
        [i0, i1, p2]
        i2 = strlen(p2)
        i3 = int_add(2, i2)
        p3 = newstr(i3)
        strsetitem(p3, 0, i0)
        strsetitem(p3, 1, i1)
        copystrcontent(p2, p3, 0, 2, i2)
        jump(i1, i0, p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_str_vstr2(self):
        ops = """
        [i0, i1, p2]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        p3 = call(0, p2, p1, descr=strconcatdescr)
        jump(i1, i0, p3)
        """
        expected = """
        [i0, i1, p2]
        i2 = strlen(p2)
        i3 = int_add(i2, 2)
        p3 = newstr(i3)
        copystrcontent(p2, p3, 0, 0, i2)
        strsetitem(p3, i2, i0)
        i5 = int_add(i2, 1)
        strsetitem(p3, i5, i1)
        i6 = int_add(i5, 1)      # will be killed by the backend
        jump(i1, i0, p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_str_str_str(self):
        ops = """
        [p1, p2, p3]
        p4 = call(0, p1, p2, descr=strconcatdescr)
        p5 = call(0, p4, p3, descr=strconcatdescr)
        jump(p2, p3, p5)
        """
        expected = """
        [p1, p2, p3]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i12 = int_add(i1, i2)
        i3 = strlen(p3)
        i123 = int_add(i12, i3)
        p5 = newstr(i123)
        copystrcontent(p1, p5, 0, 0, i1)
        copystrcontent(p2, p5, 0, i1, i2)
        copystrcontent(p3, p5, 0, i12, i3)
        jump(p2, p3, p5)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_str_cstr1(self):
        ops = """
        [p2]
        p3 = call(0, p2, s"x", descr=strconcatdescr)
        jump(p3)
        """
        expected = """
        [p2]
        i2 = strlen(p2)
        i3 = int_add(i2, 1)
        p3 = newstr(i3)
        copystrcontent(p2, p3, 0, 0, i2)
        strsetitem(p3, i2, 120)     # == ord('x')
        jump(p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_consts(self):
        ops = """
        []
        p1 = same_as(s"ab")
        p2 = same_as(s"cde")
        p3 = call(0, p1, p2, descr=strconcatdescr)
        escape(p3)
        jump()
        """
        expected = """
        []
        escape(s"abcde")
        jump()
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_1(self):
        ops = """
        [p1, i1, i2]
        p2 = call(0, p1, i1, i2, descr=strslicedescr)
        jump(p2, i1, i2)
        """
        expected = """
        [p1, i1, i2]
        i3 = int_sub(i2, i1)
        p2 = newstr(i3)
        copystrcontent(p1, p2, i1, 0, i3)
        jump(p2, i1, i2)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_2(self):
        ops = """
        [p1, i2]
        p2 = call(0, p1, 0, i2, descr=strslicedescr)
        jump(p2, i2)
        """
        expected = """
        [p1, i2]
        p2 = newstr(i2)
        copystrcontent(p1, p2, 0, 0, i2)
        jump(p2, i2)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_3(self):
        ops = """
        [p1, i1, i2, i3, i4]
        p2 = call(0, p1, i1, i2, descr=strslicedescr)
        p3 = call(0, p2, i3, i4, descr=strslicedescr)
        jump(p3, i1, i2, i3, i4)
        """
        expected = """
        [p1, i1, i2, i3, i4]
        i0 = int_sub(i2, i1)     # killed by the backend
        i5 = int_sub(i4, i3)
        i6 = int_add(i1, i3)
        p3 = newstr(i5)
        copystrcontent(p1, p3, i6, 0, i5)
        jump(p3, i1, i2, i3, i4)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_getitem1(self):
        ops = """
        [p1, i1, i2, i3]
        p2 = call(0, p1, i1, i2, descr=strslicedescr)
        i4 = strgetitem(p2, i3)
        escape(i4)
        jump(p1, i1, i2, i3)
        """
        expected = """
        [p1, i1, i2, i3]
        i6 = int_sub(i2, i1)      # killed by the backend
        i5 = int_add(i1, i3)
        i4 = strgetitem(p1, i5)
        escape(i4)
        jump(p1, i1, i2, i3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_plain(self):
        ops = """
        [i3, i4]
        p1 = newstr(2)
        strsetitem(p1, 0, i3)
        strsetitem(p1, 1, i4)
        p2 = call(0, p1, 1, 2, descr=strslicedescr)
        i5 = strgetitem(p2, 0)
        escape(i5)
        jump(i3, i4)
        """
        expected = """
        [i3, i4]
        escape(i4)
        jump(i3, i4)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_concat(self):
        ops = """
        [p1, i1, i2, p2]
        p3 = call(0, p1, i1, i2, descr=strslicedescr)
        p4 = call(0, p3, p2, descr=strconcatdescr)
        jump(p4, i1, i2, p2)
        """
        expected = """
        [p1, i1, i2, p2]
        i3 = int_sub(i2, i1)     # length of p3
        i4 = strlen(p2)
        i5 = int_add(i3, i4)
        p4 = newstr(i5)
        copystrcontent(p1, p4, i1, 0, i3)
        copystrcontent(p2, p4, 0, i3, i4)
        jump(p4, i1, i2, p2)
        """
        self.optimize_strunicode_loop(ops, expected)

    # ----------
    def optimize_strunicode_loop_extradescrs(self, ops, optops):
        class FakeCallInfoCollection:
            def callinfo_for_oopspec(self, oopspecindex):
                calldescrtype = type(LLtypeMixin.strequaldescr)
                effectinfotype = type(LLtypeMixin.strequaldescr.get_extra_info())
                for value in LLtypeMixin.__dict__.values():
                    if isinstance(value, calldescrtype):
                        extra = value.get_extra_info()
                        if (extra and isinstance(extra, effectinfotype) and
                            extra.oopspecindex == oopspecindex):
                            # returns 0 for 'func' in this test
                            return value, 0
                raise AssertionError("not found: oopspecindex=%d" %
                                     oopspecindex)
        #
        self.callinfocollection = FakeCallInfoCollection()
        self.optimize_strunicode_loop(ops, optops)

    def test_str_equal_noop1(self):
        ops = """
        [p1, p2]
        i0 = call(0, p1, p2, descr=strequaldescr)
        escape(i0)
        jump(p1, p2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, ops)

    def test_str_equal_noop2(self):
        ops = """
        [p1, p2, p3]
        p4 = call(0, p1, p2, descr=strconcatdescr)
        i0 = call(0, p3, p4, descr=strequaldescr)
        escape(i0)
        jump(p1, p2, p3)
        """
        expected = """
        [p1, p2, p3]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i3 = int_add(i1, i2)
        p4 = newstr(i3)
        copystrcontent(p1, p4, 0, 0, i1)
        copystrcontent(p2, p4, 0, i1, i2)
        i0 = call(0, p3, p4, descr=strequaldescr)
        escape(i0)
        jump(p1, p2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice1(self):
        ops = """
        [p1, i1, i2, p3]
        p4 = call(0, p1, i1, i2, descr=strslicedescr)
        i0 = call(0, p4, p3, descr=strequaldescr)
        escape(i0)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        i3 = int_sub(i2, i1)
        i0 = call(0, p1, i1, i3, p3, descr=streq_slice_checknull_descr)
        escape(i0)
        jump(p1, i1, i2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice2(self):
        ops = """
        [p1, i1, i2, p3]
        p4 = call(0, p1, i1, i2, descr=strslicedescr)
        i0 = call(0, p3, p4, descr=strequaldescr)
        escape(i0)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        i4 = int_sub(i2, i1)
        i0 = call(0, p1, i1, i4, p3, descr=streq_slice_checknull_descr)
        escape(i0)
        jump(p1, i1, i2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice3(self):
        ops = """
        [p1, i1, i2, p3]
        guard_nonnull(p3) []
        p4 = call(0, p1, i1, i2, descr=strslicedescr)
        i0 = call(0, p3, p4, descr=strequaldescr)
        escape(i0)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        guard_nonnull(p3) []
        i4 = int_sub(i2, i1)
        i0 = call(0, p1, i1, i4, p3, descr=streq_slice_nonnull_descr)
        escape(i0)
        jump(p1, i1, i2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice4(self):
        ops = """
        [p1, i1, i2]
        p3 = call(0, p1, i1, i2, descr=strslicedescr)
        i0 = call(0, p3, s"x", descr=strequaldescr)
        escape(i0)
        jump(p1, i1, i2)
        """
        expected = """
        [p1, i1, i2]
        i3 = int_sub(i2, i1)
        i0 = call(0, p1, i1, i3, 120, descr=streq_slice_char_descr)
        escape(i0)
        jump(p1, i1, i2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice5(self):
        ops = """
        [p1, i1, i2, i3]
        p4 = call(0, p1, i1, i2, descr=strslicedescr)
        p5 = newstr(1)
        strsetitem(p5, 0, i3)
        i0 = call(0, p5, p4, descr=strequaldescr)
        escape(i0)
        jump(p1, i1, i2, i3)
        """
        expected = """
        [p1, i1, i2, i3]
        i4 = int_sub(i2, i1)
        i0 = call(0, p1, i1, i4, i3, descr=streq_slice_char_descr)
        escape(i0)
        jump(p1, i1, i2, i3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_none1(self):
        ops = """
        [p1]
        i0 = call(0, p1, NULL, descr=strequaldescr)
        escape(i0)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = ptr_eq(p1, NULL)
        escape(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_none2(self):
        ops = """
        [p1]
        i0 = call(0, NULL, p1, descr=strequaldescr)
        escape(i0)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = ptr_eq(p1, NULL)
        escape(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull1(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        i0 = call(0, p1, s"hello world", descr=strequaldescr)
        escape(i0)
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        i0 = call(0, p1, s"hello world", descr=streq_nonnull_descr)
        escape(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull2(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        i0 = call(0, p1, s"", descr=strequaldescr)
        escape(i0)
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        i1 = strlen(p1)
        i0 = int_eq(i1, 0)
        escape(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull3(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        i0 = call(0, p1, s"x", descr=strequaldescr)
        escape(i0)
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        i0 = call(0, p1, 120, descr=streq_nonnull_char_descr)
        escape(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull4(self):
        ops = """
        [p1, p2]
        p4 = call(0, p1, p2, descr=strconcatdescr)
        i0 = call(0, s"hello world", p4, descr=strequaldescr)
        escape(i0)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i3 = int_add(i1, i2)
        p4 = newstr(i3)
        copystrcontent(p1, p4, 0, 0, i1)
        copystrcontent(p2, p4, 0, i1, i2)
        i0 = call(0, s"hello world", p4, descr=streq_nonnull_descr)
        escape(i0)
        jump(p1, p2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars0(self):
        ops = """
        [i1]
        p1 = newstr(0)
        i0 = call(0, p1, s"", descr=strequaldescr)
        escape(i0)
        jump(i1)
        """
        expected = """
        [i1]
        escape(1)
        jump(i1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars1(self):
        ops = """
        [i1]
        p1 = newstr(1)
        strsetitem(p1, 0, i1)
        i0 = call(0, p1, s"x", descr=strequaldescr)
        escape(i0)
        jump(i1)
        """
        expected = """
        [i1]
        i0 = int_eq(i1, 120)     # ord('x')
        escape(i0)
        jump(i1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars2(self):
        ops = """
        [i1, i2]
        p1 = newstr(2)
        strsetitem(p1, 0, i1)
        strsetitem(p1, 1, i2)
        i0 = call(0, p1, s"xy", descr=strequaldescr)
        escape(i0)
        jump(i1, i2)
        """
        expected = """
        [i1, i2]
        p1 = newstr(2)
        strsetitem(p1, 0, i1)
        strsetitem(p1, 1, i2)
        i0 = call(0, p1, s"xy", descr=streq_lengthok_descr)
        escape(i0)
        jump(i1, i2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars3(self):
        ops = """
        [p1]
        i0 = call(0, s"x", p1, descr=strequaldescr)
        escape(i0)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = call(0, p1, 120, descr=streq_checknull_char_descr)
        escape(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_lengthmismatch1(self):
        ops = """
        [i1]
        p1 = newstr(1)
        strsetitem(p1, 0, i1)
        i0 = call(0, s"xy", p1, descr=strequaldescr)
        escape(i0)
        jump(i1)
        """
        expected = """
        [i1]
        escape(0)
        jump(i1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str2unicode_constant(self):
        ops = """
        []
        p0 = call(0, "xy", descr=s2u_descr)      # string -> unicode
        escape(p0)
        jump()
        """
        expected = """
        []
        escape(u"xy")
        jump()
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str2unicode_nonconstant(self):
        ops = """
        [p0]
        p1 = call(0, p0, descr=s2u_descr)      # string -> unicode
        escape(p1)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, ops)
        # more generally, supporting non-constant but virtual cases is
        # not obvious, because of the exception UnicodeDecodeError that
        # can be raised by ll_str2unicode()

    def test_strgetitem_repeated(self):
        ops = """
        [p0, i0]
        i1 = strgetitem(p0, i0)
        i2 = strgetitem(p0, i0)
        i3 = int_eq(i1, i2)
        guard_true(i3) []
        escape(i2)
        jump(p0, i0)
        """
        expected = """
        [p0, i0]
        i1 = strgetitem(p0, i0)
        escape(i1)
        jump(p0, i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_int_is_true_bounds(self):
        ops = """
        [p0]
        i0 = strlen(p0)
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_ge(0, i0)
        guard_false(i2) []
        jump(p0)
        """
        expected = """
        [p0]
        i0 = strlen(p0)
        i1 = int_is_true(i0)
        guard_true(i1) []
        jump(p0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_strslice_subtraction_folds(self):
        ops = """
        [p0, i0]
        i1 = int_add(i0, 1)
        p1 = call(0, p0, i0, i1, descr=strslicedescr)
        escape(p1)
        jump(p0, i1)
        """
        expected = """
        [p0, i0]
        i1 = int_add(i0, 1)
        p1 = newstr(1)
        i2 = strgetitem(p0, i0)
        strsetitem(p1, 0, i2)
        escape(p1)
        jump(p0, i1)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_float_mul_reversed(self):
        ops = """
        [f0, f1]
        f2 = float_mul(f0, f1)
        f3 = float_mul(f1, f0)
        jump(f2, f3)
        """
        expected = """
        [f0, f1]
        f2 = float_mul(f0, f1)
        jump(f2, f2)
        """
        self.optimize_loop(ops, expected)

    def test_null_char_str(self):
        ops = """
        [p0]
        p1 = newstr(4)
        setfield_gc(p0, p1, descr=valuedescr)
        jump(p0)
        """
        # It used to be the case that this would have a series of
        # strsetitem(p1, idx, 0), which was silly because memory is 0 filled
        # when allocated.
        expected = """
        [p0]
        p1 = newstr(4)
        setfield_gc(p0, p1, descr=valuedescr)
        jump(p0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_newstr_strlen(self):
        ops = """
        [i0]
        p0 = newstr(i0)
        escape(p0)
        i1 = strlen(p0)
        i2 = int_add(i1, 1)
        jump(i2)
        """
        expected = """
        [i0]
        p0 = newstr(i0)
        escape(p0)
        i1 = int_add(i0, 1)
        jump(i1)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_intmod_bounds(self):
        ops = """
        [i0, i1]
        i2 = int_mod(i0, 12)
        i3 = int_gt(i2, 12)
        guard_false(i3) []
        i4 = int_lt(i2, -12)
        guard_false(i4) []
        i5 = int_mod(i1, -12)
        i6 = int_lt(i5, -12)
        guard_false(i6) []
        i7 = int_gt(i5, 12)
        guard_false(i7) []
        jump(i2, i5)
        """
        expected = """
        [i0, i1]
        i2 = int_mod(i0, 12)
        i5 = int_mod(i1, -12)
        jump(i2, i5)
        """
        self.optimize_loop(ops, expected)

        # This the sequence of resoperations that is generated for a Python
        # app-level int % int.  When the modulus is constant and when i0
        # is known non-negative it should be optimized to a single int_mod.
        ops = """
        [i0]
        i5 = int_ge(i0, 0)
        guard_true(i5) []
        i1 = int_mod(i0, 42)
        i2 = int_rshift(i1, %d)
        i3 = int_and(42, i2)
        i4 = int_add(i1, i3)
        finish(i4)
        """ % (LONG_BIT-1)
        expected = """
        [i0]
        i5 = int_ge(i0, 0)
        guard_true(i5) []
        i1 = int_mod(i0, 42)
        finish(i1)
        """
        self.optimize_loop(ops, expected)

        # 'n % power-of-two' can be turned into int_and(); at least that's
        # easy to do now if n is known to be non-negative.
        ops = """
        [i0]
        i5 = int_ge(i0, 0)
        guard_true(i5) []
        i1 = int_mod(i0, 8)
        i2 = int_rshift(i1, %d)
        i3 = int_and(42, i2)
        i4 = int_add(i1, i3)
        finish(i4)
        """ % (LONG_BIT-1)
        expected = """
        [i0]
        i5 = int_ge(i0, 0)
        guard_true(i5) []
        i1 = int_and(i0, 7)
        finish(i1)
        """
        self.optimize_loop(ops, expected)

        # Of course any 'maybe-negative % power-of-two' can be turned into
        # int_and(), but that's a bit harder to detect here because it turns
        # into several operations, and of course it is wrong to just turn
        # int_mod(i0, 16) into int_and(i0, 15).
        ops = """
        [i0]
        i1 = int_mod(i0, 16)
        i2 = int_rshift(i1, %d)
        i3 = int_and(16, i2)
        i4 = int_add(i1, i3)
        finish(i4)
        """ % (LONG_BIT-1)
        expected = """
        [i0]
        i4 = int_and(i0, 15)
        finish(i4)
        """
        py.test.skip("harder")
        self.optimize_loop(ops, expected)

    def test_bounded_lazy_setfield(self):
        ops = """
        [p0, i0]
        i1 = int_gt(i0, 2)
        guard_true(i1) []
        setarrayitem_gc(p0, 0, 3)
        setarrayitem_gc(p0, 2, 4)
        setarrayitem_gc(p0, i0, 15)
        i2 = getarrayitem_gc(p0, 2)
        jump(p0, i2)
        """
        # Remove the getarrayitem_gc, because we know that p[i0] does not alias
        # p0[2]
        expected = """
        [p0, i0]
        i1 = int_gt(i0, 2)
        guard_true(i1) []
        setarrayitem_gc(p0, i0, 15)
        setarrayitem_gc(p0, 0, 3)
        setarrayitem_gc(p0, 2, 4)
        jump(p0, 4)
        """
        self.optimize_loop(ops, expected)

    def test_empty_copystrunicontent(self):
        ops = """
        [p0, p1, i0, i2, i3]
        i4 = int_eq(i3, 0)
        guard_true(i4) []
        copystrcontent(p0, p1, i0, i2, i3)
        jump(p0, p1, i0, i2, i3)
        """
        expected = """
        [p0, p1, i0, i2, i3]
        i4 = int_eq(i3, 0)
        guard_true(i4) []
        jump(p0, p1, i0, i2, 0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_empty_copystrunicontent_virtual(self):
        ops = """
        [p0]
        p1 = newstr(23)
        copystrcontent(p0, p1, 0, 0, 0)
        jump(p0)
        """
        expected = """
        [p0]
        jump(p0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_forced_virtuals_aliasing(self):
        ops = """
        [i0, i1]
        p0 = new(descr=ssize)
        p1 = new(descr=ssize)
        escape(p0)
        escape(p1)
        setfield_gc(p0, i0, descr=adescr)
        setfield_gc(p1, i1, descr=adescr)
        i2 = getfield_gc(p0, descr=adescr)
        jump(i2, i2)
        """
        expected = """
        [i0, i1]
        p0 = new(descr=ssize)
        escape(p0)
        p1 = new(descr=ssize)
        escape(p1)
        setfield_gc(p0, i0, descr=adescr)
        setfield_gc(p1, i1, descr=adescr)
        jump(i0, i0)
        """
        py.test.skip("not implemented")
        # setfields on things that used to be virtual still can't alias each
        # other
        self.optimize_loop(ops, expected)

    def test_plain_virtual_string_copy_content(self):
        ops = """
        []
        p0 = newstr(6)
        copystrcontent(s"hello!", p0, 0, 0, 6)
        p1 = call(0, p0, s"abc123", descr=strconcatdescr)
        i0 = strgetitem(p1, 0)
        finish(i0)
        """
        expected = """
        []
        p0 = newstr(6)
        copystrcontent(s"hello!", p0, 0, 0, 6)
        p1 = newstr(12)
        copystrcontent(p0, p1, 0, 0, 6)
        copystrcontent(s"abc123", p1, 0, 6, 6)
        i0 = strgetitem(p1, 0)
        finish(i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_ptr_eq_str_constant(self):
        ops = """
        []
        i0 = ptr_eq(s"abc", s"\x00")
        finish(i0)
        """
        expected = """
        []
        finish(0)
        """
        self.optimize_loop(ops, expected)


class TestLLtype(BaseTestOptimizeBasic, LLtypeMixin):
    pass


##class TestOOtype(BaseTestOptimizeBasic, OOtypeMixin):

##    def test_instanceof(self):
##        ops = """
##        [i0]
##        p0 = new_with_vtable(ConstClass(node_vtable))
##        i1 = instanceof(p0, descr=nodesize)
##        jump(i1)
##        """
##        expected = """
##        [i0]
##        jump(1)
##        """
##        self.optimize_loop(ops, expected)

##    def test_instanceof_guard_class(self):
##        ops = """
##        [i0, p0]
##        guard_class(p0, ConstClass(node_vtable)) []
##        i1 = instanceof(p0, descr=nodesize)
##        jump(i1, p0)
##        """
##        expected = """
##        [i0, p0]
##        guard_class(p0, ConstClass(node_vtable)) []
##        jump(1, p0)
##        """
##        self.optimize_loop(ops, expected)
