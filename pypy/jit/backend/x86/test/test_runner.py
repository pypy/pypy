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
import ctypes
import sys

class FakeStats(object):
    pass

class FakeMetaInterp(object):
    pass

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

# ____________________________________________________________

class TestX86(object):
    def setup_class(cls):
        cls.cpu = CPU(rtyper=None, stats=FakeStats())
        cls.cpu.set_meta_interp(FakeMetaInterp())

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
        cpu.set_meta_interp(FakeMetaInterp())
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
        res = self.cpu.execute_operations(loop, [BoxInt(0), BoxInt(10)])
        assert [arg.value for arg in res.args] == [0, 55]

    def test_passing_guards(self):
        vtable_for_T = lltype.malloc(MY_VTABLE, immortal=True)
        cpu = self.cpu
        cpu._cache_gcstruct2vtable = {T: vtable_for_T}
        for (opname, args) in [(rop.GUARD_TRUE, [BoxInt(1)]),
                               (rop.GUARD_FALSE, [BoxInt(0)]),
                               (rop.GUARD_VALUE, [BoxInt(42), BoxInt(42)])]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.cpu._guard_index == -1
            
        t = lltype.malloc(T)
        t.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(rffi.cast(lltype.Signed, vtable_for_T))
        null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        assert self.execute_operation(rop.GUARD_CLASS, [t_box, T_box], 'void') == None

    def test_failing_guards(self):
        vtable_for_T = lltype.malloc(MY_VTABLE, immortal=True)
        vtable_for_U = lltype.malloc(MY_VTABLE, immortal=True)
        cpu = self.cpu
        cpu._cache_gcstruct2vtable = {T: vtable_for_T, U: vtable_for_U}
        cpu.set_meta_interp(FakeMetaInterp())
        t = lltype.malloc(T)
        t.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(rffi.cast(lltype.Signed, vtable_for_T))
        u = lltype.malloc(U)
        u.parent.parent.typeptr = vtable_for_U
        u_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        U_box = ConstInt(rffi.cast(lltype.Signed, vtable_for_U))
        null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        for opname, args in [(rop.GUARD_TRUE, [BoxInt(0)]),
                             (rop.GUARD_FALSE, [BoxInt(1)]),
                             (rop.GUARD_VALUE, [BoxInt(42), BoxInt(41)]),
                             (rop.GUARD_CLASS, [t_box, U_box]),
                             (rop.GUARD_CLASS, [u_box, T_box]),
                             ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.cpu._guard_index != -1

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

    def test_same_as(self):
        py.test.skip("I think no longer needed")
        u = lltype.malloc(U)
        uadr = lltype.cast_opaque_ptr(llmemory.GCREF, u)
        for op, args, tp, res in [
            ('same_as', [BoxInt(7)], 'int', 7),
            ('same_as', [ConstInt(7)], 'int', 7),
            ('same_as', [BoxPtr(uadr)], 'ptr', uadr),
            ('same_as', [ConstPtr(uadr)], 'ptr', uadr),
            ]:
            assert self.execute_operation(op, args, tp).value == res

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
        r = self.execute_operation(rop.GETARRAYITEM_GC, [res, BoxInt(3)],
                                   'int', descr)
        assert r.value == 42

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
        ofs_f = self.cpu.fielddescrof(TP, 'f')
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
        self.execute_operation(rop.SETFIELD_GC, [res, ConstInt(2)], 'void',
                               ofsc2)
        self.execute_operation(rop.SETFIELD_GC, [res, ConstInt(3)], 'void',
                               ofsc3)
        c = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofsc1)
        assert c.value == 1
        c = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofsc2)
        assert c.value == 2
        c = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofsc3)
        assert c.value == 3
        
    def test_ovf_ops(self):
        py.test.skip("Cannot run like this, rewrite me")
        arg0 = BoxInt(12)
        arg1 = BoxInt(13)
        res = self.execute_operation(rop.INT_MUL_OVF, [arg0, arg1], 'int')
        assert res.value == 12*13
        arg0 = BoxInt(sys.maxint/2)
        arg1 = BoxInt(2222)
        self.execute_operation(rop.INT_MUL_OVF, [arg0, arg1], 'int')
        assert self.cpu.assembler._exception_data[0] == 1
        self.cpu.assembler._exception_data[0] = 0

    def test_uint_ops(self):
        from pypy.rlib.rarithmetic import r_uint, intmask

        arg0 = BoxInt(intmask(r_uint(sys.maxint + 3)))
        arg1 = BoxInt(intmask(r_uint(4)))
        res = self.execute_operation(rop.UINT_ADD, [arg0, arg1], 'int')
        assert res.value == intmask(r_uint(sys.maxint + 3) + r_uint(4))

        arg0 = BoxInt(intmask(sys.maxint + 10))
        arg1 = BoxInt(10)
        res = self.execute_operation(rop.UINT_MUL, [arg0, arg1], 'int')
        assert res.value == intmask((sys.maxint + 10) * 10)

        arg0 = BoxInt(intmask(r_uint(sys.maxint + 3)))
        arg1 = BoxInt(intmask(r_uint(4)))

        res = self.execute_operation(rop.UINT_GT, [arg0, arg1], 'int')
        assert res.value == 1

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
        x = cpu.do_new_with_vtable(
            [BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(vtable2)))],
            descrsize2)
        assert isinstance(x, BoxPtr)
        # well...
        #assert x.getptr(rclass.OBJECTPTR).typeptr == vtable2
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
        # XXX cannot work without rtyper
        #s = execute(cpu, rop.INT_MUL_OVF, [BoxInt(sys.maxint/2), BoxInt(10)])
        #assert cpu.get_exception()

