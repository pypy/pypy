"""Incminimark with GC flags stored in a separate page for fork-friendliness."""

from rpython.memory.gc import incminimark
from rpython.rtyper.lltypesystem import lltype, llmemory

class IncrementalMiniMarkRemoteHeaderGC(incminimark.IncrementalMiniMarkGC):
    # The GC header is similar to incminimark, except that the flags can be
    # placed anywhere, not just in the bits of tid.
    # TODO: Actually place flags somewhere other than tid.
    HDR = lltype.Struct('header',
                        ('tid', lltype.Signed),
                        ('remote_flags', lltype.Ptr(lltype.FixedSizeArray(lltype.Signed, 1))))

    def init_gc_object(self, addr, typeid16, flags=0):
        super(IncrementalMiniMarkRemoteHeaderGC, self).init_gc_object(addr, typeid16, flags)
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
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
        # TODO: make new remote flag sometimes.

    # Manipulate flags through a pointer.

    def get_flags(self, obj):
        return self.header(obj).remote_flags[0]

    def set_flags(self, obj, flags):
        self.header(obj).remote_flags[0] = flags

    def add_flags(self, obj, flags):
        self.header(obj).remote_flags[0] |= flags

    def remove_flags(self, obj, flags):
        self.header(obj).remote_flags[0] &= ~flags
