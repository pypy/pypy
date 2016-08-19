from rpython.rtyper.llannotation import SomePtr, SomeAddress, s_None
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.memory.gctransform.framework import (BaseFrameworkGCTransformer, BaseRootWalker)

VISIT_FPTR = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Void))

class QcgcFrameworkGCTransformer(BaseFrameworkGCTransformer):
    autoregister_ptrs = list()

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
            visit_fn(root)
        def pypy_trace_cb(obj, visit_fn):
            gc.trace(obj, invokecallback, visit_fn)
        pypy_trace_cb.c_name = "pypy_trace_cb"
        self.autoregister_ptrs.append(
            getfn(pypy_trace_cb, [SomeAddress(),
                                     SomePtr(VISIT_FPTR)],
                  s_None))

    def push_roots(sef, hop, keep_current_args=False):
        raise NotImplementedError

    def pop_roots(sef, hop, livevars):
        raise NotImplementedError

class QcgcRootWalker(BaseRootWalker):
    def walk_stack_roots(self, collect_stack_root, is_minor=False):
        raise NotImplementedError
