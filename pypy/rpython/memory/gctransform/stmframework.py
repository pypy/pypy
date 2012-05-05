from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.memory.gctransform.framework import sizeofaddr
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import rmodel
from pypy.annotation import model as annmodel
from pypy.rlib.debug import fatalerror_notb
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.objectmodel import specialize


class StmFrameworkGCTransformer(FrameworkGCTransformer):

    def _declare_functions(self, GCClass, getfn, s_gc, *args):
        super(StmFrameworkGCTransformer, self)._declare_functions(
            GCClass, getfn, s_gc, *args)
        self.stm_writebarrier_ptr = getfn(
            self.gcdata.gc.stm_writebarrier,
            [annmodel.SomeAddress()], annmodel.SomeAddress())
        self.stm_normalize_global_ptr = getfn(
            self.gcdata.gc.stm_normalize_global,
            [annmodel.SomeAddress()], annmodel.SomeAddress())

    def build_root_walker(self):
        return StmShadowStackRootWalker(self)

    def _gc_adr_of_gcdata_attr(self, hop, attrname):
        x = self.root_walker.stackgcdata
        c_const_stackgcdata = rmodel.inputconst(lltype.typeOf(x), x)
        op = hop.spaceop
        ofs = llmemory.offsetof(c_const_stackgcdata.concretetype.TO,
                                attrname)
        c_ofs = rmodel.inputconst(lltype.Signed, ofs)
        v_gcdata_adr = hop.genop('cast_ptr_to_adr', [c_const_stackgcdata],
                                 resulttype=llmemory.Address)
        hop.genop('adr_add', [v_gcdata_adr, c_ofs], resultvar=op.result)

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
        livevars = self.push_roots(hop)
        hop.genop("direct_call", [self.stm_start_ptr, self.c_const_gc])
        self.pop_roots(hop, livevars)

    def gct_stm_stop_transaction(self, hop):
        livevars = self.push_roots(hop)
        hop.genop("direct_call", [self.stm_stop_ptr, self.c_const_gc])
        self.pop_roots(hop, livevars)


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
        @specialize.argtype(1)
        def walk_stack_root(callback, arg, start, end):
            root_iterator.setcontext(NonConstant(llmemory.NULL))
            gc = self.gc
            addr = end
            while True:
                addr = root_iterator.nextleft(gc, start, addr)
                if addr == llmemory.NULL:
                    return
                callback(arg, addr)
        self.rootstackhook = walk_stack_root

        rsd = gctransformer.root_stack_depth
        if rsd is not None:
            self.root_stack_depth = rsd

    def need_thread_support(self, gctransformer, getfn):
        gc = gctransformer.gcdata.gc
        #
        def gc_thread_start():
            self.allocate_shadow_stack()
            gc.setup_thread()
        #
        def gc_thread_die():
            gc.teardown_thread()
            self.free_shadow_stack()
        #
        self.thread_start_ptr = getfn(
            gc_thread_start,
            [], annmodel.s_None)
        self.thread_die_ptr = getfn(
            gc_thread_die,
            [], annmodel.s_None)

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

    def start_transaction(self):
        # When a transaction is aborted, it leaves behind its shadow
        # stack content.  We have to clear it here.
        stackgcdata = self.stackgcdata
        stackgcdata.root_stack_top = stackgcdata.root_stack_base

    def walk_stack_roots(self, collect_stack_root):
        raise NotImplementedError
        # XXX only to walk the main thread's shadow stack, so far
        stackgcdata = self.stackgcdata
        if self.gcdata.main_thread_stack_base != stackgcdata.root_stack_base:
            fatalerror_notb("XXX not implemented: walk_stack_roots in thread")
        self.rootstackhook(collect_stack_root, self.gcdata.gc,
                           stackgcdata.root_stack_base,
                           stackgcdata.root_stack_top)

    @specialize.argtype(2)
    def walk_current_stack_roots(self, collect_stack_root, arg):
        stackgcdata = self.stackgcdata
        self.rootstackhook(collect_stack_root, arg,
                           stackgcdata.root_stack_base,
                           stackgcdata.root_stack_top)

    @specialize.argtype(2)
    def walk_current_nongc_roots(self, collect_nongc_root, arg):
        gcdata = self.gcdata
        gc = self.gc
        addr = gcdata.static_root_start
        end = gcdata.static_root_nongcend
        while addr != end:
            result = addr.address[0]
            if gc.points_to_valid_gc_object(result):
                collect_nongc_root(arg, result)
            addr += sizeofaddr
