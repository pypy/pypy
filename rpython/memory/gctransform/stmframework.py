from rpython.annotator import model as annmodel
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gctransform.framework import ( TYPE_ID,
     BaseFrameworkGCTransformer, BaseRootWalker, sizeofaddr)
from rpython.memory.gctypelayout import WEAKREF, WEAKREFPTR
from rpython.rtyper import rmodel, llannotation


class StmFrameworkGCTransformer(BaseFrameworkGCTransformer):

    def _declare_functions(self, GCClass, getfn, s_gc, s_typeid16):
        BaseFrameworkGCTransformer._declare_functions(self, GCClass, getfn,
                                                      s_gc, s_typeid16)
        gc = self.gcdata.gc
        #
        s_gcref = llannotation.SomePtr(llmemory.GCREF)

        self.malloc_weakref_ptr = self._getfn(
            GCClass.malloc_weakref.im_func,
            [s_gc, s_typeid16, annmodel.SomeInteger(nonneg=True),
             s_gcref], s_gcref)
        #
        def pypy_stmcb_size_rounded_up(obj):
            return gc.get_size(obj)
        pypy_stmcb_size_rounded_up.c_name = "pypy_stmcb_size_rounded_up"
        self.autoregister_ptrs.append(
            getfn(pypy_stmcb_size_rounded_up, [llannotation.SomeAddress()],
                  annmodel.SomeInteger()))
        #
        def invokecallback(root, visit_fn):
            visit_fn(root)
        def pypy_stmcb_trace(obj, visit_fn):
            gc.trace(obj, invokecallback, visit_fn)
        pypy_stmcb_trace.c_name = "pypy_stmcb_trace"
        self.autoregister_ptrs.append(
            getfn(pypy_stmcb_trace, [llannotation.SomeAddress(),
                                     llannotation.SomePtr(GCClass.VISIT_FPTR)],
                  annmodel.s_None))

    def build_root_walker(self):
        return StmRootWalker(self)

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        for var in livevars:
            hop.genop("stm_push_root", [var])
        return livevars

    def pop_roots(self, hop, livevars):
        for var in reversed(livevars):
            hop.genop("stm_pop_root_into", [var])

    def transform_generic_set(self, hop):
        # XXX detect if we're inside a 'stm_ignored' block and... do what?
        assert self.write_barrier_ptr == "stm"
        opname = hop.spaceop.opname
        v_struct = hop.spaceop.args[0]
        assert opname in ('setfield', 'setarrayitem', 'setinteriorfield',
                          'raw_store')
        if (v_struct.concretetype.TO._gckind == "gc"
                and hop.spaceop not in self.clean_sets):
            self.write_barrier_calls += 1
            hop.genop("stm_write", [v_struct])
        hop.rename('bare_' + opname)

    def gc_header_for(self, obj, needs_hash=False):
        return self.gcdata.gc.gcheaderbuilder.header_of_object(obj)

    def gct_gc_adr_of_root_stack_top(self, hop):
        hop.genop("stm_get_root_stack_top", [], resultvar=hop.spaceop.result)

    def gct_weakref_create(self, hop):
        XXX
        op = hop.spaceop
        
        type_id = self.get_type_id(WEAKREF)
        
        c_type_id = rmodel.inputconst(TYPE_ID, type_id)
        info = self.layoutbuilder.get_info(type_id)
        c_size = rmodel.inputconst(lltype.Signed, info.fixedsize)
        malloc_ptr = self.malloc_weakref_ptr
        c_null = rmodel.inputconst(llmemory.Address, llmemory.NULL)
        args = [self.c_const_gc, c_type_id, c_size, c_null]
        # XXX: for now, set weakptr ourselves and simply pass NULL

        # push and pop the current live variables *including* the argument
        # to the weakref_create operation, which must be kept alive and
        # moved if the GC needs to collect
        livevars = self.push_roots(hop, keep_current_args=True)
        v_result = hop.genop("direct_call", [malloc_ptr] + args,
                             resulttype=llmemory.GCREF)
        v_result = hop.genop("cast_opaque_ptr", [v_result],
                            resulttype=WEAKREFPTR)
        self.pop_roots(hop, livevars)
        # cast_ptr_to_adr must be done after malloc, as the GC pointer
        # might have moved just now.
        v_instance, = op.args
        v_addr = hop.genop("cast_ptr_to_adr", [v_instance],
                           resulttype=llmemory.Address)
        hop.genop("bare_setfield",
                  [v_result, rmodel.inputconst(lltype.Void, "weakptr"), v_addr])
        v_weakref = hop.genop("cast_ptr_to_weakrefptr", [v_result],
                              resulttype=llmemory.WeakRefPtr)
        hop.cast_result(v_weakref)

##    def _gct_with_roots_pushed(self, hop):
##        livevars = self.push_roots(hop)
##        self.default(hop)
##        self.pop_roots(hop, livevars)

##    # sync with lloperation.py
##    gct_stm_become_inevitable                       = _gct_with_roots_pushed
##    gct_stm_partial_commit_and_resume_other_threads = _gct_with_roots_pushed
##    gct_stm_perform_transaction                     = _gct_with_roots_pushed
##    gct_stm_inspect_abort_info                      = _gct_with_roots_pushed
##    gct_stm_threadlocalref_set                      = _gct_with_roots_pushed


class StmRootWalker(BaseRootWalker):

    def need_thread_support(self, gctransformer, getfn):
        # gc_thread_start() and gc_thread_die() don't need to become
        # anything.  When a new thread start, there is anyway first
        # the "after/before" callbacks from rffi, which contain calls
        # to "stm_enter_callback_call/stm_leave_callback_call".
        pass

    def walk_stack_roots(self, collect_stack_root):
        raise NotImplementedError
