"""Incminimark with GC flags stored in a separate page for fork-friendliness."""

from rpython.rtyper.lltypesystem import llarena
from rpython.memory.gc import incminimark
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory

SIGNEDP = lltype.Ptr(lltype.FixedSizeArray(lltype.Signed, 1))

class IncrementalMiniMarkRemoteHeaderGC(incminimark.IncrementalMiniMarkGC):
    # The GC header is similar to incminimark, except that the flags can be
    # placed anywhere, not just in the bits of tid.
    HDR = lltype.Struct('header',
                        ('tid', lltype.Signed),
                        ('remote_flags', SIGNEDP))

    def __init__(self, config, **kwargs):
        super(IncrementalMiniMarkRemoteHeaderGC, self).__init__(config, **kwargs)
        ArenaCollectionClass = kwargs.get('ArenaCollectionClass', None)
        if ArenaCollectionClass is None:
            from rpython.memory.gc import minimarkpage
            ArenaCollectionClass = minimarkpage.ArenaCollection

        # TODO: can I reuse self.ac somehow? Is there a better thing to use?
        # This seems absurd.
        self.__ac_for_flags = ArenaCollectionClass(
                64*incminimark.WORD, 16*incminimark.WORD,
                small_request_threshold=LONG_BIT)

    def init_gc_object(self, adr, typeid16, flags=0):
        super(IncrementalMiniMarkRemoteHeaderGC, self).init_gc_object(adr, typeid16, flags)
        hdr = llmemory.cast_adr_to_ptr(adr, lltype.Ptr(self.HDR))
        hdr.remote_flags = lltype.direct_fieldptr(hdr, 'tid')

    def make_forwardstub(self, obj, forward_to):
        assert (self.header(obj).remote_flags
                == lltype.direct_fieldptr(self.header(obj), 'tid')), \
            "Nursery objects should not have separately-allocated flags."
        super(IncrementalMiniMarkRemoteHeaderGC, self).make_forwardstub(obj, forward_to)
        hdr = self.header(obj)
        hdr.remote_flags = lltype.direct_fieldptr(hdr, 'tid')

    def copy_header(self, src, dest):
        dest_hdr = self.header(dest)
        dest_hdr.tid = self.get_flags(src)
        dest_hdr.remote_flags = lltype.direct_fieldptr(dest_hdr, 'tid')
        self.__extract_flags_to_pointer(dest_hdr)

    def __extract_flags_to_pointer(self, hdr):
        """Make an object's GC header use out-of-line flags.

        Expects the object to not use inline tid-flags.
        """
        assert (hdr.remote_flags == lltype.nullptr(SIGNEDP.TO)
                or hdr.remote_flags == lltype.direct_fieldptr(hdr, 'tid')), \
                    "leaking old remote_flags!"
        size = llmemory.sizeof(lltype.Signed)
        adr = self.__ac_for_flags.malloc(size)
        hdr.remote_flags = llmemory.cast_adr_to_ptr(adr, SIGNEDP)
        hdr.remote_flags[0] = hdr.tid

    def finalize_header(self, adr):
        hdr = llmemory.cast_adr_to_ptr(adr, lltype.Ptr(self.HDR))
        if hdr.remote_flags != lltype.nullptr(SIGNEDP.TO):
            # If it points to allocated memory, this will be picked up by
            # __free_flags_if_finalized.
            hdr.remote_flags[0] |= incminimark.GCFLAG_DEAD

    def __free_flags_if_finalized(self, adr):
        flag_ptr = llmemory.cast_adr_to_ptr(adr, SIGNEDP)
        # If -42, it was set in finalize_header and the object was freed.
        return flag_ptr[0] & incminimark.GCFLAG_DEAD

    def free_unvisited_arena_objects_step(self, limit):
        done = super(IncrementalMiniMarkRemoteHeaderGC, self).free_unvisited_arena_objects_step(limit)
        self.__ac_for_flags.mass_free_incremental(
            self.__free_flags_if_finalized, done)
        return done

    def start_free(self):
        super(IncrementalMiniMarkRemoteHeaderGC, self).start_free()
        self.__ac_for_flags.mass_free_prepare()

    # Manipulate flags through a pointer.

    def get_flags(self, obj):
        return self.header(obj).remote_flags[0]

    def set_flags(self, obj, flags):
        self.header(obj).remote_flags[0] = flags

    def add_flags(self, obj, flags):
        self.header(obj).remote_flags[0] |= flags

    def remove_flags(self, obj, flags):
        self.header(obj).remote_flags[0] &= ~flags
