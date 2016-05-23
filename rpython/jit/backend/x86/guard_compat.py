from rpython.rlib import rgc
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.rarithmetic import r_uint
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import cast_instance_to_gcref, llhelper
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.jit.metainterp.compile import GuardCompatibleDescr
from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.x86 import rx86, codebuf, regloc
from rpython.jit.backend.x86.regalloc import gpr_reg_mgr_cls
from rpython.jit.backend.x86.arch import WORD, DEFAULT_FRAME_BYTES


#
# GUARD_COMPATIBLE(reg, const-ptr) produces the following assembler.
# We also have the normal failure code at <failure_recovery>, which is
# not put in the assembler but only in a field of the descr.  In the
# following code, ofs(x) means the offset in the GC table of the
# pointer 'x':
#
#     MOV reg2, [RIP + ofs(_backend_choices)]    # LOAD_FROM_GC_TABLE
#     CMP reg, [reg2 + bc_most_recent]
#     JNE slow_case
#     JMP *[reg2 + bc_most_recent + 8]
#   slow_case:
#     PUSH RDX        # save
#     PUSH RAX        # save
#     MOV RDX=reg2, RAX=reg
#            RDX is the _backend_choices object, RAX is the value to search for
#     JMP search_tree    # see below
#   sequel:
#
# The faildescr for this guard is a GuardCompatibleDescr.  We add to
# them a few fields:
#
#     - _backend_choices_addr: points inside the GC table, to
#                              ofs(_backend_choices)
#     - _backend_sequel_label: points to the <sequel> label
#     - _backend_failure_recovery: points to the <failure_recovery> label
#     - _backend_gcmap: a copy of the gcmap at this point
#
# The '_backend_choices' object itself is a separate GC struct/array
# with the following fields:
#
#     - bc_faildescr: a copy of the faildescr of that guard
#     - bc_most_recent: 1 pair (gcref, asmaddr)
#     - bc_list: N pairs (gcref, asmaddr) sorted according to gcref
#
# It has a custom trace hook that keeps the bc_list sorted if the
# gcrefs move, and ignores the tail of bc_list which contains the
# invalid gcref of value -1.
#
# Initially, the _backend_choices contains a list of length 1, and
# both bc_most_recent and bc_list[0] contain the same pair (gcref,
# sequel), where 'gcref' is the 2nd argument to guard_compatible() and
# <sequel> is the address of the label above.
#
# In general, the list can grow to contain all items for which
# find_compatible() was called and returned non-zero.  Every entry
# caches the result in 'asmaddr'.  The separate 'most_recent' entry
# caches the last value seen, along with the result of
# find_compatible().  If this find_compatible() returned zero, then
# the cache entry contains the 'fail_guard' label below as the
# 'asmaddr' value (such a value is never found inside bc_list, only in
# bc_most_recent).
#
# The list is sorted, so we can search it using binary search.  The
# length N of the list is equal to '2**D - 1', where D is the depth of
# the tree algo.  Lists start with 1 item (D=1) and grow to the next
# power-of-two-minus-one every time they need to be reallocated.  The
# list is over-allocated, and the tail contains pairs (-1, ?), with -1
# being the largest unsigned value (and never a valid GC pointer).
#
# When find_compatible() returns -1, we replace it with the address of
# the 'sequel' label above, so that we don't have to special-case it
# any more.  When find_compatible() returns 0, it is not stored in the
# list, but still stored in bc_most_recent, with the 0 replaced with
# the <failure_recovery> address introduced above.
#
# Here is the x86-64 runtime code to walk the tree:
#
#   search_tree:
#     MOV [RSP+16], RDX                    # save
#     MOV R11, [RDX + bc_list.length]      # a power of two minus one
#     ADD RDX, $bc_list.items
#     JMP loop
#
#   right:
#     LEA RDX, [RDX + 8*R11 + 8]
#   left:
#     SHR R11, 1
#     JZ not_found
#   loop:
#     # search for the item at addresses between RDX and RDX+16*R11, included
#     CMP RAX, [RDX + 8*R11 - 8]      # R11 = ...31, 15, 7, 3, 1
#     JA right
#     JNE left
#
#   found:
#     MOV R11, [RDX + 8*R11]
#     MOV RDX, [RSP+16]
#     MOV [RDX + bc_most_recent], RAX
#     MOV [RDX + bc_most_recent + 8], R11
#     POP RAX
#     POP RDX
#     JMP *R11
#
#   not_found:
#     <save all registers to the jitframe RBP,
#         reading and popping the original RAX and RDX off the stack>
#     <call invoke_find_compatible(_backend_choices=[RSP], value=RAX),
#                                  jitframe=RBP>
#     <_reload_frame_if_necessary>
#     MOV R11, RAX
#     <restore the non-saved registers>
#     JMP *R11
#
#
# invoke_find_compatible(bchoices, new_gcref, jitframe):
#     descr = bchoices.bc_faildescr
#     try:
#         jitframe.jf_gcmap = descr._backend_gcmap
#         result = descr.find_compatible(cpu, new_gcref)
#         if result == 0:
#             result = descr._backend_failure_recovery
#         else:
#             if result == -1:
#                 result = descr._backend_sequel_label
#             bchoices = add_in_tree(bchoices, new_gcref, result)
#             descr.bchoices_addr[0] = bchoices  # GC table
#         bchoices.bc_most_recent.gcref = new_gcref
#         bchoices.bc_most_recent.asmaddr = result
#         jitframe.jf_gcmap = 0
#         return result
#     except:             # oops!
#         return descr._backend_failure_recovery
#
# add_in_tree(bchoices, new_gcref, new_addr):
#     if bchoices.bc_list[len(bchoices.bc_list) - 1] != -1:
#         ...reallocate...
#     bchoices.bc_list[len(bchoices.bc_list) - 1].gcref = new_gcref
#     bchoices.bc_list[len(bchoices.bc_list) - 1].asmaddr = new_addr
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

# Possible optimization: GUARD_COMPATIBLE(reg, const-ptr) could emit
# first assembler that is similar to a GUARD_VALUE.  As soon as a
# second case is seen, this assembler is patched (once) to turn it
# into the general switching version above.  The entry in the GC table
# at ofs(_backend_choices) starts with the regular const-ptr, and the
# BACKEND_CHOICES object is only allocated when the assembler is
# patched.  The original assembler can be similar to a GUARD_VALUE:
#
#     MOV reg2, [RIP + ofs(const-ptr)]    # == ofs(_backend_choices)
#     CMP reg, reg2
#     JE sequel
#     PUSH [RIP + ofs(guard_compatible_descr)]
#     JMP guard_compat_second_case
#     <padding to make the code large enough for patching>
#     <ends with one byte which tells the size of this block>
#   sequel:
#
# ____________________________________________________________


PAIR = lltype.Struct('PAIR', ('gcref', llmemory.GCREF),
                             ('asmaddr', lltype.Signed))
BACKEND_CHOICES = lltype.GcStruct('BACKEND_CHOICES',
                        ('bc_faildescr', llmemory.GCREF),
                        ('bc_most_recent', PAIR),
                        ('bc_list', lltype.Array(PAIR)))

def _getofs(name):
    return llmemory.offsetof(BACKEND_CHOICES, name)
BCFAILDESCR = _getofs('bc_faildescr')
BCMOSTRECENT = _getofs('bc_most_recent')
BCLIST = _getofs('bc_list')
del _getofs
BCLISTLENGTHOFS = llmemory.arraylengthoffset(BACKEND_CHOICES.bc_list)
BCLISTITEMSOFS = llmemory.itemoffsetof(BACKEND_CHOICES.bc_list, 0)
PAIRSIZE = llmemory.sizeof(PAIR)

def _real_number(ofs):    # hack
    return rffi.cast(lltype.Signed, rffi.cast(lltype.Unsigned, ofs))

def bchoices_pair(gc, pair_addr, callback, arg):
    gcref_addr = pair_addr + llmemory.offsetof(PAIR, 'gcref')
    old = gcref_addr.unsigned[0]
    if old != r_uint(-1):
        gc._trace_callback(callback, arg, gcref_addr)
    new = gcref_addr.unsigned[0]
    return old != new

def bchoices_trace(gc, obj_addr, callback, arg):
    gc._trace_callback(callback, arg, obj_addr + BCFAILDESCR)
    bchoices_pair(gc, obj_addr + BCMOSTRECENT, callback, arg)
    length = (obj_addr + BCLIST + BCLISTLENGTHOFS).signed[0]
    array_addr = obj_addr + BCLIST + BCLISTITEMSOFS
    item_addr = array_addr
    i = 0
    changes = False
    while i < length:
        changes |= bchoices_pair(gc, item_addr, callback, arg)
        item_addr += PAIRSIZE
    if changes:
        pairs_quicksort(array_addr, length)
lambda_bchoices_trace = lambda: bchoices_trace

eci = ExternalCompilationInfo(separate_module_sources=["""

static int _pairs_compare(const void *p1, const void *p2)
{
    if (*(Unsigned *const *)p1 < *(Unsigned *const *)p2)
        return -1;
    else if (*(Unsigned *const *)p1 == *(Unsigned *const *)p2)
        return 0;
    else
        return 1;
}
RPY_EXTERN
void pypy_pairs_quicksort(void *base_addr, Signed length)
{
    qsort(base_addr, length, 2 * sizeof(void *), _pairs_compare);
}
"""])
pairs_quicksort = rffi.llexternal('pypy_pairs_quicksort',
                                  [llmemory.Address, lltype.Signed],
                                  lltype.Void,
                                  sandboxsafe=True,
                                  _nowrapper=True,
                                  compilation_info=eci)


INVOKE_FIND_COMPATIBLE_FUNC = lltype.Ptr(lltype.FuncType(
                [lltype.Ptr(BACKEND_CHOICES), llmemory.GCREF],
                lltype.Signed))

@specialize.memo()
def make_invoke_find_compatible(cpu):
    def invoke_find_compatible(bchoices, new_gcref):
        descr = bchoices.bc_faildescr
        descr = cast_gcref_to_instance(GuardCompatibleDescr, descr)
        try:
            result = descr.find_compatible(cpu, new_gcref)
            if result == 0:
                result = descr._backend_failure_recovery
            else:
                if result == -1:
                    result = descr._backend_sequel_label
                bchoices = add_in_tree(bchoices, new_gcref, result)
                # ---no GC operation---
                choices_addr = descr._backend_choices_addr  # GC table
                bchoices_int = rffi.cast(lltype.Signed, bchoices)
                llop.raw_store(lltype.Void, choices_addr, 0, bchoices_int)
                # ---no GC operation end---
            bchoices.bc_most_recent.gcref = new_gcref
            bchoices.bc_most_recent.asmaddr = result
            return result
        except:             # oops!
            if not we_are_translated():
                import sys, pdb
                pdb.post_mortem(sys.exc_info()[2])
            return descr._backend_failure_recovery
    return invoke_find_compatible

def add_in_tree(bchoices, new_gcref, new_asmaddr):
    rgc.register_custom_trace_hook(BACKEND_CHOICES, lambda_bchoices_trace)
    length = len(bchoices.bc_list)
    #
    gcref_base = lltype.cast_opaque_ptr(llmemory.GCREF, bchoices)
    ofs = BCLIST + BCLISTITEMSOFS
    ofs += (length - 1) * llmemory.sizeof(PAIR)
    ofs = _real_number(ofs)
    if llop.raw_load(lltype.Unsigned, gcref_base, ofs) != r_uint(-1):
        # reallocate
        new_bchoices = lltype.malloc(BACKEND_CHOICES, length * 2 + 1, zero=True)
        # --- no GC below: it would mess up the order of bc_list ---
        new_bchoices.bc_faildescr = bchoices.bc_faildescr
        new_bchoices.bc_most_recent.gcref = bchoices.bc_most_recent.gcref
        new_bchoices.bc_most_recent.asmaddr = bchoices.bc_most_recent.asmaddr
        i = 0
        while i < length:
            new_bchoices.bc_list[i].gcref = bchoices.bc_list[i].gcref
            new_bchoices.bc_list[i].asmaddr = bchoices.bc_list[i].asmaddr
            i += 1
        # fill the new pairs with the invalid gcref value -1
        length = len(new_bchoices.bc_list)
        ofs = (llmemory.offsetof(BACKEND_CHOICES, 'bc_list') +
               llmemory.itemoffsetof(BACKEND_CHOICES.bc_list) +
               i * llmemory.sizeof(PAIR))
        while i < length:
            invalidate_pair(new_bchoices, ofs)
            ofs += llmemory.sizeof(PAIR)
            i += 1
        bchoices = new_bchoices
    #
    bchoices.bc_list[length - 1].gcref = new_gcref
    bchoices.bc_list[length - 1].asmaddr = new_asmaddr
    # --- no GC above ---
    addr = llmemory.cast_ptr_to_adr(bchoices)
    addr += BCLIST + BCLISTITEMSOFS
    pairs_quicksort(addr, length)
    return bchoices

def initial_bchoices(guard_compat_descr, initial_gcref):
    bchoices = lltype.malloc(BACKEND_CHOICES, 1)
    bchoices.bc_faildescr = cast_instance_to_gcref(guard_compat_descr)
    bchoices.bc_most_recent.gcref = initial_gcref
    # bchoices.bc_most_recent.asmaddr: patch_guard_compatible()
    bchoices.bc_list[0].gcref = initial_gcref
    # bchoices.bc_list[0].asmaddr: patch_guard_compatible()
    return bchoices

def descr_to_bchoices(descr):
    assert isinstance(descr, GuardCompatibleDescr)
    # ---no GC operation---
    bchoices = llop.raw_load(lltype.Signed, descr._backend_choices_addr, 0)
    bchoices = rffi.cast(lltype.Ptr(BACKEND_CHOICES), bchoices)
    # ---no GC operation end---
    return bchoices

def patch_guard_compatible(guard_token, rawstart, gc_table_addr):
    # go to the address in the gctable, number 'bindex'
    bindex = guard_token.guard_compat_bindex
    choices_addr = gc_table_addr + WORD * bindex
    sequel_label = rawstart + guard_token.pos_jump_offset
    failure_recovery = rawstart + guard_token.pos_recovery_stub
    gcmap = guard_token.gcmap
    # choices_addr:     points to bchoices in the GC table
    # sequel_label:     "sequel:" label above
    # failure_recovery: failure recovery address
    guard_compat_descr = guard_token.faildescr
    assert isinstance(guard_compat_descr, GuardCompatibleDescr)
    guard_compat_descr._backend_choices_addr = choices_addr
    guard_compat_descr._backend_sequel_label = sequel_label
    guard_compat_descr._backend_failure_recovery = failure_recovery
    guard_compat_descr._backend_gcmap = gcmap
    #
    bchoices = descr_to_bchoices(guard_compat_descr)
    assert len(bchoices.bc_list) == 1
    assert (cast_gcref_to_instance(GuardCompatibleDescr, bchoices.bc_faildescr)
            is guard_compat_descr)
    bchoices.bc_most_recent.asmaddr = sequel_label
    bchoices.bc_list[0].asmaddr = sequel_label

def invalidate_pair(bchoices, pair_ofs):
    gcref_base = lltype.cast_opaque_ptr(llmemory.GCREF, bchoices)
    llop.raw_store(lltype.Void, gcref_base, _real_number(pair_ofs), r_uint(-1))
    llop.raw_store(lltype.Void, gcref_base, _real_number(pair_ofs), r_uint(-1))

def invalidate_cache(faildescr):
    """Write -1 inside bchoices.bc_most_recent.gcref."""
    bchoices = descr_to_bchoices(faildescr)
    invalidate_pair(bchoices, BCMOSTRECENT)


def _fix_forward_label(mc, jmp_location):
    offset = mc.get_relative_pos() - jmp_location
    assert 0 < offset <= 127
    mc.overwrite(jmp_location-1, chr(offset))

def setup_once(assembler):
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

    ofs1 = _real_number(BCLIST + BCLISTLENGTHOFS)
    ofs2 = _real_number(BCLIST + BCLISTITEMSOFS)
    mc.MOV_sr(16, rdx)                      # MOV [RSP+16], RDX
    mc.MOV_rm(r11, (rdx, ofs1))             # MOV R11, [RDX + bc_list.length]
    mc.ADD_ri(rdx, ofs2)                    # ADD RDX, $bc_list.items
    mc.JMP_l8(0)                            # JMP loop
    jmp_location = mc.get_relative_pos()
    mc.force_frame_size(frame_size)

    right_label = mc.get_relative_pos()
    mc.LEA_ra(rdx, (rdx, r11, 3, 8))        # LEA RDX, [RDX + 8*R11 + 8]
    left_label = mc.get_relative_pos()
    mc.SHR_ri(r11, 1)                       # SHR R11, 1
    mc.J_il8(rx86.Conditions['Z'], 0)       # JZ not_found
    jz_location = mc.get_relative_pos()

    _fix_forward_label(mc, jmp_location)    # loop:
    mc.CMP_ra(rax, (rdx, r11, 3, -8))       # CMP RAX, [RDX + 8*R11 - 8]
    mc.J_il8(rx86.Conditions['A'], right_label - (mc.get_relative_pos() + 2))
    mc.J_il8(rx86.Conditions['NE'], left_label - (mc.get_relative_pos() + 2))

    mc.MOV_ra(r11, (rdx, r11, 3, 0))        # MOV R11, [RDX + 8*R11]
    mc.MOV_rs(rdx, 16)                      # MOV RDX, [RSP+16]
    ofs = _real_number(BCMOSTRECENT)
    mc.MOV_mr((rdx, ofs), rax)              # MOV [RDX+bc_most_recent], RAX
    mc.MOV_mr((rdx, ofs + 8), r11)          # MOV [RDX+bc_most_recent+8], R11
    mc.POP_r(rax)                           # POP RAX
    mc.POP_r(rdx)                           # POP RDX
    mc.JMP_r(r11)                           # JMP *R11
    mc.force_frame_size(frame_size)

    _fix_forward_label(mc, jz_location)     # not_found:

    # read and pop the original RAX and RDX off the stack
    base_ofs = assembler.cpu.get_baseofs_of_frame_field()
    v = gpr_reg_mgr_cls.all_reg_indexes[rdx]
    mc.POP_b(v * WORD + base_ofs)           # POP [RBP + saved_rdx]
    v = gpr_reg_mgr_cls.all_reg_indexes[rax]
    mc.POP_b(v * WORD + base_ofs)           # POP [RBP + saved_rax]
    # save all other registers to the jitframe RBP
    assembler._push_all_regs_to_frame(mc, [regloc.eax, regloc.edx],
                                      withfloats=True)

    mc.MOV_rs(rdi, 0)                       # MOV RDI, [RSP]
    mc.MOV_rr(regloc.esi.value, rax)        # MOV RSI, RAX
    mc.MOV_rr(regloc.edx.value,             # MOV RDX, RBP
              regloc.ebp.value)
    invoke_find_compatible = make_invoke_find_compatible(assembler.cpu)
    llfunc = llhelper(INVOKE_FIND_COMPATIBLE_FUNC, invoke_find_compatible)
    llfunc = assembler.cpu.cast_ptr_to_int(llfunc)
    mc.CALL(regloc.imm(llfunc))             # CALL invoke_find_compatible
    assembler._reload_frame_if_necessary(mc)
    mc.MOV_rr(r11, rax)                     # MOV R11, RAX

    # restore the registers that the CALL has clobbered.  Other other
    # registers are saved above, for the gcmap, but don't need to be
    # restored here.  (We restore RAX and RDX too.)
    assembler._pop_all_regs_from_frame(mc, [], withfloats=True,
                                       callee_only=True)
    mc.JMP_r(r11)                           # JMP *R11

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
