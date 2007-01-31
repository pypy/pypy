import py
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.model import ReplayBuilder, dummy_var
from pypy.jit.codegen.i386.codebuf import CodeBlockOverflow
from pypy.jit.codegen.i386.operation import *
from pypy.jit.codegen.i386.regalloc import RegAllocator, StorageInStack, Place
from pypy.jit.codegen.i386.regalloc import DEBUG_STACK
from pypy.jit.codegen import conftest
from pypy.rpython.annlowlevel import llhelper

DEBUG_TRAP = conftest.option.trap

# ____________________________________________________________

class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    @specialize.arg(1)
    def revealconst(self, T):
        return cast_int_to_whatever(T, self.value)

    def __repr__(self):
        "NOT_RPYTHON"
        try:
            return "const=%s" % (imm(self.value).assembler(),)
        except TypeError:   # from Symbolics
            return "const=%r" % (self.value,)

    def repr(self):
        return "const=$%s" % (self.value,)

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
    REG = eax

    def __init__(self, rgenop, inputargs_gv, inputoperands):
        self.rgenop = rgenop
        self.inputargs_gv = inputargs_gv
        self.inputoperands = inputoperands
        self.defaultcaseaddr = 0

    def initialize(self, mc):
        self._reserve(mc)
        default_builder = Builder(self.rgenop, self.inputargs_gv,
                                  self.inputoperands)
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
        targetbuilder = Builder(self.rgenop, self.inputargs_gv,
                                self.inputoperands)
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
        mc.CMP(FlexSwitch.REG, imm(value))
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
    operations = None
    update_defaultcaseaddr_of = None
    force_in_stack = None

    def __init__(self, rgenop, inputargs_gv, inputoperands):
        self.rgenop = rgenop
        self.inputargs_gv = inputargs_gv
        self.inputoperands = inputoperands

    def start_writing(self):
        assert self.operations is None
        self.operations = []

    def generate_block_code(self, final_vars_gv, force_vars=[],
                                                 force_operands=[],
                                                 renaming=True,
                                                 minimal_stack_depth=0):
        allocator = RegAllocator()
        if self.force_in_stack is not None:
            allocator.force_stack_storage(self.force_in_stack)
        allocator.set_final(final_vars_gv)
        if not renaming:
            final_vars_gv = allocator.var2loc.keys()  # unique final vars
        allocator.allocate_locations(self.operations)
        allocator.force_var_operands(force_vars, force_operands,
                                     at_start=False)
        allocator.force_var_operands(self.inputargs_gv, self.inputoperands,
                                     at_start=True)
        allocator.allocate_registers()
        if allocator.required_frame_depth < minimal_stack_depth:
            allocator.required_frame_depth = minimal_stack_depth
        mc = self.start_mc()
        allocator.mc = mc
        allocator.generate_initial_moves()
        allocator.generate_operations()
        if self.force_in_stack is not None:
            allocator.save_storage_places(self.force_in_stack)
            self.force_in_stack = None
        self.operations = None
        if renaming:
            self.inputargs_gv = [GenVar() for v in final_vars_gv]
        else:
            # just keep one copy of each Variable that is alive
            self.inputargs_gv = final_vars_gv
        self.inputoperands = [allocator.get_operand(v) for v in final_vars_gv]
        return mc

    def enter_next_block(self, kinds, args_gv):
##        mc = self.generate_block_code(args_gv)
##        assert len(self.inputargs_gv) == len(args_gv)
##        args_gv[:len(args_gv)] = self.inputargs_gv
##        self.set_coming_from(mc)
##        self.rgenop.close_mc(mc)
##        self.start_writing()
        for i in range(len(args_gv)):
            op = OpSameAs(args_gv[i])
            args_gv[i] = op
            self.operations.append(op)
        lbl = Label()
        lblop = OpLabel(lbl, args_gv)
        self.operations.append(lblop)
        return lbl

    def set_coming_from(self, mc, insncond=INSN_JMP):
        self.coming_from_cond = insncond
        self.coming_from = mc.tell()
        insnemit = EMIT_JCOND[insncond]
        insnemit(mc, rel32(0))
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

    def _jump_if(self, gv_condition, args_for_jump_gv, negate):
        newbuilder = Builder(self.rgenop, list(args_for_jump_gv), None)
        # if the condition does not come from an obvious comparison operation,
        # e.g. a getfield of a Bool or an input argument to the current block,
        # then insert an OpIntIsTrue
        if gv_condition.cc_result < 0 or gv_condition not in self.operations:
            gv_condition = OpIntIsTrue(gv_condition)
            self.operations.append(gv_condition)
        self.operations.append(JumpIf(gv_condition, newbuilder, negate=negate))
        return newbuilder

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, args_for_jump_gv, True)

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, args_for_jump_gv, False)

    def finish_and_goto(self, outputargs_gv, targetlbl):
        operands = targetlbl.inputoperands
        if operands is None:
            # this occurs when jumping back to the same currently-open block;
            # close the block and re-open it
            self.pause_writing(outputargs_gv)
            self.start_writing()
            operands = targetlbl.inputoperands
            assert operands is not None
        mc = self.generate_block_code(outputargs_gv, outputargs_gv, operands,
                              minimal_stack_depth = targetlbl.targetstackdepth)
        mc.JMP(rel32(targetlbl.targetaddr))
        mc.done()
        self.rgenop.close_mc(mc)

    def finish_and_return(self, sigtoken, gv_returnvar):
        mc = self.generate_block_code([gv_returnvar], [gv_returnvar], [eax])
        # --- epilogue ---
        mc.LEA(esp, mem(ebp, -12))
        mc.POP(edi)
        mc.POP(esi)
        mc.POP(ebx)
        mc.POP(ebp)
        mc.RET()
        # ----------------
        mc.done()
        self.rgenop.close_mc(mc)

    def pause_writing(self, alive_gv):
        mc = self.generate_block_code(alive_gv, renaming=False)
        self.set_coming_from(mc)
        mc.done()
        self.rgenop.close_mc(mc)
        return self

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
    def genop2(self, opname, gv_arg1, gv_arg2):
        cls = getopclass2(opname)
        op = cls(gv_arg1, gv_arg2)
        self.operations.append(op)
        return op

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
        reg = FlexSwitch.REG
        mc = self.generate_block_code(args_gv, [gv_exitswitch], [reg],
                                      renaming=False)
        result = FlexSwitch(self.rgenop, self.inputargs_gv, self.inputoperands)
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
        op = OpGetFrameBase()
        self.operations.append(op)
        return op

    def get_frame_info(self, vars_gv):
        if self.force_in_stack is None:
            self.force_in_stack = []
        result = []
        for v in vars_gv:
            if not v.is_const:
                place = StorageInStack()
                self.force_in_stack.append((v, place))
                v = place
            result.append(v)
        return result

    def alloc_frame_place(self, kind, gv_initial_value):
        if self.force_in_stack is None:
            self.force_in_stack = []
        v = OpSameAs(gv_initial_value)
        self.operations.append(v)
        place = Place()
        place.stackvar = v
        self.force_in_stack.append((v, place))
        return place

    def genop_absorb_place(self, kind, place):
        v = place.stackvar
        place.stackvar = None  # break reference to potentially lots of memory
        return v


class Label(GenLabel):
    targetaddr = 0
    targetstackdepth = 0
    inputoperands = None

# ____________________________________________________________


class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
    from pypy.jit.codegen.i386.codebuf import InMemoryCodeBuilder

    MC_SIZE = 65536
    if DEBUG_STACK:
        MC_SIZE *= 16

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

    def newgraph(self, sigtoken, name):
        # --- prologue ---
        mc = self.open_mc()
        entrypoint = mc.tell()
        if DEBUG_TRAP:
            mc.BREAKPOINT()
        mc.PUSH(ebp)
        mc.MOV(ebp, esp)
        mc.PUSH(ebx)
        mc.PUSH(esi)
        mc.PUSH(edi)
        # ^^^ pushed 5 words including the retval ( == PROLOGUE_FIXED_WORDS)
        # ----------------
        numargs = sigtoken     # for now
        inputargs_gv = []
        inputoperands = []
        for i in range(numargs):
            inputargs_gv.append(GenVar())
            inputoperands.append(mem(ebp, WORD * (2+i)))
        builder = Builder(self, inputargs_gv, inputoperands)
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

MALLOC_SIGTOKEN = RI386GenOp.sigToken(GC_MALLOC.TO)
