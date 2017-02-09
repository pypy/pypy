from rpython.rlib import rgc
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.rarithmetic import r_uint
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.jit.metainterp.compile import GuardCompatibleDescr
from rpython.jit.backend.llsupport import jitframe


# See ../x86/guard_compat.py for an explanation of the idea, based on
# x86-64 code.  Here, we have the generic data structures and algos.


PAIR = lltype.Struct('PAIR', ('gcref', lltype.Unsigned),   # a GC ref or -1
                             ('asmaddr', lltype.Signed))
BACKEND_CHOICES = lltype.GcStruct('BACKEND_CHOICES',
                        ('bc_faildescr', llmemory.GCREF),
                        ('bc_gcmap', lltype.Ptr(jitframe.GCMAP)),
                        ('bc_gc_table_tracer', llmemory.GCREF),
                        ('bc_search_tree', lltype.Signed),
                        ('bc_most_recent', PAIR),
                        ('bc_list', lltype.Array(PAIR)))

def _getofs(name):
    return llmemory.offsetof(BACKEND_CHOICES, name)
BCFAILDESCR = _getofs('bc_faildescr')
BCGCMAP = _getofs('bc_gcmap')
BCGCTABLETRACER = _getofs('bc_gc_table_tracer')
BCSEARCHTREE = _getofs('bc_search_tree')
BCMOSTRECENT = _getofs('bc_most_recent')
BCLIST = _getofs('bc_list')
del _getofs
BCLISTLENGTHOFS = llmemory.arraylengthoffset(BACKEND_CHOICES.bc_list)
BCLISTITEMSOFS = llmemory.itemoffsetof(BACKEND_CHOICES.bc_list, 0)
PAIRSIZE = llmemory.sizeof(PAIR)

def _real_number(ofs):    # hack
    return rffi.cast(lltype.Signed, rffi.cast(lltype.Unsigned, ofs))

@specialize.arg(2)
def bchoices_pair(gc, pair_addr, callback, arg):
    gcref_addr = pair_addr + llmemory.offsetof(PAIR, 'gcref')
    old = gcref_addr.unsigned[0]
    if old != r_uint(-1):
        gc._trace_callback(callback, arg, gcref_addr)
    new = gcref_addr.unsigned[0]
    return old != new

def bchoices_trace(gc, obj_addr, callback, arg):
    gc._trace_callback(callback, arg, obj_addr + BCFAILDESCR)
    gc._trace_callback(callback, arg, obj_addr + BCGCTABLETRACER)
    bchoices_pair(gc, obj_addr + BCMOSTRECENT, callback, arg)
    length = (obj_addr + BCLIST + BCLISTLENGTHOFS).signed[0]
    array_addr = obj_addr + BCLIST + BCLISTITEMSOFS
    item_addr = array_addr
    i = 0
    changes = False
    while i < length:
        changes |= bchoices_pair(gc, item_addr, callback, arg)
        item_addr += PAIRSIZE
        i += 1
    if changes:
        pairs_quicksort(array_addr, length)
lambda_bchoices_trace = lambda: bchoices_trace

eci = ExternalCompilationInfo(post_include_bits=["""
RPY_EXTERN void pypy_pairs_quicksort(void *base_addr, Signed length);
"""], separate_module_sources=["""
#include <stdlib.h>

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

def gcref_to_unsigned(gcref):
    return rffi.cast(lltype.Unsigned, gcref)


P_ARG = lltype.Struct('P_ARG', ('new_gcref', llmemory.GCREF),
                               ('bchoices', lltype.Ptr(BACKEND_CHOICES)),
                               ('jump_to', lltype.Signed))

INVOKE_FIND_COMPATIBLE_FUNC = lltype.Ptr(lltype.FuncType(
                [lltype.Ptr(P_ARG), lltype.Ptr(jitframe.JITFRAME)],
                lltype.Signed))

@specialize.memo()
def make_invoke_find_compatible(cpu):
    def invoke_find_compatible(p_arg, jitframe):
        bchoices = p_arg.bchoices
        new_gcref = p_arg.new_gcref
        descr = bchoices.bc_faildescr
        descr = cast_gcref_to_instance(GuardCompatibleDescr, descr)
        try:
            jitframe.jf_gcmap = bchoices.bc_gcmap
            result = descr.find_compatible(cpu, new_gcref)
            if result == 0:
                result = cpu.assembler.guard_compat_recovery
            else:
                if result == -1:
                    result = descr.adr_jump_offset
                bchoices = add_in_tree(bchoices, new_gcref, result)
                # ---no GC operation---
                choices_addr = descr._backend_choices_addr  # GC table
                bchoices_int = rffi.cast(lltype.Signed, bchoices)
                llop.raw_store(lltype.Void, choices_addr, 0, bchoices_int)
                llop.gc_writebarrier(lltype.Void, bchoices.bc_gc_table_tracer)
                # ---no GC operation end---
            bchoices.bc_most_recent.gcref = gcref_to_unsigned(new_gcref)
            bchoices.bc_most_recent.asmaddr = result
            llop.gc_writebarrier(lltype.Void, bchoices)
        except:             # oops!
            if not we_are_translated():
                import sys, pdb
                pdb.post_mortem(sys.exc_info()[2])
            result = cpu.assembler.guard_compat_recovery
        jitframe.jf_gcmap = lltype.nullptr(lltype.typeOf(jitframe.jf_gcmap).TO)
        p_arg.bchoices = bchoices
        p_arg.jump_to = result
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
        new_bchoices = lltype.malloc(BACKEND_CHOICES, length * 2 + 1)
        # --- no GC below: it would mess up the order of bc_list ---
        new_bchoices.bc_faildescr = bchoices.bc_faildescr
        new_bchoices.bc_gc_table_tracer = bchoices.bc_gc_table_tracer
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
    bchoices.bc_list[length - 1].gcref = gcref_to_unsigned(new_gcref)
    bchoices.bc_list[length - 1].asmaddr = new_asmaddr
    llop.gc_writebarrier(lltype.Void, bchoices)
    # --- no GC above ---
    addr = llmemory.cast_ptr_to_adr(bchoices)
    addr += BCLIST + BCLISTITEMSOFS
    pairs_quicksort(addr, length)
    return bchoices

def initial_bchoices(guard_compat_descr):
    bchoices = lltype.malloc(BACKEND_CHOICES, 1)
    bchoices.bc_faildescr = cast_instance_to_gcref(guard_compat_descr)
    bchoices.bc_gc_table_tracer = lltype.nullptr(llmemory.GCREF.TO)   # (*)
    bchoices.bc_most_recent.gcref = r_uint(-1)
    bchoices.bc_list[0].gcref = r_uint(-1)
    llop.gc_writebarrier(lltype.Void, bchoices)
    return bchoices

def descr_to_bchoices(descr):
    assert isinstance(descr, GuardCompatibleDescr)
    # ---no GC operation---
    bchoices = llop.raw_load(lltype.Signed, descr._backend_choices_addr, 0)
    bchoices = rffi.cast(lltype.Ptr(BACKEND_CHOICES), bchoices)
    # ---no GC operation end---
    return bchoices

def patch_guard_compatible(guard_token, get_addr_in_gc_table,
                           gc_table_tracer, search_tree_addr):
    guard_compat_descr = guard_token.faildescr
    assert isinstance(guard_compat_descr, GuardCompatibleDescr)
    #
    # read the initial value of '_backend_choices_addr', which is used
    # to store the index of the '_backend_choices' gc object in the gc
    # table
    bindex = guard_compat_descr._backend_choices_addr
    #
    # go to this address in the gctable
    choices_addr = get_addr_in_gc_table(bindex)
    #
    # now fix '_backend_choices_addr' to really point to the raw address
    # in the gc table
    guard_compat_descr._backend_choices_addr = choices_addr
    #
    bchoices = descr_to_bchoices(guard_compat_descr)
    assert len(bchoices.bc_list) == 1
    assert (cast_gcref_to_instance(GuardCompatibleDescr, bchoices.bc_faildescr)
            is guard_compat_descr)
    bchoices.bc_gcmap = guard_token.gcmap
    bchoices.bc_gc_table_tracer = lltype.cast_opaque_ptr(llmemory.GCREF,
                                                         gc_table_tracer)
    bchoices.bc_search_tree = search_tree_addr

def invalidate_pair(bchoices, pair_ofs):
    gcref_base = lltype.cast_opaque_ptr(llmemory.GCREF, bchoices)
    llop.raw_store(lltype.Void, gcref_base, _real_number(pair_ofs), r_uint(-1))
    ofs = pair_ofs + llmemory.sizeof(lltype.Unsigned)
    llop.raw_store(lltype.Void, gcref_base, _real_number(ofs), -1)

def invalidate_cache(faildescr):
    """Write -1 inside bchoices.bc_most_recent.gcref."""
    bchoices = descr_to_bchoices(faildescr)
    invalidate_pair(bchoices, BCMOSTRECENT)
