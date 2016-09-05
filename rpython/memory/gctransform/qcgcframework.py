from rpython.rtyper.llannotation import SomePtr, SomeAddress, s_None
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper import rmodel
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gctransform.framework import (BaseFrameworkGCTransformer,
        BaseRootWalker, TYPE_ID, WEAKREF, WEAKREFPTR)

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

    #Compilation error when overriding, no idea why
    #def finish_tables(self):
    #    BaseFrameworkGCTransformer.finish_tables(self)
        #Makes test fail, works when translating pypy (but compiling still fails)
        #assert len(self.layoutbuilder.addresses_of_static_ptrs_in_nongc) == 2

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

    def gct_weakref_create(self, hop):
        # Custom weakref creation as their registration is slightly different
        op = hop.spaceop

        type_id = self.get_type_id(WEAKREF)

        c_type_id = rmodel.inputconst(TYPE_ID, type_id)
        info = self.layoutbuilder.get_info(type_id)
        c_size = rmodel.inputconst(lltype.Signed, info.fixedsize)
        malloc_ptr = self.malloc_fixedsize_ptr
        c_false = rmodel.inputconst(lltype.Bool, False)
        c_has_weakptr = rmodel.inputconst(lltype.Bool, True)
        args = [self.c_const_gc, c_type_id, c_size,
                c_false, c_false, c_has_weakptr]

        # push and pop the current live variables *including* the argument
        # to the weakref_create operation, which must be kept alive if the GC
        # needs to collect
        livevars = self.push_roots(hop, keep_current_args=True)
        v_result = hop.genop("direct_call", [malloc_ptr] + args,
                             resulttype=llmemory.GCREF)
        v_result = hop.genop("cast_opaque_ptr", [v_result],
                            resulttype=WEAKREFPTR)
        self.pop_roots(hop, livevars)
        #
        v_instance, = op.args
        v_addr = hop.genop("cast_ptr_to_adr", [v_instance],
                           resulttype=llmemory.Address)
        c_weakptr = rmodel.inputconst(lltype.Void, "weakptr")
        hop.genop("bare_setfield",
                  [v_result, c_weakptr, v_addr])
        v_weakref = hop.genop("cast_ptr_to_weakrefptr", [v_result],
                              resulttype=llmemory.WeakRefPtr)
        # Register weakref
        v_fieldaddr = hop.genop("direct_fieldptr", [v_result, c_weakptr],
                            resulttype=llmemory.Address)
        hop.genop("qcgc_register_weakref", [v_result, v_fieldaddr])
        hop.cast_result(v_weakref)

class QcgcRootWalker(BaseRootWalker):
    def walk_stack_roots(self, collect_stack_root, is_minor=False):
        raise NotImplementedError
