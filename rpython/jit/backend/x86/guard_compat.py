from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.backend.x86 import rx86, codebuf, regloc
from rpython.jit.backend.x86.regalloc import gpr_reg_mgr_cls
from rpython.jit.backend.x86.arch import WORD, IS_X86_64, IS_X86_32
from rpython.jit.backend.x86.arch import DEFAULT_FRAME_BYTES

from rpython.jit.backend.llsupport.guard_compat import *
from rpython.jit.backend.llsupport.guard_compat import _real_number


#
# GUARD_COMPATIBLE(reg, const-ptr) produces the same assembler as
# a GUARD_VALUE.  In the following code, ofs(x) means the offset in
# the GC table of the pointer 'x':
#
#     MOV reg2, [RIP + ofs(const-ptr)]     # LOAD_FROM_GC_TABLE
#     CMP reg, reg2
#     JNE recovery_stub
#   sequel:
#     <reg2 not used any more>
#
# The difference is that 'recovery_stub' does not jump to one of the
# 'failure_recovery_code' versions, but instead it jumps to
# 'expand_guard_compatible'.  The latter calls invoke_find_compatible.
# The result is one of:
#
#   * 0: bail out.  We jump to the 'failure_recovery_code'.
#
#   * -1: continue running on the same path.  We patch ofs(const-ptr)
#     to contain the new value, and jump to 'sequel'.
#
#   * otherwise, it's the address of a bridge.  We jump to that bridge.
#
# This is the basic idea, but not the truth.  Things are more
# complicated because we cache in the assembler the
# invoke_find_compatible call results.  'expand_guard_compatible'
# actually allocates a '_backend_choices' object, copies on it
# various data it got from the recovery_stub, then patches the
# recovery stub to this (the original recovery stub was padded if
# necessary to have enough room):
#
#   recovery_stub:
#     MOV R11, [RIP + ofs(_backend_choices)]
#     CMP reg, [R11 + bc_most_recent]
#     JNE slow_case
#     JMP *[R11 + bc_most_recent + 8]
#   slow_case:
#     PUSH RAX        # save the original value of RAX
#     MOV RAX, reg    # the value to search for
#     JMP *[R11 + bc_search_tree]    # x86-64: trick for a compact encoding
#
# The faildescr for the GUARD_COMPATIBLE is a GuardCompatibleDescr.
# Fields relevant for this discussion:
#
#     - _backend_ptr_addr: points inside the GC table, to ofs(const-ptr).
#                          ofs(_backend_choices) is just afterwards.
#                          Initially _backend_choices is NULL.
#     - adr_jump_offset: raw address of the 'sequel' label (this field
#                        is the same as on any other GuardDescr)
#
# The '_backend_choices' object itself, when allocated, is a separate
# GC struct/array with the following fields:
#
#     - bc_faildescr: a reference to the faildescr of that guard
#     - bc_gcmap: a copy of the gcmap at this point
#     - bc_gc_table_tracer: only for a gc_writebarrier()
#     - bc_search_tree: always the 'search_tree' label below
#     - bc_most_recent: 1 pair (gcref, asmaddr)
#     - bc_list: N pairs (gcref, asmaddr) sorted according to gcref
#
# It has a custom trace hook that keeps the bc_list sorted if the
# gcrefs move, and ignores the tail of bc_list which contains the
# invalid gcref of value -1.
#
# The bc_list can grow to contain all items for which find_compatible()
# was called and returned non-zero.  Every entry caches the result in
# 'asmaddr'.  The separate 'most_recent' entry caches the last value
# seen, along with the result of find_compatible().
#
# The list is sorted, so we can search it using binary search.  The
# length N of the list is equal to '2**D - 1', where D is the depth of
# the tree algo.  Lists start with room for 3 items (D=2) and grow to the next
# power-of-two-minus-one every time they need to be reallocated.  The
# list is over-allocated, and the tail contains pairs (-1, ?), with -1
# being the largest unsigned value (and never a valid GC pointer).
#
# When find_compatible() returns -1, we save instead the address of
# 'sequel' in 'asmaddr'.  We could also patch ofs(const-ptr) so that the
# fastest path applies if the same value is seen the next time; it
# should be measured if it changes anything or not, because such a
# patching occurs only once (i.e. 'search_tree' will not patch it
# again).
#
# When find_compatible() returns 0, it is not stored in bc_list,
# but still stored in bc_most_recent, with 'guard_compat_recovery'
# as the 'asmaddr'.  Here is 'guard_compat_recovery': it emulates
# generate_quick_failure() from assembler.py, and so it plays the role
# of the original (patched) recovery stub.
#
#   guard_compat_recovery:
#     PUSH R11
#     PUSH [R11 + bc_gcmap]
#     JMP target
#
# Here is the x86-64 runtime code to walk the tree:
#
#   search_tree:
#     MOV [ESP+8], RCX                     # save the original value
#     MOV [ESP+16], R11                    # save the _backend_choices object
#     MOV RCX, [R11 + bc_list.length]      # a power of two minus one
#     ADD R11, $bc_list.items
#     JMP loop
#
#   right:
#     LEA R11, [R11 + 8*RCX + 8]
#   left:
#     SHR RCX, 1
#     JZ not_found
#   loop:
#     # search for the item at addresses between R11 and R11+16*RCX, included
#     # (note that RCX is always odd here; even though we use 8*RCX in the
#     # following instruction, we're really accessing 16-bytes-sized items)
#     CMP RAX, [R11 + 8*RCX - 8]      # RCX = ...31, 15, 7, 3, 1
#     JA right
#     JNE left
#
#   found:
#     MOV R11, [R11 + 8*RCX]             # address to jump to next
#     MOV RCX, [ESP+16]                  # reload the _backend_choices object
#     MOV [RCX + bc_most_recent], RAX
#     MOV [RCX + bc_most_recent + 8], R11
#     MOV RCX, [ESP+8]                   # restore saved value
#     POP RAX                            # pushed by the caller
#     JMP *R11
#
#   not_found:
#     <save all registers to the jitframe RBP,
#         reading and popping the original RAX and RCX off the stack>
#     <call invoke_find_compatible(_backend_choices=[RSP], value=RAX),
#                                  jitframe=RBP>
#     <_reload_frame_if_necessary>
#     MOV R11, RAX
#     <restore all registers>
#     JMP *R11
#
#
# invoke_find_compatible(bchoices, new_gcref, jitframe):
#     IN PSEUDO-CODE:
#     result = bchoices.bc_faildescr.find_compatible(cpu, new_gcref)
#     if result == 0:
#         result = descr._backend_failure_recovery
#     else:
#         if result == -1:
#             result = descr._backend_sequel_label
#         bchoices = add_in_tree(bchoices, new_gcref, result)
#         <if bchoices changed, update the GC table>
#     bchoices.bc_most_recent.gcref = new_gcref
#     bchoices.bc_most_recent.asmaddr = result
#     return result
#
# add_in_tree(bchoices, new_gcref, new_addr):
#     if bchoices.bc_list does not end in -1, reallocate a bigger one
#     bchoices.bc_list[last].gcref = new_gcref
#     bchoices.bc_list[last].asmaddr = new_addr
#     quicksort(bchoices.bc_list)
#     return bchoices
#
# Other issues: compile_bridge() called on a GuardCompatibleDescr must
# not to do any patching, but instead it needs to clear
# bchoices.bc_most_recent.  Otherwise, we will likely directly jump to
# <failure_recovery> next time, if the newly added gcref is still in
# bc_most_recent.gcref.  (We can't add it to bc_most_recent or bc_list
# from compile_bridge(), because we don't know what the gcref should
# be, but it doesn't matter.)
#
# ____________________________________________________________


# A lot of the logic is not specific to the x86 backend and is
# written in ../llsupport/guard_compat.py.


def _fix_forward_label(mc, jmp_location):
    offset = mc.get_relative_pos() - jmp_location
    assert 0 < offset <= 127
    mc.overwrite(jmp_location-1, chr(offset))

def build_once(assembler):
    """Generate the 'search_tree' block of code"""
    rax = regloc.eax.value
    rdx = regloc.edx.value
    rdi = regloc.edi.value
    r11 = regloc.r11.value
    frame_size = DEFAULT_FRAME_BYTES + 2 * WORD
    # contains two extra words on the stack:
    #    - saved RDX
    #    - saved RAX

    mc = codebuf.MachineCodeBlockWrapper()
    mc.force_frame_size(frame_size)
    if IS_X86_32:    # save edi as an extra scratch register
        mc.MOV_sr(3*WORD, rdi)
        r11 = rdi    # r11 doesn't exist on 32-bit, use "edi" instead

    ofs1 = _real_number(BCLIST + BCLISTLENGTHOFS)
    ofs2 = _real_number(BCLIST + BCLISTITEMSOFS)
    mc.MOV_sr(2*WORD, rdx)                  # MOV [RSP+16], RDX
    mc.MOV_rm(r11, (rdx, ofs1))             # MOV R11, [RDX + bc_list.length]
    # in the sequel, "RDX + bc_list.items" is a pointer to the leftmost
    # array item of the range still under consideration.  The length of
    # this range is R11, which is always a power-of-two-minus-1.
    mc.JMP_l8(0)                            # JMP loop
    jmp_location = mc.get_relative_pos()
    mc.force_frame_size(frame_size)

    SH = 3 if IS_X86_64 else 2

    right_label = mc.get_relative_pos()
    mc.LEA_ra(rdx, (rdx, r11, SH, WORD))    # LEA RDX, [RDX + 8*R11 + 8]
    left_label = mc.get_relative_pos()
    mc.SHR_ri(r11, 1)                       # SHR R11, 1
    mc.J_il8(rx86.Conditions['Z'], 0)       # JZ not_found
    jz_location = mc.get_relative_pos()

    _fix_forward_label(mc, jmp_location)    # loop:
    mc.CMP_ra(rax, (rdx, r11, SH, ofs2-WORD))
                                            # CMP RAX, [RDX + items + 8*R11 - 8]
    mc.J_il8(rx86.Conditions['A'], right_label - (mc.get_relative_pos() + 2))
    mc.J_il8(rx86.Conditions['NE'], left_label - (mc.get_relative_pos() + 2))

    mc.MOV_ra(r11, (rdx, r11, SH, ofs2))    # MOV R11, [RDX + items + 8*R11]
    mc.MOV_rs(rdx, 2*WORD)                  # MOV RDX, [RSP+16]
    ofs = _real_number(BCMOSTRECENT)
    mc.MOV_mr((rdx, ofs), rax)              # MOV [RDX+bc_most_recent], RAX
    mc.MOV_mr((rdx, ofs+WORD), r11)         # MOV [RDX+bc_most_recent+8], R11
    mc.POP_r(rax)                           # POP RAX
    mc.POP_r(rdx)                           # POP RDX
    if IS_X86_64:
        mc.JMP_r(r11)                       # JMP *R11
    elif IS_X86_32:
        mc.MOV_sr(0, r11) # r11==rdi here
        mc.MOV_rs(rdi, WORD)
        mc.JMP_s(0)
    mc.force_frame_size(frame_size)

    _fix_forward_label(mc, jz_location)     # not_found:

    if IS_X86_32:
        mc.MOV_rs(rdi, 3*WORD)

    # read and pop the original RAX and RDX off the stack
    base_ofs = assembler.cpu.get_baseofs_of_frame_field()
    v = gpr_reg_mgr_cls.all_reg_indexes[rax]
    mc.POP_b(v * WORD + base_ofs)           # POP [RBP + saved_rax]
    v = gpr_reg_mgr_cls.all_reg_indexes[rdx]
    mc.POP_b(v * WORD + base_ofs)           # POP [RBP + saved_rdx]
    # save all other registers to the jitframe RBP
    assembler._push_all_regs_to_frame(mc, [regloc.eax, regloc.edx],
                                      withfloats=True)

    if IS_X86_64:
        mc.MOV_rs(rdi, 0)                   # MOV RDI, [RSP]
        mc.MOV_rr(regloc.esi.value, rax)    # MOV RSI, RAX
        mc.MOV_rr(regloc.edx.value,         # MOV RDX, RBP
                  regloc.ebp.value)
    elif IS_X86_32:
        # argument #1 is already in [ESP]
        mc.MOV_sr(1 * WORD, rax)
        mc.MOV_sr(2 * WORD, regloc.ebp.value)

    invoke_find_compatible = make_invoke_find_compatible(assembler.cpu)
    llfunc = llhelper(INVOKE_FIND_COMPATIBLE_FUNC, invoke_find_compatible)
    llfunc = assembler.cpu.cast_ptr_to_int(llfunc)
    mc.CALL(regloc.imm(llfunc))             # CALL invoke_find_compatible
    assembler._reload_frame_if_necessary(mc)
    if IS_X86_64:
        mc.MOV_rr(r11, rax)                 # MOV R11, RAX
    elif IS_X86_32:
        mc.MOV_sr(0, rax)

    # restore the registers that the CALL has clobbered, plus the ones
    # containing GC pointers that may have moved.  That means we just
    # restore them all.  (We restore RAX and RDX and RDI too.)
    assembler._pop_all_regs_from_frame(mc, [], withfloats=True)
    if IS_X86_64:
        mc.JMP_r(r11)                       # JMP *R11
    elif IS_X86_32:
        mc.JMP_s(0)

    assembler.guard_compat_search_tree = mc.materialize(assembler.cpu, [])


def generate_guard_compatible(assembler, guard_token, reg, bindex, reg2):
    mc = assembler.mc
    rax = regloc.eax.value
    rdx = regloc.edx.value
    frame_size = DEFAULT_FRAME_BYTES

    ofs = _real_number(BCMOSTRECENT)
    mc.CMP_rm(reg, (reg2, ofs))             # CMP reg, [reg2 + bc_most_recent]
    mc.J_il8(rx86.Conditions['NE'], 0)      # JNE slow_case
    jne_location = mc.get_relative_pos()

    mc.JMP_m((reg2, ofs + WORD))            # JMP *[reg2 + bc_most_recent + 8]
    mc.force_frame_size(frame_size)

    _fix_forward_label(mc, jne_location)    # slow_case:
    mc.PUSH_r(rdx)                          # PUSH RDX
    mc.PUSH_r(rax)                          # PUSH RAX
    # manually move reg to RAX and reg2 to RDX
    if reg2 == rax:
        if reg == rdx:
            mc.XCHG_rr(rax, rdx)
            reg = rax
        else:
            mc.MOV_rr(rdx, rax)
        reg2 = rdx
    if reg != rax:
        assert reg2 != rax
        mc.MOV_rr(rax, reg)
    if reg2 != rdx:
        mc.MOV_rr(rdx, reg2)

    mc.JMP(regloc.imm(assembler.guard_compat_search_tree))
    mc.force_frame_size(frame_size)

    # abuse this field to store the 'sequel' relative offset
    guard_token.pos_jump_offset = mc.get_relative_pos()
    guard_token.guard_compat_bindex = bindex
    assembler.pending_guard_tokens.append(guard_token)
