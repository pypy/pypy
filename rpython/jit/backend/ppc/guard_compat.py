from rpython.rtyper.annlowlevel import llhelper
import rpython.jit.backend.ppc.register as r
from rpython.jit.backend.ppc.arch import WORD, PARAM_SAVE_AREA_OFFSET
from rpython.jit.backend.ppc.codebuilder import PPCBuilder, OverwritingBuilder

from rpython.jit.backend.llsupport.guard_compat import *
from rpython.jit.backend.llsupport.guard_compat import _real_number


# See comments in ../x86/guard_compat.py.


MANAGED_REGS_WITHOUT_R7_AND_R10 = list(r.MANAGED_REGS)
MANAGED_REGS_WITHOUT_R7_AND_R10.remove(r.r7)
MANAGED_REGS_WITHOUT_R7_AND_R10.remove(r.r10)


def build_once(assembler):
    """Generate the 'search_tree' block of code"""
    # called with r2 containing the BACKEND_CHOICES object,
    # and r0 containing the actual value of the guard

    mc = PPCBuilder()
    r0 = r.SCRATCH
    r2 = r.SCRATCH2
    r3 = r.r3
    r4 = r.r4
    r5 = r.r5
    r7 = r.r7
    r10 = r.r10

    # save the values of r7 and r10 in the jitframe
    assembler._push_core_regs_to_jitframe(mc, [r7, r10])

    # save the original value of r2 for later
    mc.std(r2.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)

    ofs1 = _real_number(BCLIST + BCLISTLENGTHOFS)
    ofs2 = _real_number(BCLIST + BCLISTITEMSOFS)
    assert ofs2 - 8 == ofs1
    mc.ldu(r10.value, r2.value, ofs1)       # ldu  r10, [r2 + bc_list.length]
    mc.sldi(r10.value, r10.value, 3)        # sldi r10, r10, 3
    b_location = mc.get_relative_pos()
    mc.trap()                               # b loop

    right_label = mc.get_relative_pos()
    mc.add(r2.value, r2.value, r10.value)   # add r2, r2, r10
    mc.addi(r2.value, r2.value, WORD)       # addi r2, r2, 8
    left_label = mc.get_relative_pos()
    mc.rldicr(r10.value, r10.value, 63, 60) # rldicr r10, r10, 63, 60
    # ^^ note: this does r10 = (r10 >> 1) & ~7
    mc.cmp_op(0, r10.value, 8, imm=True)    # cmp r10, 8
    blt_location = mc.get_relative_pos()
    mc.trap()                               # beq not_found
    #                                     loop:
    pmc = OverwritingBuilder(mc, b_location, 1)
    pmc.b(mc.currpos() - b_location)        # jump here unconditionally
    pmc.overwrite()
    mc.ldx(r7.value, r2.value, r10.value)   # ldx r7, [r2 + r10]
    mc.cmp_op(0, r0.value, r7.value,
              signed=False)                 # cmp r0, r7
    mc.bgt(right_label - mc.currpos())      # bgt right_label
    mc.bne(left_label - mc.currpos())       # bne left_label

    #                                     found:
    mc.add(r2.value, r2.value, r10.value)   # add r2, r2, r10
    mc.ld(r10.value, r2.value, 8)           # ld r10, [r2 + 8]

    # restore the value of r2 from the stack
    mc.ld(r2.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)    # ld r2, [sp + ..]

    ofs = _real_number(BCMOSTRECENT)
    mc.std(r0.value, r2.value, ofs)         # std r0, [r2 + bc_most_recent]
    mc.std(r10.value, r2.value, ofs + WORD) # std r0, [r2 + bc_most_recent + 8]
    mc.mtctr(r10.value)

    # restore the values of r7 and r10 from the jitframe
    assembler._pop_core_regs_from_jitframe(mc, [r7, r10])

    mc.bctr()                               # jump to the old r10

    # ----------

    #                                     not_found:
    pmc = OverwritingBuilder(mc, blt_location, 1)
    pmc.blt(mc.currpos() - blt_location)    # jump here if r10 < 8
    pmc.overwrite()

    # save all other registers to the jitframe SPP, in addition to
    # r7 and r10 which have already been saved
    assembler._push_core_regs_to_jitframe(mc, MANAGED_REGS_WITHOUT_R7_AND_R10)
    assembler._push_fp_regs_to_jitframe(mc)

    # arg #1 (r3): the BACKEND_CHOICES objects, from the original value of r2
    # arg #2 (r4): the actual value of the guard, from r0
    # arg #3 (r5): the jitframe
    mc.ld(r3.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)    # ld r3, [sp + ..]
    mc.mr(r4.value, r0.value)
    mc.mr(r5.value, r.SPP.value)

    invoke_find_compatible = make_invoke_find_compatible(assembler.cpu)
    llfunc = llhelper(INVOKE_FIND_COMPATIBLE_FUNC, invoke_find_compatible)
    llfunc = assembler.cpu.cast_ptr_to_int(llfunc)
    mc.load_imm(mc.RAW_CALL_REG, llfunc)
    mc.raw_call()                           # mtctr / bctrl
    assembler._reload_frame_if_necessary(mc)
    mc.mtctr(r3.value)                      # mtctr r3

    # restore the registers that the CALL has clobbered, plus the ones
    # containing GC pointers that may have moved.  That means we just
    # restore them all.
    assembler._pop_core_regs_from_jitframe(mc)
    assembler._pop_fp_regs_from_jitframe(mc)

    mc.bctr()                               # jump to the old r3

    assembler.guard_compat_search_tree = mc.materialize(assembler.cpu, [])

    #print hex(assembler.guard_compat_search_tree)
    #raw_input('press enter...')


def generate_guard_compatible(assembler, guard_token, l0, bindex):
    mc = assembler.mc
    r0 = r.SCRATCH
    r2 = r.SCRATCH2

    assembler._load_from_gc_table(r2, r2, bindex)  # ld r2, [gc tbl at bindex]

    ofs = _real_number(BCMOSTRECENT)
    mc.ld(r0.value, r2.value, ofs)          # ld r0, [r2 + bc_most_recent]
    mc.cmp_op(0, l0.value, r0.value)        # cmp l0, r0

    bne_location = mc.get_relative_pos()
    mc.trap()                               # patched later to a 'bc'

    mc.ld(r2.value, r2.value, ofs + WORD)   # ld r2, [r2 + bc_most_recent + 8]
    mc.mtctr(r2.value)
    mc.bctr()                               # jump to r2

    #                                     slowpath:
    pmc = OverwritingBuilder(mc, bne_location, 1)
    pmc.bne(mc.currpos() - bne_location)    # jump here if l0 != r0
    pmc.overwrite()

    mc.load_imm(r0, assembler.guard_compat_search_tree)
    mc.mtctr(r0.value)
    mc.mr(r0.value, l0.value)
    mc.bctr()

    # abuse this field to store the 'sequel' relative offset
    guard_token.pos_jump_offset = mc.get_relative_pos()
    guard_token.guard_compat_bindex = bindex
