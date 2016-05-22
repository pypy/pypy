from rpython.rlib import rgc
from rpython.rlib.objectmodel import specialize
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
#     MOV reg2, [RIP + ofs(_backend_choices)]
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
#
# The '_backend_choices' object itself is a separate GC struct/array
# with the following fields:
#
#     - bc_gcmap: a copy of the gcmap at this point
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
#     MOV RDI, [RSP]
#     MOV R11, [RDI + bc_gcmap]
#     MOV [RBP + jf_gcmap], R11
#     <call invoke_find_compatible(_backend_choices=RDI, value=RAX)>
#     <_reload_frame_if_necessary>
#     MOV R11, RAX
#     <restore the non-saved registers>
#     JMP *R11
#
#
# invoke_find_compatible(bchoices, new_gcref):
#     descr = bchoices.bc_faildescr
#     try:
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


PAIR = lltype.Struct('PAIR', ('gcref', llmemory.GCREF),
                             ('asmaddr', lltype.Signed))
BACKEND_CHOICES = lltype.GcStruct('BACKEND_CHOICES',
                        ('bc_gcmap', lltype.Ptr(jitframe.GCMAP)),
                        ('bc_faildescr', llmemory.GCREF),
                        ('bc_most_recent', PAIR),
                        ('bc_list', lltype.Array(PAIR)))

def _getofs(name):
    return llmemory.offsetof(BACKEND_CHOICES, name)
BCGCMAP = _getofs('bc_gcmap')
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

def invoke_find_compatible(bchoices, new_gcref):
    descr = bchoices.bc_faildescr
    descr = cast_gcref_to_instance(GuardCompatibleDescr, descr)
    try:
        xxx # temp
        result = descr.find_compatible(cpu, new_gcref)
        if result == 0:
            result = descr._backend_failure_recovery
        else:
            if result == -1:
                result = descr._backend_sequel_label
            bchoices = add_in_tree(bchoices, new_gcref, result)
            descr._backend_choices_addr[0] = bchoices  # GC table
        bchoices.bc_most_recent.gcref = new_gcref
        bchoices.bc_most_recent.asmaddr = result
        return result
    except:             # oops!
        if not we_are_translated():
            import sys, pdb
            pdb.post_mortem(sys.exc_info()[2])
        return descr._backend_failure_recovery

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
        new_bchoices.bc_gcmap = bchoices.bc_gcmap
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

def initial_bchoices(guard_compat_descr, initial_gcref, gcmap):
    bchoices = lltype.malloc(BACKEND_CHOICES, 1)
    bchoices.bc_gcmap = gcmap
    bchoices.bc_faildescr = cast_instance_to_gcref(guard_compat_descr)
    bchoices.bc_most_recent.gcref = initial_gcref
    # bchoices.bc_most_recent.asmaddr: later
    bchoices.bc_list[0].gcref = initial_gcref
    # bchoices.bc_list[0].asmaddr: later
    return bchoices

def finish_guard_compatible_descr(guard_compat_descr,
            choices_addr,      # points to bchoices in the GC table
            sequel_label,      # "sequel:" label above
            failure_recovery): # failure recovery address
    guard_compat_descr._backend_choices_addr = choices_addr
    guard_compat_descr._backend_sequel_label = sequel_label
    guard_compat_descr._backend_failure_recovery = failure_recovery
    bchoices = rffi.cast(lltype.Ptr(BACKEND_CHOICES), choices_addr[0])
    assert len(bchoices.bc_list) == 1
    assert bchoices.bc_faildescr == cast_instance_to_gcref(guard_compat_descr)
    bchoices.bc_most_recent.asmaddr = sequel_label
    bchoices.bc_list[0].asmaddr = sequel_label

def invalidate_pair(bchoices, pair_ofs):
    gcref_base = lltype.cast_opaque_ptr(llmemory.GCREF, bchoices)
    llop.raw_store(lltype.Void, gcref_base, _real_number(pair_ofs), r_uint(-1))
    llop.raw_store(lltype.Void, gcref_base, _real_number(pair_ofs), r_uint(-1))

def invalidate_cache(bchoices):
    """Write -1 inside bchoices.bc_most_recent.gcref."""
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

    bc_gcmap = _real_number(BCGCMAP)
    jf_gcmap = assembler.cpu.get_ofs_of_frame_field('jf_gcmap')
    mc.MOV_rs(rdi, 0)                       # MOV RDI, [RSP]
    mc.MOV_rr(regloc.esi.value, rax)        # MOV RSI, RAX
    mc.MOV_rm(r11, (rdi, bc_gcmap))         # MOV R11, [RDI + bc_gcmap]
    mc.MOV_br(jf_gcmap, r11)                # MOV [RBP + jf_gcmap], R11
    llfunc = llhelper(INVOKE_FIND_COMPATIBLE_FUNC, invoke_find_compatible)
    llfunc = assembler.cpu.cast_ptr_to_int(llfunc)
    mc.CALL(regloc.imm(llfunc))             # CALL invoke_find_compatible
    assembler._reload_frame_if_necessary(mc)
    mc.MOV_bi(jf_gcmap, 0)                  # MOV [RBP + jf_gcmap], 0

    mc.MOV_rr(r11, rax)                     # MOV R11, RAX

    # restore the registers that the CALL has clobbered.  Other other
    # registers are saved above, for the gcmap, but don't need to be
    # restored here.  (We restore RAX and RDX too.)
    assembler._pop_all_regs_from_frame(mc, [], withfloats=True,
                                       callee_only=True)
    mc.JMP_r(r11)                           # JMP *R11

    assembler.guard_compat_search_tree = mc.materialize(assembler.cpu, [])





# ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def generate_guard_compatible(assembler, guard_token, loc_reg, initial_value):
    # fast-path check
    mc = assembler.mc
    if IS_X86_64:
        mc.MOV_ri64(X86_64_SCRATCH_REG.value, initial_value)
        rel_pos_compatible_imm = mc.get_relative_pos()
        mc.CMP_rr(loc_reg.value, X86_64_SCRATCH_REG.value)
    elif IS_X86_32:
        mc.CMP_ri32(loc_reg.value, initial_value)
        rel_pos_compatible_imm = mc.get_relative_pos()
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

    if IS_X86_64:
        mc.MOV_ri64(X86_64_SCRATCH_REG.value, compatinfoaddr)  # patchable
        guard_token.pos_compatinfo_offset = mc.get_relative_pos() - WORD
        mc.PUSH_r(X86_64_SCRATCH_REG.value)
    elif IS_X86_32:
        mc.PUSH_i32(compatinfoaddr)   # patchable
        guard_token.pos_compatinfo_offset = mc.get_relative_pos() - WORD
    mc.CALL(imm(checker))
    mc.stack_frame_size_delta(-WORD)

    small_ofs = rel_pos_compatible_imm - mc.get_relative_pos()
    assert -128 <= small_ofs < 128
    compatinfo[0] = small_ofs & 0xFF

    assembler.guard_success_cc = rx86.Conditions['Z']
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


def grow_switch(cpu, compiled_loop_token, guarddescr, gcref):
    # XXX is it ok to force gcref to be non-movable?
    if not rgc._make_sure_does_not_move(gcref):
        raise AssertionError("oops")
    new_value = rffi.cast(lltype.Signed, gcref)

    # XXX related to the above: for now we keep alive the gcrefs forever
    # in the compiled_loop_token
    if compiled_loop_token._keepalive_extra is None:
        compiled_loop_token._keepalive_extra = []
    compiled_loop_token._keepalive_extra.append(gcref)

    if not we_are_translated() and isinstance(guarddescr, BasicFailDescr):
        pass    # for tests
    else:
        assert isinstance(guarddescr, GuardCompatibleDescr)
    compatinfop = rffi.cast(rffi.VOIDPP, guarddescr._backend_compatinfo)
    compatinfo = rffi.cast(rffi.SIGNEDP, compatinfop[0])
    length = 3
    while compatinfo[length - 1] != -1:
        length += 1

    allblocks = compiled_loop_token.get_asmmemmgr_blocks()
    datablockwrapper = MachineDataBlockWrapper(cpu.asmmemmgr, allblocks)
    newcompatinfoaddr = datablockwrapper.malloc_aligned(
        (length + 1) * WORD, alignment=WORD)
    datablockwrapper.done()

    newcompatinfo = rffi.cast(rffi.SIGNEDP, newcompatinfoaddr)
    newcompatinfo[0] = compatinfo[0]

    if GROW_POSITION == 0:
        newcompatinfo[1] = new_value
        for i in range(1, length):
            newcompatinfo[i + 1] = compatinfo[i]
    elif GROW_POSITION == 1:
        for i in range(1, length - 2):
            newcompatinfo[i] = compatinfo[i]
        newcompatinfo[length - 2] = new_value
        newcompatinfo[length - 1] = compatinfo[length - 2]
        newcompatinfo[length] = -1    # == compatinfo[length - 1]
    else:
        for i in range(1, length - 1):
            newcompatinfo[i] = compatinfo[i]
        newcompatinfo[length - 1] = new_value
        newcompatinfo[length] = -1    # == compatinfo[length - 1]

    # the old 'compatinfo' is not used any more, but will only be freed
    # when the looptoken is freed
    compatinfop[0] = rffi.cast(rffi.VOIDP, newcompatinfo)
    valgrind.discard_translations(rffi.cast(lltype.Signed, compatinfop), WORD)

    # the machine code is not updated here.  We leave it to the actual
    # guard_compatible to update it if needed.


def _build_inner_loop(mc, regnum, tmp, immediate_return):
    pos = mc.get_relative_pos()
    mc.CMP_mr((tmp, WORD), regnum)
    mc.J_il8(rx86.Conditions['E'], 0)    # patched below
    je_location = mc.get_relative_pos()
    mc.CMP_mi((tmp, WORD), -1)
    mc.LEA_rm(tmp, (tmp, WORD))
    mc.J_il8(rx86.Conditions['NE'], pos - (mc.get_relative_pos() + 2))
    #
    # not found!  Return the condition code 'Not Zero' to mean 'not found'.
    mc.OR_rr(tmp, tmp)
    #
    # if 'immediate_return', patch the JE above to jump here.  When we
    # follow that path, we get condition code 'Zero', which means 'found'.
    if immediate_return:
        offset = mc.get_relative_pos() - je_location
        assert 0 < offset <= 127
        mc.overwrite(je_location-1, chr(offset))
    #
    if IS_X86_32:
        mc.POP_r(tmp)
    mc.RET16_i(WORD)
    mc.force_frame_size(8)   # one word on X86_64, two words on X86_32
    #
    # if not 'immediate_return', patch the JE above to jump here.
    if not immediate_return:
        offset = mc.get_relative_pos() - je_location
        assert 0 < offset <= 127
        mc.overwrite(je_location-1, chr(offset))

def get_or_build_checker(assembler, regnum):
    """Returns a piece of assembler that checks if the value is in
    some array (there is one such piece per input register 'regnum')
    """
    addr = assembler._guard_compat_checkers[regnum]
    if addr != 0:
        return addr

    mc = codebuf.MachineCodeBlockWrapper()

    if IS_X86_64:
        tmp = X86_64_SCRATCH_REG.value
        stack_ret = 0
        stack_arg = WORD
    elif IS_X86_32:
        if regnum != eax.value:
            tmp = eax.value
        else:
            tmp = edx.value
        mc.PUSH_r(tmp)
        stack_ret = WORD
        stack_arg = 2 * WORD

    mc.MOV_rs(tmp, stack_arg)

    if UPDATE_ASM > 0:
        CONST_TO_ADD = int((1 << 24) / (UPDATE_ASM + 0.3))
        if CONST_TO_ADD >= (1 << 23):
            CONST_TO_ADD = (1 << 23) - 1
        if CONST_TO_ADD < 1:
            CONST_TO_ADD = 1
        CONST_TO_ADD <<= 8
        #
        mc.ADD32_mi32((tmp, 0), CONST_TO_ADD)
        mc.J_il8(rx86.Conditions['C'], 0)    # patched below
        jc_location = mc.get_relative_pos()
    else:
        jc_location = -1

    _build_inner_loop(mc, regnum, tmp, immediate_return=True)

    if jc_location != -1:
        # patch the JC above
        offset = mc.get_relative_pos() - jc_location
        assert 0 < offset <= 127
        mc.overwrite(jc_location-1, chr(offset))
        #
        _build_inner_loop(mc, regnum, tmp, immediate_return=False)
        #
        # found!  update the assembler by writing the value at 'small_ofs'
        # bytes before our return address.  This should overwrite the const in
        # 'MOV_ri64(r11, const)', first instruction of the guard_compatible.
        mc.MOV_rs(tmp, stack_arg)
        mc.MOVSX8_rm(tmp, (tmp, 0))
        mc.ADD_rs(tmp, stack_ret)
        mc.MOV_mr((tmp, -WORD), regnum)
        #
        # Return condition code 'Zero' to mean 'found'.
        mc.CMP_rr(regnum, regnum)
        if IS_X86_32:
            mc.POP_r(tmp)
        mc.RET16_i(WORD)

    addr = mc.materialize(assembler.cpu, [])
    assembler._guard_compat_checkers[regnum] = addr
    return addr
