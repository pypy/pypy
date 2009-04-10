
import sys
from pypy.jit.metainterp.history import (BoxInt, Box, BoxPtr, TreeLoop,
                                         ConstInt, ConstPtr)
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rffi
from pypy.jit.metainterp.executor import execute
from pypy.rlib.rarithmetic import r_uint, intmask

MY_VTABLE = lltype.Struct('my_vtable')    # for tests only

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S', ('typeptr', lltype.Ptr(MY_VTABLE)),
                              ('value', lltype.Signed),
                              ('next', lltype.Ptr(S)),
                         hints = {'typeptr': True}))
T = lltype.GcStruct('T', ('parent', S),
                         ('next', lltype.Ptr(S)))
U = lltype.GcStruct('U', ('parent', T),
                         ('next', lltype.Ptr(S)))

class Runner(object):
        
    def execute_operation(self, opname, valueboxes, result_type, descr=0):
        loop = self.get_compiled_single_operation(opname, result_type,
                                                  valueboxes, descr)
        boxes = [box for box in valueboxes if isinstance(box, Box)]
        res = self.cpu.execute_operations(loop, boxes)
        if result_type != 'void':
            return res.args[0]

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
        operations[-1].ovf = False
        operations[-1].exc = False
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
        FPTR = lltype.Ptr(lltype.FuncType([lltype.Char], lltype.Char))
        func_ptr = llhelper(FPTR, func)
        calldescr = cpu.calldescrof([lltype.Char], lltype.Char)
        x = cpu.do_call(
            [BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(func_ptr))),
             BoxInt(ord('A'))],
            calldescr)
        assert x.value == ord('B')

    def test_executor(self):
        cpu = self.cpu
        x = execute(cpu, rop.INT_ADD, [BoxInt(100), ConstInt(42)])
        assert x.value == 142
        s = execute(cpu, rop.NEWSTR, [BoxInt(8)])
        assert len(s.getptr(lltype.Ptr(rstr.STR)).chars) == 8

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

    def test_int_floordiv_ovf(self):
        v1 = BoxInt(-sys.maxint)
        v2 = BoxInt(-1)
        res_v = BoxInt()
        ops = [
            ResOperation(rop.INT_FLOORDIV_OVF, [v1, v2], res_v),
            ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
            ResOperation(rop.FAIL, [ConstInt(0)], None),
            ]
        ops[1].suboperations = [ResOperation(rop.FAIL, [ConstInt(1)], None)]
        loop = TreeLoop('name')
        loop.operations = ops
        loop.inputargs = [v1, v2]
        self.cpu.compile_operations(loop)
        op = self.cpu.execute_operations(loop, [v1, v2])
        assert op.args[0].value == 1

    def test_uint_xor(self):
        x = execute(self.cpu, rop.UINT_XOR, [BoxInt(100), ConstInt(4)])
        assert x.value == 100 ^ 4
        for a, b in [(ConstInt(1), BoxInt(-15)),
                     (BoxInt(22), BoxInt(13)),
                     (BoxInt(-112), ConstInt(11))]:
            res = self.execute_operation(rop.UINT_XOR, [a, b], 'int')
            assert res.value == intmask(r_uint(a.value) ^ r_uint(b.value))

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


    def test_passing_guards(self):
        vtable_for_T = lltype.malloc(MY_VTABLE, immortal=True)
        vtable_for_T_addr = llmemory.cast_ptr_to_adr(vtable_for_T)
        cpu = self.cpu
        cpu._cache_gcstruct2vtable = {T: vtable_for_T}
        for (opname, args) in [(rop.GUARD_TRUE, [BoxInt(1)]),
                               (rop.GUARD_FALSE, [BoxInt(0)]),
                               (rop.GUARD_VALUE, [BoxInt(42), BoxInt(42)]),
                               #(rop.GUARD_VALUE_INVERSE, [BoxInt(42), BoxInt(41)]),
                               ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert not self.cpu.guard_failed()
            
        t = lltype.malloc(T)
        t.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(cpu.cast_adr_to_int(vtable_for_T_addr))
        null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        self.execute_operation(rop.GUARD_CLASS, [t_box, T_box], 'void')
        assert not self.cpu.guard_failed()
        #self.execute_operation(rop.GUARD_CLASS_INVERSE, [t_box, null_box],
        #                       'void')

    def test_failing_guards(self):
        vtable_for_T = lltype.malloc(MY_VTABLE, immortal=True)
        vtable_for_T_addr = llmemory.cast_ptr_to_adr(vtable_for_T)
        vtable_for_U = lltype.malloc(MY_VTABLE, immortal=True)
        vtable_for_U_addr = llmemory.cast_ptr_to_adr(vtable_for_U)
        cpu = self.cpu
        cpu._cache_gcstruct2vtable = {T: vtable_for_T, U: vtable_for_U}
        t = lltype.malloc(T)
        t.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(self.cpu.cast_adr_to_int(vtable_for_T_addr))
        u = lltype.malloc(U)
        u.parent.parent.typeptr = vtable_for_U
        u_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        U_box = ConstInt(self.cpu.cast_adr_to_int(vtable_for_U_addr))
        null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        for opname, args in [(rop.GUARD_TRUE, [BoxInt(0)]),
                             (rop.GUARD_FALSE, [BoxInt(1)]),
                             (rop.GUARD_VALUE, [BoxInt(42), BoxInt(41)]),
                             (rop.GUARD_CLASS, [t_box, U_box]),
                             (rop.GUARD_CLASS, [u_box, T_box]),
                             #(rop.GUARD_VALUE_INVERSE, [BoxInt(10), BoxInt(10)]),
                             ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.cpu.guard_failed()

            
