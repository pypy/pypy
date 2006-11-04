from pypy.jit.codegen.ppc.instruction import gprs, NO_REGISTER, GP_REGISTER, \
     FP_REGISTER, CR_FIELD, CT_REGISTER, CMPInsn, Spill, Unspill, crfs, ctr, stack_slot

class RegisterAllocation:
    def __init__(self, minreg, initial_mapping, initial_spill_offset):
        #print
        #print "RegisterAllocation __init__", initial_mapping

        self.insns = []   # Output list of instructions
        self.freeregs = gprs[minreg:] # Registers with dead values
        self.var2loc = {} # Maps a Var to an AllocationSlot
        self.loc2var = {} # Maps an AllocationSlot to a Var
        self.lru = []     # Least-recently-used list of vars; first is oldest.
                          # Contains all vars in registers, and no vars on stack
        self.spill_offset = initial_spill_offset # Where to put next spilled
                                                 # value, relative to rFP,
                                                 # measured in bytes

        # Go through the initial mapping and initialize the data structures
        for var, loc in initial_mapping.iteritems():
            self.loc2var[loc] = var
            self.var2loc[var] = loc
            if loc in self.freeregs:
                self.freeregs.remove(loc)
                self.lru.append(var)
        self.crfinfo = [(0, 0)] * 8

    def spill(self):
        """ Returns an offset onto the stack for an unused spill location """
        # TODO --- reuse spill slots when contained values go dead?
        self.spill_offset -= 4
        return self.spill_offset

    def _allocate_reg(self, newarg):

        # check if there is a register available
        if self.freeregs:
            reg = self.freeregs.pop()
            self.loc2var[reg] = newarg
            self.var2loc[newarg] = reg
            #print "allocate_reg: Putting %r into fresh register %r" % (newarg, reg)
            return reg

        # if not, find something to spill
        argtospill = self.lru.pop(0)
        reg = self.var2loc[argtospill]
        assert reg.is_register

        # Move the value we are spilling onto the stack, both in the
        # data structures and in the instructions:
        spill = stack_slot(self.spill())
        self.var2loc[argtospill] = spill
        self.loc2var[spill] = argtospill
        self.insns.append(Spill(argtospill, reg, spill))
        #print "allocate_reg: Spilled %r to %r." % (argtospill, spill)

        # If the value is currently on the stack, load it up into the
        # register we are putting it into
        if newarg in self.var2loc:
            spill = self.var2loc[newarg]
            assert not spill.is_register
            self.insns.append(Unspill(newarg, reg, spill))
            del self.loc2var[spill] # not stored there anymore, reuse??
            #print "allocate_reg: Unspilled %r from %r." % (newarg, spill)

        # Update data structures to put newarg into the register
        self.var2loc[newarg] = reg
        self.loc2var[reg] = newarg
        #print "allocate_reg: Put %r in stolen reg %r." % (newarg, reg)
        return reg

    def _promote(self, arg):
        if arg in self.lru:
            self.lru.remove(arg)
        self.lru.append(arg)

    def allocate_for_insns(self, insns):
        # Walk through instructions in forward order
        for insn in insns:

            #print "Processing instruction %r with args %r and result %r:" % (insn, insn.reg_args, insn.result)

            #print "LRU list was: %r" % (self.lru,)

            # put things into the lru
            for i in range(len(insn.reg_args)):
                arg = insn.reg_args[i]
                argcls = insn.reg_arg_regclasses[i]
                if argcls == GP_REGISTER:
                    self._promote(arg)
            if insn.result and insn.result_regclass == GP_REGISTER:
                self._promote(insn.result)
            #print "LRU list is now: %r" % (self.lru,)

            # We need to allocate a register for each used
            # argument that is not already in one
            for i in range(len(insn.reg_args)):
                arg = insn.reg_args[i]
                argcls = insn.reg_arg_regclasses[i]
                #print "Allocating register for %r..." % (arg,)

                if not self.var2loc[arg].is_register:
                    # It has no register now because it has been spilled
                    assert argcls is GP_REGISTER, "uh-oh"
                    self._allocate_reg(arg)
                else:
                    #print "it was in ", self.var2loc[arg]
                    pass

            # Need to allocate a register for the destination
            assert not insn.result or insn.result not in self.var2loc
            cand = None
            if insn.result_regclass is GP_REGISTER:
                #print "Allocating register for result %r..." % (insn.result,)
                cand = self._allocate_reg(insn.result)
            elif insn.result_regclass is CR_FIELD:
                assert crfs[0] not in self.loc2var
                assert isinstance(insn, CMPInsn)
                cand = crfs[0]
                self.crfinfo[0] = insn.info
            elif insn.result_regclass is CT_REGISTER:
                assert ctr not in self.loc2var
                cand = ctr
            elif insn.result_regclass is not NO_REGISTER:
                assert 0
            if cand is not None and cand not in self.loc2var:
                self.var2loc[insn.result] = cand
                self.loc2var[cand] = insn.result
            else:
                assert cand is None or self.loc2var[cand] is insn.result
            insn.allocate(self)
            self.insns.append(insn)
        return self.insns
