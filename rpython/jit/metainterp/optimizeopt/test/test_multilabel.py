from __future__ import with_statement
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, Storage,
    FakeMetaInterpStaticData)
from rpython.jit.metainterp.history import TreeLoop, JitCellToken, TargetToken
from rpython.jit.metainterp.resoperation import rop, opname, ResOperation
from rpython.jit.metainterp.optimize import InvalidLoop
from py.test import raises
from rpython.jit.metainterp.optimizeopt.optimizer import Optimization
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.optimizeopt.heap import OptHeap
from rpython.jit.metainterp.optimizeopt.rewrite import OptRewrite


class BaseTestMultiLabel(BaseTest):
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"

    def optimize_loop(self, ops, expected, expected_shorts=None):
        loop = self.parse(ops)
        if expected != "crash!":
            expected = self.parse(expected)

        part = TreeLoop('part')
        part.inputargs = loop.inputargs
        token = loop.original_jitcell_token

        optimized = TreeLoop('optimized')
        optimized.inputargs = loop.inputargs
        optimized.operations = []

        labels = [i for i, op in enumerate(loop.operations) \
                  if op.getopnum()==rop.LABEL]
        prv = 0
        last_label = []
        state = None
        for nxt in labels + [len(loop.operations)]:
            assert prv != nxt
            operations = last_label + loop.operations[prv:nxt]
            if nxt < len(loop.operations):
                label = loop.operations[nxt]
                assert label.getopnum() == rop.LABEL
                if label.getdescr() is None:
                    label.setdescr(token)
                operations.append(label)
            part.operations = operations

            self.add_guard_future_condition(part)
            state = self._do_optimize_loop(part, None, state,
                                           export_state=True)
            if part.operations[-1].getopnum() == rop.LABEL:
                last_label = [part.operations.pop()]
            else:
                last_label = []

            optimized.operations.extend(part.operations)
            prv = nxt + 1

        #
        print
        print "Optimized:"
        if optimized.operations:
            print '\n'.join([str(o) for o in optimized.operations])
        else:
            print 'Failed!'
        print

        shorts = [op.getdescr().short_preamble
                  for op in optimized.operations
                  if op.getopnum() == rop.LABEL]

        if expected_shorts:
            for short in shorts:
                print
                print "Short preamble:"
                print '\n'.join([str(o) for o in short])


        assert expected != "crash!", "should have raised an exception"
        self.assert_equal(optimized, expected)

        if expected_shorts:
            assert len(shorts) == len(expected_shorts)
            for short, expected_short in zip(shorts, expected_shorts):
                expected_short = self.parse(expected_short)
                short_preamble = TreeLoop('short preamble')
                assert short[0].getopnum() == rop.LABEL
                short_preamble.inputargs = short[0].getarglist()
                short_preamble.operations = short
                self.assert_equal(short_preamble, expected_short,
                                  text_right='expected short preamble')


        return optimized

class OptimizeoptTestMultiLabel(BaseTestMultiLabel):

    def test_simple(self):
        ops = """
        [i1]
        i2 = int_add(i1, 1)
        escape(i2)
        label(i1)
        i3 = int_add(i1, 1)
        escape(i3)
        jump(i1)
        """
        expected = """
        [i1]
        i2 = int_add(i1, 1)
        escape(i2)
        label(i1, i2)
        escape(i2)
        jump(i1, i2)
        """
        self.optimize_loop(ops, expected)

    def test_forced_virtual(self):
        ops = """
        [p1]
        p3 = new_with_vtable(ConstClass(node_vtable))
        label(p3)
        escape(p3)
        jump(p3)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_virtuals_with_nonmatching_fields(self):
        ops = """
        [p1]
        p3 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p3, 1, descr=valuedescr)
        label(p3)
        p4 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p4, 1, descr=nextdescr)
        jump(p4)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_virtual_arrays_with_nonmatching_lens(self):
        ops = """
        [p1]
        p2 = new_array(3, descr=arraydescr)
        label(p2)
        p4 = new_array(2, descr=arraydescr)
        jump(p4)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_nonmatching_arraystruct_1(self):
        ops = """
        [p1, f0]
        p2 = new_array_clear(3, descr=complexarraydescr)
        setinteriorfield_gc(p2, 2, f0, descr=complexrealdescr)
        label(p2, f0)
        p4 = new_array_clear(3, descr=complexarraydescr)
        setinteriorfield_gc(p4, 2, f0, descr=compleximagdescr)
        jump(p4, f0)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_nonmatching_arraystruct_2(self):
        ops = """
        [p1, f0]
        p2 = new_array_clear(3, descr=complexarraydescr)
        setinteriorfield_gc(p2, 2, f0, descr=complexrealdescr)
        label(p2, f0)
        p4 = new_array_clear(2, descr=complexarraydescr)
        setinteriorfield_gc(p4, 0, f0, descr=complexrealdescr)
        jump(p4, f0)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_not_virtual(self):
        ops = """
        [p1]
        p3 = new_with_vtable(ConstClass(node_vtable))
        label(p3)
        p4 = escape()
        jump(p4)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_not_virtual_array(self):
        ops = """
        [p1]
        p3 = new_array(3, descr=arraydescr)
        label(p3)
        p4 = escape()
        jump(p4)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_not_virtual_arraystruct(self):
        ops = """
        [p1]
        p3 = new_array_clear(3, descr=complexarraydescr)
        label(p3)
        p4 = escape()
        jump(p4)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_virtual_turns_constant(self):
        ops = """
        [p1]
        p3 = new_with_vtable(ConstClass(node_vtable))
        label(p3)
        guard_value(p3, ConstPtr(myptr)) []
        jump(p3)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_virtuals_turns_not_equal(self):
        ops = """
        [p1, p2]
        p3 = new_with_vtable(ConstClass(node_vtable))
        label(p3, p3)
        p4 = new_with_vtable(ConstClass(node_vtable))
        jump(p3, p4)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_two_intermediate_labels_basic_1(self):
        ops = """
        [p1, i1]
        i2 = getfield_gc(p1, descr=valuedescr)
        label(p1, i1)
        i3 = getfield_gc(p1, descr=valuedescr)
        i4 = int_add(i1, i3)
        label(p1, i4)
        i5 = int_add(i4, 1)
        jump(p1, i5)
        """
        expected = """
        [p1, i1]
        i2 = getfield_gc(p1, descr=valuedescr)
        label(p1, i1, i2)
        i4 = int_add(i1, i2)
        label(p1, i4)
        i5 = int_add(i4, 1)
        jump(p1, i5)
        """
        short1 = """
        [p1, i1]
        label(p1, i1)
        i2 = getfield_gc(p1, descr=valuedescr)
        jump(p1, i1, i2)
        """
        short2 = """
        [p1, i1]
        label(p1, i1)
        jump(p1, i1)
        """
        self.optimize_loop(ops, expected, expected_shorts=[short1, short2])

    def test_two_intermediate_labels_basic_2(self):
        ops = """
        [p1, i1]
        i2 = int_add(i1, 1)
        label(p1, i1)
        i3 = getfield_gc(p1, descr=valuedescr)
        i4 = int_add(i1, i3)
        label(p1, i4)
        i5 = getfield_gc(p1, descr=valuedescr)
        i6 = int_add(i4, i5)
        jump(p1, i6)
        """
        expected = """
        [p1, i1]
        i2 = int_add(i1, 1)
        label(p1, i1)
        i3 = getfield_gc(p1, descr=valuedescr)
        i4 = int_add(i1, i3)
        label(p1, i4, i3)
        i6 = int_add(i4, i3)
        jump(p1, i6, i3)
        """
        short1 = """
        [p1, i1]
        label(p1, i1)
        jump(p1, i1)
        """
        short2 = """
        [p1, i1]
        label(p1, i1)
        i2 = getfield_gc(p1, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, expected, expected_shorts=[short1, short2])

    def test_two_intermediate_labels_both(self):
        ops = """
        [p1, i1]
        i2 = getfield_gc(p1, descr=valuedescr)
        label(p1, i1)
        i3 = getfield_gc(p1, descr=valuedescr)
        i4 = int_add(i1, i3)
        label(p1, i4)
        i5 = getfield_gc(p1, descr=valuedescr)
        i6 = int_mul(i4, i5)
        jump(p1, i6)
        """
        expected = """
        [p1, i1]
        i2 = getfield_gc(p1, descr=valuedescr)
        label(p1, i1, i2)
        i4 = int_add(i1, i2)
        label(p1, i4, i2)
        i6 = int_mul(i4, i2)
        jump(p1, i6, i2)
        """
        short = """
        [p1, i1]
        label(p1, i1)
        i2 = getfield_gc(p1, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, expected, expected_shorts=[short, short])

    def test_import_across_multiple_labels_basic(self):
        # Not supported, juts make sure we get a functional trace
        ops = """
        [p1, i1]
        i2 = getfield_gc(p1, descr=valuedescr)
        label(p1, i1)
        i3 = int_add(i1, 1)
        label(p1, i1)
        i4 = getfield_gc(p1, descr=valuedescr)
        i5 = int_add(i4, 1)
        jump(p1, i5)
        """
        self.optimize_loop(ops, ops)

    def test_import_across_multiple_labels_with_duplication(self):
        # Not supported, juts make sure we get a functional trace
        ops = """
        [p1, i1]
        i2 = getfield_gc(p1, descr=valuedescr)
        label(p1, i2)
        i3 = int_add(i2, 1)
        label(p1, i2)
        i4 = getfield_gc(p1, descr=valuedescr)
        i5 = int_add(i4, 1)
        jump(p1, i5)
        """
        exported = """
        [p1, i1]
        i2 = getfield_gc(p1, descr=valuedescr)
        i6 = same_as(i2)
        label(p1, i2)
        i3 = int_add(i2, 1)
        label(p1, i2)
        i4 = getfield_gc(p1, descr=valuedescr)
        i5 = int_add(i4, 1)
        jump(p1, i5)
        """
        self.optimize_loop(ops, exported)

    def test_import_virtual_across_multiple_labels(self):
        ops = """
        [p0, i1]
        i1a = int_add(i1, 1)
        pv = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(pv, i1a, descr=valuedescr)
        label(pv, i1)
        i2 = int_mul(i1, 3)
        label(pv, i2)
        i3 = getfield_gc(pv, descr=valuedescr)
        i4 = int_add(i3, i2)
        jump(pv, i4)
        """
        expected = """
        [p0, i1]
        i1a = int_add(i1, 1)
        i5 = same_as(i1a)
        label(i1a, i1)
        i2 = int_mul(i1, 3)
        label(i1a, i2)
        i4 = int_add(i1a, i2)
        jump(i1a, i4)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_as_field_of_forced_box(self):
        ops = """
        [p0]
        pv1 = new_with_vtable(ConstClass(node_vtable))
        label(pv1, p0)
        pv2 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(pv2, pv1, descr=valuedescr)
        jump(pv1, pv2)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)

    def test_issue1045(self):
        ops = """
        [i55]
        i73 = int_mod(i55, 2)
        i75 = int_rshift(i73, 63)
        i76 = int_and(2, i75)
        i77 = int_add(i73, i76)
        i81 = int_eq(i77, 1)
        i0 = int_ge(i55, 1)
        guard_true(i0) []
        label(i55)
        i3 = int_mod(i55, 2)
        i5 = int_rshift(i3, 63)
        i6 = int_and(2, i5)
        i7 = int_add(i3, i6)
        i8 = int_eq(i7, 1)
        escape(i8)
        jump(i55)
        """
        expected = """
        [i55]
        i73 = int_mod(i55, 2)
        i75 = int_rshift(i73, 63)
        i76 = int_and(2, i75)
        i77 = int_add(i73, i76)
        i81 = int_eq(i77, 1)
        i0 = int_ge(i55, 1)
        guard_true(i0) []
        label(i55, i81)
        escape(i81)
        jump(i55, i81)
        """
        self.optimize_loop(ops, expected)

    def test_boxed_opaque_unknown_class(self):
        ops = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr)
        mark_opaque_ptr(p2)
        i3 = getfield_gc(p2, descr=otherdescr)
        label(p1)
        i4 = getfield_gc(p1, descr=otherdescr)
        label(p1)
        p5 = getfield_gc(p1, descr=nextdescr)
        mark_opaque_ptr(p5)
        i6 = getfield_gc(p5, descr=otherdescr)
        i7 = call(i6, descr=nonwritedescr)
        """
        expected = """
        [p1]
        p2 = getfield_gc(p1, descr=nextdescr)
        i3 = getfield_gc(p2, descr=otherdescr)
        label(p1)
        i4 = getfield_gc(p1, descr=otherdescr)
        label(p1)
        p5 = getfield_gc(p1, descr=nextdescr)
        i6 = getfield_gc(p5, descr=otherdescr)
        i7 = call(i6, descr=nonwritedescr)
        """
        self.optimize_loop(ops, expected)

    def test_opaque_pointer_fails_to_close_loop(self):
        ops = """
        [p1, p11]
        p2 = getfield_gc(p1, descr=nextdescr)
        guard_class(p2, ConstClass(node_vtable)) []
        mark_opaque_ptr(p2)
        i3 = getfield_gc(p2, descr=otherdescr)
        label(p1, p11)
        p12 = getfield_gc(p1, descr=nextdescr)
        i13 = getfield_gc(p2, descr=otherdescr)
        i14 = call(i13, descr=nonwritedescr)
        jump(p11, p1)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)




class OptRenameStrlen(Optimization):
    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def optimize_STRLEN(self, op):
        newop = op.clone()
        newop.result = op.result.clonebox()
        self.emit_operation(newop)
        self.make_equal_to(op.result, self.getvalue(newop.result))

dispatch_opt = make_dispatcher_method(OptRenameStrlen, 'optimize_',
                                      default=OptRenameStrlen.emit_operation)

class BaseTestOptimizerRenamingBoxes(BaseTestMultiLabel):

    def _do_optimize_loop(self, loop, call_pure_results, state,
                          export_state=False):
        from rpython.jit.metainterp.optimizeopt.unroll import optimize_unroll
        from rpython.jit.metainterp.optimizeopt.util import args_dict
        from rpython.jit.metainterp.optimizeopt.pure import OptPure

        self.loop = loop
        loop.call_pure_results = args_dict()
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        return optimize_unroll(metainterp_sd, loop, [OptRewrite(), OptRenameStrlen(), OptHeap(), OptPure()], True, state, export_state)

    def test_optimizer_renaming_boxes1(self):
        ops = """
        [p1]
        i1 = strlen(p1)
        label(p1)
        i2 = strlen(p1)
        i3 = int_add(i2, 7)
        jump(p1)
        """
        expected = """
        [p1]
        i1 = strlen(p1)
        label(p1, i1)
        i11 = same_as(i1)
        i2 = int_add(i11, 7)
        jump(p1, i11)
        """
        self.optimize_loop(ops, expected)

    def test_optimizer_renaming_boxes_not_imported(self):
        ops = """
        [p1]
        i1 = strlen(p1)
        label(p1)
        jump(p1)
        """
        expected = """
        [p1]
        i1 = strlen(p1)
        label(p1, i1)
        i11 = same_as(i1)
        jump(p1, i11)
        """
        self.optimize_loop(ops, expected)


class XxxTestLLtype(OptimizeoptTestMultiLabel, LLtypeMixin):
    pass

class XxxTestOptimizerRenamingBoxesLLtype(BaseTestOptimizerRenamingBoxes, LLtypeMixin):
    pass
