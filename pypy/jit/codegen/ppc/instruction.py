r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, \
    r13, r14, r15, r16, r17, r18, r19, r20, r21, r22, \
    r23, r24, r25, r26, r27, r28, r29, r30, r31 = range(32)
rSCRATCH = r0
rSP = r1
rFP = r2 # the ABI doesn't specify a frame pointer.  however, we want one

class AllocationSlot(object):
    offset = 0
    number = 0
    def __init__(self):
        # The field alloc points to a singleton used by the register
        # allocator to detect conflicts.  No two AllocationSlot
        # instances with the same value in self.alloc can be used at
        # once.
        self.alloc = self

    def make_loc(self):
        """ When we assign a variable to one of these registers, we
        call make_loc() to get the actual location instance; that
        instance will have its alloc field set to self.  For
        everything but condition registers, this is self."""
        return self

class _StackSlot(AllocationSlot):
    is_register = False
    def __init__(self, offset):
        AllocationSlot.__init__(self)
        self.offset = offset
    def __repr__(self):
        return "stack@%s"%(self.offset,)

_stack_slot_cache = {}
def stack_slot(offset):
    # because stack slots are put into dictionaries which compare by
    # identity, it is important that there's a unique _StackSlot
    # object for each offset, at least per function generated or
    # something.  doing the caching here is easier, though.
    if offset in _stack_slot_cache:
        return _stack_slot_cache[offset]
    _stack_slot_cache[offset] = res = _StackSlot(offset)
    return res

NO_REGISTER = -1
GP_REGISTER = 0
FP_REGISTER = 1
CR_FIELD = 2
CT_REGISTER = 3

class Register(AllocationSlot):
    is_register = True
    def __init__(self):
        AllocationSlot.__init__(self)

class GPR(Register):
    regclass = GP_REGISTER
    def __init__(self, number):
        Register.__init__(self)
        self.number = number
    def __repr__(self):
        return 'r' + str(self.number)
gprs = map(GPR, range(32))

class FPR(Register):
    regclass = FP_REGISTER
    def __init__(self, number):
        Register.__init__(self)
        self.number = number

fprs = map(GPR, range(32))

class BaseCRF(Register):
    """ These represent condition registers; however, we never actually
    use these as the location of something in the register allocator.
    Instead, we place it in an instance of CRF which indicates which
    bits are required to extract the value.  Note that CRF().alloc will
    always be an instance of this. """
    regclass = CR_FIELD
    def __init__(self, number):
        self.number = number
        self.alloc = self
    def make_loc(self):
        return CRF(self)

crfs = map(BaseCRF, range(8))

class CRF(Register):
    regclass = CR_FIELD
    def __init__(self, crf):
        Register.__init__(self)
        self.alloc = crf
        self.number = crf.number
        self.info = (-1,-1) # (bit, negated)
    def set_info(self, info):
        assert len(info) == 2
        self.info = info
    def make_loc(self):
        # should never call this on a CRF, only a BaseCRF
        raise NotImplementedError
    def move_to_gpr(self, allocator, gpr):
        bit, negated = self.info
        return _CRF2GPR(gpr, self.alloc.number*4 + bit, negated)
    def move_from_gpr(self, allocator, gpr):
        # cmp2info['ne']
        self.set_info((2, 1))
        return _GPR2CRF(self, gpr)
    def __repr__(self):
        return 'crf' + str(self.number) + str(self.info)

class CTR(Register):
    regclass = CT_REGISTER
    def move_from_gpr(self, allocator, gpr):
        return _GPR2CTR(gpr)

ctr = CTR()

_insn_index = [0]

class Insn(object):
    '''
    result is the Var instance that holds the result, or None
    result_regclass is the class of the register the result goes into

    reg_args is the vars that need to have registers allocated for them
    reg_arg_regclasses is the type of register that needs to be allocated
    '''
    def __init__(self):
        self._magic_index = _insn_index[0]
        _insn_index[0] += 1
    def __repr__(self):
        return "<%s %d>" % (self.__class__.__name__, self._magic_index)
    def emit(self, asm):
        pass

class Insn_GPR__GPR_GPR(Insn):
    def __init__(self, methptr, result, args):
        Insn.__init__(self)
        self.methptr = methptr

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER]

        self.result_reg = None
        self.arg_reg1 = None
        self.arg_reg2 = None

    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
        self.arg_reg1 = allocator.loc_of(self.reg_args[0])
        self.arg_reg2 = allocator.loc_of(self.reg_args[1])

    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        if self.arg_reg1:
            a1 = "%s@%s"%(self.reg_args[0], self.arg_reg1)
        else:
            a1 = str(self.reg_args[0])
        if self.arg_reg2:
            a2 = "%s@%s"%(self.reg_args[1], self.arg_reg2)
        else:
            a2 = str(self.reg_args[1])
        return "<%s-%s %s %s, %s, %s>" % (self.__class__.__name__, self._magic_index,
                                          self.methptr.im_func.func_name,
                                          r, a1, a2)

    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.arg_reg1.number,
                     self.arg_reg2.number)

class Insn_GPR__GPR_IMM(Insn):
    def __init__(self, methptr, result, args):
        Insn.__init__(self)
        self.methptr = methptr
        self.imm = args[1]

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = [args[0]]
        self.reg_arg_regclasses = [GP_REGISTER]
        self.result_reg = None
        self.arg_reg = None
    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
        self.arg_reg = allocator.loc_of(self.reg_args[0])
    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        if self.arg_reg:
            a = "%s@%s"%(self.reg_args[0], self.arg_reg)
        else:
            a = str(self.reg_args[0])
        return "<%s-%d %s %s, %s, (%s)>" % (self.__class__.__name__, self._magic_index,
                                            self.methptr.im_func.func_name,
                                            r, a, self.imm.value)

    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.arg_reg.number,
                     self.imm.value)

class Insn_GPR__GPR(Insn):
    def __init__(self, methptr, result, arg):
        Insn.__init__(self)
        self.methptr = methptr

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = [arg]
        self.reg_arg_regclasses = [GP_REGISTER]

        self.result_reg = None
        self.arg_reg = None
    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
        self.arg_reg = allocator.loc_of(self.reg_args[0])
    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        if self.arg_reg:
            a = "%s@%s"%(self.reg_args[0], self.arg_reg)
        else:
            a = str(self.reg_args[0])
        return "<%s-%d %s %s, %s>" % (self.__class__.__name__, self._magic_index,
                                   self.methptr.im_func.func_name, r, a)
    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.arg_reg.number)


class Insn_GPR(Insn):
    def __init__(self, methptr, result):
        Insn.__init__(self)
        self.methptr = methptr

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result_reg = None
    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        return "<%s-%d %s %s>" % (self.__class__.__name__, self._magic_index,
                                  self.methptr.im_func.func_name, r)
    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number)

class Insn_GPR__IMM(Insn):
    def __init__(self, methptr, result, args):
        Insn.__init__(self)
        self.methptr = methptr
        self.imm = args[0]

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result_reg = None
    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        return "<%s-%d %s %s, (%s)>" % (self.__class__.__name__, self._magic_index,
                                        self.methptr.im_func.func_name, r,
                                        self.imm.value)
    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.imm.value)

class MoveCRB2GPR(Insn):
    def __init__(self, result, gv_condition):
        Insn.__init__(self)
        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = [gv_condition]
        self.reg_arg_regclasses = [CR_FIELD]
    def allocate(self, allocator):
        self.targetreg = allocator.loc_of(self.result)
        self.crf = allocator.loc_of(self.reg_args[0])
    def emit(self, asm):
        assert isinstance(self.crf, CRF)
        bit, negated = self.crf.info
        asm.mfcr(self.targetreg.number)
        asm.extrwi(self.targetreg.number, self.targetreg.number, 1, self.crf.number*4+bit)
        if negated:
            asm.xori(self.targetreg.number, self.targetreg.number, 1)

class Insn_None__GPR_GPR_IMM(Insn):
    def __init__(self, methptr, args):
        Insn.__init__(self)
        self.methptr = methptr
        self.imm = args[2]

        self.result = None
        self.result_regclass = NO_REGISTER
        self.reg_args = args[:2]
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER]
    def allocate(self, allocator):
        self.reg1 = allocator.loc_of(self.reg_args[0])
        self.reg2 = allocator.loc_of(self.reg_args[1])
    def __repr__(self):
        return "<%s %s %d>" % (self.__class__.__name__, self.methptr.im_func.func_name, self._magic_index)

    def emit(self, asm):
        self.methptr(asm,
                     self.reg1.number,
                     self.reg2.number,
                     self.imm.value)

class Insn_None__GPR_GPR_GPR(Insn):
    def __init__(self, methptr, args):
        Insn.__init__(self)
        self.methptr = methptr

        self.result = None
        self.result_regclass = NO_REGISTER
        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER, GP_REGISTER]
    def allocate(self, allocator):
        self.reg1 = allocator.loc_of(self.reg_args[0])
        self.reg2 = allocator.loc_of(self.reg_args[1])
        self.reg3 = allocator.loc_of(self.reg_args[2])
    def __repr__(self):
        return "<%s %s %d>" % (self.__class__.__name__, self.methptr.im_func.func_name, self._magic_index)

    def emit(self, asm):
        self.methptr(asm,
                     self.reg1.number,
                     self.reg2.number,
                     self.reg3.number)

class Extrwi(Insn):
    def __init__(self, result, source, size, bit):
        Insn.__init__(self)

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = [source]
        self.reg_arg_regclasses = [GP_REGISTER]
        self.result_reg = None
        self.arg_reg = None

        self.size = size
        self.bit = bit
    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
        self.arg_reg = allocator.loc_of(self.reg_args[0])
    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        if self.arg_reg:
            a = "%s@%s"%(self.reg_args[0], self.arg_reg)
        else:
            a = str(self.reg_args[0])
        return "<%s-%d extrwi %s, %s, %s, %s>" % (self.__class__.__name__, self._magic_index,
                                                  r, a, self.size, self.bit)

    def emit(self, asm):
        asm.extrwi(self.result_reg.number,
                   self.arg_reg.number,
                   self.size, self.bit)


class CMPInsn(Insn):
    def __init__(self, info, result):
        Insn.__init__(self)
        self.info = info
        self.result = result
        self.result_reg = None

    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
        assert isinstance(self.result_reg, CRF)
        self.result_reg.set_info(self.info)

class CMPW(CMPInsn):
    def __init__(self, info, result, args):
        CMPInsn.__init__(self, info, result)
        self.result_regclass = CR_FIELD
        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER]
        self.arg_reg1 = None
        self.arg_reg2 = None

    def allocate(self, allocator):
        CMPInsn.allocate(self, allocator)
        self.arg_reg1 = allocator.loc_of(self.reg_args[0])
        self.arg_reg2 = allocator.loc_of(self.reg_args[1])

    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        if self.arg_reg1:
            a1 = "%s@%s"%(self.reg_args[0], self.arg_reg1)
        else:
            a1 = str(self.reg_args[0])
        if self.arg_reg2:
            a2 = "%s@%s"%(self.reg_args[1], self.arg_reg2)
        else:
            a2 = str(self.reg_args[1])
        return "<%s-%d %s %s, %s, %s>"%(self.__class__.__name__, self._magic_index,
                                        self.__class__.__name__.lower(),
                                        r, a1, a2)

    def emit(self, asm):
        asm.cmpw(self.result_reg.number, self.arg_reg1.number, self.arg_reg2.number)

class CMPWL(CMPW):
    def emit(self, asm):
        asm.cmplw(self.result_reg.number, self.arg_reg1.number, self.arg_reg2.number)

class CMPWI(CMPInsn):
    def __init__(self, info, result, args):
        CMPInsn.__init__(self, info, result)
        self.imm = args[1]
        self.result_regclass = CR_FIELD
        self.reg_args = [args[0]]
        self.reg_arg_regclasses = [GP_REGISTER]
        self.arg_reg = None

    def allocate(self, allocator):
        CMPInsn.allocate(self, allocator)
        self.arg_reg = allocator.loc_of(self.reg_args[0])

    def __repr__(self):
        if self.result_reg:
            r = "%s@%s"%(self.result, self.result_reg)
        else:
            r = str(self.result)
        if self.arg_reg:
            a = "%s@%s"%(self.reg_args[0], self.arg_reg)
        else:
            a = str(self.reg_args[0])
        return "<%s-%d %s %s, %s, (%s)>"%(self.__class__.__name__, self._magic_index,
                                        self.__class__.__name__.lower(),
                                        r, a, self.imm.value)
    def emit(self, asm):
        #print "CMPWI", asm.mc.tell()
        asm.cmpwi(self.result_reg.number, self.arg_reg.number, self.imm.value)

class CMPWLI(CMPW):
    def emit(self, asm):
        asm.cmplwi(self.result_reg.number, self.arg_reg.number, self.imm.value)


## class MTCTR(Insn):
##     def __init__(self, result, args):
##         Insn.__init__(self)
##         self.result = result
##         self.result_regclass = CT_REGISTER

##         self.reg_args = args
##         self.reg_arg_regclasses = [GP_REGISTER]

##     def allocate(self, allocator):
##         self.arg_reg = allocator.loc_of(self.reg_args[0])

##     def emit(self, asm):
##         asm.mtctr(self.arg_reg.number)

class Jump(Insn):
    def __init__(self, gv_cond, targetbuilder, jump_if_true, jump_args_gv):
        Insn.__init__(self)
        self.gv_cond = gv_cond
        self.jump_if_true = jump_if_true

        self.result = None
        self.result_regclass = NO_REGISTER
        self.reg_args = [gv_cond]
        self.reg_arg_regclasses = [CR_FIELD]
        self.crf = None

        self.jump_args_gv = jump_args_gv
        self.targetbuilder = targetbuilder
    def allocate(self, allocator):
        self.crf = allocator.loc_of(self.reg_args[0])
        assert self.crf.info[0] != -1

        assert self.targetbuilder.initial_var2loc is None
        self.targetbuilder.initial_var2loc = {}
        from pypy.jit.codegen.ppc.rgenop import Var
        for gv_arg in self.jump_args_gv:
            if isinstance(gv_arg, Var):
                self.targetbuilder.initial_var2loc[gv_arg] = allocator.var2loc[gv_arg]
        allocator.builders_to_tell_spill_offset_to.append(self.targetbuilder)
    def __repr__(self):
        if self.jump_if_true:
            op = 'if_true'
        else:
            op = 'if_false'
        if self.crf:
            a = '%s@%s'%(self.reg_args[0], self.crf)
        else:
            a = self.reg_args[0]
        return '<%s-%d %s %s>'%(self.__class__.__name__, self._magic_index,
                                op, a)
    def emit(self, asm):
        if self.targetbuilder.start:
            asm.load_word(rSCRATCH, self.targetbuilder.start)
        else:
            self.targetbuilder.patch_start_here = asm.mc.tell()
            asm.load_word(rSCRATCH, 0)
        asm.mtctr(rSCRATCH)
        bit, negated = self.crf.info
        assert bit != -1
        if negated ^ self.jump_if_true:
            BO = 12 # jump if relavent bit is set in the CR
        else:
            BO = 4  # jump if relavent bit is NOT set in the CR
        asm.bcctr(BO, self.crf.number*4 + bit)

class Label(Insn):
    def __init__(self, label):
        Insn.__init__(self)
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result_regclass =  NO_REGISTER
        self.result = None
        self.label = label
    def allocate(self, allocator):
        for gv in self.label.args_gv:
            loc = allocator.loc_of(gv)
            if isinstance(loc, CRF):
                allocator.forget(gv, loc)
                allocator.lru.remove(gv)
                allocator.freeregs[loc.regclass].append(loc.alloc)
                new_loc = allocator._allocate_reg(GP_REGISTER, gv)
                allocator.lru.append(gv)
                allocator.insns.append(loc.move_to_gpr(allocator, new_loc.number))
                loc = new_loc
        self.label.arg_locations = []
        for gv in self.label.args_gv:
            loc = allocator.loc_of(gv)
            self.label.arg_locations.append(loc)
        allocator.labels_to_tell_spill_offset_to.append(self.label)
    def __repr__(self):
        if hasattr(self.label, 'arg_locations'):
            arg_locations = '[' + ', '.join(
                ['%s@%s'%(gv, loc) for gv, loc in
                 zip(self.label.args_gv, self.label.arg_locations)]) + ']'
        else:
            arg_locations = str(self.label.args_gv)
        return '<Label-%s %s>'%(self._magic_index,
                                arg_locations)
    def emit(self, asm):
        self.label.startaddr = asm.mc.tell()

class LoadFramePointer(Insn):
    def __init__(self, result):
        Insn.__init__(self)
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result = result
        self.result_regclass = GP_REGISTER
    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
    def emit(self, asm):
        asm.mr(self.result_reg.number, rFP)

class CopyIntoStack(Insn):
    def __init__(self, place, v):
        Insn.__init__(self)
        self.reg_args = [v]
        self.reg_arg_regclasses = [GP_REGISTER]
        self.result = None
        self.result_regclass = NO_REGISTER
        self.place = place
    def allocate(self, allocator):
        self.arg_reg = allocator.loc_of(self.reg_args[0])
        self.target_slot = allocator.spill_slot()
        self.place.offset = self.target_slot.offset
    def emit(self, asm):
        asm.stw(self.arg_reg.number, rFP, self.target_slot.offset)

class CopyOffStack(Insn):
    def __init__(self, v, place):
        Insn.__init__(self)
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result = v
        self.result_regclass = GP_REGISTER
        self.place = place
    def allocate(self, allocator):
        self.result_reg = allocator.loc_of(self.result)
        allocator.free_stack_slots.append(stack_slot(self.place.offset))
    def emit(self, asm):
        asm.lwz(self.result_reg.number, rFP, self.place.offset)

class SpillCalleeSaves(Insn):
    def __init__(self):
        Insn.__init__(self)
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result = None
        self.result_regclass = NO_REGISTER
    def allocate(self, allocator):
        # cough cough cough
        callersave = gprs[3:13]
        for v in allocator.var2loc:
            loc = allocator.loc_of(v)
            if loc in callersave:
                allocator.spill(loc, v)
                allocator.freeregs[GP_REGISTER].append(loc)
    def emit(self, asm):
        pass

class LoadArg(Insn):
    def __init__(self, argnumber, arg):
        Insn.__init__(self)
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result = None
        self.result_regclass = NO_REGISTER

        self.argnumber = argnumber
        self.arg = arg
    def allocate(self, allocator):
        from pypy.jit.codegen.ppc.rgenop import Var
        if isinstance(self.arg, Var):
            self.loc = allocator.loc_of(self.arg)
        else:
            self.loc = None
    def emit(self, asm):
        if self.argnumber < 8: # magic numbers 'r' us
            targetreg = 3+self.argnumber
            if self.loc is None:
                self.arg.load_now(asm, gprs[targetreg])
            elif self.loc.is_register:
                asm.mr(targetreg, self.loc.number)
            else:
                asm.lwz(targetreg, rFP, self.loc.offset)
        else:
            targetoffset = 24+self.argnumber*4
            if self.loc is None:
                self.arg.load_now(asm, gprs[0])
                asm.stw(r0, r1, targetoffset)
            elif self.loc.is_register:
                asm.stw(self.loc.number, r1, targetoffset)
            else:
                asm.lwz(r0, rFP, self.loc.offset)
                asm.stw(r0, r1, targetoffset)

class CALL(Insn):
    def __init__(self, result, target):
        Insn.__init__(self)
        from pypy.jit.codegen.ppc.rgenop import Var
        if isinstance(target, Var):
            self.reg_args = [target]
            self.reg_arg_regclasses = [CT_REGISTER]
        else:
            self.reg_args = []
            self.reg_arg_regclasses = []
            self.target = target
        self.result = result
        self.result_regclass = GP_REGISTER
    def allocate(self, allocator):
        if self.reg_args:
            assert allocator.loc_of(self.reg_args[0]) is ctr
        self.resultreg = allocator.loc_of(self.result)
    def emit(self, asm):
        if not self.reg_args:
            self.target.load_now(asm, gprs[0])
            asm.mtctr(0)
        asm.bctrl()
        asm.lwz(rFP, rSP, 0)
        if self.resultreg != gprs[3]:
            asm.mr(self.resultreg.number, 3)


class AllocTimeInsn(Insn):
    def __init__(self):
        Insn.__init__(self)
        self.reg_args = []
        self.reg_arg_regclasses = []
        self.result_regclass =  NO_REGISTER
        self.result = None

class Move(AllocTimeInsn):
    def __init__(self, dest, src):
        AllocTimeInsn.__init__(self)
        self.dest = dest
        self.src = src
    def emit(self, asm):
        asm.mr(self.dest.number, self.src.number)

class Load(AllocTimeInsn):
    def __init__(self, dest, const):
        AllocTimeInsn.__init__(self)
        self.dest = dest
        self.const = const
    def __repr__(self):
        return "<Load-%d %s, (%s)>"%(self._magic_index, self.dest, self.const)
    def emit(self, asm):
        self.const.load_now(asm, self.dest)

class Unspill(AllocTimeInsn):
    """ A special instruction inserted by our register "allocator."  It
    indicates that we need to load a value from the stack into a register
    because we spilled a particular value. """
    def __init__(self, var, reg, stack):
        """
        var --- the var we spilled (a Var)
        reg --- the reg we spilled it from (an integer)
        offset --- the offset on the stack we spilled it to (an integer)
        """
        AllocTimeInsn.__init__(self)
        self.var = var
        self.reg = reg
        self.stack = stack
        if not isinstance(self.reg, GPR):
            assert isinstance(self.reg, CRF)
            self.moveinsn = self.reg.move_from_gpr(None, 0)
        else:
            self.moveinsn = None
    def __repr__(self):
        return '<Unspill-%d %s: %s, %s>'%(self._magic_index, self.var, self.reg, self.stack)
    def emit(self, asm):
        if isinstance(self.reg, GPR):
            r = self.reg.number
        else:
            r = 0
        asm.lwz(r, rFP, self.stack.offset)
        if self.moveinsn:
            self.moveinsn.emit(asm)

class Spill(AllocTimeInsn):
    """ A special instruction inserted by our register "allocator."
    It indicates that we need to store a value from the register into
    the stack because we spilled a particular value."""
    def __init__(self, var, reg, stack):
        """
        var --- the var we are spilling (a Var)
        reg --- the reg we are spilling it from (an integer)
        offset --- the offset on the stack we are spilling it to (an integer)
        """
        AllocTimeInsn.__init__(self)
        self.var = var
        self.reg = reg
        self.stack = stack
    def __repr__(self):
        return '<Spill-%d %s: %s, %s>'%(self._magic_index, self.var, self.stack, self.reg)
    def emit(self, asm):
        if isinstance(self.reg, GPR):
            r = self.reg.number
        else:
            assert isinstance(self.reg, CRF)
            self.reg.move_to_gpr(None, 0).emit(asm)
            r = 0
        #print 'spilling to', self.stack.offset
        asm.stw(r, rFP, self.stack.offset)

class _CRF2GPR(AllocTimeInsn):
    def __init__(self, targetreg, bit, negated):
        AllocTimeInsn.__init__(self)
        self.targetreg = targetreg
        self.bit = bit
        self.negated = negated
    def __repr__(self):
        number = self.bit // 4
        bit = self.bit % 4
        return '<CRF2GPR-%d r%s, crf%s(%s, %s)>' % (
            self._magic_index, self.targetreg, number, bit, self.negated)
    def emit(self, asm):
        asm.mfcr(self.targetreg)
        asm.extrwi(self.targetreg, self.targetreg, 1, self.bit)
        if self.negated:
            asm.xori(self.targetreg, self.targetreg, 1)

class _GPR2CRF(AllocTimeInsn):
    def __init__(self, targetreg, fromreg):
        AllocTimeInsn.__init__(self)
        self.targetreg = targetreg
        self.fromreg = fromreg
    def __repr__(self):
        return '<GPR2CRF-%d %s, r%s>' % (
            self._magic_index, self.targetreg, self.fromreg)
    def emit(self, asm):
        asm.cmpwi(self.targetreg.number, self.fromreg, 0)

class _GPR2CTR(AllocTimeInsn):
    def __init__(self, fromreg):
        AllocTimeInsn.__init__(self)
        self.fromreg = fromreg
    def emit(self, asm):
        asm.mtctr(self.fromreg)

class Return(Insn):
    """ Ensures the return value is in r3 """
    def __init__(self, var):
        Insn.__init__(self)
        self.var = var
        self.reg_args = [self.var]
        self.reg_arg_regclasses = [GP_REGISTER]
        self.result = None
        self.result_regclass = NO_REGISTER
        self.reg = None
    def allocate(self, allocator):
        self.reg = allocator.loc_of(self.reg_args[0])
    def emit(self, asm):
        if self.reg.number != 3:
            asm.mr(r3, self.reg.number)

class FakeUse(Insn):
    """ A fake use of a var to get it into a register.  And reserving
    a condition register field."""
    def __init__(self, rvar, var):
        Insn.__init__(self)
        self.var = var
        self.reg_args = [self.var]
        self.reg_arg_regclasses = [GP_REGISTER]
        self.result = rvar
        self.result_regclass = CR_FIELD
    def allocate(self, allocator):
        pass
    def emit(self, asm):
        pass
