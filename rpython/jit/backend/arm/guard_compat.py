from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.backend.arm import conditions as c
from rpython.jit.backend.arm import registers as r
from rpython.jit.backend.llsupport.guard_compat import *
from rpython.jit.backend.llsupport.guard_compat import _real_number


# See comments in ../x86/guard_compat.py.


def build_once(assembler):
    """Generate the 'search_tree' block of code"""
    # Called with lr containing the BACKEND_CHOICES object, and r1
    # containing the actual value of the guard.  The old value of r1
    # is pushed on the stack.  Additionally, r0 and lr are already
    # pushed on the stack as well (the same values as the one passed
    # in).

    mc = PPCBuilder()
    r0 = r.r0
    r1 = r.r1
    lr = r.lr
    ip = r.ip

    ofs1 = _real_number(BCLIST + BCLISTLENGTHOFS)
    ofs2 = _real_number(BCLIST + BCLISTITEMSOFS)
    mc.LDR_ri(r0.value, lr.value, ofs1)    # LDR r0, [lr + bc_list.length]
    mc.ADD_ri(lr.value, lr.value, imm=ofs2 - WORD)   # ADD lr, lr, $items - 4
    # ^^^ NB. this could be done with a single LDR in "pre-indexed" mode
    mc.LSL_ri(r0.value, r0.value, 2)       # LSL r0, r0, 2
    # in the sequel, "lr + 4" is a pointer to the leftmost array item of
    # the range still under consideration.  The length of this range,
    # which is always a power-of-two-minus-1, is equal to "r0 / 4".
    b_location = mc.currpos()
    mc.BKPT()                              # B loop

    right_label = mc.get_relative_pos()
    mc.ADD_rr(lr.value, lr.value, r0.value)# ADD lr, lr, r0
    mc.ADD_ri(lr.value, lr.value, WORD)    # ADD lr, lr, 4
    left_label = mc.get_relative_pos()
    mc.LSR_ri(r0.value, r0.value, 1)       # LSR r0, r0, 1
    mc.SUBS_ri(r0.value, r0.value, 4)      # SUBS r0, r0, 4
    beq_location = mc.get_relative_pos()
    mc.trap()                              # BEQ not_found
    #                                     loop:
    pmc = OverwritingBuilder(mc, b_location, WORD)
    pmc.B_offs(mc.currpos(), c.AL)
    mc.LDR_rr(ip.value, lr.value, r0.value)# LDR ip, [lr + r0]
    mc.CMP_rr(r1.value, ip.value)          # CMP r1, ip
    mc.B_offs(right_label - mc.currpos(), c.GT)  # BGT right_label
    mc.B_offs(left_label - mc.currpos(), c.NE)   # BNE left_label

    #                                  found:
    mc.ADD_rr(ip.value, lr.value, r0.value)# ADD ip, lr, r0
    mc.LDR_ri(ip.value, ip.value, WORD)    # LDR ip, [ip + 4]

    mc.POP([lr.value])                     # POP {lr}

    ofs = _real_number(BCMOSTRECENT)
    mc.STR(r1.value, lr.value, ofs)        # STR r1, [lr + bc_most_recent]
    mc.STR(ip.value, lr.value, ofs + WORD) # STR ip, [lr + bc_most_recent + 4]

    mc.POP([r0.value, r1.value])           # POP {r0, r1}
    mc.BX(ip.value)                        # BX ip

    # ----------

    #                                     not_found:
    pmc = OverwritingBuilder(mc, beq_location, 1)
    pmc.B(mc.currpos() - beq_location, cond.EQ)    # jump here if r0 is now 0
    pmc.overwrite()

    # save all registers to the jitframe, expect r0 and r1
    assembler._push_all_regs_to_jitframe(mc, [r0, r1], withfloats=True)

    # pop the three values from the stack:
    #    r2 = saved value originally in r0
    #    r3 = saved value originally in r1
    #    lr = BACKEND_CHOICES object
    mc.POP([r2.value, r3.value, lr.value])

    # save r2 and r3 into the jitframe, at locations for r0 and r1
    assert r.all_regs[0] is r0
    assert r.all_regs[1] is r1
    base_ofs = assembler.cpu.get_baseofs_of_frame_field()
    assembler.store_reg(mc, r2, r.fp, base_ofs + 0 * WORD)
    assembler.store_reg(mc, r3, r.fp, base_ofs + 1 * WORD)

    # arg #1 (r0): the BACKEND_CHOICES objects, from the original value of lr
    # arg #2 (r1): the actual value of the guard, already in r1
    # arg #3 (r2): the jitframe
    mc.MOV_rr(r0.value, lr.value)
    mc.MOV_rr(r2.value, r.fp.value)

    invoke_find_compatible = make_invoke_find_compatible(assembler.cpu)
    llfunc = llhelper(INVOKE_FIND_COMPATIBLE_FUNC, invoke_find_compatible)
    llfunc = assembler.cpu.cast_ptr_to_int(llfunc)
    mc.BL(llfunc)
    assembler._reload_frame_if_necessary(mc)
    mc.MOV_rr(lr.value, r0.value)

    # restore the registers that the CALL has clobbered, plus the ones
    # containing GC pointers that may have moved.  That means we just
    # restore them all.
    assembler._pop_all_regs_from_jitframe(mc, [], withfloats=True)

    mc.BX(lr.value)                  # jump to the return value above

    assembler.guard_compat_search_tree = mc.materialize(assembler.cpu, [])

    print hex(assembler.guard_compat_search_tree)
    raw_input('press enter...')


def generate_guard_compatible(assembler, guard_token, l0, bindex):
    mc = assembler.mc
    ip = r.ip
    lr = r.lr
    r4 = r.r4

    assembler.load_from_gc_table(lr.value, bindex)  # LDR lr, [gctbl at bindex]

    ofs = _real_number(BCMOSTRECENT)
    mc.LDR_ri(ip.value, lr.value, ofs)      # LDR ip, [lr + bc_most_recent]
    mc.CMP_rr(l0.value, ip.value)           # CMP l0, ip

    mc.LDR_ri(ip.value, lr.value,           # LDR.EQ ip, [lr + most_recent + 8]
              ofs + WORD, cond=c.EQ)
    mc.BR(ip.value, cond=c.EQ)              # BR.EQ ip

    mc.PUSH([r0.value, r1.value, lr.value]) # PUSH {r0, r1, lr}
    mc.MOV_rr(r1.value, l0.value)           # MOV r1, l0
    mc.BL(assembler.guard_compat_search_tree)   # MOVW/MOVT ip, BLX ip

    # abuse this field to store the 'sequel' relative offset
    guard_token.pos_jump_offset = mc.get_relative_pos()
    guard_token.guard_compat_bindex = bindex
