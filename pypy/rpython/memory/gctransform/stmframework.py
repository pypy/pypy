from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.memory.gctransform.framework import sizeofaddr
from pypy.rpython.lltypesystem import llmemory
from pypy.annotation import model as annmodel
from pypy.rlib.debug import fatalerror_notb


class StmFrameworkGCTransformer(FrameworkGCTransformer):

    def _declare_functions(self, GCClass, getfn, s_gc, *args):
        #
        def setup_thread(gc):
            self.root_walker.allocate_shadow_stack()
            gc.setup_thread()
        #
        def teardown_thread(gc):
            gc.teardown_thread()
            self.root_walker.free_shadow_stack()
        #
        super(StmFrameworkGCTransformer, self)._declare_functions(
            GCClass, getfn, s_gc, *args)
        self.setup_secondary_thread_ptr = getfn(
            setup_thread,
            [s_gc], annmodel.s_None)
        self.teardown_thread_ptr = getfn(
            teardown_thread,
            [s_gc], annmodel.s_None)
        self.stm_writebarrier_ptr = getfn(
            self.gcdata.gc.stm_writebarrier,
            [annmodel.SomeAddress()], annmodel.SomeAddress())
        self.stm_normalize_global_ptr = getfn(
            self.gcdata.gc.stm_normalize_global,
            [annmodel.SomeAddress()], annmodel.SomeAddress())
        self.stm_enter_transactional_mode_ptr = getfn(
            self.gcdata.gc.enter_transactional_mode.im_func
            [s_sc], annmodel.s_None)
        self.stm_leave_transactional_mode_ptr = getfn(
            self.gcdata.gc.leave_transactional_mode.im_func
            [s_sc], annmodel.s_None)
        self.stm_start_ptr = getfn(
            self.gcdata.gc.start_transaction.im_func,
            [s_gc], annmodel.s_None)
        self.stm_commit_ptr = getfn(
            self.gcdata.gc.commit_transaction.im_func,
            [s_gc], annmodel.s_None)

    def build_root_walker(self):
        return StmShadowStackRootWalker(self)

    def gct_stm_descriptor_init(self, hop):
        hop.genop("direct_call", [self.setup_secondary_thread_ptr,
                                  self.c_const_gc])

    def gct_stm_descriptor_done(self, hop):
        hop.genop("direct_call", [self.teardown_thread_ptr, self.c_const_gc])

    def gct_stm_writebarrier(self, hop):
        op = hop.spaceop
        v_adr = hop.genop('cast_ptr_to_adr',
                          [op.args[0]], resulttype=llmemory.Address)
        v_localadr = hop.genop("direct_call",
                               [self.stm_writebarrier_ptr, v_adr],
                               resulttype=llmemory.Address)
        hop.genop('cast_adr_to_ptr', [v_localadr], resultvar=op.result)

    def gct_stm_normalize_global(self, hop):
        op = hop.spaceop
        v_adr = hop.genop('cast_ptr_to_adr',
                          [op.args[0]], resulttype=llmemory.Address)
        v_globaladr = hop.genop("direct_call",
                                [self.stm_normalize_global_ptr, v_adr],
                                resulttype=llmemory.Address)
        hop.genop('cast_adr_to_ptr', [v_globaladr], resultvar=op.result)

    def gct_stm_start_transaction(self, hop):
        hop.genop("direct_call", [self.stm_start_ptr, self.c_const_gc])

    def gct_stm_commit_transaction(self, hop):
        hop.genop("direct_call", [self.stm_commit_ptr, self.c_const_gc])


class StmShadowStackRootWalker(BaseRootWalker):
    need_root_stack = True
    root_stack_depth = 163840

    def __init__(self, gctransformer):
        from pypy.rpython.memory.gctransform import shadowstack
        #
        BaseRootWalker.__init__(self, gctransformer)
        # we use the thread-local self.stackgcdata to store state;
        # 'self' is frozen.
        STACKGCDATA = lltype.Struct('STACKGCDATA',
            ('root_stack_top',  llmemory.Address),
            ('root_stack_base', llmemory.Address),
            hints={'stm_thread_local': True})
        stackgcdata = lltype.malloc(STACKGCDATA, immortal=True)
        self.stackgcdata = stackgcdata

        def incr_stack(n):
            top = stackgcdata.root_stack_top
            stackgcdata.root_stack_top = top + n*sizeofaddr
            return top
        self.incr_stack = incr_stack

        def decr_stack(n):
            top = stackgcdata.root_stack_top - n*sizeofaddr
            stackgcdata.root_stack_top = top
            return top
        self.decr_stack = decr_stack

        root_iterator = shadowstack.get_root_iterator(gctransformer)
        def walk_stack_root(callback, start, end):
            root_iterator.setcontext(NonConstant(llmemory.NULL))
            gc = self.gc
            addr = end
            while True:
                addr = root_iterator.nextleft(gc, start, addr)
                if addr == llmemory.NULL:
                    return
                callback(gc, addr)
        self.rootstackhook = walk_stack_root

        rsd = gctransformer.root_stack_depth
        if rsd is not None:
            self.root_stack_depth = rsd

    def setup_root_walker(self):
        self.allocate_shadow_stack()
        self.gcdata.main_thread_stack_base = self.stackgcdata.root_stack_base
        BaseRootWalker.setup_root_walker(self)

    def allocate_shadow_stack(self):
        root_stack_size = sizeofaddr * self.root_stack_depth
        base = llmemory.raw_malloc(root_stack_size)
        if base == llmemory.NULL:
            raise MemoryError
        self.stackgcdata.root_stack_base = base
        self.stackgcdata.root_stack_top  = base

    def free_shadow_stack(self):
        base = self.stackgcdata.root_stack_base
        llmemory.raw_free(base)

    def walk_stack_roots(self, collect_stack_root):
        # XXX only to walk the main thread's shadow stack, so far
        stackgcdata = self.stackgcdata
        if self.gcdata.main_thread_stack_base != stackgcdata.root_stack_base:
            fatalerror_notb("XXX not implemented: walk_stack_roots in thread")
        self.rootstackhook(collect_stack_root,
                           stackgcdata.root_stack_base,
                           stackgcdata.root_stack_top)
