import weakref
from pypy.rpython.lltypesystem import lltype, llmemory


class GCHeaderBuilder(object):

    def __init__(self, HDR):
        """NOT_RPYTHON"""
        self.HDR = HDR
        self.obj2header = weakref.WeakKeyDictionary()
        self.header2obj = weakref.WeakKeyDictionary()
        self.size_gc_header = llmemory.GCHeaderOffset(self)

    def header_of_object(self, gcptr):
        return self.obj2header[gcptr._as_obj()]

    def object_from_header(self, headerptr):
        return self.header2obj[headerptr._as_obj()]

    def get_header(self, gcptr):
        return self.obj2header.get(gcptr._as_obj(), None)

    def new_header(self, gcptr):
        gcobj = gcptr._as_obj()
        assert gcobj not in self.obj2header
        # sanity checks
        assert isinstance(gcobj._TYPE, lltype.GC_CONTAINER)
        assert not isinstance(gcobj._TYPE, lltype.GcOpaqueType)
        assert not gcobj._parentstructure()
        headerptr = lltype.malloc(self.HDR, immortal=True)
        self.obj2header[gcobj] = headerptr
        self.header2obj[headerptr._obj] = gcptr._as_ptr()
        return headerptr

    def _freeze_(self):
        return True     # for reads of size_gc_header
