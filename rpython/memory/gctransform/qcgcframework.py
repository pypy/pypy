from rpython.rtyper.llannotation import SomePtr, SomeAddress, s_None
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gctransform.framework import (BaseFrameworkGCTransformer, BaseRootWalker)

VISIT_FPTR = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Void))

class QcgcFrameworkGCTransformer(BaseFrameworkGCTransformer):

    def build_root_walker(self):
        return QcgcRootWalker(self)

    def _declare_functions(self, GCClass, getfn, s_gc, s_typeid16):
        BaseFrameworkGCTransformer._declare_functions(self, GCClass, getfn,
                                                      s_gc, s_typeid16)
        gc = self.gcdata.gc
        #
        s_gcref = SomePtr(llmemory.GCREF)

        #self.malloc_weakref_ptr = self._getfn(
        #    GCClass.malloc_weakref.im_func,
        #    [s_gc, s_typeid16, annmodel.SomeInteger(nonneg=True),
        #     s_gcref], s_gcref)
        #
        def invokecallback(root, visit_fn):
            ref = llmemory.cast_adr_to_ptr(root, rffi.VOIDPP)
            visit_fn(llmemory.cast_ptr_to_adr(ref[0]))
        def pypy_trace_cb(obj, visit_fn):
            gc.trace(obj, invokecallback, visit_fn)
        pypy_trace_cb.c_name = "pypy_trace_cb"
        self.autoregister_ptrs.append(
            getfn(pypy_trace_cb,
                  [SomeAddress(), SomePtr(VISIT_FPTR)],
                  s_None))

    def gc_header_for(self, obj, needs_hash=False):
        hdr = self.gcdata.gc.gcheaderbuilder.header_of_object(obj)
        withhash, flag = self.gcdata.gc.withhash_flag_is_in_field
        x = getattr(hdr, withhash)
        TYPE = lltype.typeOf(x)
        x = lltype.cast_primitive(lltype.Signed, x)
        if needs_hash:
            x |= flag       # set the flag in the header
        else:
            x &= ~flag      # clear the flag in the header
        x = lltype.cast_primitive(TYPE, x)
        setattr(hdr, withhash, x)
        return hdr

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        for var in livevars:
            hop.genop("qcgc_push_root", [var])
        return livevars

    def pop_roots(self, hop, livevars):
        for _ in livevars: # Does not move, so no writing back
            hop.genop("qcgc_pop_root", [])

class QcgcRootWalker(BaseRootWalker):
    def walk_stack_roots(self, collect_stack_root, is_minor=False):
        raise NotImplementedError
