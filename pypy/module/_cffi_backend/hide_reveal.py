from rpython.rlib import rgc
from rpython.rlib.rweaklist import RWeakListMixin
from rpython.rlib.objectmodel import fetch_translated_config
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi


class HideRevealRWeakList:
    """Slow implementation of HideReveal: uses a RWeakListMixin."""

    def __init__(self):
        class GlobGcrefs(RWeakListMixin):
            pass
        self.glob_gcrefs = GlobGcrefs()
        self.glob_gcrefs.initialize()

    def _freeze_(self):
        return True

    def hide_object(self, obj):
        # XXX leaks if we call this function often on the same object
        index = self.glob_gcrefs.add_handle(obj)
        return rffi.cast(llmemory.Address, index)

    def reveal_object(self, Class, addr):
        index = rffi.cast(lltype.Signed, addr)
        return self.glob_gcrefs.fetch_handle(index)


class HideRevealCast:
    """Fast implementation of HideReveal: just a cast."""

    def _freeze_(self):
        return True

    def hide_object(self, obj):
        gcref = rgc.cast_instance_to_gcref(obj)
        raw = rgc.hide_nonmovable_gcref(gcref)
        return rffi.cast(rffi.VOIDP, raw)

    def reveal_object(self, Class, raw_ptr):
        addr = rffi.cast(llmemory.Address, raw_ptr)
        gcref = rgc.reveal_gcref(addr)
        return rgc.try_cast_gcref_to_instance(Class, gcref)


hide_reveal_slow = HideRevealRWeakList()
hide_reveal_fast = HideRevealCast()

def hide_reveal():
    config = fetch_translated_config()
    if config is not None and config.translation.split_gc_address_space:
        return hide_reveal_slow
    else:
        return hide_reveal_fast
