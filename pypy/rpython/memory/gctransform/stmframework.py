from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.annotation import model as annmodel


class StmFrameworkGCTransformer(FrameworkGCTransformer):

    def _declare_functions(self, GCClass, getfn, s_gc, *args):
        super(StmFrameworkGCTransformer, self)._declare_functions(
            GCClass, getfn, s_gc, *args)
        self.setup_secondary_thread_ptr = getfn(
            GCClass._setup_secondary_thread.im_func,
            [s_gc], annmodel.s_None)
        self.teardown_thread_ptr = getfn(
            GCClass.teardown_thread.im_func,
            [s_gc], annmodel.s_None)

    def push_roots(self, hop, keep_current_args=False):
        pass

    def pop_roots(self, hop, livevars):
        pass

    def build_root_walker(self):
        return StmStackRootWalker(self)

    def gct_stm_descriptor_init(self, hop):
        hop.genop("direct_call", [self.setup_secondary_thread_ptr,
                                  self.c_const_gc])

    def gct_stm_descriptor_done(self, hop):
        hop.genop("direct_call", [self.teardown_thread_ptr, self.c_const_gc])


class StmStackRootWalker(BaseRootWalker):

    def walk_stack_roots(self, collect_stack_root):
        raise NotImplementedError
