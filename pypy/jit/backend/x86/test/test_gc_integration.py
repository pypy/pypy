
""" Tests for register allocation for common constructs
"""

import py
from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.backend.llsupport.descr import GcCache
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.backend.x86.regalloc import RegAlloc, WORD
from pypy.jit.metainterp.test.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import rclass, rstr
from pypy.jit.backend.x86.ri386 import *
from pypy.jit.backend.llsupport.gc import GcLLDescr_framework, GcRefList, GcPtrFieldDescr

from pypy.jit.backend.x86.test.test_regalloc import MockAssembler
from pypy.jit.backend.x86.test.test_regalloc import BaseTestRegalloc
from pypy.jit.backend.x86.regalloc import X86RegisterManager, X86StackManager

class MockGcRootMap(object):
    def get_basic_shape(self):
        return ['shape']
    def add_ebp_offset(self, shape, offset):
        shape.append(offset)
    def add_ebx(self, shape):
        shape.append('ebx')
    def add_esi(self, shape):
        shape.append('esi')
    def add_edi(self, shape):
        shape.append('edi')
    def compress_callshape(self, shape):
        assert shape[0] == 'shape'
        return ['compressed'] + shape[1:]

class MockGcDescr(GcCache):
    def get_funcptr_for_new(self):
        return 123
    get_funcptr_for_newarray = get_funcptr_for_new
    get_funcptr_for_newstr = get_funcptr_for_new
    get_funcptr_for_newunicode = get_funcptr_for_new
    
    moving_gc = True
    gcrootmap = MockGcRootMap()

    def initialize(self):
        self.gcrefs = GcRefList()
        self.gcrefs.initialize()
        self.single_gcref_descr = GcPtrFieldDescr(0)
        
    rewrite_assembler = GcLLDescr_framework.rewrite_assembler.im_func

class TestRegallocDirectGcIntegration(object):

    def test_mark_gc_roots(self):
        cpu = CPU(None, None)
        regalloc = RegAlloc(MockAssembler(cpu, MockGcDescr(False)))
        boxes = [BoxPtr() for i in range(len(X86RegisterManager.all_regs))]
        longevity = {}
        for box in boxes:
            longevity[box] = (0, 1)
        regalloc.sm = X86StackManager()
        regalloc.rm = X86RegisterManager(longevity, regalloc.sm,
                                         assembler=regalloc.assembler)
        cpu = regalloc.assembler.cpu
        for box in boxes:
            regalloc.rm.try_allocate_reg(box)
        TP = lltype.FuncType([], lltype.Signed)
        calldescr = cpu.calldescrof(TP, TP.ARGS, TP.RESULT)
        regalloc.rm._check_invariants()
        box = boxes[0]
        regalloc.position = 0
        regalloc.consider_call(ResOperation(rop.CALL, [box], BoxInt(),
                                            calldescr), None)
        assert len(regalloc.assembler.movs) == 3
        #
        mark = regalloc.get_mark_gc_roots(cpu.gc_ll_descr.gcrootmap)
        assert mark[0] == 'compressed'
        expected = ['ebx', 'esi', 'edi', -16, -20, -24]
        assert dict.fromkeys(mark[1:]) == dict.fromkeys(expected)

class TestRegallocGcIntegration(BaseTestRegalloc):
    
    cpu = CPU(None, None)
    cpu.gc_ll_descr = MockGcDescr(False)
    
    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('field', lltype.Ptr(S)),
                             ('int', lltype.Signed)))

    fielddescr = cpu.fielddescrof(S, 'field')

    struct_ptr = lltype.malloc(S)
    struct_ref = lltype.cast_opaque_ptr(llmemory.GCREF, struct_ptr)
    child_ptr = lltype.nullptr(S)
    struct_ptr.field = child_ptr


    descr0 = cpu.fielddescrof(S, 'int')
    ptr0 = struct_ref

    namespace = locals().copy()

    def test_basic(self):
        ops = '''
        [p0]
        p1 = getfield_gc(p0, descr=fielddescr)
        fail(p1)
        '''
        self.interpret(ops, [self.struct_ptr])
        assert not self.getptr(0, lltype.Ptr(self.S))

    def test_rewrite_constptr(self):
        ops = '''
        []
        p1 = getfield_gc(ConstPtr(struct_ref), descr=fielddescr)
        fail(p1)
        '''
        self.interpret(ops, [])
        assert not self.getptr(0, lltype.Ptr(self.S))

    def test_bug_0(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8]
        guard_value(i2, 1)
            fail(i2, i3, i4, i5, i6, i7, i0, i1, i8)
        guard_class(i4, 138998336)
            fail(i4, i5, i6, i7, i0, i1, i8)
        i11 = getfield_gc(i4, descr=descr0)
        i12 = ooisnull(i11)
        guard_false(i12)
            fail(i4, i5, i6, i7, i0, i1, i11, i8)
        i13 = getfield_gc(i11, descr=descr0)
        i14 = ooisnull(i13)
        guard_true(i14)
            fail(i4, i5, i6, i7, i0, i1, i11, i8)
        i15 = getfield_gc(i4, descr=descr0)
        i17 = int_lt(i15, 0)
        guard_false(i17)
            fail(i4, i5, i6, i7, i0, i1, i11, i15, i8)
        i18 = getfield_gc(i11, descr=descr0)
        i19 = int_ge(i15, i18)
        guard_false(i19)
            fail(i4, i5, i6, i7, i0, i1, i11, i15, i8)
        i20 = int_lt(i15, 0)
        guard_false(i20)
            fail(i4, i5, i6, i7, i0, i1, i11, i15, i8)
        i21 = getfield_gc(i11, descr=descr0)
        i22 = getfield_gc(i11, descr=descr0)
        i23 = int_mul(i15, i22)
        i24 = int_add(i21, i23)
        i25 = getfield_gc(i4, descr=descr0)
        i27 = int_add(i25, 1)
        setfield_gc(i4, i27, descr=descr0)
        i29 = getfield_raw(144839744, descr=descr0)
        i31 = int_and(i29, -2141192192)
        i32 = int_is_true(i31)
        guard_false(i32)
            fail(i4, i6, i7, i0, i1, i24)
        i33 = getfield_gc(i0, descr=descr0)
        guard_value(i33, ConstPtr(ptr0))
            fail(i4, i6, i7, i0, i1, i33, i24)
        jump(i0, i1, 1, 17, i4, ConstPtr(ptr0), i6, i7, i24)
        '''
        self.interpret(ops, [0, 0, 0, 0, 0, 0, 0, 0, 0], run=False)
