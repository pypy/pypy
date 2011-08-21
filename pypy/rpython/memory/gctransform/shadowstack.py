from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.memory.gctransform.framework import sizeofaddr
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.annotation import model as annmodel


class ShadowStackRootWalker(BaseRootWalker):
    need_root_stack = True

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

        translator = gctransformer.translator
        if hasattr(translator, '_jit2gc'):
            iterator_setup = translator._jit2gc['root_iterator_setup']
            iterator_next  = translator._jit2gc['root_iterator_next']
            def jit_walk_stack_root(callback, addr, end):
                gc = self.gc
                iterator_setup()
                while True:
                    end = iterator_next(end, addr)
                    if end == llmemory.NULL:
                        return
                    callback(gc, end)
            self.rootstackhook = jit_walk_stack_root
        else:
            def default_walk_stack_root(callback, addr, end):
                gc = self.gc
                while addr != end:
                    if gc.points_to_valid_gc_object(addr):
                        callback(gc, addr)
                    addr += sizeofaddr
            self.rootstackhook = default_walk_stack_root

        self.shadow_stack_pool = ShadowStackPool(gcdata)

    def push_stack(self, addr):
        top = self.incr_stack(1)
        top.address[0] = addr

    def pop_stack(self):
        top = self.decr_stack(1)
        return top.address[0]

    def setup_root_walker(self):
        self.shadow_stack_pool.initial_setup()
        BaseRootWalker.setup_root_walker(self)

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        self.rootstackhook(collect_stack_root,
                           gcdata.root_stack_base, gcdata.root_stack_top)

    def need_stacklet_support(self):
        XXXXXX   # FIXME
        # stacklet support: BIG HACK for rlib.rstacklet
        from pypy.rlib import _stacklet_shadowstack
        _stacklet_shadowstack._shadowstackrootwalker = self # as a global! argh

    def need_thread_support(self, gctransformer, getfn):
        from pypy.module.thread import ll_thread    # xxx fish
        from pypy.rpython.memory.support import AddressDict
        from pypy.rpython.memory.support import copy_without_null_values
        gcdata = self.gcdata
        # the interfacing between the threads and the GC is done via
        # two completely ad-hoc operations at the moment:
        # gc_thread_run and gc_thread_die.  See docstrings below.

        shadow_stack_pool = self.shadow_stack_pool

        # this is a dict {tid: SHADOWSTACKREF}, where the tid for the
        # current thread may be missing so far
        gcdata.thread_stacks = None

        # Return the thread identifier, as an integer.
        get_tid = ll_thread.get_ident

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
            """
            tid = get_tid()
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
                new_ref = NULL_SHADOWSTACKREF
            try:
                old_ref = thread_stacks[gcdata.active_tid]
            except KeyError:
                # first time we ask for a SHADOWSTACKREF for this active_tid
                old_ref = shadow_stack_pool.allocate()
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
                gcdata.thread_stacks.clear()
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
                                            annmodel.SomeAddress()],
                                           annmodel.s_None,
                                           minimal_transform=False)
        self.has_thread_support = True

# ____________________________________________________________

class ShadowStackPool(object):
    """Manages a pool of shadowstacks.  The MAX most recently used
    shadowstacks are fully allocated and can be directly jumped into.
    The rest are stored in a more virtual-memory-friendly way, i.e.
    with just the right amount malloced.  Before they can run, they
    must be copied into a full shadowstack.
    """
    _alloc_flavor_ = "raw"
    root_stack_depth = 163840
    root_stack_size = sizeofaddr * root_stack_depth

    #MAX = 20  not implemented yet

    def __init__(self, gcdata):
        self.unused_full_stack = llmemory.NULL
        self.gcdata = gcdata

    def initial_setup(self):
        self._prepare_unused_stack()
        self.start_fresh_new_state()

    def allocate(self):
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
        #shadowstackref.fullstack = True
        llop.gc_assume_young_pointers(lltype.Void, shadowstackref)
        self.gcdata.root_stack_top = llmemory.NULL  # to detect missing restore

    def forget_current_state(self):
        if self.unused_full_stack:
            llmemory.raw_free(self.unused_full_stack)
        self.unused_full_stack = self.gcdata.root_stack_base
        self.gcdata.root_stack_top = llmemory.NULL  # to detect missing restore

    def restore_state_from(self, shadowstackref):
        self.gcdata.root_stack_base = shadowstackref.base
        self.gcdata.root_stack_top  = shadowstackref.top
        shadowstackref.base = llmemory.NULL
        shadowstackref.top  = llmemory.NULL

    def start_fresh_new_state(self):
        self.gcdata.root_stack_base = self.unused_full_stack
        self.gcdata.root_stack_top  = self.unused_full_stack
        self.unused_full_stack = llmemory.NULL

    def _prepare_unused_stack(self):
        if self.unused_full_stack == llmemory.NULL:
            self.unused_full_stack = llmemory.raw_malloc(self.root_stack_size)
            if self.unused_full_stack == llmemory.NULL:
                raise MemoryError


SHADOWSTACKREFPTR = lltype.Ptr(lltype.GcForwardReference())
SHADOWSTACKREF = lltype.GcStruct('ShadowStackRef',
                                 ('base', llmemory.Address),
                                 ('top', llmemory.Address),
                                 #('fullstack', lltype.Bool),
                                 rtti=True)
SHADOWSTACKREFPTR.TO.become(SHADOWSTACKREF)
NULL_SHADOWSTACKREF = lltype.nullptr(SHADOWSTACKREF)

def customtrace(obj, prev):
    # a simple but not JIT-ready version
    if not prev:
        prev = llmemory.cast_adr_to_ptr(obj, SHADOWSTACKREFPTR).top
    if prev != llmemory.cast_adr_to_ptr(obj, SHADOWSTACKREFPTR).base:
        return prev - sizeofaddr
    else:
        return llmemory.NULL

CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                  llmemory.Address)
customtraceptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), customtrace)
lltype.attachRuntimeTypeInfo(SHADOWSTACKREF, customtraceptr=customtraceptr)
