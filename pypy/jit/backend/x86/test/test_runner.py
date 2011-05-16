import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr, rclass
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.history import ResOperation, LoopToken
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstFloat,
                                         ConstPtr, Box, BoxFloat, BasicFailDescr)
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.x86.arch import WORD
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.executor import execute
from pypy.jit.backend.test.runner_test import LLtypeBackendTest
from pypy.jit.tool.oparser import parse
from pypy.tool.udir import udir
import ctypes
import sys
import os

CPU = getcpuclass()

class FakeStats(object):
    pass

U = LLtypeBackendTest.U
S = LLtypeBackendTest.S

# ____________________________________________________________

class TestX86(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py
    
    def setup_method(self, meth):
        self.cpu = CPU(rtyper=None, stats=FakeStats())
        self.cpu.setup_once()

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

    @staticmethod
    def _resbuf(res, item_tp=ctypes.c_long):
        return ctypes.cast(res.value._obj.intval, ctypes.POINTER(item_tp))

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
        # ctypes produces an unsigned value. We need it to be signed for, eg,
        # relative addressing to work properly.
        addr = rffi.cast(lltype.Signed, addr)
        
        self.cpu.assembler.setup_once()
        self.cpu.assembler.malloc_func_addr = addr
        ofs = symbolic.get_field_token(rstr.STR, 'chars', False)[0]

        res = self.execute_operation(rop.NEWSTR, [ConstInt(7)], 'ref')
        assert allocs[0] == 7 + ofs + WORD
        resbuf = self._resbuf(res)
        assert resbuf[ofs/WORD] == 7

        # ------------------------------------------------------------

        res = self.execute_operation(rop.NEWSTR, [BoxInt(7)], 'ref')
        assert allocs[0] == 7 + ofs + WORD
        resbuf = self._resbuf(res)
        assert resbuf[ofs/WORD] == 7

        # ------------------------------------------------------------

        TP = lltype.GcArray(lltype.Signed)
        ofs = symbolic.get_field_token(TP, 'length', False)[0]
        descr = self.cpu.arraydescrof(TP)

        res = self.execute_operation(rop.NEW_ARRAY, [ConstInt(10)],
                                         'ref', descr)
        assert allocs[0] == 10*WORD + ofs + WORD
        resbuf = self._resbuf(res)            
        assert resbuf[ofs/WORD] == 10

        # ------------------------------------------------------------

        res = self.execute_operation(rop.NEW_ARRAY, [BoxInt(10)],
                                         'ref', descr)
        assert allocs[0] == 10*WORD + ofs + WORD
        resbuf = self._resbuf(res)                        
        assert resbuf[ofs/WORD] == 10

    def test_stringitems(self):
        from pypy.rpython.lltypesystem.rstr import STR
        ofs = symbolic.get_field_token(STR, 'chars', False)[0]
        ofs_items = symbolic.get_field_token(STR.chars, 'items', False)[0]

        res = self.execute_operation(rop.NEWSTR, [ConstInt(10)], 'ref')
        self.execute_operation(rop.STRSETITEM, [res, ConstInt(2), ConstInt(ord('d'))], 'void')
        resbuf = self._resbuf(res, ctypes.c_char)
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
                                     'ref', descr)
        resbuf = self._resbuf(res)
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
                                     'ref', descr)
        resbuf = self._resbuf(res, ctypes.c_char)
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
                             ('i', rffi.INT),
                             ('f', lltype.Float),
                             ('u', rffi.USHORT),
                             ('c1', lltype.Char),
                             ('c2', lltype.Char),
                             ('c3', lltype.Char))
        res = self.execute_operation(rop.NEW, [],
                                     'ref', self.cpu.sizeof(TP))
        ofs_s = self.cpu.fielddescrof(TP, 's')
        ofs_i = self.cpu.fielddescrof(TP, 'i')
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

        self.execute_operation(rop.SETFIELD_GC, [res, BoxInt(1234)], 'void', ofs_i)
        i = self.execute_operation(rop.GETFIELD_GC, [res], 'int', ofs_i)
        assert i.value == 1234
        
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

    def test_nullity_with_guard(self):
        allops = [rop.INT_IS_TRUE]
        guards = [rop.GUARD_TRUE, rop.GUARD_FALSE]
        p = lltype.cast_opaque_ptr(llmemory.GCREF,
                                   lltype.malloc(lltype.GcStruct('x')))
        nullptr = lltype.nullptr(llmemory.GCREF.TO)
        f = BoxInt()
        for op in allops:
            for guard in guards:
                if op == rop.INT_IS_TRUE:
                    bp = BoxInt(1)
                    n = BoxInt(0)
                else:
                    bp = BoxPtr(p)
                    n = BoxPtr(nullptr)
                for b in (bp, n):
                    i1 = BoxInt(1)
                    ops = [
                        ResOperation(rop.SAME_AS, [ConstInt(1)], i1),
                        ResOperation(op, [b], f),
                        ResOperation(guard, [f], None,
                                     descr=BasicFailDescr()),
                        ResOperation(rop.FINISH, [ConstInt(0)], None,
                                     descr=BasicFailDescr()),
                        ]
                    ops[-2].setfailargs([i1])
                    looptoken = LoopToken()
                    self.cpu.compile_loop([b], ops, looptoken)
                    if op == rop.INT_IS_TRUE:
                        self.cpu.set_future_value_int(0, b.value)
                    else:
                        self.cpu.set_future_value_ref(0, b.value)
                    self.cpu.execute_token(looptoken)
                    result = self.cpu.get_latest_value_int(0)
                    if guard == rop.GUARD_FALSE:
                        assert result == execute(self.cpu, None,
                                                 op, None, b).value
                    else:
                        assert result != execute(self.cpu, None,
                                                 op, None, b).value
                    

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
                    i1 = BoxInt(1)
                    ops = [
                        ResOperation(rop.SAME_AS, [ConstInt(1)], i1),
                        ResOperation(op, [a, b], res),
                        ResOperation(guard, [res], None,
                                     descr=BasicFailDescr()),
                        ResOperation(rop.FINISH, [ConstInt(0)], None,
                                     descr=BasicFailDescr()),
                        ]
                    ops[-2].setfailargs([i1])
                    inputargs = [i for i in (a, b) if isinstance(i, Box)]
                    looptoken = LoopToken()
                    self.cpu.compile_loop(inputargs, ops, looptoken)
                    for i, box in enumerate(inputargs):
                        self.cpu.set_future_value_int(i, box.value)
                    self.cpu.execute_token(looptoken)
                    result = self.cpu.get_latest_value_int(0)
                    expected = execute(self.cpu, None, op, None, a, b).value
                    if guard == rop.GUARD_FALSE:
                        assert result == expected
                    else:
                        assert result != expected

    def test_compile_bridge_check_profile_info(self):
        class FakeProfileAgent(object):
            def __init__(self):
                self.functions = []
            def native_code_written(self, name, address, size):
                self.functions.append((name, address, size))
        self.cpu.profile_agent = agent = FakeProfileAgent()

        i0 = BoxInt()
        i1 = BoxInt()
        i2 = BoxInt()
        faildescr1 = BasicFailDescr(1)
        faildescr2 = BasicFailDescr(2)
        looptoken = LoopToken()
        looptoken.number = 17
        class FakeString(object):
            def __init__(self, val):
                self.val = val

            def _get_str(self):
                return self.val

        operations = [
            ResOperation(rop.DEBUG_MERGE_POINT, [FakeString("hello"), 0], None),
            ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1),
            ResOperation(rop.INT_LE, [i1, ConstInt(9)], i2),
            ResOperation(rop.GUARD_TRUE, [i2], None, descr=faildescr1),
            ResOperation(rop.JUMP, [i1], None, descr=looptoken),
            ]
        inputargs = [i0]
        operations[3].setfailargs([i1])
        self.cpu.compile_loop(inputargs, operations, looptoken)
        name, loopaddress, loopsize = agent.functions[0]
        assert name == "Loop # 17: hello"
        assert loopaddress <= looptoken._x86_loop_code
        assert loopsize >= 40 # randomish number

        i1b = BoxInt()
        i3 = BoxInt()
        bridge = [
            ResOperation(rop.INT_LE, [i1b, ConstInt(19)], i3),
            ResOperation(rop.GUARD_TRUE, [i3], None, descr=faildescr2),
            ResOperation(rop.DEBUG_MERGE_POINT, [FakeString("bye"), 0], None),
            ResOperation(rop.JUMP, [i1b], None, descr=looptoken),
        ]
        bridge[1].setfailargs([i1b])

        self.cpu.compile_bridge(faildescr1, [i1b], bridge, looptoken)
        name, address, size = agent.functions[1]
        assert name == "Bridge # 0: bye"
        # Would be exactly ==, but there are some guard failure recovery
        # stubs in-between
        assert address >= loopaddress + loopsize
        assert size >= 10 # randomish number

        self.cpu.set_future_value_int(0, 2)
        fail = self.cpu.execute_token(looptoken)
        assert fail.identifier == 2
        res = self.cpu.get_latest_value_int(0)
        assert res == 20

    def test_ops_offset(self):
        from pypy.rlib import debug
        i0 = BoxInt()
        i1 = BoxInt()
        i2 = BoxInt()
        looptoken = LoopToken()
        operations = [
            ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1),
            ResOperation(rop.INT_LE, [i1, ConstInt(9)], i2),
            ResOperation(rop.JUMP, [i1], None, descr=looptoken),
            ]
        inputargs = [i0]
        debug._log = dlog = debug.DebugLog()
        ops_offset = self.cpu.compile_loop(inputargs, operations, looptoken)
        debug._log = None
        #
        assert ops_offset is looptoken._x86_ops_offset
        # getfield_raw/int_add/setfield_raw + ops + None
        assert len(ops_offset) == 3 + len(operations) + 1
        assert (ops_offset[operations[0]] <=
                ops_offset[operations[1]] <=
                ops_offset[operations[2]] <=
                ops_offset[None])

class TestDebuggingAssembler(object):
    def setup_method(self, meth):
        self.cpu = CPU(rtyper=None, stats=FakeStats())
        self.cpu.setup_once()

    def test_debugger_on(self):
        from pypy.tool.logparser import parse_log_file, extract_category
        from pypy.rlib import debug
        
        loop = """
        [i0]
        debug_merge_point('xyz', 0)
        i1 = int_add(i0, 1)
        i2 = int_ge(i1, 10)
        guard_false(i2) []
        jump(i1)
        """
        ops = parse(loop)
        debug._log = dlog = debug.DebugLog()
        try:
            self.cpu.assembler.set_debug(True)
            self.cpu.compile_loop(ops.inputargs, ops.operations, ops.token)
            self.cpu.set_future_value_int(0, 0)
            self.cpu.execute_token(ops.token)
            # check debugging info
            struct = self.cpu.assembler.loop_run_counters[0]
            assert struct.i == 10
            self.cpu.finish_once()
        finally:
            debug._log = None
        assert ('jit-backend-counts', [('debug_print', '0:10')]) in dlog

    def test_debugger_checksum(self):
        loop = """
        [i0]
        debug_merge_point('xyz', 0)
        i1 = int_add(i0, 1)
        i2 = int_ge(i1, 10)
        guard_false(i2) []
        jump(i1)
        """
        ops = parse(loop)
        self.cpu.assembler.set_debug(True)
        self.cpu.compile_loop(ops.inputargs, ops.operations, ops.token)
        self.cpu.set_future_value_int(0, 0)
        self.cpu.execute_token(ops.token)
        assert ops.token._x86_debug_checksum == sum([op.getopnum()
                                                     for op in ops.operations])
