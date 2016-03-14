from rpython.rtyper.lltypesystem import rffi
from rpython.jit.backend.x86.arch import WORD
from rpython.jit.backend.x86 import rx86, codebuf
from rpython.jit.backend.x86.regloc import X86_64_SCRATCH_REG, imm

# uses the raw structure COMPATINFO, which is informally defined like this:
# it is an array containing all the expected values that should pass the
# guard, terminated with a small_ofs value ( < 128, see in code).


def generate_guard_compatible(assembler, guard_token, loc_reg, initial_value):
    # fast-path check
    mc = assembler.mc
    mc.MOV_ri64(X86_64_SCRATCH_REG.value, initial_value)
    rel_pos_compatible_imm = mc.get_relative_pos()
    mc.CMP_rr(loc_reg.value, X86_64_SCRATCH_REG.value)
    mc.J_il8(rx86.Conditions['E'], 0)
    je_location = mc.get_relative_pos()

    # fast-path failed, call the slow-path checker
    checker = get_or_build_checker(assembler, loc_reg.value)

    # initialize 'compatinfo' with only 'initial_value' in it
    compatinfoaddr = assembler.datablockwrapper.malloc_aligned(
        2 * WORD, alignment=WORD)
    compatinfo = rffi.cast(rffi.SIGNEDP, compatinfoaddr)
    compatinfo[0] = initial_value

    mc.MOV_ri64(X86_64_SCRATCH_REG.value, compatinfoaddr)  # patchable
    mc.PUSH_r(X86_64_SCRATCH_REG.value)
    mc.CALL(imm(checker))
    mc.stack_frame_size_delta(-WORD)

    small_ofs = mc.get_relative_pos() - rel_pos_compatible_imm
    assert 0 <= small_ofs <= 127
    compatinfo[1] = small_ofs

    assembler.guard_success_cc = rx86.Conditions['NZ']
    assembler.implement_guard(guard_token)
    #
    # patch the JE above
    offset = mc.get_relative_pos() - je_location
    assert 0 < offset <= 127
    mc.overwrite(je_location-1, chr(offset))


def setup_once(assembler):
    nb_registers = WORD * 2
    assembler._guard_compat_checkers = [0] * nb_registers


def get_or_build_checker(assembler, regnum):
    """Returns a piece of assembler that checks if the value is in
    some array (there is one such piece per input register 'regnum')
    """
    addr = assembler._guard_compat_checkers[regnum]
    if addr != 0:
        return addr

    mc = codebuf.MachineCodeBlockWrapper()

    mc.MOV_rs(X86_64_SCRATCH_REG.value, WORD)

    pos = mc.get_relative_pos()
    mc.CMP_mr((X86_64_SCRATCH_REG.value, 0), regnum)
    mc.J_il8(rx86.Conditions['E'], 0)    # patched below
    je_location = mc.get_relative_pos()
    mc.ADD_ri(X86_64_SCRATCH_REG.value, WORD)
    mc.CMP_mi((X86_64_SCRATCH_REG.value, 0), 127)
    mc.J_il8(rx86.Conditions['NBE'], pos - (mc.get_relative_pos() + 2))

    # not found!  Return the condition code 'Zero' to mean 'not found'.
    mc.CMP_rr(regnum, regnum)
    mc.RET16_i(WORD)

    mc.force_frame_size(WORD)

    # patch the JE above
    offset = mc.get_relative_pos() - je_location
    assert 0 < offset <= 127
    mc.overwrite(je_location-1, chr(offset))

    # found!  update the assembler by writing the value at 'small_ofs'
    # bytes before our return address.  This should overwrite the const in
    # 'MOV_ri64(r11, const)', first instruction of the guard_compatible.
    mc.NEG_r(X86_64_SCRATCH_REG.value)
    mc.ADD_rs(X86_64_SCRATCH_REG.value, 0)
    mc.MOV_mr((X86_64_SCRATCH_REG.value, -WORD), regnum)

    # the condition codes say 'Not Zero', as a result of the ADD above.
    # Return this condition code to mean 'found'.
    mc.RET16_i(WORD)

    addr = mc.materialize(assembler.cpu, [])
    assembler._guard_compat_checkers[regnum] = addr
    return addr
