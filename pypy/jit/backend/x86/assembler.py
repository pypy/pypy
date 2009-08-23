import sys, os
import ctypes
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.history import Const, Box, BoxPtr, PTR
from pypy.rpython.lltypesystem import lltype, rffi, ll2ctypes, rstr, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.annotation import model as annmodel
from pypy.tool.uid import fixid
from pypy.jit.backend.x86.regalloc import (RegAlloc, WORD, REGS, TempBox,
                                           lower_byte, stack_pos)
from pypy.rlib.objectmodel import we_are_translated, specialize, compute_unique_id
from pypy.jit.backend.x86 import codebuf
from pypy.jit.backend.x86.ri386 import *
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.logger import AbstractLogger

# our calling convention - we pass three first args as edx, ecx and eax
# and the rest stays on the stack

MAX_FAIL_BOXES = 1000
if sys.platform == 'darwin':
    # darwin requires the stack to be 16 bytes aligned on calls
    CALL_ALIGN = 4
else:
    CALL_ALIGN = 1


def align_stack_words(words):
    return (words + CALL_ALIGN - 1) & ~(CALL_ALIGN-1)

class x86Logger(AbstractLogger):

    is_oo = False

    def repr_of_descr(self, descr):
        from pypy.jit.backend.x86.runner import ConstDescr3
        if isinstance(descr, ConstDescr3):
            return (str(descr.v0) + "," + str(descr.v1) +
                    "," + str(descr.flag2))
        return AbstractLogger.repr_of_descr(self, descr)


class MachineCodeBlockWrapper(object):
    MC_SIZE = 1024*1024

    def __init__(self):
        self.old_mcs = [] # keepalive
        self._mc = codebuf.MachineCodeBlock(self.MC_SIZE)

    def tell(self):
        return self._mc.tell()

    def done(self):
        self._mc.done()

def _new_method(name):
    def method(self, *args):
        # XXX er.... pretty random number, just to be sure
        #     not to write half-instruction
        if self._mc._pos + 64 >= self._mc._size:
            new_mc = codebuf.MachineCodeBlock(self.MC_SIZE)
            self._mc.JMP(rel32(new_mc.tell()))
            self._mc.done()
            self.old_mcs.append(self._mc)
            self._mc = new_mc
        getattr(self._mc, name)(*args)    
    method.func_name = name
    return method

for name in dir(codebuf.MachineCodeBlock):
    if name.upper() == name:
        setattr(MachineCodeBlockWrapper, name, _new_method(name))

class MachineCodeStack(object):
    def __init__(self):
        self.mcstack = []
        self.counter = 0

    def next_mc(self):
        if len(self.mcstack) == self.counter:
            mc = MachineCodeBlockWrapper()
            self.mcstack.append(mc)
        else:
            mc = self.mcstack[self.counter]
        self.counter += 1
        return mc

    def give_mc_back(self, mc):
        mc.done()
        assert self.mcstack[self.counter - 1] is mc
        self.counter -= 1

class Assembler386(object):
    mc = None
    mc2 = None
    debug_markers = True

    def __init__(self, cpu, translate_support_code=False):
        self.cpu = cpu
        self.verbose = False
        self.rtyper = cpu.rtyper
        self.malloc_func_addr = 0
        self.malloc_array_func_addr = 0
        self.malloc_str_func_addr = 0
        self.malloc_unicode_func_addr = 0
        self._exception_data = lltype.nullptr(rffi.CArray(lltype.Signed))
        self._exception_addr = 0
        self.mcstack = MachineCodeStack()
        self.logger = x86Logger()
        self.fail_boxes_int = lltype.malloc(lltype.GcArray(lltype.Signed),
                                            MAX_FAIL_BOXES, zero=True)
        self.fail_boxes_ptr = lltype.malloc(lltype.GcArray(llmemory.GCREF),
                                            MAX_FAIL_BOXES, zero=True)

    def make_sure_mc_exists(self):
        if self.mc is None:
            from pypy.jit.backend.x86.runner import ConstDescr3

            rffi.cast(lltype.Signed, self.fail_boxes_int)   # workaround
            rffi.cast(lltype.Signed, self.fail_boxes_ptr)   # workaround
            self.fail_box_int_addr = rffi.cast(lltype.Signed,
                lltype.direct_arrayitems(self.fail_boxes_int))
            self.fail_box_ptr_addr = rffi.cast(lltype.Signed,
                lltype.direct_arrayitems(self.fail_boxes_ptr))

            self.logger.create_log()
            # we generate the loop body in 'mc'
            # 'mc2' is for guard recovery code
            if we_are_translated():
                addr = llop.get_exception_addr(llmemory.Address)
                self._exception_data = llmemory.cast_adr_to_ptr(addr, rffi.CArrayPtr(lltype.Signed))
            else:
                self._exception_data = lltype.malloc(rffi.CArray(lltype.Signed), 2,
                                                     zero=True, flavor='raw')
            self._exception_addr = self.cpu.cast_ptr_to_int(
                self._exception_data)
            # a backup, in case our exception can be somehow mangled,
            # by a handling code
            self._exception_bck = lltype.malloc(rffi.CArray(lltype.Signed), 2,
                                                zero=True, flavor='raw')
            self._exception_bck_addr = self.cpu.cast_ptr_to_int(
                self._exception_bck)
            self.mc = self.mcstack.next_mc()
            self.mc2 = self.mcstack.next_mc()
            # the address of the function called by 'new'
            gc_ll_descr = self.cpu.gc_ll_descr
            ll_new = gc_ll_descr.get_funcptr_for_new()
            self.malloc_func_addr = rffi.cast(lltype.Signed, ll_new)
            if gc_ll_descr.get_funcptr_for_newarray is not None:
                ll_new_array = gc_ll_descr.get_funcptr_for_newarray()
                self.malloc_array_func_addr = rffi.cast(lltype.Signed,
                                                        ll_new_array)
            if gc_ll_descr.get_funcptr_for_newstr is not None:
                ll_new_str = gc_ll_descr.get_funcptr_for_newstr()
                self.malloc_str_func_addr = rffi.cast(lltype.Signed,
                                                      ll_new_str)
            if gc_ll_descr.get_funcptr_for_newunicode is not None:
                ll_new_unicode = gc_ll_descr.get_funcptr_for_newunicode()
                self.malloc_unicode_func_addr = rffi.cast(lltype.Signed,
                                                          ll_new_unicode)
            # for moving GCs, the array used to hold the address of GC objects
            # that appear as ConstPtr.
            if gc_ll_descr.moving_gc:
                self.gcrefs = gc_ll_descr.GcRefList()
                self.single_gcref_descr = ConstDescr3(0, WORD, True)
            else:
                self.gcrefs = None
            self.gcrootmap = gc_ll_descr.gcrootmap
            if self.gcrootmap:
                self.gcrootmap.initialize()


    def _compute_longest_fail_op(self, ops):
        max_so_far = 0
        for op in ops:
            if op.opnum == rop.FAIL:
                max_so_far = max(max_so_far, len(op.args))
            if op.is_guard():
                max_so_far = max(max_so_far, self._compute_longest_fail_op(
                    op.suboperations))
        assert max_so_far < MAX_FAIL_BOXES
        return max_so_far

    def assemble(self, tree):
        self.places_to_patch_framesize = []
        self.jumps_to_look_at = []
        # the last operation can be 'jump', 'return' or 'guard_pause';
        # a 'jump' can either close a loop, or end a bridge to some
        # previously-compiled code.
        self._compute_longest_fail_op(tree.operations)
        self.tree = tree
        self.make_sure_mc_exists()
        inputargs = tree.inputargs
        self.logger.eventually_log_operations(tree.inputargs, tree.operations, None,
                                              compute_unique_id(tree))
        regalloc = RegAlloc(self, tree, self.cpu.translate_support_code)
        self._regalloc = regalloc
        regalloc.walk_operations(tree)
        self.sanitize_tree(tree.operations)
        self.mc.done()
        self.mc2.done()
        stack_words = regalloc.max_stack_depth
        # possibly align, e.g. for Mac OS X
        RET_BP = 5 # ret ip + bp + bx + esi + edi = 5 words
        stack_words = align_stack_words(stack_words+RET_BP)
        tree._x86_stack_depth = stack_words-RET_BP        
        for place in self.places_to_patch_framesize:
            mc = codebuf.InMemoryCodeBuilder(place, place + 128)
            mc.ADD(esp, imm32(tree._x86_stack_depth * WORD))
            mc.done()
        for op, pos in self.jumps_to_look_at:
            if op.jump_target._x86_stack_depth != tree._x86_stack_depth:
                tl = op.jump_target
                self.patch_jump(pos, tl._x86_compiled, tl.arglocs, tl.arglocs,
                                tree._x86_stack_depth, tl._x86_stack_depth)
        if we_are_translated():
            self._regalloc = None   # else keep it around for debugging

    def sanitize_tree(self, operations):
        """ Cleans up all attributes attached by regalloc and backend
        """
        for op in operations:
            if op.is_guard():
                op.inputargs = None
                op.longevity = None
                self.sanitize_tree(op.suboperations)

    def assemble_bootstrap_code(self, jumpaddr, arglocs, args, framesize):
        self.make_sure_mc_exists()
        addr = self.mc.tell()
        #if self.gcrootmap:
        self.mc.PUSH(ebp)
        self.mc.MOV(ebp, esp)
        self.mc.PUSH(ebx)
        self.mc.PUSH(esi)
        self.mc.PUSH(edi)
        # NB. exactly 4 pushes above; if this changes, fix stack_pos().
        # You must also keep _get_callshape() in sync.
        self.mc.SUB(esp, imm(framesize * WORD))
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if not isinstance(loc, REG):
                if args[i].type == PTR:
                    # This uses XCHG to put zeroes in fail_boxes_ptr after
                    # reading them
                    self.mc.XOR(ecx, ecx)
                    self.mc.XCHG(ecx, addr_add(imm(self.fail_box_ptr_addr),
                                               imm(i*WORD)))
                else:
                    self.mc.MOV(ecx, addr_add(imm(self.fail_box_int_addr),
                                              imm(i*WORD)))
                self.mc.MOV(loc, ecx)
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if isinstance(loc, REG):
                if args[i].type == PTR:
                    # This uses XCHG to put zeroes in fail_boxes_ptr after
                    # reading them
                    self.mc.XOR(loc, loc)
                    self.mc.XCHG(loc, addr_add(imm(self.fail_box_ptr_addr),
                                               imm(i*WORD)))
                else:
                    self.mc.MOV(loc, addr_add(imm(self.fail_box_int_addr),
                                              imm(i*WORD)))
        self.mc.JMP(rel32(jumpaddr))
        self.mc.done()
        return addr

    def dump(self, text):
        if not self.verbose:
            return
        _prev = Box._extended_display
        try:
            Box._extended_display = False
            print >> sys.stderr, ' 0x%x  %s' % (fixid(self.mc.tell()), text)
        finally:
            Box._extended_display = _prev

    # ------------------------------------------------------------

    def regalloc_load(self, from_loc, to_loc):
        self.mc.MOV(to_loc, from_loc)

    regalloc_store = regalloc_load

    def regalloc_push(self, loc):
        self.mc.PUSH(loc)

    def regalloc_pop(self, loc):
        self.mc.POP(loc)

    def regalloc_stackdiscard(self, count):
        self.mc.ADD(esp, imm(WORD * count))

    def regalloc_perform(self, op, arglocs, resloc):
        genop_list[op.opnum](self, op, arglocs, resloc)

    def regalloc_perform_discard(self, op, arglocs):
        genop_discard_list[op.opnum](self, op, arglocs)

    def regalloc_perform_with_guard(self, op, guard_op, regalloc,
                                    arglocs, resloc):
        addr = self.implement_guard_recovery(guard_op, regalloc)
        genop_guard_list[op.opnum](self, op, guard_op, addr, arglocs,
                                   resloc)

    def regalloc_perform_guard(self, op, regalloc, arglocs, resloc):
        addr = self.implement_guard_recovery(op, regalloc)
        genop_guard_list[op.opnum](self, op, None, addr, arglocs,
                                   resloc)

    def load_effective_addr(self, sizereg, baseofs, scale, result):
        self.mc.LEA(result, addr_add(imm(0), sizereg, baseofs, scale))

    def _unaryop(asmop):
        def genop_unary(self, op, arglocs, resloc):
            getattr(self.mc, asmop)(arglocs[0])
        return genop_unary

    def _binaryop(asmop, can_swap=False):
        def genop_binary(self, op, arglocs, result_loc):
            getattr(self.mc, asmop)(arglocs[0], arglocs[1])
        return genop_binary

    def _cmpop(cond, rev_cond):
        def genop_cmp(self, op, arglocs, result_loc):
            if isinstance(op.args[0], Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                self.mc.MOV(result_loc, imm8(0))
                getattr(self.mc, 'SET' + rev_cond)(lower_byte(result_loc))
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                self.mc.MOV(result_loc, imm8(0))
                getattr(self.mc, 'SET' + cond)(lower_byte(result_loc))
        return genop_cmp

    def _cmpop_guard(cond, rev_cond, false_cond, false_rev_cond):
        def genop_cmp_guard(self, op, guard_op, addr, arglocs, result_loc):
            if isinstance(op.args[0], Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                if guard_op.opnum == rop.GUARD_FALSE:
                    name = 'J' + rev_cond
                    self.implement_guard(addr, guard_op, getattr(self.mc, name))
                else:
                    name = 'J' + false_rev_cond
                    self.implement_guard(addr, guard_op, getattr(self.mc, name))
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                if guard_op.opnum == rop.GUARD_FALSE:
                    self.implement_guard(addr, guard_op,
                                         getattr(self.mc, 'J' + cond))
                else:
                    name = 'J' + false_cond
                    self.implement_guard(addr, guard_op, getattr(self.mc, name))
        return genop_cmp_guard
            
    def align_stack_for_call(self, nargs):
        # xxx do something when we don't use push anymore for calls
        extra_on_stack = align_stack_words(nargs)
        for i in range(extra_on_stack-nargs):
            self.mc.PUSH(imm(0))
        return extra_on_stack

    def call(self, addr, args, res):
        nargs = len(args)
        extra_on_stack = self.align_stack_for_call(nargs)
        for i in range(nargs-1, -1, -1):
            arg = args[i]
            assert not isinstance(arg, MODRM)
            self.mc.PUSH(arg)
        self.mc.CALL(rel32(addr))
        self.mark_gc_roots()
        self.mc.ADD(esp, imm(extra_on_stack * WORD))
        assert res is eax

    genop_int_neg = _unaryop("NEG")
    genop_int_invert = _unaryop("NOT")
    genop_int_add = _binaryop("ADD", True)
    genop_int_sub = _binaryop("SUB")
    genop_int_mul = _binaryop("IMUL", True)
    genop_int_and = _binaryop("AND", True)
    genop_int_or  = _binaryop("OR", True)
    genop_int_xor = _binaryop("XOR", True)

    genop_int_mul_ovf = genop_int_mul
    genop_int_sub_ovf = genop_int_sub
    genop_int_add_ovf = genop_int_add

    genop_int_lt = _cmpop("L", "G")
    genop_int_le = _cmpop("LE", "GE")
    genop_int_eq = _cmpop("E", "E")
    genop_oois = genop_int_eq
    genop_int_ne = _cmpop("NE", "NE")
    genop_ooisnot = genop_int_ne
    genop_int_gt = _cmpop("G", "L")
    genop_int_ge = _cmpop("GE", "LE")

    genop_uint_gt = _cmpop("A", "B")
    genop_uint_lt = _cmpop("B", "A")
    genop_uint_le = _cmpop("BE", "AE")
    genop_uint_ge = _cmpop("AE", "BE")

    genop_guard_int_lt = _cmpop_guard("L", "G", "GE", "LE")
    genop_guard_int_le = _cmpop_guard("LE", "GE", "G", "L")
    genop_guard_int_eq = _cmpop_guard("E", "E", "NE", "NE")
    genop_guard_int_ne = _cmpop_guard("NE", "NE", "E", "E")
    genop_guard_int_gt = _cmpop_guard("G", "L", "LE", "GE")
    genop_guard_int_ge = _cmpop_guard("GE", "LE", "L", "G")

    genop_guard_uint_gt = _cmpop_guard("A", "B", "BE", "AE")
    genop_guard_uint_lt = _cmpop_guard("B", "A", "AE", "BE")
    genop_guard_uint_le = _cmpop_guard("BE", "AE", "A", "B")
    genop_guard_uint_ge = _cmpop_guard("AE", "BE", "B", "A")

    # for now all chars are being considered ints, although we should make
    # a difference at some point
    xxx_genop_char_eq = genop_int_eq

    def genop_bool_not(self, op, arglocs, resloc):
        self.mc.XOR(arglocs[0], imm8(1))

    def genop_int_lshift(self, op, arglocs, resloc):
        loc, loc2 = arglocs
        if loc2 is ecx:
            loc2 = cl
        self.mc.SHL(loc, loc2)

    def genop_int_rshift(self, op, arglocs, resloc):
        loc, loc2 = arglocs
        if loc2 is ecx:
            loc2 = cl
        self.mc.SAR(loc, loc2)

    def genop_uint_rshift(self, op, arglocs, resloc):
        loc, loc2 = arglocs
        if loc2 is ecx:
            loc2 = cl
        self.mc.SHR(loc, loc2)

    def genop_int_is_true(self, op, arglocs, resloc):
        argloc = arglocs[0]
        self.mc.TEST(argloc, argloc)
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETNZ(lower_byte(resloc))

    def genop_guard_oononnull(self, op, guard_op, addr, arglocs, resloc):
        loc = arglocs[0]
        self.mc.TEST(loc, loc)
        if guard_op.opnum == rop.GUARD_TRUE:
            self.implement_guard(addr, guard_op, self.mc.JZ)
        else:
            self.implement_guard(addr, guard_op, self.mc.JNZ)

    def genop_guard_ooisnull(self, op, guard_op, addr, arglocs, resloc):
        loc = arglocs[0]
        self.mc.TEST(loc, loc)
        if guard_op.opnum == rop.GUARD_TRUE:
            self.implement_guard(addr, guard_op, self.mc.JNZ)
        else:
            self.implement_guard(addr, guard_op, self.mc.JZ)

    def genop_oononnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETNE(lower_byte(resloc))

    def genop_ooisnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETE(lower_byte(resloc))

    def genop_same_as(self, op, arglocs, resloc):
        self.mc.MOV(resloc, arglocs[0])
    genop_cast_int_to_ptr = genop_same_as
    genop_cast_ptr_to_int = genop_same_as

    def genop_int_mod(self, op, arglocs, resloc):
        self.mc.CDQ()
        self.mc.IDIV(ecx)

    genop_int_floordiv = genop_int_mod

    def genop_new_with_vtable(self, op, arglocs, result_loc):
        assert result_loc is eax
        loc_vtable = arglocs[-1]
        assert isinstance(loc_vtable, IMM32)
        arglocs = arglocs[:-1]
        self.call(self.malloc_func_addr, arglocs, eax)
        # xxx ignore NULL returns for now
        self.mc.MOV(mem(eax, self.cpu.vtable_offset), loc_vtable)

    # XXX genop_new is abused for all varsized mallocs with Boehm, for now
    # (instead of genop_new_array, genop_newstr, genop_newunicode)
    def genop_new(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_func_addr, arglocs, eax)

    def genop_new_array(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_array_func_addr, arglocs, eax)

    def genop_newstr(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_str_func_addr, arglocs, eax)

    def genop_newunicode(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_unicode_func_addr, arglocs, eax)

    def genop_getfield_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, size_loc = arglocs
        assert isinstance(size_loc, IMM32)
        size = size_loc.value
        if size == 1:
            self.mc.MOVZX(resloc, addr8_add(base_loc, ofs_loc))
        elif size == 2:
            self.mc.MOVZX(resloc, addr_add(base_loc, ofs_loc))
        elif size == WORD:
            self.mc.MOV(resloc, addr_add(base_loc, ofs_loc))
        else:
            raise NotImplementedError("getfield size = %d" % size)

    genop_getfield_gc_pure = genop_getfield_gc

    def genop_getarrayitem_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, scale, ofs = arglocs
        assert isinstance(ofs, IMM32)
        assert isinstance(scale, IMM32)
        if scale.value == 0:
            self.mc.MOVZX(resloc, addr8_add(base_loc, ofs_loc, ofs.value,
                                            scale.value))
        elif scale.value == 2:
            self.mc.MOV(resloc, addr_add(base_loc, ofs_loc, ofs.value,
                                         scale.value))
        else:
            print "[asmgen]setarrayitem unsupported size: %d" % scale.value
            raise NotImplementedError()

    genop_getfield_raw = genop_getfield_gc
    genop_getarrayitem_gc_pure = genop_getarrayitem_gc

    def genop_discard_setfield_gc(self, op, arglocs):
        base_loc, ofs_loc, size_loc, value_loc = arglocs
        assert isinstance(size_loc, IMM32)
        size = size_loc.value
        if size == WORD:
            self.mc.MOV(addr_add(base_loc, ofs_loc), value_loc)
        elif size == 2:
            self.mc.MOV16(addr_add(base_loc, ofs_loc), value_loc)
        elif size == 1:
            self.mc.MOV(addr8_add(base_loc, ofs_loc), lower_byte(value_loc))
        else:
            print "[asmgen]setfield addr size %d" % size
            raise NotImplementedError("Addr size %d" % size)

    def genop_discard_setarrayitem_gc(self, op, arglocs):
        base_loc, ofs_loc, value_loc, scale_loc, baseofs = arglocs
        assert isinstance(baseofs, IMM32)
        assert isinstance(scale_loc, IMM32)
        if scale_loc.value == 2:
            self.mc.MOV(addr_add(base_loc, ofs_loc, baseofs.value,
                                 scale_loc.value), value_loc)
        elif scale_loc.value == 0:
            self.mc.MOV(addr8_add(base_loc, ofs_loc, baseofs.value,
                                 scale_loc.value), lower_byte(value_loc))
        else:
            raise NotImplementedError("scale = %d" % scale_loc.value)

    def genop_discard_strsetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                              self.cpu.translate_support_code)
        assert itemsize == 1
        self.mc.MOV(addr8_add(base_loc, ofs_loc, basesize),
                    lower_byte(val_loc))

    def genop_discard_unicodesetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                              self.cpu.translate_support_code)
        if itemsize == 4:
            self.mc.MOV(addr_add(base_loc, ofs_loc, basesize, 2), val_loc)
        elif itemsize == 2:
            self.mc.MOV16(addr_add(base_loc, ofs_loc, basesize, 1), val_loc)
        else:
            assert 0, itemsize

    genop_discard_setfield_raw = genop_discard_setfield_gc

    def genop_strlen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_unicodelen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_arraylen_gc(self, op, arglocs, resloc):
        ofs = self.cpu.gc_ll_descr.array_length_ofs
        base_loc, ofs_loc = arglocs
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs))

    def genop_strgetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        self.mc.MOVZX(resloc, addr8_add(base_loc, ofs_loc, basesize))

    def genop_unicodegetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        if itemsize == 4:
            self.mc.MOV(resloc, addr_add(base_loc, ofs_loc, basesize, 2))
        elif itemsize == 2:
            self.mc.MOVZX(resloc, addr_add(base_loc, ofs_loc, basesize, 1))
        else:
            assert 0, itemsize

    def make_merge_point(self, tree, locs):
        pos = self.mc.tell()
        tree._x86_compiled = pos
        #tree.comeback_bootstrap_addr = self.assemble_comeback_bootstrap(pos,
        #                                                locs, stacklocs)

    def patch_jump(self, old_pos, new_pos, oldlocs, newlocs, olddepth, newdepth):
        for i in range(len(oldlocs)):
            oldloc = oldlocs[i]
            newloc = newlocs[i]
            if isinstance(newloc, MODRM):
                assert isinstance(oldloc, MODRM)
                assert newloc.position == oldloc.position
            else:
                assert newloc is oldloc
            # newlocs should be sorted in acending order, excluding the regs
            if not we_are_translated():
                locs = [loc.position for loc in newlocs if isinstance(loc, MODRM)]
                assert locs == sorted(locs)
        #
        mc = codebuf.InMemoryCodeBuilder(old_pos, old_pos +
                                         MachineCodeBlockWrapper.MC_SIZE)
        mc.SUB(esp, imm(WORD * (newdepth - olddepth)))
        mc.JMP(rel32(new_pos))
        mc.done()

    def genop_discard_jump(self, op, locs):
        targetmp = op.jump_target
        if op.jump_target is not self.tree:
            self.jumps_to_look_at.append((op, self.mc.tell()))
        self.mc.JMP(rel32(targetmp._x86_compiled))
        if op.jump_target is not self.tree:
            # Reserve 6 bytes for a possible later patch by patch_jump().
            # Put them after the JMP by default, as it's not doing anything.
            self.mc.SUB(esp, imm32(0))

    def genop_guard_guard_true(self, op, ign_1, addr, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(addr, op, self.mc.JZ)

    def genop_guard_guard_no_exception(self, op, ign_1, addr, locs, ign_2):
        self.mc.CMP(heap(self._exception_addr), imm(0))
        self.implement_guard(addr, op, self.mc.JNZ)

    def genop_guard_guard_exception(self, op, ign_1, addr, locs, resloc):
        loc = locs[0]
        loc1 = locs[1]
        self.mc.MOV(loc1, heap(self._exception_addr))
        self.mc.CMP(loc1, loc)
        self.implement_guard(addr, op, self.mc.JNE)
        if resloc is not None:
            self.mc.MOV(resloc, addr_add(imm(self._exception_addr), imm(WORD)))
        self.mc.MOV(heap(self._exception_addr), imm(0))
        self.mc.MOV(addr_add(imm(self._exception_addr), imm(WORD)), imm(0))

    def genop_guard_guard_no_overflow(self, op, ign_1, addr, locs, resloc):
        self.implement_guard(addr, op, self.mc.JO)

    def genop_guard_guard_overflow(self, op, ign_1, addr, locs, resloc):
        self.implement_guard(addr, op, self.mc.JNO)

    def genop_guard_guard_false(self, op, ign_1, addr, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(addr, op, self.mc.JNZ)

    def genop_guard_guard_value(self, op, ign_1, addr, locs, ign_2):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(addr, op, self.mc.JNE)

    def genop_guard_guard_class(self, op, ign_1, addr, locs, ign_2):
        offset = self.cpu.vtable_offset
        self.mc.CMP(mem(locs[0], offset), locs[1])
        self.implement_guard(addr, op, self.mc.JNE)

    def implement_guard_recovery(self, guard_op, regalloc):
        oldmc = self.mc
        self.mc = self.mc2
        self.mc2 = self.mcstack.next_mc()
        addr = self.mc.tell()
        exc = (guard_op.opnum == rop.GUARD_EXCEPTION or
               guard_op.opnum == rop.GUARD_NO_EXCEPTION)
        # XXX this is a heuristics to detect whether we're handling this
        # exception or not. We should have a bit better interface to deal
        # with that I fear
        if (exc and (guard_op.suboperations[0].opnum == rop.GUARD_EXCEPTION or
                    guard_op.suboperations[0].opnum == rop.GUARD_NO_EXCEPTION)):
            exc = False
        regalloc.walk_guard_ops(guard_op.inputargs, guard_op.suboperations, exc)
        self.mcstack.give_mc_back(self.mc2)
        self.mc2 = self.mc
        self.mc = oldmc
        return addr

    def generate_failure(self, op, locs, exc):
        pos = self.mc.tell()
        for i in range(len(locs)):
            loc = locs[i]
            if isinstance(loc, REG):
                if op.args[i].type == PTR:
                    base = self.fail_box_ptr_addr
                else:
                    base = self.fail_box_int_addr
                self.mc.MOV(addr_add(imm(base), imm(i*WORD)), loc)
        for i in range(len(locs)):
            loc = locs[i]
            if not isinstance(loc, REG):
                if op.args[i].type == PTR:
                    base = self.fail_box_ptr_addr
                else:
                    base = self.fail_box_int_addr
                self.mc.MOV(eax, loc)
                self.mc.MOV(addr_add(imm(base), imm(i*WORD)), eax)
        if self.debug_markers:
            self.mc.MOV(eax, imm(pos))
            self.mc.MOV(addr_add(imm(self.fail_box_int_addr),
                                 imm(len(locs) * WORD)),
                                 eax)
        if exc:
            self.generate_exception_handling(eax)
        self.places_to_patch_framesize.append(self.mc.tell())
        self.mc.ADD(esp, imm32(0))
        guard_index = self.cpu.make_guard_index(op)
        self.mc.MOV(eax, imm(guard_index))
        #if self.gcrootmap:
        self.mc.POP(edi)
        self.mc.POP(esi)
        self.mc.POP(ebx)
        self.mc.POP(ebp)
        self.mc.RET()

    def generate_exception_handling(self, loc):
        self.mc.MOV(loc, heap(self._exception_addr))
        self.mc.MOV(heap(self._exception_bck_addr), loc)
        self.mc.MOV(loc, addr_add(imm(self._exception_addr), imm(WORD)))
        self.mc.MOV(addr_add(imm(self._exception_bck_addr), imm(WORD)), loc)
        # clean up the original exception, we don't want
        # to enter more rpython code with exc set
        self.mc.MOV(heap(self._exception_addr), imm(0))
        self.mc.MOV(addr_add(imm(self._exception_addr), imm(WORD)), imm(0))

    @specialize.arg(3)
    def implement_guard(self, addr, guard_op, emit_jump):
        emit_jump(rel32(addr))

    def genop_call(self, op, arglocs, resloc):
        sizeloc = arglocs[0]
        assert isinstance(sizeloc, IMM32)
        size = sizeloc.value
        arglocs = arglocs[1:]
        nargs = len(op.args)-1
        extra_on_stack = self.align_stack_for_call(nargs)
        for i in range(nargs, 0, -1):
            v = op.args[i]
            loc = arglocs[i]
            self.mc.PUSH(loc)
        if isinstance(op.args[0], Const):
            x = rel32(op.args[0].getint())
        else:
            x = arglocs[0]
        self.mc.CALL(x)
        self.mark_gc_roots()
        self.mc.ADD(esp, imm(WORD * extra_on_stack))
        if size == 1:
            self.mc.AND(eax, imm(0xff))
        elif size == 2:
            self.mc.AND(eax, imm(0xffff))

    genop_call_pure = genop_call

    def not_implemented_op_discard(self, op, arglocs):
        print "not implemented operation: %s" % op.getopname()
        raise NotImplementedError

    def not_implemented_op(self, op, arglocs, resloc):
        print "not implemented operation with res: %s" % op.getopname()
        raise NotImplementedError

    def not_implemented_op_guard(self, op, regalloc, arglocs, resloc, descr):
        print "not implemented operation (guard): %s" % op.getopname()
        raise NotImplementedError

    #def genop_call__1(self, op, arglocs, resloc):
    #    self.gen_call(op, arglocs, resloc)
    #    self.mc.MOVZX(eax, al)

    #def genop_call__2(self, op, arglocs, resloc):
    #    # XXX test it test it test it
    #    self.gen_call(op, arglocs, resloc)
    #    self.mc.MOVZX(eax, eax)

    def mark_gc_roots(self):
        if self.gcrootmap:
            gclocs = []
            regalloc = self._regalloc
            for v, val in regalloc.stack_bindings.items():
                if (isinstance(v, BoxPtr) and
                    regalloc.longevity[v][1] > regalloc.position):
                    gclocs.append(val)
            #alllocs = []
            #for loc in gclocs:
            #    assert isinstance(loc, MODRM)
            #    alllocs.append(str(loc.position))
            #print self.mc.tell()
            #print ", ".join(alllocs)
            shape = self.gcrootmap.encode_callshape(gclocs)
            self.gcrootmap.put(rffi.cast(llmemory.Address, self.mc.tell()),
                               shape)

genop_discard_list = [Assembler386.not_implemented_op_discard] * rop._LAST
genop_list = [Assembler386.not_implemented_op] * rop._LAST
genop_guard_list = [Assembler386.not_implemented_op_guard] * rop._LAST

for name, value in Assembler386.__dict__.iteritems():
    if name.startswith('genop_discard_'):
        opname = name[len('genop_discard_'):]
        num = getattr(rop, opname.upper())
        genop_discard_list[num] = value
    elif name.startswith('genop_guard_') and name != 'genop_guard_exception': 
        opname = name[len('genop_guard_'):]
        num = getattr(rop, opname.upper())
        genop_guard_list[num] = value
    elif name.startswith('genop_'):
        opname = name[len('genop_'):]
        num = getattr(rop, opname.upper())
        genop_list[num] = value

def addr_add(reg_or_imm1, reg_or_imm2, offset=0, scale=0):
    if isinstance(reg_or_imm1, IMM32):
        if isinstance(reg_or_imm2, IMM32):
            return heap(reg_or_imm1.value + offset +
                        (reg_or_imm2.value << scale))
        else:
            return memSIB(None, reg_or_imm2, scale, reg_or_imm1.value + offset)
    else:
        if isinstance(reg_or_imm2, IMM32):
            return mem(reg_or_imm1, offset + (reg_or_imm2.value << scale))
        else:
            return memSIB(reg_or_imm1, reg_or_imm2, scale, offset)

def addr8_add(reg_or_imm1, reg_or_imm2, offset=0, scale=0):
    if isinstance(reg_or_imm1, IMM32):
        if isinstance(reg_or_imm2, IMM32):
            return heap8(reg_or_imm1.value + (offset << scale) +
                         reg_or_imm2.value)
        else:
            return memSIB8(None, reg_or_imm2, scale, reg_or_imm1.value + offset)
    else:
        if isinstance(reg_or_imm2, IMM32):
            return mem8(reg_or_imm1, (offset << scale) + reg_or_imm2.value)
        else:
            return memSIB8(reg_or_imm1, reg_or_imm2, scale, offset)

def addr_add_const(reg_or_imm1, offset):
    if isinstance(reg_or_imm1, IMM32):
        return heap(reg_or_imm1.value + offset)
    else:
        return mem(reg_or_imm1, offset)
