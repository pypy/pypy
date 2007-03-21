"""Register allocation.

"""

import sys
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.i386.operation import *

DEBUG_STACK = False


class StackOpCache:
    INITIAL_STACK_EBP_OFS = -1
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

def write_stack_reserve(mc, stackn):
    addr = mc.tell()
    mc.SUB(esp, IMM32(WORD * stackn))     # always encode offset on 32 bits
    return addr

def write_stack_adj(mc, stackn):
    addr = mc.tell()
    # always encode offset on 32 bits
    mc.LEA(esp, fixedsize_ebp_ofs(-WORD * stackn))
    return addr


class RegAllocator(object):

    def __init__(self, operations):
        self.operations = operations
        self.operationindex = len(operations)
        self.lifetime = {}                 # {variable: operation_index}
        self.suggested_location = {}       # {variable: location}
        self.var2loc = {gv_frame_base: ebp}

    # ----------

    def set_final(self, final_vars_gv, locations=None):
        for i in range(len(final_vars_gv)):
            v = final_vars_gv[i]
            self.using(v)
            if locations is not None:
                self.suggested_location[v] = locations[i]

    def compute_lifetimes(self):
        for i in range(len(self.operations)-1, -1, -1):
            self.operationindex = i
            op = self.operations[i]
            if not op.side_effects and op not in self.lifetime:
                self.operations[i] = dead_operation   # operation not used
            else:
                op.mark_used_vars(self)

    def using(self, v):
        if v.is_const or v in self.lifetime:
            return False
        else:
            self.lifetime[v] = self.operationindex
            return True    # variable is dying here

    def using_inplace(self, v, vtarget):
        if self.using(v):
            # this operation 'vtarget' can modify its argument 'v'
            # in-place, and 'v' is not alive after the operation.
            # Propagate the suggested location for 'vtarget' backwards to 'v'.
            try:
                self.suggested_location[v] = self.suggested_location[vtarget]
                return True    # got a suggestion
            except KeyError:
                pass
        return False    # got no suggestion

    def suggests(self, v, loc):
        self.suggested_location[v] = loc

    def varsused(self):
        return self.lifetime.keys()

    # ----------

    AVAILABLE_REGS = (eax.bitmask |
                      edx.bitmask |
                      ecx.bitmask |
                      ebx.bitmask |
                      esi.bitmask |
                      edi.bitmask)

    def init_reg_alloc(self, inputvars_gv, inputlocations):
        self.registers_free = self.AVAILABLE_REGS     # bitmask
        self.cc_used_by = None
        self.stack_op_used = {}
        self.nstackidx = 0
        self.nstackmax = 0
        self.vars_in_use = {}     # {variable: dying_operation_index}
        self.operationindex = 0
        self.inputvars_gv = inputvars_gv
        self.inputlocations = inputlocations

    def force_loc_used(self, v, loc):
        ok = self.consume_loc(v, loc)
        assert ok

    def consume_loc(self, v, loc):
        if isinstance(loc, MODRM):
            if loc not in self.stack_op_used:
                self.stack_op_used[loc] = None
                n = stack_n_from_op(loc)
                if n >= self.nstackmax:
                    self.nstackmax = n + 1
                return True
        elif isinstance(loc, REG):
            if self.registers_free & loc.bitmask:
                self.registers_free &= ~loc.bitmask
                return True
        elif isinstance(loc, CCFLAG):
            if self.cc_used_by is None:
                self.cc_used_by = v
                return True
        return False

    def _no_longer_in_use(self, v):
        del self.vars_in_use[v]
        loc = self.var2loc[v]
        if isinstance(loc, CCFLAG):
            assert self.cc_used_by is v
        self._mark_loc_as_free(loc)

    def _mark_loc_as_free(self, loc):
        if isinstance(loc, MODRM):
            del self.stack_op_used[loc]
        elif isinstance(loc, REG):
            self.registers_free |= loc.bitmask
        elif isinstance(loc, CCFLAG):
            self.cc_used_by = None

    def generate_operations(self, mc):
        if not we_are_translated():
            print

        # reserve locations for the inputvars
        for i in range(len(self.inputvars_gv)):
            v = self.inputvars_gv[i]
            if v in self.lifetime:   # else: input argument is not used
                loc = self.inputlocations[i]
                if v in self.var2loc:   # duplicate inputvars_gv, which is ok
                    assert self.var2loc[v] == loc
                else:
                    self.var2loc[v] = loc
                    self.vars_in_use[v] = self.lifetime[v]
                    self.force_loc_used(v, loc)
                if not we_are_translated():
                    print 'in %20s:  %s' % (loc, short(v))

        self._check()
        self.mc = mc
        # Generate all operations.
        # Actual registers or stack locations are allocated as we go.
        for i in range(len(self.operations)):
            self.registers_pinned = 0        # bitmask
            op = self.operations[i]
            if op.clobbers_cc:
                self.clobber_cc()
                self._check()
            op.generate(self)
            if not we_are_translated():
                self._showprogress()
            self.operationindex = i + 1

    def _showprogress(self):
        class Collector:
            def __init__(self):
                self.lst = []
                self.using = self.lst.append
            def using_inplace(self, v, _):
                self.lst.append(v)
            def suggests(self, v, loc):
                pass
        col = Collector()
        i = self.operationindex
        op = self.operations[i]
        op.mark_used_vars(col)
        args = [short(v) for v in col.lst]
        args = ', '.join(args)
        print ' | %20s:  %s (%s)' % (self.var2loc.get(op, ''),
                                     short(op), args)
        for v, endtime in self.vars_in_use.items():
            assert endtime > i
        self._check()

    def _use_another_stack_loc(self):
        for i in range(self.nstackidx, self.nstackmax):
            loc = stack_op(i)
            if loc not in self.stack_op_used:
                self.nstackidx = i + 1
                break
        else:
            for i in range(self.nstackidx):
                loc = stack_op(i)
                if loc not in self.stack_op_used:
                    self.nstackidx = i + 1
                    break
            else:
                i = self.nstackidx = self.nstackmax
                self.nstackmax = i + 1
                loc = stack_op(i)
                assert loc not in self.stack_op_used
        self.stack_op_used[loc] = None
        return loc

    def reserve_extra_stack(self, extra):
        max = self.nstackmax
        base = max - extra
        if base < 0:
            base = 0
        while max > base and stack_op(max-1) not in self.stack_op_used:
            max -= 1
        self.nstackmax = max + extra

    def get_operand(self, v):
        if v.is_const:
            return imm(v.revealconst(lltype.Signed))
        else:
            return self.var2loc[v]

    def grab_operand(self, v):
        """Like get_operand() but if the result is in a register, it won't
        be spilled before the end of the current instruction."""
        loc = self.get_operand(v)
        if isinstance(loc, REG):
            self.registers_pinned |= loc.bitmask
        return loc

    def _use_next_modrm(self, v, regnum_must_be_before=8):
        """Select the next mod/rm location to use for the new operation 'v'.
        If 'v' is None, this will always return a register; else it might
        decide to immediately create 'v' in a stack location.
        """
        #print self.registers_free
        if self.registers_free:
            for i in range(regnum_must_be_before-1, -1, -1):
                if self.registers_free & (1 << i):
                    self.registers_free &= ~ (1 << i)
                    return registers[i]
        # spill the register holding the variable that has the longest
        # time remaining to live (it may be our 'v' itself)
        if v is None:
            dyinglimit = self.operationindex  # must pick vars dying after that
            spillvar = None
        else:
            dyinglimit = self.lifetime[v]
            spillvar = v  # initial guess, can be overridden in the loop below
        regloc = None
        for v1, dying in self.vars_in_use.iteritems():
            if dying > dyinglimit:
                loc = self.var2loc[v1]
                if not isinstance(loc, REG):
                    continue
                if loc.op >= regnum_must_be_before:
                    continue   # never reached if regnum_must_be_before == 8
                if loc.bitmask & self.registers_pinned:
                    continue   # don't spill this register
                regloc = loc
                dyinglimit = dying
                spillvar = v1
        if spillvar is None:
            raise OutOfRegistersError
        #print 'time span of %s: now is %d, lives until %d' % (
        #    v, self.operationindex, self.lifetime[v])
        if spillvar is v:
            return self._use_another_stack_loc()
        else:
            assert regloc is not None
            self._spill(spillvar, regloc)
            return regloc

    def _spill(self, spillvar, oldloc):
        spillloc = self._use_another_stack_loc()
        if not we_are_translated():
            print ' # %20s:  SPILL %s' % (spillloc, oldloc)
        self.mc.MOV(spillloc, oldloc)
        self.var2loc[spillvar] = spillloc
        return spillloc

    def _use_next_reg(self):
        return self._use_next_modrm(None)

    def _use_next_reg_abcd(self):
        return self._use_next_modrm(None, regnum_must_be_before=4)

    def _created(self, v, loc):
        assert v not in self.var2loc
        assert loc is not None
        self.vars_in_use[v] = ltime = self.lifetime[v]
        assert ltime > self.operationindex
        self.var2loc[v] = loc
        if isinstance(loc, REG):
            self.registers_pinned |= loc.bitmask

    def release(self, v):
        """Stop using argument 'v'.  Must be called for each used argument."""
        ok = self.lastuse(v) and v in self.vars_in_use
        if ok:
            self._no_longer_in_use(v)
        return ok

    def lastuse(self, v):
        """Is this the last time the argument 'v' is used?"""
        if v.is_const:
            return False
        else:
            endtime = self.lifetime[v]
            assert endtime >= self.operationindex
            return endtime == self.operationindex

    def create(self, v, suggested_loc=None):
        """Create the result of the operation 'v', possibly at the
        suggested location.  CAN SPILL ONE REGISTER."""
        if suggested_loc is not None and self.consume_loc(v, suggested_loc):
            self._created(v, suggested_loc)
            return suggested_loc
        suggested_loc = self.suggested_location.get(v, None)
        if suggested_loc is not None and self.consume_loc(v, suggested_loc):
            self._created(v, suggested_loc)
            return suggested_loc
        loc = self._use_next_modrm(v)
        self._created(v, loc)
        return loc

    def create_reg(self, v, srcloc=None):
        """Create the result of the operation 'v' in any register
        currently available.  CAN SPILL ONE REGISTER."""
        suggested_loc = self.suggested_location.get(v, None)
        if (isinstance(suggested_loc, REG) and
            self.consume_loc(v, suggested_loc)):
            loc = suggested_loc
        else:
            loc = self._use_next_reg()
        self._created(v, loc)
        if srcloc is not None and loc is not srcloc:
            # if srcop was spilled, srcloc still contains its value right now
            # and then it's possible that srcop == dstop (no MOV needed then)
            self.mc.MOV(loc, srcloc)
        return loc

    def create_exactly_at(self, v, loc):
        """Create the result of the operation 'v' at 'loc'."""
        ok = self.consume_loc(v, loc)
        assert ok
        self._created(v, loc)

    def create_in_cc(self, v, ccloc):
        """Create the result of the operation 'v' in the given cc flags.
        Doesn't move stuff around."""
        assert self.cc_used_by is None
        self._created(v, ccloc)
        self.cc_used_by = v

    def create_scratch_reg(self, srcloc=None):
        """Return a scratch register for the current operation.
        Warning, this might be the same register as one of the input args.
        CAN SPILL ONE REGISTER.  You must eventually call end_clobber()."""
        reg = self._use_next_reg()
        if srcloc is not None and reg is not srcloc:
            self.mc.MOV(reg, srcloc)
        return reg

    def create_scratch_reg8(self, srcloc=None):
        reg32 = self._use_next_reg_abcd()
        reg8 = reg32.lowest8bits()
        if srcloc is not None and reg8 is not srcloc and reg32 is not srcloc:
            if srcloc.width == 1:
                self.mc.MOV(reg8, srcloc)
            else:
                self.mc.MOV(reg32, srcloc)
        return reg8

    def operation_result_is_used(self, v):
        return v in self.lifetime

    def clobber(self, reg):
        """Clobbers a register, i.e. move away a value that would be there.
        It might go to a different register or to the stack.
        You must eventually call end_clobber()."""
        assert isinstance(reg, REG)
        if not self.registers_free & reg.bitmask:
            assert not (reg.bitmask & self.registers_pinned)
            for v1 in self.vars_in_use:
                if self.var2loc[v1] == reg:
                    self._move_away(v1)
                    break
            assert self.registers_free & reg.bitmask
        self.registers_free &= ~reg.bitmask

    def clobber2(self, reg1, reg2):
        """Clobbers two registers.  Unlike two individual clobber() calls,
        where the first call might overwrite the other reg, this one
        preserves the current content of both 'reg1' and 'reg2'.
        You must eventually call end_clobber() twice."""
        if not self.registers_free & reg2.bitmask:
            # order trick: if reg2 is free but reg1 used, doing clobber() in
            # the following order could first move reg1 to reg2, and then
            # immediately away from reg2.
            self.clobber(reg1)     # <- here reg1 cannot go to reg2
            self.clobber(reg2)
        else:
            self.clobber(reg2)     # reg2 is free, so it doesn't go anywhere
            self.clobber(reg1)

    def clobber3(self, reg1, reg2, reg3):
        if not self.registers_free & reg3.bitmask:
            self.clobber2(reg1, reg2)    # they cannot go to reg3
            self.clobber(reg3)
        else:
            self.clobber(reg3)           # free, so doesn't go anywhere
            self.clobber2(reg1, reg2)

    def end_clobber(self, reg):
        if isinstance(reg, REG):
            bitmask = reg.bitmask
        else:
            assert isinstance(reg, REG8)
            assert reg.op < 4
            bitmask = reg.bitmask
        self.registers_free |= bitmask

    def clobber_cc(self):
        v = self.cc_used_by
        if v is not None:
            self.cc_used_by = None
            # pick a newloc that is either one of [eax, ecx, edx, ebx]
            # or a stack location
            oldloc = self.var2loc[v]
            newloc = self._use_next_modrm(v, regnum_must_be_before=4)
            if not we_are_translated():
                print ' # %20s:  MOVE AWAY FROM %s' % (newloc, oldloc)
            assert isinstance(oldloc, CCFLAG)
            mc = self.mc
            newloc8 = newloc.lowest8bits()
            if isinstance(newloc, REG):
                oldloc.SETCOND(mc, newloc8)
                mc.MOVZX(newloc, newloc8)
            else:
                mc.MOV(newloc, imm8(0))
                oldloc.SETCOND(mc, newloc8)
            self._mark_loc_as_free(oldloc)
            self.var2loc[v] = newloc

    def lock(self, loc):
        """Temporarily prevent 'loc' from being overwritten by the
        functions marked as 'moves stuff around'.  Return True if the
        lock is sucessful, False if the location was not free in the
        first place."""
        return self.consume_loc(None, loc)

    def unlock(self, loc):
        """Call sometime after a lock() that returned True."""
        self._mark_loc_as_free(loc)

    def _move_away(self, v):
        # move 'v' away, into a newly allocated register or stack location,
        # possibly spilling another register
        oldloc = self.var2loc[v]
        newloc = self._use_next_modrm(v)
        if not we_are_translated():
            print ' # %20s:  MOVE AWAY FROM %s' % (newloc, oldloc)
        self.mc.MOV(newloc, oldloc)
        self._mark_loc_as_free(oldloc)
        self.var2loc[v] = newloc
        return newloc

    def _check(self):
        if not we_are_translated():
            def unpackbitmask(x):
                return dict.fromkeys([r for r in registers if x & r.bitmask])
            rf = unpackbitmask(self.AVAILABLE_REGS)
            locs_seen = {}
            for v in self.vars_in_use:
                loc = self.var2loc[v]
                assert loc not in locs_seen
                locs_seen[loc] = v
                if isinstance(loc, REG):
                    del rf[loc]
            assert unpackbitmask(self.registers_free) == rf

    # ----------

    def generate_final_moves(self, final_vars_gv, locations):
        # XXX naive algo for now
        pops = []
        for i in range(len(final_vars_gv)):
            v = final_vars_gv[i]
            if not v.is_const:
                srcloc = self.var2loc[v]
                dstloc = locations[i]
                if srcloc != dstloc:
                    if not we_are_translated():
                        print ' > %20s--->->->---%s' % (srcloc, dstloc)
                    if isinstance(srcloc, CCFLAG):
                        self.mc.PUSH(imm8(0))
                        srcloc.SETCOND(self.mc, mem8(esp))
                    else:
                        self.mc.PUSH(srcloc)
                    pops.append(dstloc)
        while pops:
            dstloc = pops.pop()
            self.mc.POP(dstloc)
        for i in range(len(final_vars_gv)):
            v = final_vars_gv[i]
            if v.is_const:
                dstloc = locations[i]
                self.mc.MOV(dstloc, imm(v.revealconst(lltype.Signed)))


class OutOfRegistersError(Exception):
    pass

def short(op, memo={}):
    key = op.__class__.__name__
    d = memo.setdefault(key, {})
    try:
        n = d[op]
    except KeyError:
        n = d[op] = len(d)
    return '%s-%d' % (key, n)

# ____________________________________________________________

class DeadOperation(Operation):
    clobbers_cc = False
    side_effects = False
    def mark_used_vars(self, allocator):
        pass
    def generate(self, allocator):
        pass
dead_operation = DeadOperation()
gv_frame_base = GenVar()

class Place(Operation):
    """Place of a variable that must live in the stack.  Its position is
    choosen by the register allocator and put in the 'offset' attribute."""
    def __init__(self, x):
        self.x = x
    def mark_used_vars(self, allocator):
        if self.x is not None:
            allocator.using(self.x)
    def get_offset(self):
        return self.offset
    def generate(self, allocator):
        assert allocator.operation_result_is_used(self), "place not absorbed!"
        loc = allocator._use_another_stack_loc()
        allocator._created(self, loc)
        if self.x is not None:
            srcop = allocator.get_operand(self.x)
            try:
                allocator.mc.MOV(loc, srcop)
            except FailedToImplement:
                # loc and srcop are both in the stack - need a temporary reg
                tmpop = allocator.create_scratch_reg(srcop)
                # loc and srcop still valid, as they are already in the stack
                # so cannot have been spilled by create_scratch_reg()
                allocator.mc.MOV(loc, tmpop)
                allocator.end_clobber(tmpop)
            allocator.release(self.x)
            self.x = None     # hack to avoid that the Place keeps a lot of
                              # memory around
        self.offset = loc.ofs_relative_to_ebp()

class OpAbsorbPlace(Op1):
    clobbers_cc = False
    def generate(self, allocator):
        allocator.release(self.x)
        if allocator.operation_result_is_used(self):
            loc = allocator.get_operand(self.x)
            allocator.create_exactly_at(self, loc)

class StorageInStack(Place):
    def generate(self, allocator):
        # force the variable to be in the stack
        srcop = allocator.get_operand(self.x)
        if not isinstance(srcop, MODRM):
            oldop = srcop
            srcop = allocator._spill(self.x, srcop)
            allocator._mark_loc_as_free(oldop)
        # record its location
        self.offset = srcop.ofs_relative_to_ebp()
        # hack to avoid this instance keeping a lot of memory around
        self.x = None

class OpTouch(Operation):
    side_effects = True     # don't remove me!
    def __init__(self, args_gv):
        self.args_gv = args_gv
    def mark_used_vars(self, allocator):
        for v in self.args_gv:
            allocator.using(v)
    def generate(self, allocator):
        for v in self.args_gv:
            allocator.release(v)
