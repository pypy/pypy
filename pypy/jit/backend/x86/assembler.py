import sys, os
import ctypes
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.history import Const, Box, BoxPtr, REF
from pypy.rpython.lltypesystem import lltype, rffi, ll2ctypes, rstr, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.tool.uid import fixid
from pypy.jit.backend.logger import Logger
from pypy.jit.backend.x86.regalloc import (RegAlloc, WORD, REGS, TempBox,
                                           lower_byte, stack_pos)
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.jit.backend.x86 import codebuf
from pypy.jit.backend.x86.ri386 import *
from pypy.jit.metainterp.resoperation import rop



# our calling convention - we pass first 6 args in registers
# and the rest stays on the stack

RET_BP = 5 # ret ip + bp + bx + esi + edi = 5 words

MAX_FAIL_BOXES = 1000
if sys.platform == 'darwin':
    # darwin requires the stack to be 16 bytes aligned on calls
    CALL_ALIGN = 4
else:
    CALL_ALIGN = 1


def align_stack_words(words):
    return (words + CALL_ALIGN - 1) & ~(CALL_ALIGN-1)

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
        self.logger = Logger(cpu.ts)
        self.fail_boxes_int = lltype.malloc(lltype.GcArray(lltype.Signed),
                                            MAX_FAIL_BOXES, zero=True)
        self.fail_boxes_ptr = lltype.malloc(lltype.GcArray(llmemory.GCREF),
                                            MAX_FAIL_BOXES, zero=True)

    def make_sure_mc_exists(self):
        if self.mc is None:
            rffi.cast(lltype.Signed, self.fail_boxes_int)   # workaround
            rffi.cast(lltype.Signed, self.fail_boxes_ptr)   # workaround
            self.fail_box_int_addr = rffi.cast(lltype.Signed,
                lltype.direct_arrayitems(self.fail_boxes_int))
            self.fail_box_ptr_addr = rffi.cast(lltype.Signed,
                lltype.direct_arrayitems(self.fail_boxes_ptr))

            self.logger.create_log()
            # the address of the function called by 'new'
            gc_ll_descr = self.cpu.gc_ll_descr
            gc_ll_descr.initialize()
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
            # done
            # we generate the loop body in 'mc'
            # 'mc2' is for guard recovery code
            self.mc = MachineCodeBlockWrapper()
            self.mc2 = MachineCodeBlockWrapper()

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

    def assemble_loop(self, loop):
        self.assemble(loop, loop.operations, None)

    def assemble_from_guard(self, tree, guard_op):
        newaddr = self.assemble(tree, guard_op.suboperations, guard_op)
        # patch the jump from original guard
        addr = guard_op._x86_addr
        mc = codebuf.InMemoryCodeBuilder(addr, addr + 128)
        mc.write(packimm32(newaddr - addr - 4))
        mc.done()

    def assemble(self, tree, operations, guard_op):
        # the last operation can be 'jump', 'return' or 'guard_pause';
        # a 'jump' can either close a loop, or end a bridge to some
        # previously-compiled code.
        self._compute_longest_fail_op(operations)
        self.tree = tree
        self.make_sure_mc_exists()
        newpos = self.mc.tell()
        regalloc = RegAlloc(self, tree, self.cpu.translate_support_code,
                            guard_op)
        self._regalloc = regalloc
        adr_lea = 0
        if guard_op is None:
            inputargs = tree.inputargs
            self.logger.log_loop(tree)
            regalloc.walk_operations(tree)
        else:
            inputargs = regalloc.inputargs
            self.logger.log_operations(inputargs, guard_op.suboperations, {})
            mc = self.mc._mc
            adr_lea = mc.tell()
            mc.LEA(esp, fixedsize_ebp_ofs(0))
            regalloc._walk_operations(operations)
        stack_depth = regalloc.max_stack_depth
        self.mc.done()
        self.mc2.done()
        # possibly align, e.g. for Mac OS X
        if guard_op is None:
            tree._x86_stack_depth = stack_depth
        else:
            if not we_are_translated():
                # for the benefit of tests
                guard_op._x86_bridge_stack_depth = stack_depth
            mc = codebuf.InMemoryCodeBuilder(adr_lea, adr_lea + 128)
            
            mc.LEA(esp, fixedsize_ebp_ofs(-(stack_depth + RET_BP - 2) * WORD))
            mc.done()
        if we_are_translated():
            self._regalloc = None   # else keep it around for debugging
        return newpos

    def assemble_bootstrap_code(self, jumpaddr, arglocs, args, framesize):
        self.make_sure_mc_exists()
        addr = self.mc.tell()
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
                if args[i].type == REF:
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
                if args[i].type == REF:
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

    def regalloc_perform(self, op, arglocs, resloc):
        genop_list[op.opnum](self, op, arglocs, resloc)

    def regalloc_perform_discard(self, op, arglocs):
        genop_discard_list[op.opnum](self, op, arglocs)

    def regalloc_perform_with_guard(self, op, guard_op, faillocs,
                                    arglocs, resloc):
        addr = self.implement_guard_recovery(guard_op, faillocs)
        genop_guard_list[op.opnum](self, op, guard_op, addr, arglocs,
                                   resloc)

    def regalloc_perform_guard(self, op, faillocs, arglocs, resloc):
        addr = self.implement_guard_recovery(op, faillocs)
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
            self.mc.PUSH(args[i])
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


    genop_guard_int_is_true = genop_guard_oononnull

    def genop_oononnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETNE(lower_byte(resloc))

    genop_int_is_true = genop_oononnull

    def genop_ooisnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETE(lower_byte(resloc))

    def genop_same_as(self, op, arglocs, resloc):
        self.mc.MOV(resloc, arglocs[0])
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
    genop_discard_setarrayitem_raw = genop_discard_setarrayitem_gc

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
        base_loc, ofs_loc = arglocs
        assert isinstance(ofs_loc, IMM32)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_loc.value))

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

    def genop_discard_jump(self, op, locs):
        self.mc.JMP(rel32(op.jump_target._x86_compiled))

    def genop_guard_guard_true(self, op, ign_1, addr, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(addr, op, self.mc.JZ)

    def genop_guard_guard_no_exception(self, op, ign_1, addr, locs, ign_2):
        self.mc.CMP(heap(self.cpu.pos_exception()), imm(0))
        self.implement_guard(addr, op, self.mc.JNZ)

    def genop_guard_guard_exception(self, op, ign_1, addr, locs, resloc):
        loc = locs[0]
        loc1 = locs[1]
        self.mc.MOV(loc1, heap(self.cpu.pos_exception()))
        self.mc.CMP(loc1, loc)
        self.implement_guard(addr, op, self.mc.JNE)
        if resloc is not None:
            self.mc.MOV(resloc, heap(self.cpu.pos_exc_value()))
        self.mc.MOV(heap(self.cpu.pos_exception()), imm(0))
        self.mc.MOV(heap(self.cpu.pos_exc_value()), imm(0))

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

    def implement_guard_recovery(self, guard_op, fail_locs):
        addr = self.mc2.tell()
        exc = (guard_op.opnum == rop.GUARD_EXCEPTION or
               guard_op.opnum == rop.GUARD_NO_EXCEPTION)
        guard_op._x86_faillocs = fail_locs
        # XXX horrible hack that allows us to preserve order
        #     of inputargs to bridge
        guard_op._fail_op = guard_op.suboperations[0]
        self.generate_failure(self.mc2, guard_op.suboperations[0], fail_locs,
                              exc)
        return addr

    def generate_failure(self, mc, op, locs, exc):
        assert op.opnum == rop.FAIL
        pos = mc.tell()
        for i in range(len(locs)):
            loc = locs[i]
            if isinstance(loc, REG):
                if op.args[i].type == REF:
                    base = self.fail_box_ptr_addr
                else:
                    base = self.fail_box_int_addr
                mc.MOV(addr_add(imm(base), imm(i*WORD)), loc)
        for i in range(len(locs)):
            loc = locs[i]
            if not isinstance(loc, REG):
                if op.args[i].type == REF:
                    base = self.fail_box_ptr_addr
                else:
                    base = self.fail_box_int_addr
                mc.MOV(eax, loc)
                mc.MOV(addr_add(imm(base), imm(i*WORD)), eax)
        if self.debug_markers:
            mc.MOV(eax, imm(pos))
            mc.MOV(addr_add(imm(self.fail_box_int_addr),
                                 imm(len(locs) * WORD)),
                                 eax)
        if exc:
            # note that we don't have to save and restore eax, ecx and edx here
            addr = self.cpu.get_save_exception_int()
            mc.CALL(rel32(addr))
        # don't break the following code sequence!
        mc = mc._mc
        mc.LEA(esp, addr_add(imm(0), ebp, (-RET_BP + 2) * WORD))
        guard_index = self.cpu.make_guard_index(op)
        mc.MOV(eax, imm(guard_index))
        mc.POP(edi)
        mc.POP(esi)
        mc.POP(ebx)
        mc.POP(ebp)
        mc.RET()

    @specialize.arg(3)
    def implement_guard(self, addr, guard_op, emit_jump):
        emit_jump(rel32(addr))
        guard_op._x86_addr = self.mc.tell() - 4

    def genop_call(self, op, arglocs, resloc):
        sizeloc = arglocs[0]
        assert isinstance(sizeloc, IMM32)
        size = sizeloc.value
        nargs = len(op.args)-1
        extra_on_stack = self.align_stack_for_call(nargs)
        for i in range(nargs+1, 1, -1):
            self.mc.PUSH(arglocs[i])
        if isinstance(op.args[0], Const):
            x = rel32(op.args[0].getint())
        else:
            x = arglocs[1]
        self.mc.CALL(x)
        self.mark_gc_roots()
        self.mc.ADD(esp, imm(WORD * extra_on_stack))
        if size == 1:
            self.mc.AND(eax, imm(0xff))
        elif size == 2:
            self.mc.AND(eax, imm(0xffff))

    genop_call_pure = genop_call

    def genop_discard_cond_call_gc_wb(self, op, arglocs):
        # use 'mc._mc' directly instead of 'mc', to avoid
        # bad surprizes if the code buffer is mostly full
        loc_cond = arglocs[0]
        loc_mask = arglocs[1]
        mc = self.mc._mc
        mc.TEST(loc_cond, loc_mask)
        mc.write('\x74\x00')             # JZ after_the_call
        jz_location = mc.get_relative_pos()
        # the following is supposed to be the slow path, so whenever possible
        # we choose the most compact encoding over the most efficient one.
        for i in range(len(arglocs)-1, 2, -1):
            mc.PUSH(arglocs[i])
        mc.CALL(rel32(op.args[2].getint()))
        pop_count = 0
        for i in range(3, len(arglocs)):
            loc = arglocs[i]
            pop_count += 1
            if isinstance(loc, REG):
                while pop_count > 0:
                    mc.POP(loc)
                    pop_count -= 1
        if pop_count:
            mc.ADD(esp, imm(WORD * pop_count))
        # patch the JZ above
        offset = mc.get_relative_pos() - jz_location
        assert 0 < offset <= 127
        mc.overwrite(jz_location-1, chr(offset))

    def not_implemented_op_discard(self, op, arglocs):
        print "not implemented operation: %s" % op.getopname()
        raise NotImplementedError

    def not_implemented_op(self, op, arglocs, resloc):
        print "not implemented operation with res: %s" % op.getopname()
        raise NotImplementedError

    def not_implemented_op_guard(self, op, regalloc, arglocs, resloc, descr):
        print "not implemented operation (guard): %s" % op.getopname()
        raise NotImplementedError

    def mark_gc_roots(self):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            mark = self._regalloc.get_mark_gc_roots(gcrootmap)
            gcrootmap.put(rffi.cast(llmemory.Address, self.mc.tell()), mark)


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
