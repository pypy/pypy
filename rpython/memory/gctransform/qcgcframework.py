from rpython.rtyper.llannotation import SomePtr, SomeAddress, s_None
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper import rmodel
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
        if needs_hash:
            hdr.hash = lltype.identityhash_nocache(obj._as_ptr())
        else:
            assert hdr.hash == 0
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

    def gct_gc_fq_register(self, hop):
        pass
#        index = self.get_finalizer_queue_index(hop)
#        c_index = rmodel.inputconst(lltype.Signed, index)
#        v_ptr = hop.spaceop.args[1]
#        v_ptr = hop.genop("cast_opaque_ptr", [v_ptr],
#                          resulttype=llmemory.GCREF)
#        hop.genop("direct_call", [self.register_finalizer_ptr, self.c_const_gc,
#                                  c_index, v_ptr])

    def gct_gc_fq_next_dead(self, hop):
        # "return NULL" to tell PyPy that there are no finalizers to run (XXX)
        op = hop.spaceop
        null = lltype.nullptr(op.result.concretetype.TO)
        c_null = rmodel.inputconst(op.result.concretetype, null)
        hop.genop("same_as", [c_null], resultvar=op.result)

        #        index = self.get_finalizer_queue_index(hop)
#        c_ll_next_dead = self.finalizer_handlers[index][2]
#        v_adr = hop.genop("direct_call", [c_ll_next_dead],
#                          resulttype=llmemory.Address)
#        hop.genop("cast_adr_to_ptr", [v_adr],
#                  resultvar = hop.spaceop.result)

class QcgcRootWalker(BaseRootWalker):
    def walk_stack_roots(self, collect_stack_root, is_minor=False):
        raise NotImplementedError
