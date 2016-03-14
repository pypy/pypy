from rpython.rlib import rgc
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.backend.x86.arch import WORD
from rpython.jit.backend.x86 import rx86, codebuf
from rpython.jit.backend.x86.regloc import X86_64_SCRATCH_REG, imm
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.metainterp.compile import GuardCompatibleDescr
from rpython.jit.metainterp.history import BasicFailDescr


# uses the raw structure COMPATINFO, which is informally defined like this:
# it starts with a negative 'small_ofs' value (see in the code)
# then there is an array containing all the expected values that should pass
# the guard, ending in -1.


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
        3 * WORD, alignment=WORD)
    compatinfo = rffi.cast(rffi.SIGNEDP, compatinfoaddr)
    compatinfo[1] = initial_value
    compatinfo[2] = -1

    mc.MOV_ri64(X86_64_SCRATCH_REG.value, compatinfoaddr)  # patchable
    guard_token.pos_compatinfo_offset = mc.get_relative_pos() - WORD
    mc.PUSH_r(X86_64_SCRATCH_REG.value)
    mc.CALL(imm(checker))
    mc.stack_frame_size_delta(-WORD)

    small_ofs = rel_pos_compatible_imm - mc.get_relative_pos()
    compatinfo[0] = small_ofs

    assembler.guard_success_cc = rx86.Conditions['NZ']
    assembler.implement_guard(guard_token)
    #
    # patch the JE above
    offset = mc.get_relative_pos() - je_location
    assert 0 < offset <= 127
    mc.overwrite(je_location-1, chr(offset))


def patch_guard_compatible(rawstart, tok):
    descr = tok.faildescr
    if not we_are_translated() and isinstance(descr, BasicFailDescr):
        pass    # for tests
    else:
        assert isinstance(descr, GuardCompatibleDescr)
    descr._backend_compatinfo = rawstart + tok.pos_compatinfo_offset


def grow_switch(cpu, looptoken, guarddescr, gcref):
    from rpython.jit.backend.x86.assembler import Assembler386

    # XXX is it ok to force gcref to be non-movable?
    if not rgc._make_sure_does_not_move(gcref):
        raise AssertionError("oops")
    new_value = rffi.cast(lltype.Signed, gcref)

    if not we_are_translated() and isinstance(guarddescr, BasicFailDescr):
        pass    # for tests
    else:
        assert isinstance(guarddescr, GuardCompatibleDescr)
    compatinfop = rffi.cast(rffi.VOIDPP, guarddescr._backend_compatinfo)
    compatinfo = rffi.cast(rffi.SIGNEDP, compatinfop[0])
    length = 3
    while compatinfo[length - 1] != -1:
        length += 1

    allblocks = Assembler386.get_asmmemmgr_blocks(looptoken)
    datablockwrapper = MachineDataBlockWrapper(cpu.asmmemmgr, allblocks)
    newcompatinfoaddr = datablockwrapper.malloc_aligned(
        (length + 1) * WORD, alignment=WORD)
    datablockwrapper.done()

    newcompatinfo = rffi.cast(rffi.SIGNEDP, newcompatinfoaddr)
    newcompatinfo[0] = compatinfo[0]
    newcompatinfo[1] = new_value

    for i in range(1, length):
        newcompatinfo[i + 1] = compatinfo[i]

    # the old 'compatinfo' is not used any more, but will only be freed
    # when the looptoken is freed
    compatinfop[0] = rffi.cast(rffi.VOIDP, newcompatinfo)

    # the machine code is not updated here.  We leave it to the actual
    # guard_compatible to update it if needed.


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
    mc.CMP_mr((X86_64_SCRATCH_REG.value, WORD), regnum)
    mc.J_il8(rx86.Conditions['E'], 0)    # patched below
    je_location = mc.get_relative_pos()
    mc.CMP_mi((X86_64_SCRATCH_REG.value, WORD), -1)
    mc.LEA_rm(X86_64_SCRATCH_REG.value, (X86_64_SCRATCH_REG.value, WORD))
    mc.J_il8(rx86.Conditions['NE'], pos - (mc.get_relative_pos() + 2))

    # not found!  The condition code is already 'Zero', which we return
    # to mean 'not found'.
    mc.RET16_i(WORD)

    mc.force_frame_size(WORD)

    # patch the JE above
    offset = mc.get_relative_pos() - je_location
    assert 0 < offset <= 127
    mc.overwrite(je_location-1, chr(offset))

    # found!  update the assembler by writing the value at 'small_ofs'
    # bytes before our return address.  This should overwrite the const in
    # 'MOV_ri64(r11, const)', first instruction of the guard_compatible.
    mc.INT3()
    mc.MOV_rs(X86_64_SCRATCH_REG.value, WORD)
    mc.MOV_rm(X86_64_SCRATCH_REG.value, (X86_64_SCRATCH_REG.value, 0))
    mc.ADD_rs(X86_64_SCRATCH_REG.value, 0)
    mc.MOV_mr((X86_64_SCRATCH_REG.value, -WORD), regnum)

    # the condition codes say 'Not Zero', as a result of the ADD above.
    # Return this condition code to mean 'found'.
    mc.RET16_i(WORD)

    addr = mc.materialize(assembler.cpu, [])
    assembler._guard_compat_checkers[regnum] = addr
    return addr
