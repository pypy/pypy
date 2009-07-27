import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr, rclass
from pypy.jit.metainterp.history import ResOperation, TreeLoop
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         Box)
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.backend.x86.regalloc import WORD
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.executor import execute
from pypy.jit.backend.test.runner_test import LLtypeBackendTest
import ctypes
import sys

class FakeStats(object):
    pass

U = LLtypeBackendTest.U
S = LLtypeBackendTest.S

# ____________________________________________________________

class TestX86(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py
    
    def setup_class(cls):
        cls.cpu = CPU(rtyper=None, stats=FakeStats())

    def test_int_binary_ops(self):
        for op, args, res in [
            (rop.INT_SUB, [BoxInt(42), BoxInt(40)], 2),
            (rop.INT_SUB, [BoxInt(42), ConstInt(40)], 2),
            (rop.INT_SUB, [ConstInt(42), BoxInt(40)], 2),
            (rop.INT_ADD, [ConstInt(-3), ConstInt(-5)], -8),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_int_unary_ops(self):
        for op, args, res in [
            (rop.INT_NEG, [BoxInt(42)], -42),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_int_comp_ops(self):
        for op, args, res in [
            (rop.INT_LT, [BoxInt(40), BoxInt(39)], 0),
            (rop.INT_LT, [BoxInt(40), ConstInt(41)], 1),
            (rop.INT_LT, [ConstInt(41), BoxInt(40)], 0),
            (rop.INT_LE, [ConstInt(42), BoxInt(42)], 1),
            (rop.INT_GT, [BoxInt(40), ConstInt(-100)], 1),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_execute_ptr_operation(self):
        cpu = self.cpu
        u = lltype.malloc(U)
        u_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        ofs = cpu.fielddescrof(S, 'value')
        assert self.execute_operation(rop.SETFIELD_GC,
                                      [u_box, BoxInt(3)],
                                     'void', ofs) == None
        assert u.parent.parent.value == 3
        u.parent.parent.value += 100
        assert (self.execute_operation(rop.GETFIELD_GC, [u_box], 'int', ofs)
                .value == 103)

    def test_execute_operations_in_env(self):
        cpu = self.cpu
        x = BoxInt(123)
        y = BoxInt(456)
        z = BoxInt(579)
        t = BoxInt(455)
        u = BoxInt(0)    # False
        operations = [
            ResOperation(rop.INT_ADD, [x, y], z),
            ResOperation(rop.INT_SUB, [y, ConstInt(1)], t),
            ResOperation(rop.INT_EQ, [t, ConstInt(0)], u),
            ResOperation(rop.GUARD_FALSE, [u], None),
            ResOperation(rop.JUMP, [z, t], None),
            ]
        loop = TreeLoop('loop')
        loop.operations = operations
        loop.inputargs = [x, y]
        operations[-1].jump_target = loop
        operations[-2].suboperations = [ResOperation(rop.FAIL, [t, z], None)]
        cpu.compile_operations(loop)
        self.cpu.set_future_value_int(0, 0)
        self.cpu.set_future_value_int(1, 10)
        res = self.cpu.execute_operations(loop)
        assert self.cpu.get_latest_value_int(0) == 0
        assert self.cpu.get_latest_value_int(1) == 55

    def test_misc_int_ops(self):
        for op, args, res in [
            (rop.INT_MOD, [BoxInt(7), BoxInt(3)], 1),
            (rop.INT_MOD, [ConstInt(0), BoxInt(7)], 0),
            (rop.INT_MOD, [BoxInt(13), ConstInt(5)], 3),
            (rop.INT_MOD, [ConstInt(33), ConstInt(10)], 3),
            (rop.INT_FLOORDIV, [BoxInt(13), BoxInt(3)], 4),
            (rop.INT_FLOORDIV, [BoxInt(42), ConstInt(10)], 4),
            (rop.INT_FLOORDIV, [ConstInt(42), BoxInt(10)], 4),
            (rop.INT_RSHIFT, [ConstInt(3), BoxInt(4)], 3>>4),
            (rop.INT_RSHIFT, [BoxInt(3), ConstInt(10)], 3>>10),
            #(rop.INT_LSHIFT, [BoxInt(3), BoxInt(1)], 3<<1),
            ]:
            assert self.execute_operation(op, args, 'int').value == res

    def test_unicode(self):
        ofs = symbolic.get_field_token(rstr.UNICODE, 'chars', False)[0]
        u = rstr.mallocunicode(13)
        for i in range(13):
            u.chars[i] = unichr(ord(u'a') + i)
        b = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        r = self.execute_operation(rop.UNICODEGETITEM, [b, ConstInt(2)], 'int')
        assert r.value == ord(u'a') + 2
        self.execute_operation(rop.UNICODESETITEM, [b, ConstInt(2),
                                                    ConstInt(ord(u'z'))],
                               'void')
        assert u.chars[2] == u'z'
        assert u.chars[3] == u'd'
        

    def test_allocations(self):
        from pypy.rpython.lltypesystem import rstr
        
        allocs = [None]
        all = []
        def f(size):
            allocs.insert(0, size)
            buf = ctypes.create_string_buffer(size)
            all.append(buf)
            return ctypes.cast(buf, ctypes.c_void_p).value
        func = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)(f)
        addr = ctypes.cast(func, ctypes.c_void_p).value
        
        try:
            saved_addr = self.cpu.assembler.malloc_func_addr
            self.cpu.assembler.malloc_func_addr = addr
            ofs = symbolic.get_field_token(rstr.STR, 'chars', False)[0]
            
            res = self.execute_operation(rop.NEWSTR, [ConstInt(7)], 'ptr')
            assert allocs[0] == 7 + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 7
            
            # ------------------------------------------------------------

            res = self.execute_operation(rop.NEWSTR, [BoxInt(7)], 'ptr')
            assert allocs[0] == 7 + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 7

            # ------------------------------------------------------------

            TP = lltype.GcArray(lltype.Signed)
            ofs = symbolic.get_field_token(TP, 'length', False)[0]
            descr = self.cpu.arraydescrof(TP)

            res = self.execute_operation(rop.NEW_ARRAY, [ConstInt(10)],
                                             'ptr', descr)
            assert allocs[0] == 10*WORD + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 10

            # ------------------------------------------------------------

            res = self.execute_operation(rop.NEW_ARRAY, [BoxInt(10)],
                                             'ptr', descr)
            assert allocs[0] == 10*WORD + ofs + WORD
            resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
            assert resbuf[ofs/WORD] == 10
            
        finally:
            self.cpu.assembler.malloc_func_addr = saved_addr

    def test_stringitems(self):
        from pypy.rpython.lltypesystem.rstr import STR
        ofs = symbolic.get_field_token(STR, 'chars', False)[0]
        ofs_items = symbolic.get_field_token(STR.chars, 'items', False)[0]

        res = self.execute_operation(rop.NEWSTR, [ConstInt(10)], 'ptr')
        self.execute_operation(rop.STRSETITEM, [res, ConstInt(2), ConstInt(ord('d'))], 'void')
        resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_char))
        assert resbuf[ofs + ofs_items + 2] == 'd'
        self.execute_operation(rop.STRSETITEM, [res, BoxInt(2), ConstInt(ord('z'))], 'void')
        assert resbuf[ofs + ofs_items + 2] == 'z'
        r = self.execute_operation(rop.STRGETITEM, [res, BoxInt(2)], 'int')
        assert r.value == ord('z')

    def test_arrayitems(self):
        TP = lltype.GcArray(lltype.Signed)
        ofs = symbolic.get_field_token(TP, 'length', False)[0]
        itemsofs = symbolic.get_field_token(TP, 'items', False)[0]
        descr = self.cpu.arraydescrof(TP)
        res = self.execute_operation(rop.NEW_ARRAY, [ConstInt(10)],
                                     'ptr', descr)
        resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_int))
        assert resbuf[ofs/WORD] == 10
        self.execute_operation(rop.SETARRAYITEM_GC, [res,
                                                     ConstInt(2), BoxInt(38)],
                               'void', descr)
        assert resbuf[itemsofs/WORD + 2] == 38
        
        self.execute_operation(rop.SETARRAYITEM_GC, [res,
                                                     BoxInt(3), BoxInt(42)],
                               'void', descr)
        assert resbuf[itemsofs/WORD + 3] == 42

        r = self.execute_operation(rop.GETARRAYITEM_GC, [res, ConstInt(2)],
                                   'int', descr)
        assert r.value == 38
        r = self.execute_operation(rop.GETARRAYITEM_GC, [res.constbox(),
                                                         BoxInt(2)],
                                   'int', descr)
        assert r.value == 38
        r = self.execute_operation(rop.GETARRAYITEM_GC, [res.constbox(),
                                                         ConstInt(2)],
                                   'int', descr)
        assert r.value == 38
        r = self.execute_operation(rop.GETARRAYITEM_GC, [res,
                                                         BoxInt(2)],
                                   'int', descr)
        assert r.value == 38
        
        r = self.execute_operation(rop.GETARRAYITEM_GC, [res, BoxInt(3)],
                                   'int', descr)
        assert r.value == 42

    def test_arrayitems_not_int(self):
        TP = lltype.GcArray(lltype.Char)
        ofs = symbolic.get_field_token(TP, 'length', False)[0]
        itemsofs = symbolic.get_field_token(TP, 'items', False)[0]
        descr = self.cpu.arraydescrof(TP)
        res = self.execute_operation(rop.NEW_ARRAY, [ConstInt(10)],
                                     'ptr', descr)
        resbuf = ctypes.cast(res.value.intval, ctypes.POINTER(ctypes.c_char))
        assert resbuf[ofs] == chr(10)
        for i in range(10):
            self.execute_operation(rop.SETARRAYITEM_GC, [res,
                                                   ConstInt(i), BoxInt(i)],
                                   'void', descr)
        for i in range(10):
            assert resbuf[itemsofs + i] == chr(i)
        for i in range(10):
            r = self.execute_operation(rop.GETARRAYITEM_GC, [res,
                                                             ConstInt(i)],
                                         'int', descr)
            assert r.value == i

    def test_getfield_setfield(self):
        TP = lltype.GcStruct('x', ('s', lltype.Signed),
                             ('f', lltype.Float),
                             ('u', rffi.USHORT),
                             ('c1', lltype.Char),
                             ('c2', lltype.Char),
                             ('c3', lltype.Char))
        res = self.execute_operation(rop.NEW, [],
                                     'ptr', self.cpu.sizeof(TP))
        ofs_s = self.cpu.fielddescrof(TP, 's')
        #ofs_f = self.cpu.fielddescrof(TP, 'f')
        ofs_u = self.cpu.fielddescrof(TP, 'u')
        ofsc1 = self.cpu.fielddescrof(TP, 'c1')
        ofsc2 = self.cpu.fielddescrof(TP, 'c2')
        ofsc3 = self.cpu.fielddescrof(TP, 'c3')
        self.execute_operation(rop.SETFIELD_GC, [res, ConstInt(3)], 'void',
                               ofs_s)
        # XXX ConstFloat
        #self.execute_operation(rop.SETFIELD_GC, [res, ofs_f, 1e100], 'void')
        # XXX we don't support shorts (at all)
        #self.execute_operation(rop.SETFIELD_GC, [res, ofs_u, ConstInt(5)], 'void')
        s = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofs_s)
        assert s.value == 3
        self.execute_operation(rop.SETFIELD_GC, [res, BoxInt(3)], 'void',
                               ofs_s)
        s = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofs_s)
        assert s.value == 3
        #u = self.execute_operation(rop.GETFIELD_GC, [res, ofs_u], 'int')
        #assert u.value == 5
        self.execute_operation(rop.SETFIELD_GC, [res, ConstInt(1)], 'void',
                               ofsc1)
        self.execute_operation(rop.SETFIELD_GC, [res, ConstInt(3)], 'void',
                               ofsc3)
        self.execute_operation(rop.SETFIELD_GC, [res, ConstInt(2)], 'void',
                               ofsc2)
        c = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofsc1)
        assert c.value == 1
        c = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofsc2)
        assert c.value == 2
        c = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofsc3)
        assert c.value == 3

    def test_uint_ops(self):
        from pypy.rlib.rarithmetic import r_uint, intmask

        arg0 = BoxInt(intmask(r_uint(sys.maxint + 3)))
        arg1 = BoxInt(intmask(r_uint(4)))

        res = self.execute_operation(rop.UINT_GT, [arg0, arg1], 'int')
        assert res.value == 1

    def test_nullity_with_guard(self):
        allops = [rop.OONONNULL, rop.OOISNULL]
        guards = [rop.GUARD_TRUE, rop.GUARD_FALSE]
        p = lltype.cast_opaque_ptr(llmemory.GCREF,
                                   lltype.malloc(lltype.GcStruct('x')))
        p = BoxPtr(p)
        nullptr = lltype.nullptr(llmemory.GCREF.TO)
        n = BoxPtr(nullptr)
        f = BoxInt()
        for b in (p, n):
            for op in allops:
                for guard in guards:
                    ops = [
                        ResOperation(op, [b], f),
                        ResOperation(guard, [f], None),
                        ResOperation(rop.FAIL, [ConstInt(0)], None),
                        ]
                    ops[1].suboperations = [ResOperation(rop.FAIL, [ConstInt(1)], None)]
                    loop = TreeLoop('name')
                    loop.operations = ops
                    loop.inputargs = [b]
                    self.cpu.compile_operations(loop)
                    self.cpu.set_future_value_ptr(0, b.value)
                    r = self.cpu.execute_operations(loop)
                    result = self.cpu.get_latest_value_int(0)
                    if guard == rop.GUARD_FALSE:
                        assert result == execute(self.cpu, op, [b]).value
                    else:
                        assert result != execute(self.cpu, op, [b]).value
                    

    def test_stuff_followed_by_guard(self):
        boxes = [(BoxInt(1), BoxInt(0)),
                 (BoxInt(0), BoxInt(1)),
                 (BoxInt(1), BoxInt(1)),
                 (BoxInt(-1), BoxInt(1)),
                 (BoxInt(1), BoxInt(-1)),
                 (ConstInt(1), BoxInt(0)),
                 (ConstInt(0), BoxInt(1)),
                 (ConstInt(1), BoxInt(1)),
                 (ConstInt(-1), BoxInt(1)),
                 (ConstInt(1), BoxInt(-1)),
                 (BoxInt(1), ConstInt(0)),
                 (BoxInt(0), ConstInt(1)),
                 (BoxInt(1), ConstInt(1)),
                 (BoxInt(-1), ConstInt(1)),
                 (BoxInt(1), ConstInt(-1))]
        guards = [rop.GUARD_FALSE, rop.GUARD_TRUE]
        all = [rop.INT_EQ, rop.INT_NE, rop.INT_LE, rop.INT_LT, rop.INT_GT,
               rop.INT_GE, rop.UINT_GT, rop.UINT_LT, rop.UINT_LE, rop.UINT_GE]
        for a, b in boxes:
            for guard in guards:
                for op in all:
                    res = BoxInt()
                    ops = [
                        ResOperation(op, [a, b], res),
                        ResOperation(guard, [res], None),
                        ResOperation(rop.FAIL, [ConstInt(0)], None),
                        ]
                    ops[1].suboperations = [ResOperation(rop.FAIL, [ConstInt(1)], None)]
                    loop = TreeLoop('name')
                    loop.operations = ops
                    loop.inputargs = [i for i in (a, b) if isinstance(i, Box)]
                    self.cpu.compile_operations(loop)
                    for i, box in enumerate(loop.inputargs):
                        self.cpu.set_future_value_int(i, box.value)
                    r = self.cpu.execute_operations(loop)
                    result = self.cpu.get_latest_value_int(0)
                    if guard == rop.GUARD_FALSE:
                        assert result == execute(self.cpu, op, (a, b)).value
                    else:
                        assert result != execute(self.cpu, op, (a, b)).value

    def test_overflow_mc(self):
        from pypy.jit.backend.x86.assembler import MachineCodeBlockWrapper

        orig_size = MachineCodeBlockWrapper.MC_SIZE
        MachineCodeBlockWrapper.MC_SIZE = 1024
        old_mc = self.cpu.assembler.mc
        old_mc2 = self.cpu.assembler.mc2
        self.cpu.assembler.mc = None
        try:
            ops = []
            base_v = BoxInt()
            v = base_v
            for i in range(1024):
                next_v = BoxInt()
                ops.append(ResOperation(rop.INT_ADD, [v, ConstInt(1)], next_v))
                v = next_v
            ops.append(ResOperation(rop.FAIL, [v], None))
            loop = TreeLoop('name')
            loop.operations = ops
            loop.inputargs = [base_v]
            self.cpu.compile_operations(loop)
            self.cpu.set_future_value_int(0, base_v.value)
            op = self.cpu.execute_operations(loop)
            assert self.cpu.get_latest_value_int(0) == 1024
        finally:
            MachineCodeBlockWrapper.MC_SIZE = orig_size
            self.cpu.assembler.mc = old_mc
            self.cpu.assembler.mc2 = old_mc2
