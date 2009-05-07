
import sys
from pypy.jit.metainterp.history import (BoxInt, Box, BoxPtr, TreeLoop,
                                         ConstInt, ConstPtr, BoxObj,
                                         ConstObj)
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rffi, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.executor import execute
from pypy.rlib.rarithmetic import r_uint, intmask

class Runner(object):

    def execute_operation(self, opname, valueboxes, result_type, descr=None):
        loop = self.get_compiled_single_operation(opname, result_type,
                                                  valueboxes, descr)
        j = 0
        for box in valueboxes:
            if isinstance(box, BoxInt):
                self.cpu.set_future_value_int(j, box.getint())
                j += 1
            elif isinstance(box, BoxPtr):
                self.cpu.set_future_value_ptr(j, box.getptr_base())
                j += 1
            elif isinstance(box, BoxObj):
                self.cpu.set_future_value_obj(j, box.getobj())
                j += 1
        res = self.cpu.execute_operations(loop)
        if res is loop.operations[-1]:
            self.guard_failed = False
        else:
            self.guard_failed = True
        if result_type == 'int':
            return BoxInt(self.cpu.get_latest_value_int(0))
        elif result_type == 'ptr':
            return BoxPtr(self.cpu.get_latest_value_ptr(0))
        elif result_type == 'void':
            return None
        else:
            assert False

    def get_compiled_single_operation(self, opnum, result_type, valueboxes,
                                      descr):
        if result_type == 'void':
            result = None
        elif result_type == 'int':
            result = BoxInt()
        elif result_type == 'ptr':
            result = BoxPtr()
        else:
            raise ValueError(result_type)
        if result is None:
            results = []
        else:
            results = [result]
        operations = [ResOperation(opnum, valueboxes, result),
                      ResOperation(rop.FAIL, results, None)]
        operations[0].descr = descr
        if operations[0].is_guard():
            operations[0].suboperations = [ResOperation(rop.FAIL,
                                                        [ConstInt(-13)], None)]
        loop = TreeLoop('single op')
        loop.operations = operations
        loop.inputargs = [box for box in valueboxes if isinstance(box, Box)]
        self.cpu.compile_operations(loop)
        return loop


class BaseBackendTest(Runner):
    
    def test_do_call(self):
        from pypy.rpython.annlowlevel import llhelper
        cpu = self.cpu
        #
        def func(c):
            return chr(ord(c) + 1)
        FPTR = self.Ptr(self.FuncType([lltype.Char], lltype.Char))
        func_ptr = llhelper(FPTR, func)
        calldescr = cpu.calldescrof(deref(FPTR), (lltype.Char,), lltype.Char)
        x = cpu.do_call(
            [self.get_funcbox(cpu, func_ptr),
             BoxInt(ord('A'))],
            calldescr)
        assert x.value == ord('B')

    def test_executor(self):
        cpu = self.cpu
        x = execute(cpu, rop.INT_ADD, [BoxInt(100), ConstInt(42)])
        assert x.value == 142
        if self.type_system == 'lltype':
            s = execute(cpu, rop.NEWSTR, [BoxInt(8)])
            assert len(s.getptr(lltype.Ptr(rstr.STR)).chars) == 8

    def test_lshift(self):
        res = execute(self.cpu, rop.INT_LSHIFT, [BoxInt(10), ConstInt(4)])
        assert res.value == 10 << 4
        res = self.execute_operation(rop.INT_LSHIFT, [BoxInt(10), BoxInt(4)],
                                     'int')
        assert res.value == 10 << 4
        res = self.execute_operation(rop.INT_LSHIFT, [BoxInt(-10), BoxInt(4)],
                                     'int')
        assert res.value == -10 << 4

    def test_uint_rshift(self):
        res = self.execute_operation(rop.UINT_RSHIFT, [BoxInt(-1), BoxInt(4)],
                                     'int')
        assert res.value == intmask(r_uint(-1) >> r_uint(4))
        res = self.execute_operation(rop.UINT_RSHIFT, [BoxInt(1), BoxInt(4)],
                                     'int')
        assert res.value == intmask(r_uint(1) >> r_uint(4))

    def test_binary_operations(self):
        minint = -sys.maxint-1
        for opnum, testcases in [
            (rop.INT_ADD, [(10, -2, 8)]),
            (rop.INT_SUB, [(10, -2, 12)]),
            (rop.INT_MUL, [(-6, -3, 18)]),
            (rop.INT_FLOORDIV, [(110, 3, 36),
                                (-110, 3, -36),
                                (110, -3, -36),
                                (-110, -3, 36),
                                (-110, -1, 110),
                                (minint, 1, minint)]),
            (rop.INT_MOD, [(11, 3, 2),
                           (-11, 3, -2),
                           (11, -3, 2),
                           (-11, -3, -2)]),
            (rop.INT_AND, [(0xFF00, 0x0FF0, 0x0F00)]),
            (rop.INT_OR, [(0xFF00, 0x0FF0, 0xFFF0)]),
            (rop.INT_XOR, [(0xFF00, 0x0FF0, 0xF0F0)]),
            (rop.INT_LSHIFT, [(-5, 2, -20),
                              (-5, 0, -5)]),
            (rop.INT_RSHIFT, [(-17, 2, -5),
                              (19, 1, 9)]),
            ]:
            for x, y, z in testcases:
                res = self.execute_operation(opnum, [BoxInt(x), BoxInt(y)],
                                             'int')
                assert res.value == z

    def test_unary_operations(self):
        minint = -sys.maxint-1
        for opnum, testcases in [
            (rop.INT_IS_TRUE, [(0, 0), (1, 1), (2, 1), (-1, 1), (minint, 1)]),
            (rop.INT_NEG, [(0, 0), (123, -123), (-23127, 23127)]),
            (rop.INT_INVERT, [(0, ~0), (-1, ~(-1)), (123, ~123)]),
            ]:
            for x, y in testcases:
                res = self.execute_operation(opnum, [BoxInt(x)],
                                             'int')
                assert res.value == y

    def test_ovf_operations(self, reversed=False):
        minint = -sys.maxint-1
        boom = 'boom'
        for opnum, testcases in [
            (rop.INT_ADD_OVF, [(10, -2, 8),
                               (-1, minint, boom),
                               (sys.maxint//2, sys.maxint//2+2, boom)]),
            (rop.INT_SUB_OVF, [(-20, -23, 3),
                               (-2, sys.maxint, boom),
                               (sys.maxint//2, -(sys.maxint//2+2), boom)]),
            (rop.INT_MUL_OVF, [(minint/2, 2, minint),
                               (-2, -(minint/2), minint),
                               (minint/2, -2, boom)]),
            (rop.INT_NEG_OVF, [(-sys.maxint, 0, sys.maxint),
                               (sys.maxint, 0, -sys.maxint),
                               (minint, 0, boom)]),
            (rop.INT_LSHIFT_OVF, [(0x1f87611, 6, 0x7e1d8440),
                                  (-0x1f87611, 6, -0x7e1d8440),
                                  (sys.maxint//8+1, 3, boom),
                                  (minint//2-1, 1, boom),
                                  (0, 345, 0)]),
            ]:
            v1 = BoxInt(testcases[0][0])
            v2 = BoxInt(testcases[0][1])
            v_res = BoxInt()
            #
            if not reversed:
                ops = [
                    ResOperation(opnum, [v1, v2], v_res),
                    ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
                    ResOperation(rop.FAIL, [v_res], None),
                    ]
                ops[1].suboperations = [ResOperation(rop.FAIL, [], None)]
            else:
                self.cpu.set_overflow_error()
                ovferror = self.cpu.get_exception()
                self.cpu.clear_exception()
                if self.cpu.is_oo:
                    v_exc = BoxObj()
                    c_ovferror = ConstObj(ovferror)
                else:
                    v_exc = BoxPtr()
                    c_ovferror = ConstInt(ovferror)
                ops = [
                    ResOperation(opnum, [v1, v2], v_res),
                    ResOperation(rop.GUARD_EXCEPTION, [c_ovferror], v_exc),
                    ResOperation(rop.FAIL, [], None),
                    ]
                ops[1].suboperations = [ResOperation(rop.FAIL, [v_res], None)]
            #
            if opnum == rop.INT_NEG_OVF:
                del ops[0].args[1]
            loop = TreeLoop('name')
            loop.operations = ops
            loop.inputargs = [v1, v2]
            self.cpu.compile_operations(loop)
            for x, y, z in testcases:
                assert not self.cpu.get_exception()
                self.cpu.set_future_value_int(0, x)
                self.cpu.set_future_value_int(1, y)
                op = self.cpu.execute_operations(loop)
                if (z == boom) ^ reversed:
                    assert op is ops[1].suboperations[0]
                else:
                    assert op is ops[-1]
                if z != boom:
                    assert self.cpu.get_latest_value_int(0) == z
                ovferror = self.cpu.get_exception()
                if reversed:
                    # in the 'reversed' case, ovferror should always be
                    # consumed: either it is not set in the first place,
                    # or it is set and GUARD_EXCEPTION succeeds.
                    assert not ovferror
                elif ovferror:
                    assert z == boom
                    self.cpu.clear_exception()
                else:
                    assert z != boom

    def test_ovf_operations_reversed(self):
        self.test_ovf_operations(reversed=True)


    def test_passing_guards(self):
        for (opname, args) in [(rop.GUARD_TRUE, [BoxInt(1)]),
                               (rop.GUARD_FALSE, [BoxInt(0)]),
                               (rop.GUARD_VALUE, [BoxInt(42), BoxInt(42)]),
                               #(rop.GUARD_VALUE_INVERSE, [BoxInt(42), BoxInt(41)]),
                               ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert not self.guard_failed


    def test_passing_guard_class(self):
        t_box, T_box = self.alloc_instance(self.T)
        #null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        self.execute_operation(rop.GUARD_CLASS, [t_box, T_box], 'void')
        assert not self.guard_failed
        #self.execute_operation(rop.GUARD_CLASS_INVERSE, [t_box, null_box],
        #                       'void')

    def test_failing_guards(self):
        for opname, args in [(rop.GUARD_TRUE, [BoxInt(0)]),
                             (rop.GUARD_FALSE, [BoxInt(1)]),
                             (rop.GUARD_VALUE, [BoxInt(42), BoxInt(41)]),
                             ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.guard_failed

    def test_failing_guard_class(self):
        t_box, T_box = self.alloc_instance(self.T)
        u_box, U_box = self.alloc_instance(self.U)        
        #null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        for opname, args in [(rop.GUARD_CLASS, [t_box, U_box]),
                             (rop.GUARD_CLASS, [u_box, T_box]),
                             #(rop.GUARD_VALUE_INVERSE, [BoxInt(10), BoxInt(10)]),
                             ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.guard_failed

            
class LLtypeBackendTest(BaseBackendTest):

    type_system = 'lltype'
    Ptr = lltype.Ptr
    FuncType = lltype.FuncType
    malloc = staticmethod(lltype.malloc)
    nullptr = staticmethod(lltype.nullptr)

    @classmethod
    def get_funcbox(cls, cpu, func_ptr):
        addr = llmemory.cast_ptr_to_adr(func_ptr)
        return BoxInt(cpu.cast_adr_to_int(addr))

    
    MY_VTABLE = rclass.OBJECT_VTABLE    # for tests only

    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('parent', rclass.OBJECT),
                                  ('value', lltype.Signed),
                                  ('next', lltype.Ptr(S))))
    T = lltype.GcStruct('T', ('parent', S),
                             ('next', lltype.Ptr(S)))
    U = lltype.GcStruct('U', ('parent', T),
                             ('next', lltype.Ptr(S)))


    def alloc_instance(self, T):
        vtable_for_T = lltype.malloc(self.MY_VTABLE, immortal=True)
        vtable_for_T_addr = llmemory.cast_ptr_to_adr(vtable_for_T)
        cpu = self.cpu
        if not hasattr(cpu, '_cache_gcstruct2vtable'):
            cpu._cache_gcstruct2vtable = {}
        cpu._cache_gcstruct2vtable.update({T: vtable_for_T})
        t = lltype.malloc(T)
        if T == self.T:
            t.parent.parent.typeptr = vtable_for_T
        elif T == self.U:
            t.parent.parent.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(self.cpu.cast_adr_to_int(vtable_for_T_addr))
        return t_box, T_box


    def test_casts(self):
        from pypy.rpython.lltypesystem import lltype, llmemory
        TP = lltype.GcStruct('x')
        x = lltype.malloc(TP)        
        x = lltype.cast_opaque_ptr(llmemory.GCREF, x)
        res = self.execute_operation(rop.CAST_PTR_TO_INT,
                                     [BoxPtr(x)],  'int').value
        res2 = self.execute_operation(rop.CAST_INT_TO_PTR,
                                      [BoxInt(res)], 'ptr').value
        assert res2 == x

    def test_ooops_non_gc(self):
        x = lltype.malloc(lltype.Struct('x'), flavor='raw')
        v = self.cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(x))
        r = self.execute_operation(rop.OOIS, [BoxInt(v), BoxInt(v)], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OOISNOT, [BoxInt(v), BoxInt(v)], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OOISNULL, [BoxInt(v)], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OONONNULL, [BoxInt(v)], 'int')
        assert r.value == 1
        lltype.free(x, flavor='raw')


class OOtypeBackendTest(BaseBackendTest):

    type_system = 'ootype'
    Ptr = staticmethod(lambda x: x)
    FuncType = ootype.StaticMethod
    malloc = staticmethod(ootype.new)
    nullptr = staticmethod(ootype.null)

    @classmethod
    def get_funcbox(cls, cpu, func_ptr):
        return BoxObj(ootype.cast_to_object(func_ptr))

    S = ootype.Instance('S', ootype.ROOT, {'value': ootype.Signed})
    S._add_fields({'next': S})
    T = ootype.Instance('T', S)
    U = ootype.Instance('U', T)

    def alloc_instance(self, T):
        t = ootype.new(T)
        cls = ootype.classof(t)
        t_box = BoxObj(ootype.cast_to_object(t))
        T_box = ConstObj(ootype.cast_to_object(cls))
        return t_box, T_box
