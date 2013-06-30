from rpython.annotator import model as annmodel
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gctransform.framework import (
     BaseFrameworkGCTransformer, BaseRootWalker, sizeofaddr)


class StmFrameworkGCTransformer(BaseFrameworkGCTransformer):

    def _declare_functions(self, GCClass, getfn, s_gc, s_typeid16):
        BaseFrameworkGCTransformer._declare_functions(self, GCClass, getfn,
                                                      s_gc, s_typeid16)
        gc = self.gcdata.gc
        #
        def pypy_stmcb_size(obj):
            return gc.get_size(obj)
        pypy_stmcb_size.c_name = "pypy_stmcb_size"
        self.autoregister_ptrs.append(
            getfn(pypy_stmcb_size, [annmodel.SomeAddress()],
                  annmodel.SomeInteger()))
        #
        def invokecallback(root, visit_fn):
            visit_fn(root)
        def pypy_stmcb_trace(obj, visit_fn):
            gc.trace(obj, invokecallback, visit_fn)
        pypy_stmcb_trace.c_name = "pypy_stmcb_trace"
        self.autoregister_ptrs.append(
            getfn(pypy_stmcb_trace, [annmodel.SomeAddress(),
                                     annmodel.SomePtr(GCClass.VISIT_FPTR)],
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

    def gc_header_for(self, obj, needs_hash=False):
        return self.gcdata.gc.gcheaderbuilder.header_of_object(obj)


class StmRootWalker(BaseRootWalker):

    def need_thread_support(self, gctransformer, getfn):
        def thread_start():
            llop.stm_initialize(lltype.Void)
        def thread_die():
            llop.stm_finalize(lltype.Void)
        self.thread_start_ptr = getfn(thread_start, [], annmodel.s_None)
        self.thread_die_ptr = getfn(thread_die, [], annmodel.s_None)

    def walk_stack_roots(self, collect_stack_root):
        raise NotImplementedError
