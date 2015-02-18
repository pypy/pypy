from rpython.rlib import _rffi_stacklet as _c
from rpython.rlib.debug import ll_assert
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop


NULL_SUSPSTACK = lltype.nullptr(llmemory.GCREF.TO)


def _new_callback(h, arg):
    # We still have the old shadowstack active at this point; save it
    # away, and start a fresh new one
    oldsuspstack = gcrootfinder.oldsuspstack
    h = llmemory.cast_ptr_to_adr(h)
    llop.gc_save_current_state_away(lltype.Void,
                                    oldsuspstack, h)
    llop.gc_start_fresh_new_state(lltype.Void)
    gcrootfinder.oldsuspstack = NULL_SUSPSTACK
    #
    newsuspstack = gcrootfinder.callback(oldsuspstack, arg)
    #
    # Finishing this stacklet.
    gcrootfinder.oldsuspstack = NULL_SUSPSTACK
    gcrootfinder.newsuspstack = newsuspstack
    h = llop.gc_shadowstackref_context(llmemory.Address, newsuspstack)
    return llmemory.cast_adr_to_ptr(h, _c.handle)

def prepare_old_suspstack():
    if not gcrootfinder.oldsuspstack:   # else reuse the one still there
        _allocate_old_suspstack()

def _allocate_old_suspstack():
    suspstack = llop.gc_shadowstackref_new(llmemory.GCREF)
    gcrootfinder.oldsuspstack = suspstack
_allocate_old_suspstack._dont_inline_ = True

def get_result_suspstack(h):
    # Now we are in the target, after the switch() or the new().
    # Note that this whole module was carefully written in such a way as
    # not to invoke pushing/popping things off the shadowstack at
    # unexpected moments...
    oldsuspstack = gcrootfinder.oldsuspstack
    newsuspstack = gcrootfinder.newsuspstack
    gcrootfinder.oldsuspstack = NULL_SUSPSTACK
    gcrootfinder.newsuspstack = NULL_SUSPSTACK
    if not h:
        raise MemoryError
    # We still have the old shadowstack active at this point; save it
    # away, and restore the new one
    if oldsuspstack:
        ll_assert(not _c.is_empty_handle(h),"unexpected empty stacklet handle")
        h = llmemory.cast_ptr_to_adr(h)
        llop.gc_save_current_state_away(lltype.Void, oldsuspstack, h)
    else:
        ll_assert(_c.is_empty_handle(h),"unexpected non-empty stacklet handle")
        llop.gc_forget_current_state(lltype.Void)
    #
    llop.gc_restore_state_from(lltype.Void, newsuspstack)
    #
    # From this point on, 'newsuspstack' is consumed and done, its
    # shadow stack installed as the current one.  It should not be
    # used any more.  For performance, we avoid it being deallocated
    # by letting it be reused on the next switch.
    gcrootfinder.oldsuspstack = newsuspstack
    # Return.
    return oldsuspstack


class StackletGcRootFinder(object):
    def new(thrd, callback, arg):
        gcrootfinder.callback = callback
        thread_handle = thrd._thrd
        prepare_old_suspstack()
        h = _c.new(thread_handle, llhelper(_c.run_fn, _new_callback), arg)
        return get_result_suspstack(h)
    new._dont_inline_ = True
    new = staticmethod(new)

    def switch(suspstack):
        # suspstack has a handle to target, i.e. where to switch to
        ll_assert(suspstack != gcrootfinder.oldsuspstack,
                  "stacklet: invalid use")
        gcrootfinder.newsuspstack = suspstack
        h = llop.gc_shadowstackref_context(llmemory.Address, suspstack)
        h = llmemory.cast_adr_to_ptr(h, _c.handle)
        prepare_old_suspstack()
        h = _c.switch(h)
        return get_result_suspstack(h)
    switch._dont_inline_ = True
    switch = staticmethod(switch)

    @staticmethod
    def is_empty_handle(suspstack):
        return not suspstack

    @staticmethod
    def get_null_handle():
        return NULL_SUSPSTACK


gcrootfinder = StackletGcRootFinder()
gcrootfinder.oldsuspstack = NULL_SUSPSTACK
gcrootfinder.newsuspstack = NULL_SUSPSTACK
