"""Register allocation.

"""

from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.i386.operation import *


class StackOpCache:
    INITIAL_STACK_EBP_OFS = -4
stack_op_cache = StackOpCache()
stack_op_cache.lst = []

def stack_op(n):
    "Return the mem operand that designates the nth stack-spilled location"
    assert n >= 0
    lst = stack_op_cache.lst
    while len(lst) <= n:
        ofs = WORD * (StackOpCache.INITIAL_STACK_EBP_OFS - len(lst))
        lst.append(mem(ebp, ofs))
    return lst[n]

def stack_n_from_op(op):
    ofs = op.ofs_relative_to_ebp()
    return StackOpCache.INITIAL_STACK_EBP_OFS - ofs / WORD


class RegAllocator(object):
    AVAILABLE_REGS = [eax, edx, ebx, esi, edi]   # XXX ecx reserved for stuff

    # 'gv' -- GenVars, used as arguments and results of operations
    #
    # 'loc' -- location, a small integer that represents an abstract
    #          register number
    #
    # 'operand' -- a concrete machine code operand, which can be a
    #              register (ri386.eax, etc.) or a stack memory operand

    def __init__(self):
        self.nextloc = 0
        self.var2loc = {}
        self.available_locs = []
        self.force_loc2operand = {}
        self.force_operand2loc = {}
        self.initial_moves = []
        self.num_stack_locs = 0

    def set_final(self, final_vars_gv):
        for v in final_vars_gv:
            self.using(v)

    def creating(self, v):
        try:
            loc = self.var2loc[v]
        except KeyError:
            pass
        else:
            if loc >= self.num_stack_locs:
                self.available_locs.append(loc) # now available again for reuse

    def using(self, v):
        if not v.is_const and v not in self.var2loc:
            try:
                loc = self.available_locs.pop()
            except IndexError:
                loc = self.nextloc
                self.nextloc += 1
            self.var2loc[v] = loc

    def creating_cc(self, v):
        if self.need_var_in_cc is v:
            # common case: v is a compare operation whose result is precisely
            # what we need to be in the CC
            self.need_var_in_cc = None
        self.creating(v)

    def save_cc(self):
        # we need a value to be in the CC, but we see a clobbering
        # operation, so we copy the original CC-creating operation down
        # past the clobbering operation.
        # <pedronis> completely obscure code
        # <arigo> yes, well, needs very careful reviewing I guess :-)
        v = self.need_var_in_cc
        if not we_are_translated():
            assert v in self.operations[:self.operationindex]
        v = v.copy()
        self.operations.insert(self.operationindex, v)
        v.allocate(self)
        self.need_var_in_cc = None

    def using_cc(self, v):
        assert isinstance(v, Operation)
        assert 0 <= v.cc_result < INSN_JMP
        if self.need_var_in_cc is not None and self.need_var_in_cc is not v:
            self.save_cc()
        self.need_var_in_cc = v

    def allocate_locations(self, operations):
        # assign locations to gvars
        self.operations = operations
        self.need_var_in_cc = None
        self.operationindex = len(operations)
        for i in range(len(operations)-1, -1, -1):
            v = operations[i]
            if (self.need_var_in_cc is not None and
                self.need_var_in_cc is not v and v.clobbers_cc):
                self.save_cc()
            kind = v.result_kind
            if kind == RK_WORD:
                self.creating(v)
            elif kind == RK_CC:
                self.creating_cc(v)
            v.allocate(self)
            self.operationindex = i
        if self.need_var_in_cc is not None:
            self.save_cc()

    def force_var_operands(self, force_vars, force_operands, at_start):
        force_loc2operand = self.force_loc2operand
        force_operand2loc = self.force_operand2loc
        for i in range(len(force_vars)):
            v = force_vars[i]
            operand = force_operands[i]
            try:
                loc = self.var2loc[v]
            except KeyError:
                if at_start:
                    pass    # input variable not used anyway
                else:
                    self.add_final_move(v, operand, make_copy=v.is_const)
            else:
                # we need to make of copy of this var if we have conflicting
                # requirements about where it should go:
                #  * its location is forced to another operand
                #  * the operand is assigned to another location
                #  * it should be in the stack, but it is not
                if (loc in force_loc2operand or operand in force_operand2loc or
                    (loc < self.num_stack_locs and not (
                                 isinstance(operand, MODRM)
                                 and operand.is_relative_to_ebp()))):
                    if at_start:
                        self.initial_moves.append((loc, operand))
                    else:
                        self.add_final_move(v, operand, make_copy=True)
                else:
                    force_loc2operand[loc] = operand
                    force_operand2loc[operand] = loc

    def add_final_move(self, v, targetoperand, make_copy):
        if make_copy:
            v = OpSameAs(v)
            self.operations.append(v)
        loc = self.nextloc
        self.nextloc += 1
        self.var2loc[v] = loc
        self.force_loc2operand[loc] = targetoperand

    def allocate_registers(self):
        # assign registers to locations that don't have one already
        force_loc2operand = self.force_loc2operand
        operands = []
        seen_regs = 0
        seen_stackn = {}
        last_seen_stackn = -1
        for op in force_loc2operand.values():
            if isinstance(op, REG):
                seen_regs |= 1 << op.op
            elif isinstance(op, MODRM):
                n = stack_n_from_op(op)
                seen_stackn[n] = None
                if n > last_seen_stackn:
                    last_seen_stackn = n
        i = 0
        stackn = 0
        num_stack_locs = self.num_stack_locs
        for loc in range(self.nextloc):
            try:
                operand = force_loc2operand[loc]
            except KeyError:
                try:
                    # try to grab the next free register,
                    # unless this location is forced to go to the stack
                    if loc < num_stack_locs:
                        raise IndexError
                    while True:
                        operand = RegAllocator.AVAILABLE_REGS[i]
                        i += 1
                        if not (seen_regs & (1 << operand.op)):
                            break
                except IndexError:
                    while stackn in seen_stackn:
                        stackn += 1
                    operand = stack_op(stackn)
                    stackn += 1
            operands.append(operand)
        self.operands = operands
        if stackn <= last_seen_stackn:
            stackn = last_seen_stackn + 1
        self.required_frame_depth = stackn

    def get_operand(self, gv_source):
        if gv_source.is_const:
            return imm(gv_source.revealconst(lltype.Signed))
        else:
            loc = self.var2loc[gv_source]
            return self.operands[loc]

    def load_location_with(self, loc, gv_source):
        dstop = self.operands[loc]
        srcop = self.get_operand(gv_source)
        if srcop != dstop:
            self.mc.MOV(dstop, srcop)
        return dstop

    def generate_initial_moves(self):
        initial_moves = self.initial_moves
        # first make sure that the reserved stack frame is big enough
        last_n = self.required_frame_depth - 1
        for loc, srcoperand in initial_moves:
            if isinstance(srcoperand, MODRM):
                n = stack_n_from_op(srcoperand)
                if last_n < n:
                    last_n = n
        if last_n >= 0:
            if CALL_ALIGN > 1:
                last_n = (last_n & ~(CALL_ALIGN-1)) + (CALL_ALIGN-1)
            self.required_frame_depth = last_n + 1
            self.mc.LEA(esp, stack_op(last_n))
        # XXX naive algo for now
        for loc, srcoperand in initial_moves:
            if self.operands[loc] != srcoperand:
                self.mc.PUSH(srcoperand)
        initial_moves.reverse()
        for loc, srcoperand in initial_moves:
            if self.operands[loc] != srcoperand:
                self.mc.POP(self.operands[loc])

    def generate_operations(self):
        for v in self.operations:
            v.generate(self)
            cc = v.cc_result
            if cc >= 0 and v in self.var2loc:
                # force a comparison instruction's result into a
                # regular location
                dstop = self.get_operand(v)
                mc = self.mc
                insn = EMIT_SETCOND[cc]
                insn(mc, cl)
                try:
                    mc.MOVZX(dstop, cl)
                except FailedToImplement:
                    mc.MOVZX(ecx, cl)
                    mc.MOV(dstop, ecx)

    def force_stack_storage(self, lst):
        # this is called at the very beginning, so the 'loc' numbers
        # computed here are the smaller ones
        N = 0
        for v, place in lst:
            self.using(v)
            loc = self.var2loc[v]
            if loc >= N:
                N = loc + 1
        self.num_stack_locs = N

    def save_storage_places(self, lst):
        for v, place in lst:
            loc = self.var2loc[v]
            operand = self.operands[loc]
            place.offset = operand.ofs_relative_to_ebp()


class StorageInStack(GenVar):
    """Place of a variable that must live in the stack.  Its position is
    choosen by the register allocator and put in the 'stackn' attribute."""
    offset = 0

    def get_offset(self):
        assert self.offset != 0     # otherwise, RegAllocator bug
        return self.offset


class Place(StorageInStack):
    pass
