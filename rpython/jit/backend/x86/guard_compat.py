from rpython.rlib import rgc
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.backend.x86.arch import WORD, IS_X86_32, IS_X86_64
from rpython.jit.backend.x86 import rx86, codebuf, valgrind
from rpython.jit.backend.x86.regloc import X86_64_SCRATCH_REG, imm, eax, edx
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.metainterp.compile import GuardCompatibleDescr
from rpython.jit.metainterp.history import BasicFailDescr


#
# GUARD_COMPATIBLE(reg, const-ptr) produces the following assembler.
# It uses a special version of the failure recovery stub code written
# by generate_quick_failure(), which saves a few things at different
# locations and then jumps to the tree-searching algo, as described
# later.  We also have the normal failure code at <failure_recovery>,
# see below.  In the following code, ofs(x) means the offset in the GC
# table of the constant pointer 'x':
#
#     MOV reg2, [RIP + ofs(_backend_choices)]
#     CMP reg, [reg2 + bc_most_recent]
#     JNE <failure_and_search_tree>
#     JMP *[reg2 + bc_most_recent + 8]
#    sequel:
#
# The faildescr for this guard is a GuardCompatibleDescr.  The
# '_backend_choices' (which is added as a field to
# GuardCompatibleDescr only when not translated) has the following
# structure:
#
#     - bc_gcmap: a copy of the gcmap at this point
#     - bc_faildescr: a copy of the faildescr of that guard
#     - bc_most_recent: 1 pair (gcref, asmaddr)
#     - bc_tree: N pairs (gcref, asmaddr)
#
# The tree contains all items for which find_compatible() was called and
# returned non-zero.  It caches the non-zero result in 'asmaddr'.  The
# separate most_recent entry caches the last value seen, along with
# the result of find_compatible().  If this find_compatible() returned
# zero, then the cache entry contains the 'fail_guard' label below
# as the 'asmaddr' value (such a value is never found inside the tree,
# only in the most_recent entry).
#
# The tree is a binary-search tree with a value at every node and leaf.
# The length N of the array is equal to '2**D - 1', where D is the depth
# of the tree.  There are '2**(D-1) - 1' nodes and '2**(D-1)' leaves.
# Trees start at D=1 and grows by one every time they need to be
# reallocated.  A tree of depth D has always all its nodes used, but
# some leaves may be unused; such leaves store a pair (NULL, zero).
# For now we assume that NULL is never received by guard_compatible().
#
# Tree organization: the root is at index 0.  Starting at a node at
# index i, the left child is at i+1, and the right child is at i+w,
# where 'w' is computed as follows: start from the length of the whole
# array; divide it by two and round the (non-integer) result upwards
# for every level you see; you get 'w'.  When you reach 'w=1', you are
# at the level of leaves.
#
# The special value 'asmaddr=-1' is replaced with the actual address
# of the 'sequel' label above inside the tree, so that we don't have
# to special-case it here.  The special value 'asmaddr=0' in
# 'most_recent' is replaced with the <failure_recovery> address
# introduced above.
#
# Here is the modified <failure_and_search_tree> code:
#
#     PUSH RAX        # save
#     PUSH RDX        # save
#     MOV RAX, reg    # the value to search for
#     MOV RDX, reg2   # _backend_choices object
#     JMP search_tree
#
# Here is the x86-64 runtime code to walk the tree:
#
#   search_tree:
#     MOV [RSP+16], RDX                    # save
#     MOV R11, [RDX + bc_tree.length]
#     LEA RDX, [RDX + bc_tree.items]
#     JMP entry
#   right:
#     LEA RDX, [RDX + 8*R11 + 8]
#   loop:
#     SHR R11, 1
#     JZ not_found
#   entry:
#     CMP RAX, [RDX]
#     JA right
#     JE found
#     ADD RDX, 16
#     JMP loop
#
#   found:
#     MOV R11, [RDX + 8]
#     MOV RDX, [RSP+16]
#     MOV [RDX + bc_most_recent], RAX
#     MOV [RDX + bc_most_recent + 8], R11
#     POP RAX
#     POP RDX
#     JMP *R11
#
#   not_found:
#     MOV RDX, [RSP+16]
#     MOV R11, [RDX + bc_gcmap]
#     MOV [RBP + jf_gcmap], R11
#     <save all registers to the jitframe RBP,
#         reading and popping RAX and RDX off the stack>
#     <call invoke_find_compatible(_backend_choices=RDX, value=RAX)>
#     <_reload_frame_if_necessary>
#     MOV R11, RAX
#     <restore the non-saved registers>
#     JMP *R11
#
#
# invoke_find_compatible(_backend_choices, value):
#     try:
#         descr = _backend_choices.bc_faildescr
#         result = descr.find_compatible(cpu, value)
#         if result == 0:
#             result = <failure_recovery>
#         else:
#             if result == -1:
#                 result = <sequel>
#             _backend_choices = add_in_tree(_backend_choices, value, result)
#         _backend_choices.bc_most_recent.gcref = value
#         _backend_choices.bc_most_recent.asmaddr = result
#         return result
#     except:             # oops!
#         return <failure_recovery>
#
# ____________________________________________________________




# uses the raw structure COMPATINFO, which is informally defined like this:
# it starts with a negative 'small_ofs' value (see in the code)
# then there is an array containing all the expected values that should pass
# the guard, ending in -1.


# --tweakable parameters (you get the effect closest to before we had
# guard-compat by setting GROW_POSITION to 1 and UPDATE_ASM to 0)--

# where grow_switch puts the new value:
#   0 = at the beginning of the list
#   1 = at position N-1, just before the initial value which stays last
#   2 = at the end
GROW_POSITION = 2

# when guard_compatible's slow path is called and finds a value, when
# should we update the machine code to make this value the fast-path?
#   0 = never
#   another value = after about this many calls to the slow-path
UPDATE_ASM = 1291


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


def setup_once(assembler):
    nb_registers = WORD * 2
    assembler._guard_compat_checkers = [0] * nb_registers


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
