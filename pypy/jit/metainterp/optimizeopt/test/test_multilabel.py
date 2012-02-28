from __future__ import with_statement
from pypy.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, Storage, _sortboxes, FakeDescrWithSnapshot,
    FakeMetaInterpStaticData)
from pypy.jit.metainterp.history import TreeLoop, JitCellToken, TargetToken
from pypy.jit.metainterp.resoperation import rop, opname, ResOperation
from pypy.jit.metainterp.optimize import InvalidLoop
from py.test import raises
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method

class BaseTestMultiLabel(BaseTest):
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"

    def optimize_loop(self, ops, expected, expected_shorts=None):
        loop = self.parse(ops)
        if expected != "crash!":
            expected = self.parse(expected)

        part = TreeLoop('part')
        part.inputargs = loop.inputargs
        part.resume_at_jump_descr = FakeDescrWithSnapshot()
        token = loop.original_jitcell_token

        optimized = TreeLoop('optimized')
        optimized.inputargs = loop.inputargs
        optimized.operations = []
        
        labels = [i for i, op in enumerate(loop.operations) \
                  if op.getopnum()==rop.LABEL]
        prv = 0
        last_label = []
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

            self._do_optimize_loop(part, None)
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
        p2 = new_array(3, descr=complexarraydescr)
        setinteriorfield_gc(p2, 2, f0, descr=complexrealdescr)
        label(p2, f0)
        p4 = new_array(3, descr=complexarraydescr)
        setinteriorfield_gc(p4, 2, f0, descr=compleximagdescr)
        jump(p4, f0)
        """
        with raises(InvalidLoop):
            self.optimize_loop(ops, ops)
        
    def test_nonmatching_arraystruct_2(self):
        ops = """
        [p1, f0]
        p2 = new_array(3, descr=complexarraydescr)
        setinteriorfield_gc(p2, 2, f0, descr=complexrealdescr)
        label(p2, f0)
        p4 = new_array(2, descr=complexarraydescr)
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
        p3 = new_array(3, descr=complexarraydescr)
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

    def test_maybe_issue1045_related(self):
        ops = """
        [p8]
        p54 = getfield_gc(p8, descr=valuedescr)
        mark_opaque_ptr(p54)
        i55 = getfield_gc(p54, descr=nextdescr)
        p57 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p57, i55, descr=otherdescr)
        p69 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p69, i55, descr=otherdescr)
        i71 = int_eq(i55, -9223372036854775808)
        guard_false(i71) []
        i73 = int_mod(i55, 2)
        i75 = int_rshift(i73, 63)
        i76 = int_and(2, i75)
        i77 = int_add(i73, i76)
        p79 = new_with_vtable(ConstClass(node_vtable))
        setfield_gc(p79, i77, descr=otherdescr)
        i81 = int_eq(i77, 1)
        guard_false(i81) []
        i0 = int_ge(i55, 1)
        guard_true(i0) []
        label(p57)
        jump(p57)
        """
        expected = """
        [p8]
        p54 = getfield_gc(p8, descr=valuedescr)
        i55 = getfield_gc(p54, descr=nextdescr)
        i71 = int_eq(i55, -9223372036854775808)
        guard_false(i71) []
        i73 = int_mod(i55, 2)
        i75 = int_rshift(i73, 63)
        i76 = int_and(2, i75)
        i77 = int_add(i73, i76)
        i81 = int_eq(i77, 1)
        guard_false(i81) []
        i0 = int_ge(i55, 1)
        guard_true(i0) []
        label(i55)
        jump(i55)
        """
        self.optimize_loop(ops, expected)
        
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

    def _do_optimize_loop(self, loop, call_pure_results):
        from pypy.jit.metainterp.optimizeopt.unroll import optimize_unroll
        from pypy.jit.metainterp.optimizeopt.util import args_dict
        from pypy.jit.metainterp.optimizeopt.pure import OptPure

        self.loop = loop
        loop.call_pure_results = args_dict()
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        optimize_unroll(metainterp_sd, loop, [OptRenameStrlen(), OptPure()], True)

    def test_optimizer_renaming_boxes(self):
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
        

class TestLLtype(OptimizeoptTestMultiLabel, LLtypeMixin):
    pass

class TestOptimizerRenamingBoxesLLtype(BaseTestOptimizerRenamingBoxes, LLtypeMixin):
    pass
