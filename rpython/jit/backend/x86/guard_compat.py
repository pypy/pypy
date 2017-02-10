from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.backend.x86 import rx86, codebuf, regloc, callbuilder
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
#
# The difference is in the 'recovery_stub':
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
#     - _backend_choices_addr: points inside the GC table, to
#                              ofs(_backend_choices)
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
# the non-GUARD_COMPATIBLE case of generate_quick_failure() from
# assembler.py.
#
#   guard_compat_recovery:
#     PUSH [R11 + bc_faildescr]
#     PUSH [R11 + bc_gcmap]
#     JMP target
#
# Here is the x86-64 runtime code to walk the tree:
#
#   search_tree:
#     MOV [RSP+8], RCX                     # save the original value
#     MOV [RSP+16], R11                    # save the _backend_choices object
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
#     MOV RCX, [RSP+16]                  # reload the _backend_choices object
#     MOV [RCX + bc_most_recent], RAX
#     MOV [RCX + bc_most_recent + 8], R11
#     MOV RCX, [RSP+8]                   # restore saved value
#     POP RAX                            # pushed by the caller
#     JMP *R11                           # can't jump to guard_compat_recovery
#
#   not_found:
#     <save all registers to the jitframe RBP,
#         reading and popping the original RAX and RCX off the stack>
#     <build an array of two words on the stack, with _backend_choices
#         and value; the 'value' will be overwritten by
#         invoke_find_compatible with the address to jump to next>
#     <call invoke_find_compatible(p_arg=RSP, jitframe=RBP>
#     <_reload_frame_if_necessary>
#     <restore all registers>
#     MOV R11, [RSP+array_element_1]     # reload the _backend_choices object
#     JMP *[RSP+array_element_2]         # may jump to guard_compat_recovery
#
#
# invoke_find_compatible(p_arg, jitframe):
#     IN PSEUDO-CODE:
#     bchoices = p_arg[0]
#     new_gcref = p_arg[1]
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
# <guard_compat_recovery> next time, if the newly added gcref is still in
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
    build_once_search_tree(assembler)
    build_once_guard_compat_recovery(assembler)

def build_once_search_tree(assembler):
    """Generate the 'search_tree' block of code"""
    rax = regloc.eax.value
    rcx = regloc.ecx.value
    rdi = regloc.edi.value
    r11 = regloc.r11.value
    frame_size = DEFAULT_FRAME_BYTES + 1 * WORD
    # contains one extra word on the stack:
    #    - saved RAX

    mc = codebuf.MachineCodeBlockWrapper()
    mc.force_frame_size(frame_size)
    if IS_X86_32:    # save edi as an extra scratch register
        XXX
        mc.MOV_sr(3*WORD, rdi)
        r11 = rdi    # r11 doesn't exist on 32-bit, use "edi" instead

    mc.MOV_sr(1*WORD, rcx)                  # MOV [RSP+8], ECX
    mc.MOV_sr(2*WORD, r11)                  # MOV [RSP+16], R11

    ofs1 = _real_number(BCLIST + BCLISTLENGTHOFS)
    ofs2 = _real_number(BCLIST + BCLISTITEMSOFS)
    mc.MOV_rm(rcx, (r11, ofs1))             # MOV RCX, [R11 + bc_list.length]
    # in the sequel, "R11 + bc_list.items" is a pointer to the leftmost
    # array item of the range still under consideration.  The length of
    # this range is RCX, which is always a power-of-two-minus-1.
    mc.JMP_l8(0)                            # JMP loop
    jmp_location = mc.get_relative_pos()
    mc.force_frame_size(frame_size)

    SH = 3 if IS_X86_64 else 2

    right_label = mc.get_relative_pos()
    mc.LEA_ra(r11, (r11, rcx, SH, WORD))    # LEA R11, [R11 + 8*RCX + 8]
    left_label = mc.get_relative_pos()
    mc.SHR_ri(rcx, 1)                       # SHR RCX, 1
    mc.J_il8(rx86.Conditions['Z'], 0)       # JZ not_found
    jz_location = mc.get_relative_pos()

    _fix_forward_label(mc, jmp_location)    # loop:
    mc.CMP_ra(rax, (r11, rcx, SH, ofs2-WORD))
                                            # CMP RAX, [R11 + items + 8*RCX - 8]
    mc.J_il8(rx86.Conditions['A'], right_label - (mc.get_relative_pos() + 2))
    mc.J_il8(rx86.Conditions['NE'], left_label - (mc.get_relative_pos() + 2))

    mc.MOV_ra(r11, (r11, rcx, SH, ofs2))    # MOV R11, [R11 + items + 8*RCX]
    mc.MOV_rs(rcx, 2*WORD)                  # MOV RCX, [RSP+16]
    ofs = _real_number(BCMOSTRECENT)
    mc.MOV_mr((rcx, ofs), rax)              # MOV [RCX+bc_most_recent], RAX
    mc.MOV_mr((rcx, ofs+WORD), r11)         # MOV [RCX+bc_most_recent+8], R11
    mc.MOV_rs(rcx, 1*WORD)                  # MOV RCX, [RSP+8]
    mc.POP_r(rax)                           # POP RAX
    if IS_X86_64:
        mc.JMP_r(r11)                       # JMP *R11
    elif IS_X86_32:
        XXX
        mc.MOV_sr(0, r11) # r11==rdi here
        mc.MOV_rs(rdi, WORD)
        mc.JMP_s(0)
    mc.force_frame_size(frame_size)

    _fix_forward_label(mc, jz_location)     # not_found:

    if IS_X86_32:
        XXX
        mc.MOV_rs(rdi, 3*WORD)

    # The _backend_choices object is still referenced from [RSP+16]
    # (which becomes [RSP+8] after the POP), where it is the second of a
    # two-words array passed as argument to invoke_find_compatible().
    # The first word is the value, from RAX, which we store in (*)
    # below.

    # restore RAX and RCX
    mc.MOV_rs(rcx, 1*WORD)                  # MOV RCX, [RSP+8]
    mc.MOV_sr(1*WORD, rax)                  # MOV [RSP+8], RAX   (*)
    mc.POP_r(rax)                           # POP RAX

    # save all registers to the jitframe RBP
    assembler._push_all_regs_to_frame(mc, [], withfloats=True)

    if IS_X86_64:
        mc.MOV_rr(rdi, regloc.esp.value)    # MOV RDI, RSP
        mc.MOV_rr(regloc.esi.value,         # MOV RSI, RBP
                  regloc.ebp.value)
    elif IS_X86_32:
        XXX
        # argument #1 is already in [ESP]
        mc.MOV_sr(1 * WORD, rax)
        mc.MOV_sr(2 * WORD, regloc.ebp.value)

    invoke_find_compatible = make_invoke_find_compatible(assembler.cpu)
    llfunc = llhelper(INVOKE_FIND_COMPATIBLE_FUNC, invoke_find_compatible)
    llfunc = assembler.cpu.cast_ptr_to_int(llfunc)
    mc.CALL(regloc.imm(llfunc))             # CALL invoke_find_compatible
    assembler._reload_frame_if_necessary(mc)

    # restore the registers that the CALL has clobbered, plus the ones
    # containing GC pointers that may have moved.  That means we just
    # restore them all.
    assembler._pop_all_regs_from_frame(mc, [], withfloats=True)

    # jump to the result, which is returned as the first word of the
    # array.  In case this goes to guard_compat_recovery, we also reload
    # the _backend_choices object from the second word of the array (the
    # GC may have moved it, or it may be a completely new object).
    if IS_X86_64:
        mc.MOV_rs(r11, 1 * WORD)            # MOV R11, [RSP+8]
        mc.JMP_s(0)                         # JMP *[RSP]
    elif IS_X86_32:
        XXX
        mc.JMP_s(0)

    assembler.guard_compat_search_tree = mc.materialize(assembler.cpu, [])


def build_once_guard_compat_recovery(assembler):
    """Generate the 'guard_compat_recovery' block of code"""
    r11 = regloc.r11.value
    mc = codebuf.MachineCodeBlockWrapper()

    ofs1 = _real_number(BCFAILDESCR)
    ofs2 = _real_number(BCGCMAP)
    mc.PUSH_m((r11, ofs1))
    mc.PUSH_m((r11, ofs2))
    target = assembler.get_target_for_failure_recovery_of_guard_compat()
    mc.JMP(regloc.imm(target))

    assembler.guard_compat_recovery = mc.materialize(assembler.cpu, [])


def generate_recovery_stub(assembler, guard_token):
    rax = regloc.eax.value
    r11 = regloc.r11.value
    frame_size = DEFAULT_FRAME_BYTES

    descr = guard_token.faildescr
    assert isinstance(descr, GuardCompatibleDescr)
    assembler.load_reg_from_gc_table(r11, descr._backend_choices_addr)

    mc = assembler.mc
    reg = guard_token._guard_value_on
    ofs = _real_number(BCMOSTRECENT)
    mc.CMP_rm(reg, (r11, ofs))              # CMP reg, [R11 + bc_most_recent]
    mc.J_il8(rx86.Conditions['NE'], 0)      # JNE slow_case
    jne_location = mc.get_relative_pos()

    mc.JMP_m((r11, ofs + WORD))             # JMP *[R11 + bc_most_recent + 8]
    mc.force_frame_size(frame_size)

    _fix_forward_label(mc, jne_location)    # slow_case:
    mc.PUSH_r(rax)                          # PUSH RAX
    if reg != rax:
        mc.MOV_rr(rax, reg)                 # MOV RAX, reg

    ofs = _real_number(BCSEARCHTREE)
    mc.JMP_m((r11, ofs))                    # JMP *[R11 + bc_search_tree]
