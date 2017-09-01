from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import (Const, ConstInt, ConstPtr,
    ConstFloat, INT, REF, FLOAT, VECTOR, TargetToken, AbstractFailDescr)
from rpython.jit.backend.llsupport.descr import CallDescr
from rpython.jit.backend.x86.regloc import (FrameLoc, RegLoc, ConstFloatLoc,
    FloatImmedLoc, ImmedLoc, imm, imm0, imm1, ecx, eax, edx, ebx, esi, edi,
    ebp, r8, r9, r10, r11, r12, r13, r14, r15, xmm0, xmm1, xmm2, xmm3, xmm4,
    xmm5, xmm6, xmm7, xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14,
    X86_64_SCRATCH_REG, X86_64_XMM_SCRATCH_REG,)
from rpython.jit.backend.x86 import rx86


from rpython.jit.backend.x86.regalloc import (
    X86_64_RegisterManager, X86_64_XMMRegisterManager)

# tell the register allocator hints about which variables should be placed in
# what registers (those are just hints, the register allocator will try its
# best to achieve that).


class X86RegisterHints(object):
    def add_hints(self, longevity, inputargs, operations):
        self.longevity = longevity
        for i in range(len(operations)):
            op = operations[i]
            oplist[op.getopnum()](self, op, i)

    def not_implemented_op(self, op, position):
        # no hint by default
        pass

    def _consider_binop_part(self, op, position, symm=False):
        x = op.getarg(0)
        y = op.getarg(1)

        # For symmetrical operations, if 'y' is already in a register
        # and won't be used after the current operation finishes,
        # then swap the role of 'x' and 'y'
        if self.longevity[x].last_usage > position:
            if self.longevity[y].last_usage == position:
                x, y = y, x
                self.longevity.try_use_same_register(y, op)
        else:
            self.longevity.try_use_same_register(x, op)

    def _consider_binop(self, op, position):
        self._consider_binop_part(op, position)

    def _consider_binop_symm(self, op, position):
        self._consider_binop_part(op, position, symm=True)

    #consider_int_mul = _consider_binop_symm
    #consider_int_and = _consider_binop_symm
    #consider_int_or  = _consider_binop_symm
    #consider_int_xor = _consider_binop_symm

    #consider_int_mul_ovf = _consider_binop_symm
    #consider_int_sub_ovf = _consider_binop
    consider_int_add_ovf = _consider_binop_symm

    def _consider_lea(self, op, loc):
        argloc = self.loc(op.getarg(1))
        resloc = self.force_allocate_reg(op)
        self.perform(op, [loc, argloc], resloc)

    def consider_int_add(self, op, position):
        y = op.getarg(1)
        if isinstance(y, ConstInt) and rx86.fits_in_32bits(y.value):
            pass # nothing to be hinted
        else:
            self._consider_binop_symm(op, position)

    consider_nursery_ptr_increment = consider_int_add

    def Xconsider_int_lshift(self, op, position):
        if not isinstance(op.getarg(1), Const):
            self.longevity.fixed_register(position, ecx, op.getarg(1))

    #consider_int_rshift  = consider_int_lshift
    #consider_uint_rshift = consider_int_lshift

    def Xconsider_call_malloc_nursery(self, op, position):
        self.longevity.fixed_register(position, ecx, op)
        self.longevity.fixed_register(position, edx)

    #consider_call_malloc_nursery_varsize = consider_call_malloc_nursery
    #consider_call_malloc_nursery_varsize_frame = consider_call_malloc_nursery


    def _call(self, op, position, args, save_all_regs=False):
        # XXX fish for correct argtypes
        CallHints64(self.longevity).hint(position, args, [], save_all_regs)

    def _consider_call(self, op, position, guard_not_forced=False, first_arg_index=1):
        calldescr = op.getdescr()
        assert isinstance(calldescr, CallDescr)
        effectinfo = calldescr.get_extra_info()
        # XXX this is nonsense, share the code somehow
        if guard_not_forced:
            gc_level = 2
        elif effectinfo is None or effectinfo.check_can_collect():
            gc_level = 1
        else:
            gc_level = 0
        self._call(op, position, op.getarglist()[first_arg_index:],
                   save_all_regs=gc_level)

    def _consider_real_call(self, op, position):
        effectinfo = op.getdescr().get_extra_info()
        assert effectinfo is not None
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex != EffectInfo.OS_NONE:
            raise NotImplementedError
        self._consider_call(op, position)

    consider_call_i = _consider_real_call
    consider_call_r = _consider_real_call
    consider_call_f = _consider_real_call
    consider_call_n = _consider_real_call

oplist = [X86RegisterHints.not_implemented_op] * rop._LAST

for name, value in X86RegisterHints.__dict__.iteritems():
    if name.startswith('consider_'):
        name = name[len('consider_'):]
        num = getattr(rop, name.upper())
        oplist[num] = value



class CallHints64(object):

    ARGUMENTS_GPR = [edi, esi, edx, ecx, r8, r9]
    ARGUMENTS_XMM = [xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7]
    _ALL_CALLEE_SAVE_GPR = [ebx, r12, r13, r14, r15]

    next_arg_gpr = 0
    next_arg_xmm = 0

    def __init__(self, longevity):
        self.longevity = longevity

    def _unused_gpr(self):
        i = self.next_arg_gpr
        self.next_arg_gpr = i + 1
        try:
            res = self.ARGUMENTS_GPR[i]
        except IndexError:
            return None
        return res

    def _unused_xmm(self):
        i = self.next_arg_xmm
        self.next_arg_xmm = i + 1
        try:
            return self.ARGUMENTS_XMM[i]
        except IndexError:
            return None

    def hint(self, position, args, argtypes, save_all_regs):
        import pdb; pdb.set_trace()
        hinted_xmm = []
        hinted_gpr = []
        for i in range(len(args)):
            arg = args[i]
            if arg.type == "f":
                tgt = self._unused_xmm()
                if tgt is not None and not arg.is_constant():
                    self.longevity.fixed_register(position, tgt, arg)
                    hinted_xmm.append(tgt)
            elif i < len(argtypes) and argtypes[i] == 'S':
                # Singlefloat argument
                tgt = self._unused_xmm()
                if tgt is not None and not arg.is_constant():
                    self.longevity.fixed_register(position, tgt, arg)
                    hinted_xmm.append(tgt)
            else:
                tgt = self._unused_gpr()
                if tgt is not None and not arg.is_constant():
                    self.longevity.fixed_register(position, tgt, arg)
                    hinted_gpr.append(tgt)
        # block all remaining registers that are not caller save
        # XXX the case save_all_regs == 1 (save callee-save regs + gc ptrs) is
        # no expressible atm
        if save_all_regs == 2:
            regs = X86_64_RegisterManager.all_regs
        else:
            regs = X86_64_RegisterManager.save_around_call_regs
        for reg in regs:
            if reg not in hinted_gpr:
                self.longevity.fixed_register(position, reg)
        for reg in X86_64_XMMRegisterManager.all_regs:
            if reg not in hinted_xmm:
                self.longevity.fixed_register(position, reg)
