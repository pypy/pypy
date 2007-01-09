import sys, py, os
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.i386.codebuf import CodeBlockOverflow
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.rlib import objectmodel
from pypy.rpython.annlowlevel import llhelper

WORD = 4
DEBUG_CALL_ALIGN = True
if sys.platform == 'darwin':
    CALL_ALIGN = 4
else:
    CALL_ALIGN = 1

class Var(GenVar):

    def __init__(self, stackpos):
        # 'stackpos' is an index relative to the pushed arguments
        # (where N is the number of arguments of the function
        #  and B is a small integer for stack alignment purposes):
        #
        # B + 0  = last arg
        #        = ...
        # B +N-1 = 1st arg
        # B + N  = return address
        # B +N+1 = local var
        # B +N+2 = ...
        #          ...              <--- esp+4
        #          local var        <--- esp
        #
        self.stackpos = stackpos

    def operand(self, builder):
        return builder.stack_access(self.stackpos)

    def nonimmoperand(self, builder, tmpregister):
        return self.operand(builder)

    def __repr__(self):
        return 'var@%d' % (self.stackpos,)

    repr = __repr__


##class Const(GenConst):

##    def revealconst(self, TYPE):
##        if isinstance(self, IntConst):
##            self.revealconst_int(TYPE)
##        elif isinstance(self, PtrConst):
##            self.revealconst_ptr(TYPE)
        
##        if isinstance(TYPE, lltype.Ptr):
##            if isinstance(self, PtrConst):
##                return self.revealconst_ptr(TYPE)
##            el
##                return self.revealconst_ptr(TYPE)
##        elif TYPE is lltype.Float:
##            assert isinstance(self, DoubleConst)
##            return self.revealconst_double()
##        else:
##            assert isinstance(TYPE, lltype.Primitive)
##            assert TYPE is not lltype.Void, "cannot make red boxes of voids"
##            assert isinstance(self, IntConst)
##            return self.revealconst_primitive(TYPE)
##        return self.value
##    revealconst._annspecialcase_ = 'specialize:arg(1)'


class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def operand(self, builder):
        return imm(self.value)

    def nonimmoperand(self, builder, tmpregister):
        builder.mc.MOV(tmpregister, self.operand(builder))
        return tmpregister

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

    def __repr__(self):
        "NOT_RPYTHON"
        try:
            return "const=%s" % (imm(self.value).assembler(),)
        except TypeError:   # from Symbolics
            return "const=%r" % (self.value,)

    def repr(self):
        return "const=$%s" % (self.value,)


##class FnPtrConst(IntConst):
##    def __init__(self, value, mc):
##        self.value = value
##        self.mc = mc    # to keep it alive


class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

    def operand(self, builder):
        return imm(llmemory.cast_adr_to_int(self.addr))

    def nonimmoperand(self, builder, tmpregister):
        builder.mc.MOV(tmpregister, self.operand(builder))
        return tmpregister

    @specialize.arg(1)
    def revealconst(self, T):
        if T is llmemory.Address:
            return self.addr
        elif isinstance(T, lltype.Ptr):
            return llmemory.cast_adr_to_ptr(self.addr, T)
        elif T is lltype.Signed:
            return llmemory.cast_adr_to_int(self.addr)
        else:
            assert 0, "XXX not implemented"

    def __repr__(self):
        "NOT_RPYTHON"
        return "const=%r" % (self.addr,)

    def repr(self):
        return "const=<0x%x>" % (llmemory.cast_adr_to_int(self.addr),)


class Label(GenLabel):

    def __init__(self, startaddr, arg_positions, stackdepth):
        self.startaddr = startaddr
        self.arg_positions = arg_positions
        self.stackdepth = stackdepth


class FlexSwitch(CodeGenSwitch):

    def __init__(self, rgenop):
        self.rgenop = rgenop
        self.default_case_builder = None
        self.default_case_key = 0
        self._je_key = 0

    def initialize(self, builder, gv_exitswitch):
        mc = builder.mc
        mc.MOV(eax, gv_exitswitch.operand(builder))
        self.saved_state = builder._save_state()
        self._reserve(mc)

    def _reserve(self, mc):
        RESERVED = 11*4+5      # XXX quite a lot for now :-/
        pos = mc.tell()
        mc.UD2()
        mc.write('\x00' * (RESERVED-1))
        self.nextfreepos = pos
        self.endfreepos = pos + RESERVED

    def _reserve_more(self):
        start = self.nextfreepos
        end   = self.endfreepos
        newmc = self.rgenop.open_mc()
        self._reserve(newmc)
        self.rgenop.close_mc(newmc)
        fullmc = self.rgenop.InMemoryCodeBuilder(start, end)
        fullmc.JMP(rel32(self.nextfreepos))
        fullmc.done()
        
    def add_case(self, gv_case):
        rgenop = self.rgenop
        targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        try:
            self._add_case(gv_case, targetbuilder)
        except CodeBlockOverflow:
            self._reserve_more()
            self._add_case(gv_case, targetbuilder)
        targetbuilder._open()
        return targetbuilder
    
    def _add_case(self, gv_case, targetbuilder):
        # XXX this code needs to be simplified, now that we always
        # have a default case
        start = self.nextfreepos
        end   = self.endfreepos
        mc = self.rgenop.InMemoryCodeBuilder(start, end)
        mc.CMP(eax, gv_case.operand(None))
        self._je_key = targetbuilder.come_from(mc, 'JE', self._je_key)
        pos = mc.tell()
        if self.default_case_builder:
            self.default_case_key = self.default_case_builder.come_from(
                mc, 'JMP', self.default_case_key)
        else:
            illegal_start = mc.tell()
            mc.JMP(rel32(0))
            ud2_addr = mc.tell()
            mc.UD2()
            illegal_mc = self.rgenop.InMemoryCodeBuilder(illegal_start, end)
            illegal_mc.JMP(rel32(ud2_addr))
        mc.done()
        self._je_key = 0
        self.nextfreepos = pos

    def _add_default(self):
        rgenop = self.rgenop
        targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        self.default_case_builder = targetbuilder
        start = self.nextfreepos
        end   = self.endfreepos
        mc = self.rgenop.InMemoryCodeBuilder(start, end)
        self.default_case_key = targetbuilder.come_from(mc, 'JMP')
        targetbuilder._open()
        return targetbuilder

class Builder(GenBuilder):

    def __init__(self, rgenop, stackdepth):
        self.rgenop = rgenop
        self.stackdepth = stackdepth
        self.mc = None
        self._pending_come_from = {}
        self.start = 0
        self.closed = False
        self.tail = (0, 0)

    def _open(self):
        if self.mc is None and not self.closed:
            self.mc = self.rgenop.open_mc()
            if not self.start:
                # This is the first open. remember the start address
                # and patch all come froms.
                self.start = self.mc.tell()
                come_froms = self._pending_come_from
                self._pending_come_from = None
                for start, (end, insn) in come_froms.iteritems():
                    if end == self.start:
                        # there was a pending JMP just before self.start,
                        # so we can as well overwrite the JMP and start writing
                        # code directly there
                        self.mc.seekback(end - start)
                        self.start = start
                        break
                for start, (end, insn) in come_froms.iteritems():
                    if start != self.start:
                        mc = self.rgenop.InMemoryCodeBuilder(start, end)
                        self._emit_come_from(mc, insn, self.start)
                        mc.done()
            else:
                # We have been paused and are being opened again.
                # Is the new codeblock immediately after the previous one?
                prevstart, prevend = self.tail
                curpos = self.mc.tell()
                if prevend == curpos:
                    # Yes. We can overwrite the JMP and just continue writing
                    # code directly there
                    self.mc.seekback(prevend - prevstart)
                else:
                    # No. Patch the jump at the end of the previous codeblock.
                    mc = self.rgenop.InMemoryCodeBuilder(prevstart, prevend)
                    mc.JMP(rel32(curpos))
                    mc.done()

    def pause_writing(self, alive_vars_gv):
        if self.mc is not None:
            start = self.mc.tell()
            self.mc.JMP(rel32(0))
            end = self.mc.tell()
            self.tail = (start, end)
            self.mc.done()
            self.rgenop.close_mc(self.mc)
            self.mc = None
        return self
        
    def start_writing(self):
        self._open()
        
    def _emit_come_from(self, mc, insn, addr):
        if insn == 'JMP':
            mc.JMP(rel32(addr))
        elif insn == 'JE':
            mc.JE(rel32(addr))
        elif insn == 'JNE':
            mc.JNE(rel32(addr))
        else:
            raise ValueError('Unsupported jump')
        
    def come_from(self, mc, insn, key=0):
        start = mc.tell()
        if self._pending_come_from is None:
            self._emit_come_from(mc, insn, self.start)
        else:
            self._emit_come_from(mc, insn, 0)
            end = mc.tell()
            if key != 0:
                del self._pending_come_from[key]
            self._pending_come_from[start] = (end, insn)
        return start
    
    def end(self):
        pass

    def _write_prologue(self, sigtoken):
        self._open()
        numargs = sigtoken     # for now
        #self.mc.BREAKPOINT()
        # self.stackdepth-1 is the return address; the arguments
        # come just before
        return [Var(self.stackdepth-2-n) for n in range(numargs)]

    def _close(self):
        self.closed = True
        self.mc.done()
        self.rgenop.close_mc(self.mc)
        self.mc = None

    def _fork(self):
        return self.rgenop.newbuilder(self.stackdepth)

    def _save_state(self):
        return self.stackdepth

    @staticmethod
    def _new_from_state(rgenop, stackdepth):
        return rgenop.newbuilder(stackdepth)

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def genop_getfield(self, (offset, fieldsize), gv_ptr):
        self.mc.MOV(edx, gv_ptr.operand(self))
        if fieldsize == WORD:
            op = mem(edx, offset)
        else:
            if fieldsize == 1:
                op = mem8(edx, offset)
            else:
                assert fieldsize == 2
                op = mem(edx, offset)
            self.mc.MOVZX(eax, op)
            op = eax
        return self.returnvar(op)

    def genop_setfield(self, (offset, fieldsize), gv_ptr, gv_value):
        self.mc.MOV(eax, gv_value.operand(self))
        self.mc.MOV(edx, gv_ptr.operand(self))
        if fieldsize == 1:
            self.mc.MOV(mem8(edx, offset), al)
        else:
            if fieldsize == 2:
                self.mc.o16()    # followed by the MOV below
            else:
                assert fieldsize == WORD
            self.mc.MOV(mem(edx, offset), eax)

    def genop_getsubstruct(self, (offset, fieldsize), gv_ptr):
        self.mc.MOV(edx, gv_ptr.operand(self))
        self.mc.LEA(eax, mem(edx, offset))
        return self.returnvar(eax)

    def itemaddr(self, base, arraytoken, gv_index):
        # uses ecx
        lengthoffset, startoffset, itemoffset = arraytoken
        if itemoffset == 1:
            memSIBx = memSIB8
        else:
            memSIBx = memSIB
        if isinstance(gv_index, IntConst):
            startoffset += itemoffset * gv_index.value
            op = memSIBx(base, None, 0, startoffset)
        elif itemoffset in SIZE2SHIFT:
            self.mc.MOV(ecx, gv_index.operand(self))
            op = memSIBx(base, ecx, SIZE2SHIFT[itemoffset], startoffset)
        else:
            self.mc.IMUL(ecx, gv_index.operand(self), imm(itemoffset))
            op = memSIBx(base, ecx, 0, startoffset)
        return op

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        self.mc.MOV(edx, gv_ptr.operand(self))
        op = self.itemaddr(edx, arraytoken, gv_index)
        _, _, itemsize = arraytoken
        if itemsize != WORD:
            assert itemsize == 1 or itemsize == 2
            self.mc.MOVZX(eax, op)
            op = eax
        return self.returnvar(op)

    def genop_getarraysubstruct(self, arraytoken, gv_ptr, gv_index):
        self.mc.MOV(edx, gv_ptr.operand(self))
        op = self.itemaddr(edx, arraytoken, gv_index)
        self.mc.LEA(eax, op)
        return self.returnvar(eax)

    def genop_getarraysize(self, arraytoken, gv_ptr):
        lengthoffset, startoffset, itemoffset = arraytoken
        self.mc.MOV(edx, gv_ptr.operand(self))
        return self.returnvar(mem(edx, lengthoffset))

    def genop_setarrayitem(self, arraytoken, gv_ptr, gv_index, gv_value):
        self.mc.MOV(eax, gv_value.operand(self))
        self.mc.MOV(edx, gv_ptr.operand(self))
        destop = self.itemaddr(edx, arraytoken, gv_index)
        _, _, itemsize = arraytoken
        if itemsize != WORD:
            if itemsize == 1:
                self.mc.MOV(destop, al)
                return
            elif itemsize == 2:
                self.mc.o16()    # followed by the MOV below
            else:
                raise AssertionError
        self.mc.MOV(destop, eax)

    def genop_malloc_fixedsize(self, size):
        # XXX boehm only, no atomic/non atomic distinction for now
        self.push(imm(size))
        self.mc.CALL(rel32(gc_malloc_fnaddr()))
        return self.returnvar(eax)

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        # XXX boehm only, no atomic/non atomic distinction for now
        # XXX no overflow checking for now
        op_size = self.itemaddr(None, varsizealloctoken, gv_size)
        self.mc.LEA(edx, op_size)
        self.push(edx)
        self.mc.CALL(rel32(gc_malloc_fnaddr()))
        lengthoffset, _, _ = varsizealloctoken
        self.mc.MOV(ecx, gv_size.operand(self))
        self.mc.MOV(mem(eax, lengthoffset), ecx)
        return self.returnvar(eax)
        
    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        numargs = sigtoken      # for now
        MASK = CALL_ALIGN-1
        if MASK:
            final_depth = self.stackdepth + numargs
            delta = ((final_depth+MASK)&~MASK)-final_depth
            if delta:
                self.mc.SUB(esp, imm(delta*WORD))
                self.stackdepth += delta
        for i in range(numargs-1, -1, -1):
            gv_arg = args_gv[i]
            self.push(gv_arg.operand(self))
        if DEBUG_CALL_ALIGN:
            self.mc.MOV(eax, esp)
            self.mc.AND(eax, imm8((WORD*CALL_ALIGN)-1))
            self.mc.ADD(eax, imm32(sys.maxint))   # overflows unless eax == 0
            self.mc.INTO()
        if gv_fnptr.is_const:
            target = gv_fnptr.revealconst(lltype.Signed)
            self.mc.CALL(rel32(target))
        else:
            self.mc.CALL(gv_fnptr.operand(self))
        # XXX only for int return_kind, check calling conventions
        return self.returnvar(eax)

    def genop_same_as(self, kind, gv_x):
        if gv_x.is_const:    # must always return a var
            return self.returnvar(gv_x.operand(self))
        else:
            return gv_x

    def genop_debug_pdb(self):    # may take an args_gv later
        self.mc.BREAKPOINT()

    def enter_next_block(self, kinds, args_gv):
        self._open()
        arg_positions = []
        seen = {}
        for i in range(len(args_gv)):
            gv = args_gv[i]
            # turn constants into variables; also make copies of vars that
            # are duplicate in args_gv
            if not isinstance(gv, Var) or gv.stackpos in seen:
                gv = args_gv[i] = self.returnvar(gv.operand(self))
            # remember the var's position in the stack
            arg_positions.append(gv.stackpos)
            seen[gv.stackpos] = None
        return Label(self.mc.tell(), arg_positions, self.stackdepth)

    def jump_if_false(self, gv_condition, args_gv):
        targetbuilder = self._fork()
        self.mc.CMP(gv_condition.operand(self), imm8(0))
        targetbuilder.come_from(self.mc, 'JE')
        return targetbuilder

    def jump_if_true(self, gv_condition, args_gv):
        targetbuilder = self._fork()
        self.mc.CMP(gv_condition.operand(self), imm8(0))
        targetbuilder.come_from(self.mc, 'JNE')
        return targetbuilder

    def finish_and_return(self, sigtoken, gv_returnvar):
        self._open()
        initialstackdepth = self.rgenop._initial_stack_depth(sigtoken)
        self.mc.MOV(eax, gv_returnvar.operand(self))
        self.mc.ADD(esp, imm(WORD * (self.stackdepth - initialstackdepth)))
        self.mc.RET()
        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        self._open()
        remap_stack_layout(self, outputargs_gv, target)
        self.mc.JMP(rel32(target.startaddr))
        self._close()

    def flexswitch(self, gv_exitswitch, args_gv):
        result = FlexSwitch(self.rgenop)
        result.initialize(self, gv_exitswitch)
        self._close()
        return result, result._add_default()

    def show_incremental_progress(self):
        pass

    def log(self, msg):
        self.mc.log(msg)

    # ____________________________________________________________

    def stack_access(self, stackpos):
        return mem(esp, WORD * (self.stackdepth-1 - stackpos))

    def push(self, op):
        self.mc.PUSH(op)
        self.stackdepth += 1

    def returnvar(self, op):
        res = Var(self.stackdepth)
        self.push(op)
        return res

    @staticmethod
    def identity(gv_x):
        return gv_x

    op_int_is_true = identity

    def op_int_add(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.ADD(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_sub(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.SUB(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_mul(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.IMUL(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_floordiv(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CDQ()
        self.mc.IDIV(gv_y.nonimmoperand(self, ecx))
        return self.returnvar(eax)

    def op_int_mod(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CDQ()
        self.mc.IDIV(gv_y.nonimmoperand(self, ecx))
        return self.returnvar(edx)

    def op_int_and(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.AND(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_or(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.OR(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_xor(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.XOR(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_lt(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETL(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_le(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETLE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_eq(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_ne(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETNE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_gt(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETG(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_ge(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETGE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_neg(self, gv_x):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.NEG(eax)
        return self.returnvar(eax)

    def op_int_abs(self, gv_x):
        self.mc.MOV(eax, gv_x.operand(self))
        # ABS-computing code from Psyco, found by exhaustive search
        # on *all* short sequences of operations :-)
        self.mc.ADD(eax, eax)
        self.mc.SBB(eax, gv_x.operand(self))
        self.mc.SBB(edx, edx)
        self.mc.XOR(eax, edx)
        return self.returnvar(eax)

    def op_int_invert(self, gv_x):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.NOT(eax)
        return self.returnvar(eax)

    def op_int_lshift(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))   # XXX check if ecx >= 32
        self.mc.SHL(eax, cl)
        return self.returnvar(eax)

    def op_int_rshift(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))   # XXX check if ecx >= 32
        self.mc.SAR(eax, cl)
        return self.returnvar(eax)

    op_uint_is_true = op_int_is_true
    op_uint_invert  = op_int_invert
    op_uint_add     = op_int_add
    op_uint_sub     = op_int_sub

    def op_uint_mul(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MUL(gv_y.nonimmoperand(self, edx))
        return self.returnvar(eax)

    def op_uint_floordiv(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.XOR(edx, edx)
        self.mc.DIV(gv_y.nonimmoperand(self, ecx))
        return self.returnvar(eax)

    def op_uint_mod(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.XOR(edx, edx)
        self.mc.DIV(gv_y.nonimmoperand(self, ecx))
        return self.returnvar(edx)

    def op_uint_lt(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETB(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_uint_le(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETBE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    op_uint_eq = op_int_eq
    op_uint_ne = op_int_ne

    def op_uint_gt(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETA(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_uint_ge(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETAE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    op_uint_and    = op_int_and
    op_uint_or     = op_int_or
    op_uint_xor    = op_int_xor
    op_uint_lshift = op_int_lshift

    def op_uint_rshift(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))   # XXX check if ecx >= 32
        self.mc.SHR(eax, cl)
        return self.returnvar(eax)

    def op_bool_not(self, gv_x):
        self.mc.CMP(gv_x.operand(self), imm8(0))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_cast_bool_to_int(self, gv_x):
        self.mc.CMP(gv_x.operand(self), imm8(0))
        self.mc.SETNE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    op_cast_bool_to_uint   = op_cast_bool_to_int

    op_cast_char_to_int    = identity
    op_cast_unichar_to_int = identity
    op_cast_int_to_char    = identity
    op_cast_int_to_unichar = identity
    op_cast_int_to_uint    = identity
    op_cast_uint_to_int    = identity
    op_cast_ptr_to_int     = identity
    op_cast_int_to_ptr     = identity

    op_char_lt = op_int_lt
    op_char_le = op_int_le
    op_char_eq = op_int_eq
    op_char_ne = op_int_ne
    op_char_gt = op_int_gt
    op_char_ge = op_int_ge

    op_unichar_eq = op_int_eq
    op_unichar_ne = op_int_ne

    op_ptr_nonzero = op_int_is_true
    op_ptr_iszero  = op_bool_not        # for now
    op_ptr_eq      = op_int_eq
    op_ptr_ne      = op_int_ne


SIZE2SHIFT = {1: 0,
              2: 1,
              4: 2,
              8: 3}

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], llmemory.Address))

def gc_malloc(size):
    from pypy.rpython.lltypesystem.lloperation import llop
    return llop.call_boehm_gc_alloc(llmemory.Address, size)

def gc_malloc_fnaddr():
    """Returns the address of the Boehm 'malloc' function."""
    if objectmodel.we_are_translated():
        gc_malloc_ptr = llhelper(GC_MALLOC, gc_malloc)
        return lltype.cast_ptr_to_int(gc_malloc_ptr)
    else:
        # <pedronis> don't do this at home
        import threading
        if not isinstance(threading.currentThread(), threading._MainThread):
            import py
            py.test.skip("must run in the main thread")
        try:
            from ctypes import cast, c_void_p
            from pypy.rpython.rctypes.tool import util
            path = util.find_library('gc')
            if path is None:
                raise ImportError("Boehm (libgc) not found")
            boehmlib = util.load_library(path)
        except ImportError, e:
            import py
            py.test.skip(str(e))
        else:
            GC_malloc = boehmlib.GC_malloc
            return cast(GC_malloc, c_void_p).value

# ____________________________________________________________

def remap_stack_layout(builder, outputargs_gv, target):
##    import os
##    s = ', '.join([gv.repr() for gv in outputargs_gv])
##    os.write(2, "writing at %d (stack=%d, [%s])\n  --> %d (stack=%d, %s)\n"
##     % (builder.mc.tell(),
##        builder.stackdepth,
##        s,
##        target.startaddr,
##        target.stackdepth,
##        target.arg_positions))

    N = target.stackdepth
    if builder.stackdepth < N:
        builder.mc.SUB(esp, imm(WORD * (N - builder.stackdepth)))
        builder.stackdepth = N

    M = len(outputargs_gv)
    arg_positions = target.arg_positions
    assert M == len(arg_positions)
    targetlayout = [None] * N
    srccount = [-N] * N
    for i in range(M):
        pos = arg_positions[i]
        gv = outputargs_gv[i]
        assert targetlayout[pos] is None
        targetlayout[pos] = gv
        srccount[pos] = 0
    pending_dests = M
    for i in range(M):
        targetpos = arg_positions[i]
        gv = outputargs_gv[i]
        if isinstance(gv, Var):
            p = gv.stackpos
            if 0 <= p < N:
                if p == targetpos:
                    srccount[p] = -N     # ignore 'v=v'
                    pending_dests -= 1
                else:
                    srccount[p] += 1

    while pending_dests:
        progress = False
        for i in range(N):
            if srccount[i] == 0:
                srccount[i] = -1
                pending_dests -= 1
                gv_src = targetlayout[i]
                if isinstance(gv_src, Var):
                    p = gv_src.stackpos
                    if 0 <= p < N:
                        srccount[p] -= 1
                builder.mc.MOV(eax, gv_src.operand(builder))
                builder.mc.MOV(builder.stack_access(i), eax)
                progress = True
        if not progress:
            # we are left with only pure disjoint cycles; break them
            for i in range(N):
                if srccount[i] >= 0:
                    dst = i
                    builder.mc.MOV(edx, builder.stack_access(dst))
                    while True:
                        assert srccount[dst] == 1
                        srccount[dst] = -1
                        pending_dests -= 1
                        gv_src = targetlayout[dst]
                        assert isinstance(gv_src, Var)
                        src = gv_src.stackpos
                        assert 0 <= src < N
                        if src == i:
                            break
                        builder.mc.MOV(eax, builder.stack_access(src))
                        builder.mc.MOV(builder.stack_access(dst), eax)
                        dst = src
                    builder.mc.MOV(builder.stack_access(dst), edx)
            assert pending_dests == 0

    if builder.stackdepth > N:
        builder.mc.ADD(esp, imm(WORD * (builder.stackdepth - N)))
        builder.stackdepth = N


#

dummy_var = Var(0)

class ReplayFlexSwitch(CodeGenSwitch):

    def __init__(self, replay_builder):
        self.replay_builder = replay_builder

    def add_case(self, gv_case):
        return self.replay_builder

class ReplayBuilder(GenBuilder):

    def __init__(self, rgenop):
        self.rgenop = rgenop

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        return dummy_var

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        return dummy_var

    def genop_getfield(self, fieldtoken, gv_ptr):
        return dummy_var

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        return dummy_var

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        return dummy_var

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        return dummy_var

    def genop_getarraysubstruct(self, arraytoken, gv_ptr, gv_index):
        return dummy_var

    def genop_getarraysize(self, arraytoken, gv_ptr):
        return dummy_var

    def genop_setarrayitem(self, arraytoken, gv_ptr, gv_index, gv_value):
        return dummy_var

    def genop_malloc_fixedsize(self, size):
        return dummy_var

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        return dummy_var
        
    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        return dummy_var

    def genop_same_as(self, kind, gv_x):
        return dummy_var

    def genop_debug_pdb(self):    # may take an args_gv later
        pass

    def enter_next_block(self, kinds, args_gv):
        return None

    def jump_if_false(self, gv_condition, args_gv):
        return self

    def jump_if_true(self, gv_condition, args_gv):
        return self

    def finish_and_return(self, sigtoken, gv_returnvar):
        pass

    def finish_and_goto(self, outputargs_gv, target):
        pass

    def flexswitch(self, gv_exitswitch, args_gv):
        flexswitch = ReplayFlexSwitch(self)
        return flexswitch, self

    def show_incremental_progress(self):
        pass

class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
    from pypy.jit.codegen.i386.codebuf import InMemoryCodeBuilder

    MC_SIZE = 65536
    
    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing
        self.keepalive_gc_refs = [] 
        self.total_code_blocks = 0

    def open_mc(self):
        if self.mcs:
            # XXX think about inserting NOPS for alignment
            return self.mcs.pop()
        else:
            # XXX supposed infinite for now
            self.total_code_blocks += 1
            return self.MachineCodeBlock(self.MC_SIZE)

    def close_mc(self, mc):
        # an open 'mc' is ready for receiving code... but it's also ready
        # for being garbage collected, so be sure to close it if you
        # want the generated code to stay around :-)
        self.mcs.append(mc)

    def check_no_open_mc(self):
        assert len(self.mcs) == self.total_code_blocks

    def newbuilder(self, stackdepth):
        return Builder(self, stackdepth)

    def newgraph(self, sigtoken, name):
        builder = self.newbuilder(self._initial_stack_depth(sigtoken))
        builder._open() # Force builder to have an mc
        entrypoint = builder.mc.tell()
        inputargs_gv = builder._write_prologue(sigtoken)
        return builder, IntConst(entrypoint), inputargs_gv

    def _initial_stack_depth(self, sigtoken):
        # If a stack depth is a multiple of CALL_ALIGN then the
        # arguments are correctly aligned for a call.  We have to
        # precompute initialstackdepth to guarantee that.  For OS/X the
        # convention is that the stack should be aligned just after all
        # arguments are pushed, i.e. just before the return address is
        # pushed by the CALL instruction.  In other words, after
        # 'numargs' arguments have been pushed the stack is aligned:
        numargs = sigtoken          # for now
        MASK = CALL_ALIGN - 1
        initialstackdepth = ((numargs+MASK)&~MASK) + 1
        return initialstackdepth

    def replay(self, label, kinds):
        return ReplayBuilder(self), [dummy_var] * len(kinds)

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            if T.TO._gckind == 'gc':
                self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            assert 0, "XXX not implemented"
    
    # attached later constPrebuiltGlobal = global_rgenop.genconst

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        FIELD = getattr(T, name)
        if isinstance(FIELD, lltype.ContainerType):
            fieldsize = 0      # not useful for getsubstruct
        else:
            fieldsize = llmemory.sizeof(FIELD)
        return (llmemory.offsetof(T, name), fieldsize)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(T):
        if isinstance(T, lltype.Array):
            return RI386GenOp.arrayToken(T)
        else:
            # var-sized structs
            arrayfield = T._arrayfld
            ARRAYFIELD = getattr(T, arrayfield)
            arraytoken = RI386GenOp.arrayToken(ARRAYFIELD)
            length_offset, items_offset, item_size = arraytoken
            arrayfield_offset = llmemory.offsetof(T, arrayfield)
            return (arrayfield_offset+length_offset,
                    arrayfield_offset+items_offset,
                    item_size)

    @staticmethod
    @specialize.memo()    
    def arrayToken(A):
        return (llmemory.ArrayLengthOffset(A),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF))

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        if T is lltype.Float:
            py.test.skip("not implemented: floats in the i386 back-end")
        return None     # for now

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        numargs = 0
        for ARG in FUNCTYPE.ARGS:
            if ARG is not lltype.Void:
                numargs += 1
        return numargs     # for now

    @staticmethod
    def erasedType(T):
        if T is llmemory.Address:
            return llmemory.Address
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, lltype.Ptr):
            return llmemory.GCREF
        else:
            assert 0, "XXX not implemented"

global_rgenop = RI386GenOp()
RI386GenOp.constPrebuiltGlobal = global_rgenop.genconst
