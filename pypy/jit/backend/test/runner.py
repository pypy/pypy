
from pypy.jit.metainterp.history import BoxInt, Box, BoxPtr, TreeLoop, ConstInt
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.jit.metainterp.executor import execute
from pypy.rlib.rarithmetic import r_uint, intmask

class BaseBackendTest(object):
    
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

    def test_uint_xor(self):
        x = execute(self.cpu, rop.UINT_XOR, [BoxInt(100), ConstInt(4)])
        assert x.value == 100 ^ 4
        for a, b in [(ConstInt(1), BoxInt(-15)),
                     (BoxInt(22), BoxInt(13)),
                     (BoxInt(-112), ConstInt(11))]:
            res = self.execute_operation(rop.UINT_XOR, [a, b], 'int')
            assert res.value == intmask(r_uint(a.value) ^ r_uint(b.value))
