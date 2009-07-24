import py
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rclass
from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib.unroll import unrolling_iterable

from pypy.jit.metainterp.history import BoxInt, BoxPtr, Const, ConstInt,\
     TreeLoop
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.executor import execute
from pypy.jit.backend.test.runner_test import LLtypeBackendTest

NODE = lltype.GcForwardReference()
NODE.become(lltype.GcStruct('NODE', ('value', lltype.Signed),
                                    ('next', lltype.Ptr(NODE))))

SUBNODE = lltype.GcStruct('SUBNODE', ('parent', NODE))


class LLGraphTests:

    def setup_method(self, _):
        self.cpu = self.cpu_type(None)

    def eval_llinterp(self, runme, *args, **kwds):
        expected_class = kwds.pop('expected_class', None)
        expected_vals = [(name[9:], kwds[name])
                            for name in kwds.keys()
                                if name.startswith('expected_')]
        expected_vals = unrolling_iterable(expected_vals)

        def main():
            res = runme(*args)
            if expected_class is not None:
                assert isinstance(res, expected_class)
                for key, value in expected_vals:
                    assert getattr(res, key) == value
        interpret(main, [])

    def test_ovf_operations(self):
        py.test.skip('no way to run this without a typer')

    def test_execute_operations_in_env(self):
        py.test.skip("Rewrite me")
        x = BoxInt(123)
        y = BoxInt(456)
        z = BoxInt(579)
        t = BoxInt(455)
        u = BoxInt(0)
        operations = [
            ResOperation(rop.MERGE_POINT, [x, y], None),
            ResOperation(rop.INT_ADD, [x, y], z),
            ResOperation(rop.INT_SUB, [y, ConstInt(1)], t),
            ResOperation(rop.INT_EQ, [t, ConstInt(0)], u),
            ResOperation(rop.GUARD_FALSE, [u], None),
            ResOperation(rop.JUMP, [z, t], None),
            ]
        operations[-2].liveboxes = [t, z]
        operations[-1].jump_target = operations[0]
        cpu.compile_operations(operations)
        res = cpu.execute_operations_in_new_frame('foo', operations,
                                                  [BoxInt(0), BoxInt(10)])
        assert res.value == 42
        gf = cpu.metainterp.gf
        assert cpu.metainterp.recordedvalues == [0, 55]
        assert gf.guard_op is operations[-2]
        assert cpu.stats.exec_counters['int_add'] == 10
        assert cpu.stats.exec_jumps == 9

    def test_cast_adr_to_int_and_back(self):
        cpu = self.cpu
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x = lltype.malloc(X, immortal=True)
        x.foo = 42
        a = llmemory.cast_ptr_to_adr(x)
        i = cpu.cast_adr_to_int(a)
        assert isinstance(i, int)
        a2 = cpu.cast_int_to_adr(i)
        assert llmemory.cast_adr_to_ptr(a2, lltype.Ptr(X)) == x
        assert cpu.cast_adr_to_int(llmemory.NULL) == 0
        assert cpu.cast_int_to_adr(0) == llmemory.NULL

    def test_llinterp_simple(self):
        py.test.skip("rewrite me")
        cpu = self.cpu
        self.eval_llinterp(cpu.execute_operation, "int_sub",
                           [BoxInt(10), BoxInt(2)], "int",
                           expected_class = BoxInt,
                           expected_value = 8)

    def test_do_operations(self):
        cpu = self.cpu
        #
        A = lltype.GcArray(lltype.Char)
        descr_A = cpu.arraydescrof(A)
        a = lltype.malloc(A, 5)
        x = cpu.do_arraylen_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, a))],
            descr_A)
        assert x.value == 5
        #
        a[2] = 'Y'
        x = cpu.do_getarrayitem_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, a)), BoxInt(2)],
            descr_A)
        assert x.value == ord('Y')
        #
        B = lltype.GcArray(lltype.Ptr(A))
        descr_B = cpu.arraydescrof(B)
        b = lltype.malloc(B, 4)
        b[3] = a
        x = cpu.do_getarrayitem_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, b)), BoxInt(3)],
            descr_B)
        assert isinstance(x, BoxPtr)
        assert x.getptr(lltype.Ptr(A)) == a
        #
        s = rstr.mallocstr(6)
        x = cpu.do_strlen(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s))])
        assert x.value == 6
        #
        s.chars[3] = 'X'
        x = cpu.do_strgetitem(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)), BoxInt(3)])
        assert x.value == ord('X')
        #
        S = lltype.GcStruct('S', ('x', lltype.Char), ('y', lltype.Ptr(A)))
        descrfld_x = cpu.fielddescrof(S, 'x')
        s = lltype.malloc(S)
        s.x = 'Z'
        x = cpu.do_getfield_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s))],
            descrfld_x)
        assert x.value == ord('Z')
        #
        cpu.do_setfield_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)),
             BoxInt(ord('4'))],
            descrfld_x)
        assert s.x == '4'
        #
        descrfld_y = cpu.fielddescrof(S, 'y')
        s.y = a
        x = cpu.do_getfield_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s))],
            descrfld_y)
        assert isinstance(x, BoxPtr)
        assert x.getptr(lltype.Ptr(A)) == a
        #
        s.y = lltype.nullptr(A)
        cpu.do_setfield_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)), x],
            descrfld_y)
        assert s.y == a
        #
        RS = lltype.Struct('S', ('x', lltype.Char), ('y', lltype.Ptr(A)))
        descrfld_rx = cpu.fielddescrof(RS, 'x')
        rs = lltype.malloc(RS, immortal=True)
        rs.x = '?'
        x = cpu.do_getfield_raw(
            [BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs)))],
            descrfld_rx)
        assert x.value == ord('?')
        #
        cpu.do_setfield_raw(
            [BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))),
             BoxInt(ord('!'))],
            descrfld_rx)
        assert rs.x == '!'
        #
        descrfld_ry = cpu.fielddescrof(RS, 'y')
        rs.y = a
        x = cpu.do_getfield_raw(
            [BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs)))],
            descrfld_ry)
        assert isinstance(x, BoxPtr)
        assert x.getptr(lltype.Ptr(A)) == a
        #
        rs.y = lltype.nullptr(A)
        cpu.do_setfield_raw(
            [BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))), x],
            descrfld_ry)
        assert rs.y == a
        #
        descrsize = cpu.sizeof(S)
        x = cpu.do_new([], descrsize)
        assert isinstance(x, BoxPtr)
        x.getptr(lltype.Ptr(S))
        #
        descrsize2 = cpu.sizeof(rclass.OBJECT)
        vtable2 = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        vtable2_int = cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(vtable2))
        cpu.set_class_sizes({vtable2_int: descrsize2})
        x = cpu.do_new_with_vtable([ConstInt(vtable2_int)])
        assert isinstance(x, BoxPtr)
        assert x.getptr(rclass.OBJECTPTR).typeptr == vtable2
        #
        arraydescr = cpu.arraydescrof(A)
        x = cpu.do_new_array([BoxInt(7)], arraydescr)
        assert isinstance(x, BoxPtr)
        assert len(x.getptr(lltype.Ptr(A))) == 7
        #
        cpu.do_setarrayitem_gc(
            [x, BoxInt(5), BoxInt(ord('*'))], descr_A)
        assert x.getptr(lltype.Ptr(A))[5] == '*'
        #
        cpu.do_setarrayitem_gc(
            [BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, b)),
             BoxInt(1), x],
            descr_B)
        assert b[1] == x.getptr(lltype.Ptr(A))
        #
        x = cpu.do_newstr([BoxInt(5)])
        assert isinstance(x, BoxPtr)
        assert len(x.getptr(lltype.Ptr(rstr.STR)).chars) == 5
        #
        cpu.do_strsetitem([x, BoxInt(4), BoxInt(ord('/'))])
        assert x.getptr(lltype.Ptr(rstr.STR)).chars[4] == '/'


class TestLLTypeLLGraph(LLtypeBackendTest, LLGraphTests):
    from pypy.jit.backend.llgraph.runner import LLtypeCPU as cpu_type

## these tests never worked
## class TestOOTypeLLGraph(LLGraphTest):
##     from pypy.jit.backend.llgraph.runner import OOtypeCPU as cpu_type

def test_fielddescr_ootype():
    from pypy.rpython.ootypesystem import ootype
    from pypy.jit.backend.llgraph.runner import OOtypeCPU
    A = ootype.Instance("A", ootype.ROOT, {"foo": ootype.Signed})
    B = ootype.Instance("B", A)
    cpu = OOtypeCPU(None)
    descr1 = cpu.fielddescrof(A, "foo")
    descr2 = cpu.fielddescrof(B, "foo")
    assert descr1 is descr2
