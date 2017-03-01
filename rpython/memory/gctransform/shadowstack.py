from rpython.annotator import model as annmodel
from rpython.rtyper.llannotation import SomePtr
from rpython.rlib.debug import ll_assert
from rpython.rlib.nonconst import NonConstant
from rpython.rlib import rgc
from rpython.rtyper import rmodel
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.llannotation import SomeAddress
from rpython.memory.gctransform.framework import (
     BaseFrameworkGCTransformer, BaseRootWalker, sizeofaddr)
from rpython.rtyper.rbuiltin import gen_cast


class ShadowStackFrameworkGCTransformer(BaseFrameworkGCTransformer):
    def annotate_walker_functions(self, getfn):
        self.incr_stack_ptr = getfn(self.root_walker.incr_stack,
                                   [annmodel.SomeInteger()],
                                   SomeAddress(),
                                   inline = True)
        self.decr_stack_ptr = getfn(self.root_walker.decr_stack,
                                   [annmodel.SomeInteger()],
                                   SomeAddress(),
                                   inline = True)

    def build_root_walker(self):
        return ShadowStackRootWalker(self)

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        if not livevars:
            return []
        c_len = rmodel.inputconst(lltype.Signed, len(livevars) )
        base_addr = hop.genop("direct_call", [self.incr_stack_ptr, c_len ],
                              resulttype=llmemory.Address)
        for k,var in enumerate(livevars):
            c_k = rmodel.inputconst(lltype.Signed, k * sizeofaddr)
            v_adr = gen_cast(hop.llops, llmemory.Address, var)
            hop.genop("raw_store", [base_addr, c_k, v_adr])
        return livevars

    def pop_roots(self, hop, livevars):
        if not livevars:
            return
        c_len = rmodel.inputconst(lltype.Signed, len(livevars) )
        base_addr = hop.genop("direct_call", [self.decr_stack_ptr, c_len ],
                              resulttype=llmemory.Address)
        if self.gcdata.gc.moving_gc:
            # for moving collectors, reload the roots into the local variables
            for k,var in enumerate(livevars):
                c_k = rmodel.inputconst(lltype.Signed, k * sizeofaddr)
                v_newaddr = hop.genop("raw_load", [base_addr, c_k],
                                      resulttype=llmemory.Address)
                hop.genop("gc_reload_possibly_moved", [v_newaddr, var])


class ShadowStackRootWalker(BaseRootWalker):
    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)
        # NB. 'self' is frozen, but we can use self.gcdata to store state
        gcdata = self.gcdata

        def incr_stack(n):
            top = gcdata.root_stack_top
            gcdata.root_stack_top = top + n*sizeofaddr
            return top
        self.incr_stack = incr_stack

        def decr_stack(n):
            top = gcdata.root_stack_top - n*sizeofaddr
            gcdata.root_stack_top = top
            return top
        self.decr_stack = decr_stack

        def walk_stack_root(callback, start, end):
            gc = self.gc
            addr = end
            while addr != start:
                addr -= sizeofaddr
                if gc.points_to_valid_gc_object(addr):
                    callback(gc, addr)
        self.rootstackhook = walk_stack_root

        self.shadow_stack_pool = ShadowStackPool(gcdata)
        rsd = gctransformer.root_stack_depth
        if rsd is not None:
            self.shadow_stack_pool.root_stack_depth = rsd

    def push_stack(self, addr):
        top = self.incr_stack(1)
        top.address[0] = addr

    def pop_stack(self):
        top = self.decr_stack(1)
        return top.address[0]

    def setup_root_walker(self):
        self.shadow_stack_pool.initial_setup()
        BaseRootWalker.setup_root_walker(self)

    def walk_stack_roots(self, collect_stack_root, is_minor=False):
        gcdata = self.gcdata
        self.rootstackhook(collect_stack_root,
                           gcdata.root_stack_base, gcdata.root_stack_top)

    def need_thread_support_WITH_GIL(self, gctransformer, getfn):
        from rpython.rlib import rthread    # xxx fish
        gcdata = self.gcdata
        # the interfacing between the threads and the GC is done via
        # two completely ad-hoc operations at the moment:
        # gc_thread_run and gc_thread_die.  See docstrings below.

        shadow_stack_pool = self.shadow_stack_pool
        SHADOWSTACKREF = get_shadowstackref(self, gctransformer)

        # this is a dict {tid: SHADOWSTACKREF}, where the tid for the
        # current thread may be missing so far
        gcdata.thread_stacks = None

        # Return the thread identifier, as an integer.
        get_tid = rthread.get_ident

        def thread_setup():
            tid = get_tid()
            gcdata.main_tid = tid
            gcdata.active_tid = tid

        def thread_run():
            """Called whenever the current thread (re-)acquired the GIL.
            This should ensure that the shadow stack installed in
            gcdata.root_stack_top/root_stack_base is the one corresponding
            to the current thread.
            No GC operation here, e.g. no mallocs or storing in a dict!

            Note that here specifically we don't call rthread.get_ident(),
            but rthread.get_or_make_ident().  We are possibly in a fresh
            new thread, so we need to be careful.
            """
            tid = rthread.get_or_make_ident()
            if gcdata.active_tid != tid:
                switch_shadow_stacks(tid)

        def thread_die():
            """Called just before the final GIL release done by a dying
            thread.  After a thread_die(), no more gc operation should
            occur in this thread.
            """
            tid = get_tid()
            if tid == gcdata.main_tid:
                return   # ignore calls to thread_die() in the main thread
                         # (which can occur after a fork()).
            # we need to switch somewhere else, so go to main_tid
            gcdata.active_tid = gcdata.main_tid
            thread_stacks = gcdata.thread_stacks
            new_ref = thread_stacks[gcdata.active_tid]
            try:
                del thread_stacks[tid]
            except KeyError:
                pass
            # no more GC operation from here -- switching shadowstack!
            shadow_stack_pool.forget_current_state()
            shadow_stack_pool.restore_state_from(new_ref)

        def switch_shadow_stacks(new_tid):
            # we have the wrong shadowstack right now, but it should not matter
            thread_stacks = gcdata.thread_stacks
            try:
                if thread_stacks is None:
                    gcdata.thread_stacks = thread_stacks = {}
                    raise KeyError
                new_ref = thread_stacks[new_tid]
            except KeyError:
                new_ref = lltype.nullptr(SHADOWSTACKREF)
            try:
                old_ref = thread_stacks[gcdata.active_tid]
            except KeyError:
                # first time we ask for a SHADOWSTACKREF for this active_tid
                old_ref = shadow_stack_pool.allocate(SHADOWSTACKREF)
                thread_stacks[gcdata.active_tid] = old_ref
            #
            # no GC operation from here -- switching shadowstack!
            shadow_stack_pool.save_current_state_away(old_ref)
            if new_ref:
                shadow_stack_pool.restore_state_from(new_ref)
            else:
                shadow_stack_pool.start_fresh_new_state()
            # done
            #
            gcdata.active_tid = new_tid
        switch_shadow_stacks._dont_inline_ = True

        def thread_after_fork(result_of_fork, opaqueaddr):
            # we don't need a thread_before_fork in this case, so
            # opaqueaddr == NULL.  This is called after fork().
            if result_of_fork == 0:
                # We are in the child process.  Assumes that only the
                # current thread survived, so frees the shadow stacks
                # of all the other ones.
                gcdata.thread_stacks = None
                # Finally, reset the stored thread IDs, in case it
                # changed because of fork().  Also change the main
                # thread to the current one (because there is not any
                # other left).
                tid = get_tid()
                gcdata.main_tid = tid
                gcdata.active_tid = tid

        self.thread_setup = thread_setup
        self.thread_run_ptr = getfn(thread_run, [], annmodel.s_None,
                                    inline=True, minimal_transform=False)
        self.thread_die_ptr = getfn(thread_die, [], annmodel.s_None,
                                    minimal_transform=False)
        # no thread_before_fork_ptr here
        self.thread_after_fork_ptr = getfn(thread_after_fork,
                                           [annmodel.SomeInteger(),
                                            SomeAddress()],
                                           annmodel.s_None,
                                           minimal_transform=False)

    def need_thread_support(self, gctransformer, getfn):  # NO GIL VERSION
        from rpython.rlib import rthread
        gcdata = self.gcdata
        # the interfacing between the threads and the GC is done via
        # two completely ad-hoc operations at the moment:
        # gc_thread_run and gc_thread_die.  See docstrings below.

        tl_shadowstack = rthread.ThreadLocalField(llmemory.Address,
                                                  'shadowstack')
        tl_synclock = rthread.ThreadLocalField(lltype.Signed, 'synclock')

        def thread_setup():
            allocate_shadow_stack()
            tl_synclock.get_or_make_raw()

        def thread_run():
            # If it's the first time we see this thread, allocate
            # a shadowstack.
            if tl_shadowstack.get_or_make_raw() == llmemory.NULL:
                allocate_shadow_stack()

        def allocate_shadow_stack():
            root_stack_depth = 163840
            root_stack_size = sizeofaddr * root_stack_depth
            ss = llmemory.raw_malloc(root_stack_size)
            if not ss:
                raise MemoryError
            tl_shadowstack.setraw(ss)
        allocate_shadow_stack._dont_inline_ = True

        def thread_die():
            """Called just before the final GIL release done by a dying
            thread.  After a thread_die(), no more gc operation should
            occur in this thread.
            """
            p = tl_shadowstack.get_or_make_raw()
            tl_shadowstack.setraw(llmemory.NULL)
            llmemory.raw_free(p)

        self.thread_setup = thread_setup
        self.thread_run_ptr = getfn(thread_run, [], annmodel.s_None,
                                    inline=True, minimal_transform=False)
        self.thread_die_ptr = getfn(thread_die, [], annmodel.s_None,
                                    minimal_transform=False)

    def need_stacklet_support(self, gctransformer, getfn):
        from rpython.rlib import _stacklet_shadowstack
        _stacklet_shadowstack.complete_destrptr(gctransformer)

# ____________________________________________________________

class ShadowStackPool(object):
    """Manages a pool of shadowstacks.
    """
    _alloc_flavor_ = "raw"
    root_stack_depth = 163840

    def __init__(self, gcdata):
        self.unused_full_stack = llmemory.NULL
        self.gcdata = gcdata

    def initial_setup(self):
        self._prepare_unused_stack()
        self.start_fresh_new_state()

    def allocate(self, SHADOWSTACKREF):
        """Allocate an empty SHADOWSTACKREF object."""
        return lltype.malloc(SHADOWSTACKREF, zero=True)

    def save_current_state_away(self, shadowstackref):
        """Save the current state away into 'shadowstackref'.
        This either works, or raise MemoryError and nothing is done.
        To do a switch, first call save_current_state_away() or
        forget_current_state(), and then call restore_state_from()
        or start_fresh_new_state().
        """
        self._prepare_unused_stack()
        shadowstackref.base = self.gcdata.root_stack_base
        shadowstackref.top  = self.gcdata.root_stack_top
        ll_assert(shadowstackref.base <= shadowstackref.top,
                  "save_current_state_away: broken shadowstack")
        #
        # cannot use llop.gc_writebarrier() here, because
        # we are in a minimally-transformed GC helper :-/
        gc = self.gcdata.gc
        if hasattr(gc.__class__, 'write_barrier'):
            shadowstackadr = llmemory.cast_ptr_to_adr(shadowstackref)
            gc.write_barrier(shadowstackadr)
        #
        self.gcdata.root_stack_top = llmemory.NULL  # to detect missing restore

    def forget_current_state(self):
        ll_assert(self.gcdata.root_stack_base == self.gcdata.root_stack_top,
                  "forget_current_state: shadowstack not empty!")
        if self.unused_full_stack:
            llmemory.raw_free(self.unused_full_stack)
        self.unused_full_stack = self.gcdata.root_stack_base
        self.gcdata.root_stack_top = llmemory.NULL  # to detect missing restore

    def restore_state_from(self, shadowstackref):
        ll_assert(bool(shadowstackref.base), "empty shadowstackref!")
        ll_assert(shadowstackref.base <= shadowstackref.top,
                  "restore_state_from: broken shadowstack")
        self.gcdata.root_stack_base = shadowstackref.base
        self.gcdata.root_stack_top  = shadowstackref.top
        self._cleanup(shadowstackref)

    def start_fresh_new_state(self):
        self.gcdata.root_stack_base = self.unused_full_stack
        self.gcdata.root_stack_top  = self.unused_full_stack
        self.unused_full_stack = llmemory.NULL

    def _cleanup(self, shadowstackref):
        shadowstackref.base = llmemory.NULL
        shadowstackref.top = llmemory.NULL

    def _prepare_unused_stack(self):
        if self.unused_full_stack == llmemory.NULL:
            root_stack_size = sizeofaddr * self.root_stack_depth
            self.unused_full_stack = llmemory.raw_malloc(root_stack_size)
            if self.unused_full_stack == llmemory.NULL:
                raise MemoryError


def get_shadowstackref(root_walker, gctransformer):
    if hasattr(gctransformer, '_SHADOWSTACKREF'):
        return gctransformer._SHADOWSTACKREF

    SHADOWSTACKREFPTR = lltype.Ptr(lltype.GcForwardReference())
    SHADOWSTACKREF = lltype.GcStruct('ShadowStackRef',
                                     ('base', llmemory.Address),
                                     ('top', llmemory.Address),
                                     rtti=True)
    SHADOWSTACKREFPTR.TO.become(SHADOWSTACKREF)

    def customtrace(gc, obj, callback, arg):
        obj = llmemory.cast_adr_to_ptr(obj, SHADOWSTACKREFPTR)
        addr = obj.top
        start = obj.base
        while addr != start:
            addr -= sizeofaddr
            gc._trace_callback(callback, arg, addr)

    gc = gctransformer.gcdata.gc
    assert not hasattr(gc, 'custom_trace_dispatcher')
    # ^^^ create_custom_trace_funcs() must not run before this
    gctransformer.translator.rtyper.custom_trace_funcs.append(
        (SHADOWSTACKREF, customtrace))

    def shadowstack_destructor(shadowstackref):
        base = shadowstackref.base
        shadowstackref.base    = llmemory.NULL
        shadowstackref.top     = llmemory.NULL
        llmemory.raw_free(base)

    destrptr = gctransformer.annotate_helper(shadowstack_destructor,
                                             [SHADOWSTACKREFPTR], lltype.Void)

    lltype.attachRuntimeTypeInfo(SHADOWSTACKREF, destrptr=destrptr)

    gctransformer._SHADOWSTACKREF = SHADOWSTACKREF
    return SHADOWSTACKREF
