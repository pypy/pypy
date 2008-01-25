import py
import ctypes
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.model import ReplayBuilder, dummy_var
from pypy.jit.codegen.i386.codebuf import CodeBlockOverflow
from pypy.jit.codegen.i386.operation import *
from pypy.jit.codegen.i386.regalloc import RegAllocator, DEBUG_STACK
from pypy.jit.codegen.i386.regalloc import gv_frame_base, StorageInStack
from pypy.jit.codegen.i386.regalloc import Place, OpAbsorbPlace, OpTouch
from pypy.jit.codegen.i386.regalloc import write_stack_reserve, write_stack_adj
from pypy.jit.codegen import conftest
from pypy.rpython.annlowlevel import llhelper

DEBUG_TRAP = conftest.option.trap

# ____________________________________________________________

class AbstractConst(GenConst):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        "NOT_RPYTHON"
        try:
            return "const=%s" % (imm(self.value).assembler(),)
        except TypeError:   # from Symbolics
            return "const=%r" % (self.value,)

    def repr(self):
        return "const=$%s" % (self.value,)

class IntConst(AbstractConst):
    @specialize.arg(1)
    def revealconst(self, T):
        return cast_int_to_whatever(T, self.value)

class FloatConst(AbstractConst):
    @specialize.arg(1)
    def revealconst(self, T):
        return cast_float_to_whatever(T, self.value)

class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

    @specialize.arg(1)
    def revealconst(self, T):
        return cast_adr_to_whatever(T, self.addr)

    def __repr__(self):
        "NOT_RPYTHON"
        return "const=%r" % (self.addr,)

    def repr(self):
        return "const=<0x%x>" % (llmemory.cast_adr_to_int(self.addr),)

@specialize.arg(0)
def cast_int_to_whatever(T, value):
    if isinstance(T, lltype.Ptr):
        return lltype.cast_int_to_ptr(T, value)
    elif T is llmemory.Address:
        return llmemory.cast_int_to_adr(value)
    else:
        return lltype.cast_primitive(T, value)

@specialize.arg(0)
def cast_float_to_whatever(T, value):
    if T is lltype.Signed:
        return lltype.cast_float_to_int(value)
    elif T is lltype.Float:
        return value
    else:
        raise NotImplementedError

@specialize.arg(0)
def cast_whatever_to_int(T, value):
    if isinstance(T, lltype.Ptr):
        return lltype.cast_ptr_to_int(value)
    elif T is llmemory.Address:
        return llmemory.cast_adr_to_int(value)
    else:
        return lltype.cast_primitive(lltype.Signed, value)

@specialize.arg(0)
def cast_adr_to_whatever(T, addr):
    if T is llmemory.Address:
        return addr
    elif isinstance(T, lltype.Ptr):
        return llmemory.cast_adr_to_ptr(addr, T)
    elif T is lltype.Signed:
        return llmemory.cast_adr_to_int(addr)
    else:
        assert 0, "XXX not implemented"

# ____________________________________________________________

class FlexSwitch(CodeGenSwitch):

    def __init__(self, rgenop, graphctx, reg, inputargs_gv, inputoperands):
        self.rgenop = rgenop
        self.graphctx = graphctx
        self.reg = reg
        self.inputargs_gv = inputargs_gv
        self.inputoperands = inputoperands
        self.defaultcaseaddr = 0

    def initialize(self, mc):
        self.graphctx.write_stack_adj(mc, initial=False)
        self._reserve(mc)
        default_builder = Builder(self.rgenop, self.graphctx,
                                  self.inputargs_gv, self.inputoperands)
        start = self.nextfreepos
        end   = self.endfreepos
        fullmc = self.rgenop.InMemoryCodeBuilder(start, end)
        default_builder.set_coming_from(fullmc)
        fullmc.done()
        default_builder.update_defaultcaseaddr_of = self
        default_builder.start_writing()
        return default_builder

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
        targetbuilder = Builder(self.rgenop, self.graphctx,
                                self.inputargs_gv, self.inputoperands)
        try:
            self._add_case(gv_case, targetbuilder)
        except CodeBlockOverflow:
            self._reserve_more()
            self._add_case(gv_case, targetbuilder)
        targetbuilder.start_writing()
        return targetbuilder
    
    def _add_case(self, gv_case, targetbuilder):
        start = self.nextfreepos
        end   = self.endfreepos
        mc = self.rgenop.InMemoryCodeBuilder(start, end)
        value = gv_case.revealconst(lltype.Signed)
        mc.CMP(self.reg, imm(value))
        targetbuilder.set_coming_from(mc, Conditions['E'])
        pos = mc.tell()
        assert self.defaultcaseaddr != 0
        mc.JMP(rel32(self.defaultcaseaddr))
        mc.done()
        self.nextfreepos = pos

# ____________________________________________________________

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], llmemory.Address))

def gc_malloc(size):
    from pypy.rpython.lltypesystem.lloperation import llop
    return llop.call_boehm_gc_alloc(llmemory.Address, size)

def gc_malloc_fnaddr():
    """Returns the address of the Boehm 'malloc' function."""
    if we_are_translated():
        gc_malloc_ptr = llhelper(GC_MALLOC, gc_malloc)
        return lltype.cast_ptr_to_int(gc_malloc_ptr)
    else:
        # <pedronis> don't do this at home
        import threading
        if not isinstance(threading.currentThread(), threading._MainThread):
            import py
            py.test.skip("must run in the main thread")
        try:
            from ctypes import cast, c_void_p, util
            path = util.find_library('gc')
            if path is None:
                raise ImportError("Boehm (libgc) not found")
            boehmlib = ctypes.cdll.LoadLibrary(path)
        except ImportError, e:
            import py
            py.test.skip(str(e))
        else:
            GC_malloc = boehmlib.GC_malloc
            return cast(GC_malloc, c_void_p).value

def peek_word_at(addr):
    # now the Very Obscure Bit: when translated, 'addr' is an
    # address.  When not, it's an integer.  It just happens to
    # make the test pass, but that's probably going to change.
    if we_are_translated():
        return addr.signed[0]
    else:
        from ctypes import cast, c_void_p, c_int, POINTER
        p = cast(c_void_p(addr), POINTER(c_int))
        return p[0]

def poke_word_into(addr, value):
    # now the Very Obscure Bit: when translated, 'addr' is an
    # address.  When not, it's an integer.  It just happens to
    # make the test pass, but that's probably going to change.
    if we_are_translated():
        addr.signed[0] = value
    else:
        from ctypes import cast, c_void_p, c_int, POINTER
        p = cast(c_void_p(addr), POINTER(c_int))
        p[0] = value

# ____________________________________________________________

class Builder(GenBuilder):
    coming_from = 0
    update_defaultcaseaddr_of = None
    paused_alive_gv = None
    order_dependency = None
    keepalives_gv = None

    def __init__(self, rgenop, graphctx, inputargs_gv, inputoperands):
        self.rgenop = rgenop
        self.graphctx = graphctx
        self.inputargs_gv = inputargs_gv
        self.inputoperands = inputoperands
        self.operations = []

    def start_writing(self):
        self.paused_alive_gv = None

    def generate_block_code(self, final_vars_gv, final_operands=None,
                                                 renaming=True):
        self.insert_keepalives()
        if self.order_dependency is not None:
            self.order_dependency.force_generate_code()
            self.order_dependency = None
        allocator = RegAllocator(self.operations)
        allocator.set_final(final_vars_gv, final_operands)
        if not renaming:
            assert final_operands is None
            final_vars_gv = allocator.varsused()  # unique final vars
        allocator.compute_lifetimes()
        allocator.init_reg_alloc(self.inputargs_gv, self.inputoperands)
        mc = self.start_mc()
        allocator.generate_operations(mc)
        if final_operands is not None:
            allocator.generate_final_moves(final_vars_gv, final_operands)
        #print 'NSTACKMAX==============>', allocator.nstackmax
        self.graphctx.ensure_stack_vars(allocator.nstackmax)
        del self.operations[:]
        if renaming:
            self.inputargs_gv = [GenVar() for v in final_vars_gv]
        else:
            # just keep one copy of each Variable that is alive
            self.inputargs_gv = final_vars_gv
        self.inputoperands = [allocator.get_operand(v) for v in final_vars_gv]
        return mc

    def insert_keepalives(self):
        if self.keepalives_gv is not None:
            self.operations.append(OpTouch(self.keepalives_gv))
            self.keepalives_gv = None

    def enter_next_block(self, kinds, args_gv):
        # we get better register allocation if we write a single large mc block
        self.insert_keepalives()
        for i in range(len(args_gv)):
            op = OpSameAs(args_gv[i])
            args_gv[i] = op
            self.operations.append(op)
        lbl = Label(self)
        lblop = OpLabel(lbl, args_gv)
        self.operations.append(lblop)
        return lbl

    def set_coming_from(self, mc, insncond=INSN_JMP):
        self.coming_from_cond = insncond
        self.coming_from = mc.tell()
        insnemit = EMIT_JCOND[insncond]
        insnemit(mc, rel32(-1))
        self.coming_from_end = mc.tell()

    def start_mc(self):
        mc = self.rgenop.open_mc()
        # update the coming_from instruction
        start = self.coming_from
        if start:
            targetaddr = mc.tell()
            end = self.coming_from_end
            fallthrough = targetaddr == end
            if self.update_defaultcaseaddr_of:   # hack for FlexSwitch
                self.update_defaultcaseaddr_of.defaultcaseaddr = targetaddr
                fallthrough = False
            if fallthrough:
                # the jump would be with an offset 0, i.e. it would go
                # exactly after itself, so we don't really need the jump
                # instruction at all and we can overwrite it and continue.
                mc.seekback(end - start)
                targetaddr = start
            else:
                # normal case: patch the old jump to go to targetaddr
                oldmc = self.rgenop.InMemoryCodeBuilder(start, end)
                insn = EMIT_JCOND[self.coming_from_cond]
                insn(oldmc, rel32(targetaddr))
                oldmc.done()
            self.coming_from = 0
        return mc

    def _jump_if(self, cls, gv_condition, args_for_jump_gv):
        newbuilder = Builder(self.rgenop, self.graphctx,
                             list(args_for_jump_gv), None)
        newbuilder.order_dependency = self
        self.operations.append(cls(gv_condition, newbuilder))
        return newbuilder

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        return self._jump_if(JumpIfNot, gv_condition, args_for_jump_gv)

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        return self._jump_if(JumpIf, gv_condition, args_for_jump_gv)

    def finish_and_goto(self, outputargs_gv, targetlbl):
        operands = targetlbl.inputoperands
        if operands is None:
            # jumping to a label in a builder whose code has not been
            # generated yet - this builder could be 'self', in the case
            # of a tight loop
            self.pause_writing(outputargs_gv)
            targetlbl.targetbuilder.force_generate_code()
            self.start_writing()
            operands = targetlbl.inputoperands
            assert operands is not None
        mc = self.generate_block_code(outputargs_gv, operands)
        mc.JMP(rel32(targetlbl.targetaddr))
        mc.done()
        self.rgenop.close_mc(mc)

    def finish_and_return(self, sigtoken, gv_returnvar):
        gvs = [gv_returnvar]
        mc = self.generate_block_code(gvs, [eax])
        # --- epilogue ---
        mc.MOV(esp, ebp)
        mc.POP(ebp)
        mc.POP(edi)
        mc.POP(esi)
        mc.POP(ebx)
        mc.RET()
        # ----------------
        mc.done()
        self.rgenop.close_mc(mc)

    def pause_writing(self, alive_gv):
        self.paused_alive_gv = alive_gv
        return self

    def force_generate_code(self):
        alive_gv = self.paused_alive_gv
        if alive_gv is not None:
            self.paused_alive_gv = None
            mc = self.generate_block_code(alive_gv, renaming=False)
            self.set_coming_from(mc)
            mc.done()
            self.rgenop.close_mc(mc)

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        cls = getopclass1(opname)
        if cls is None:     # identity
            return gv_arg
        op = cls(gv_arg)
        self.operations.append(op)
        return op

    @specialize.arg(1)
    def genraisingop1(self, opname, gv_arg):
        cls = getopclass1(opname)
        op = cls(gv_arg)
        self.operations.append(op)
        op_excflag = OpFetchCC(op.ccexcflag)
        self.operations.append(op_excflag)
        return op, op_excflag

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        cls = getopclass2(opname)
        op = cls(gv_arg1, gv_arg2)
        self.operations.append(op)
        return op

    @specialize.arg(1)
    def genraisingop2(self, opname, gv_arg1, gv_arg2):
        cls = getopclass2(opname)
        op = cls(gv_arg1, gv_arg2)
        self.operations.append(op)
        op_excflag = OpFetchCC(op.ccexcflag)
        self.operations.append(op_excflag)
        return op, op_excflag

    def genop_ptr_iszero(self, kind, gv_ptr):
        cls = getopclass1('ptr_iszero')
        op = cls(gv_ptr)
        self.operations.append(op)
        return op

    def genop_ptr_nonzero(self, kind, gv_ptr):
        cls = getopclass1('ptr_nonzero')
        op = cls(gv_ptr)
        self.operations.append(op)
        return op

    def genop_ptr_eq(self, kind, gv_ptr1, gv_ptr2):
        cls = getopclass2('ptr_eq')
        op = cls(gv_ptr1, gv_ptr2)
        self.operations.append(op)
        return op

    def genop_ptr_ne(self, kind, gv_ptr1, gv_ptr2):
        cls = getopclass2('ptr_ne')
        op = cls(gv_ptr1, gv_ptr2)
        self.operations.append(op)
        return op

    def genop_cast_int_to_ptr(self, kind, gv_int):
        return gv_int     # identity

    def genop_same_as(self, kind, gv_x):
        if gv_x.is_const:    # must always return a var
            op = OpSameAs(gv_x)
            self.operations.append(op)
            return op
        else:
            return gv_x

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        op = OpCall(sigtoken, gv_fnptr, list(args_gv))
        self.operations.append(op)
        return op

    def genop_malloc_fixedsize(self, size):
        # XXX boehm only, no atomic/non atomic distinction for now
        op = OpCall(MALLOC_SIGTOKEN,
                    IntConst(gc_malloc_fnaddr()),
                    [IntConst(size)])
        self.operations.append(op)
        return op

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        # XXX boehm only, no atomic/non atomic distinction for now
        # XXX no overflow checking for now
        opsz = OpComputeSize(varsizealloctoken, gv_size)
        self.operations.append(opsz)
        opmalloc = OpCall(MALLOC_SIGTOKEN,
                          IntConst(gc_malloc_fnaddr()),
                          [opsz])
        self.operations.append(opmalloc)
        lengthtoken, _, _ = varsizealloctoken
        self.operations.append(OpSetField(lengthtoken, opmalloc, gv_size))
        return opmalloc

    def genop_getfield(self, fieldtoken, gv_ptr):
        op = OpGetField(fieldtoken, gv_ptr)
        self.operations.append(op)
        return op

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        self.operations.append(OpSetField(fieldtoken, gv_ptr, gv_value))

    def genop_getsubstruct(self, (offset, fieldsize), gv_ptr):
        op = OpIntAdd(gv_ptr, IntConst(offset))
        self.operations.append(op)
        return op

    def genop_getarrayitem(self, arraytoken, gv_array, gv_index):
        op = OpGetArrayItem(arraytoken, gv_array, gv_index)
        self.operations.append(op)
        return op

    def genop_setarrayitem(self, arraytoken, gv_array, gv_index, gv_value):
        self.operations.append(OpSetArrayItem(arraytoken, gv_array,
                                              gv_index, gv_value))

    def genop_getarraysubstruct(self, arraytoken, gv_array, gv_index):
        op = OpGetArraySubstruct(arraytoken, gv_array, gv_index)
        self.operations.append(op)
        return op

    def genop_getarraysize(self, arraytoken, gv_array):
        lengthtoken, _, _ = arraytoken
        op = OpGetField(lengthtoken, gv_array)
        self.operations.append(op)
        return op

    def flexswitch(self, gv_exitswitch, args_gv):
        op = OpGetExitSwitch(gv_exitswitch)
        self.operations.append(op)
        mc = self.generate_block_code(args_gv, renaming=False)
        result = FlexSwitch(self.rgenop, self.graphctx, op.reg,
                            self.inputargs_gv, self.inputoperands)
        default_builder = result.initialize(mc)
        mc.done()
        self.rgenop.close_mc(mc)
        return result, default_builder

    def show_incremental_progress(self):
        pass

    def log(self, msg):
        pass  # self.mc.log(msg)
        # XXX re-do this somehow...

    def genop_get_frame_base(self):
        return gv_frame_base

    def get_frame_info(self, vars_gv):
        result = []
        for v in vars_gv:
            if not v.is_const:
                if self.keepalives_gv is None:
                    self.keepalives_gv = []
                self.keepalives_gv.append(v)
                sis = StorageInStack(v)
                self.operations.append(sis)
                v = sis
            result.append(v)
        return result

    def alloc_frame_place(self, kind, gv_initial_value=None):
        place = Place(gv_initial_value)
        self.operations.append(place)
        return place

    def genop_absorb_place(self, kind, place):
        v = OpAbsorbPlace(place)
        self.operations.append(v)
        return v


class Label(GenLabel):
    targetaddr = 0
    inputoperands = None

    def __init__(self, targetbuilder):
        self.targetbuilder = targetbuilder


class GraphCtx:
    # keep this in sync with the generated function prologue:
    # how many extra words are initially pushed (including the
    # return value, pushed by the caller)
    PROLOGUE_FIXED_WORDS = 5

    def __init__(self, rgenop):
        self.rgenop = rgenop
        self.initial_addr = 0   # position where there is the initial ADD ESP
        self.adj_addrs = []     # list of positions where there is a LEA ESP
        self.reserved_stack_vars = 0

    def write_stack_adj(self, mc, initial):
        if initial:
            addr = write_stack_reserve(mc, self.reserved_stack_vars)
            self.initial_addr = addr
        else:
            addr = write_stack_adj(mc, self.reserved_stack_vars)
            self.adj_addrs.append(addr)

    def ensure_stack_vars(self, n):
        if CALL_ALIGN > 1:
            # align the stack to a multiple of CALL_ALIGN words
            stack_words = GraphCtx.PROLOGUE_FIXED_WORDS + n
            stack_words = (stack_words + CALL_ALIGN-1) & ~ (CALL_ALIGN-1)
            n = stack_words - GraphCtx.PROLOGUE_FIXED_WORDS
        # patch all the LEA ESP if the requested amount has grown
        if n > self.reserved_stack_vars:
            addr = self.initial_addr
            patchmc = self.rgenop.InMemoryCodeBuilder(addr, addr+99)
            write_stack_reserve(patchmc, n)
            patchmc.done()
            for addr in self.adj_addrs:
                patchmc = self.rgenop.InMemoryCodeBuilder(addr, addr+99)
                write_stack_adj(patchmc, n)
                patchmc.done()
            self.reserved_stack_vars = n

# ____________________________________________________________


class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
    from pypy.jit.codegen.i386.codebuf import InMemoryCodeBuilder

    MC_SIZE = 65536
    if DEBUG_STACK:
        MC_SIZE *= 16

    def __init__(self):
        self.allocated_mc = None
        self.keepalive_gc_refs = [] 

    def open_mc(self):
        # XXX supposed infinite for now
        mc = self.allocated_mc
        if mc is None:
            return self.MachineCodeBlock(self.MC_SIZE)
        else:
            self.allocated_mc = None
            return mc

    def close_mc(self, mc):
        assert self.allocated_mc is None
        self.allocated_mc = mc

    def check_no_open_mc(self):
        pass

    def newgraph(self, sigtoken, name):
        graphctx = GraphCtx(self)
        # --- prologue ---
        mc = self.open_mc()
        entrypoint = mc.tell()
        if DEBUG_TRAP:
            mc.BREAKPOINT()
        mc.PUSH(ebx)
        mc.PUSH(esi)
        mc.PUSH(edi)
        mc.PUSH(ebp)
        mc.MOV(ebp, esp)
        graphctx.write_stack_adj(mc, initial=True)
        # ^^^ pushed 5 words including the retval ( == PROLOGUE_FIXED_WORDS)
        # ----------------
        numargs = sigtoken     # for now
        inputargs_gv = []
        inputoperands = []
        for i in range(numargs):
            inputargs_gv.append(GenVar())
            ofs = WORD * (GraphCtx.PROLOGUE_FIXED_WORDS+i)
            inputoperands.append(mem(ebp, ofs))
        builder = Builder(self, graphctx, inputargs_gv, inputoperands)
        # XXX this makes the code layout in memory a bit obscure: we have the
        # prologue of the new graph somewhere in the middle of its first
        # caller, all alone...
        builder.set_coming_from(mc)
        mc.done()
        self.close_mc(mc)
        #ops = [OpSameAs(v) for v in inputargs_gv]
        #builder.operations.extend(ops)
        #inputargs_gv = ops
        return builder, IntConst(entrypoint), inputargs_gv[:]

    def replay(self, label, kinds):
        return ReplayBuilder(self), [dummy_var] * len(kinds)

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif T is lltype.Float:
            return FloatConst(lltype.cast_primitive(lltype.Float, llvalue))
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
    def genzeroconst(kind):
        return zero_const

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
            (lengthoffset, lengthsize), itemsoffset, itemsize = arraytoken
            arrayfield_offset = llmemory.offsetof(T, arrayfield)
            return ((arrayfield_offset+lengthoffset, lengthsize),
                    arrayfield_offset+itemsoffset,
                    itemsize)

    @staticmethod
    @specialize.memo()    
    def arrayToken(A):
        return ((llmemory.ArrayLengthOffset(A), WORD),
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

    @staticmethod
    @specialize.arg(0)
    def read_frame_var(T, base, info, index):
        v = info[index]
        if isinstance(v, StorageInStack):
            value = peek_word_at(base + v.get_offset())
            return cast_int_to_whatever(T, value)
        else:
            assert isinstance(v, GenConst)
            return v.revealconst(T)

    @staticmethod
    @specialize.arg(0)
    def write_frame_place(T, base, place, value):
        value = cast_whatever_to_int(T, value)
        poke_word_into(base + place.get_offset(), value)

    @staticmethod
    @specialize.arg(0)
    def read_frame_place(T, base, place):
        value = peek_word_at(base + place.get_offset())
        return cast_int_to_whatever(T, value)
        

global_rgenop = RI386GenOp()
RI386GenOp.constPrebuiltGlobal = global_rgenop.genconst
zero_const = AddrConst(llmemory.NULL)

MALLOC_SIGTOKEN = RI386GenOp.sigToken(GC_MALLOC.TO)
