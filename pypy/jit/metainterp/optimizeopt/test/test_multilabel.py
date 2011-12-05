from pypy.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin, BaseTest, Storage, _sortboxes, FakeDescrWithSnapshot)
from pypy.jit.metainterp.history import TreeLoop, JitCellToken, TargetToken
from pypy.jit.metainterp.resoperation import rop, opname, ResOperation
from pypy.jit.metainterp.optimize import InvalidLoop
from py.test import raises

class BaseTestMultiLabel(BaseTest):
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"

    def optimize_loop(self, ops, expected):
        loop = self.parse(ops)
        if expected != "crash!":
            expected = self.parse(expected)

        part = TreeLoop('part')
        part.inputargs = loop.inputargs
        part.start_resumedescr = FakeDescrWithSnapshot()
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
                jumpop = ResOperation(rop.JUMP, label.getarglist(),
                                      None, descr=token)
                operations.append(jumpop)
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

        assert expected != "crash!", "should have raised an exception"
        self.assert_equal(optimized, expected)

        return optimized

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
        
    
class TestLLtype(BaseTestMultiLabel, LLtypeMixin):
    pass

