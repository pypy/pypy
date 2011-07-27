from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.memory.gctransform.framework import sizeofaddr
from pypy.rlib.debug import ll_assert
from pypy.rpython.lltypesystem import llmemory


class ShadowStackRootWalker(BaseRootWalker):
    need_root_stack = True
    collect_stacks_from_other_threads = None

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)
        self.rootstacksize = sizeofaddr * gctransformer.root_stack_depth
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

        self.rootstackhook = gctransformer.root_stack_jit_hook
        if self.rootstackhook is None:
            def collect_stack_root(callback, gc, addr):
                if gc.points_to_valid_gc_object(addr):
                    callback(gc, addr)
                return sizeofaddr
            self.rootstackhook = collect_stack_root

    def push_stack(self, addr):
        top = self.incr_stack(1)
        top.address[0] = addr

    def pop_stack(self):
        top = self.decr_stack(1)
        return top.address[0]

    def allocate_stack(self):
        return llmemory.raw_malloc(self.rootstacksize)

    def setup_root_walker(self):
        stackbase = self.allocate_stack()
        ll_assert(bool(stackbase), "could not allocate root stack")
        self.gcdata.root_stack_top  = stackbase
        self.gcdata.root_stack_base = stackbase
        BaseRootWalker.setup_root_walker(self)

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        gc = self.gc
        rootstackhook = self.rootstackhook
        addr = gcdata.root_stack_base
        end = gcdata.root_stack_top
        while addr != end:
            addr += rootstackhook(collect_stack_root, gc, addr)
        if self.collect_stacks_from_other_threads is not None:
            self.collect_stacks_from_other_threads(collect_stack_root)

    def need_thread_support(self, gctransformer, getfn):
        from pypy.module.thread import ll_thread    # xxx fish
        from pypy.rpython.memory.support import AddressDict
        from pypy.rpython.memory.support import copy_without_null_values
        gcdata = self.gcdata
        # the interfacing between the threads and the GC is done via
        # three completely ad-hoc operations at the moment:
        # gc_thread_prepare, gc_thread_run, gc_thread_die.
        # See docstrings below.

        def get_aid():
            """Return the thread identifier, cast to an (opaque) address."""
            return llmemory.cast_int_to_adr(ll_thread.get_ident())

        def thread_setup():
            """Called once when the program starts."""
            aid = get_aid()
            gcdata.main_thread = aid
            gcdata.active_thread = aid
            gcdata.thread_stacks = AddressDict()     # {aid: root_stack_top}
            gcdata._fresh_rootstack = llmemory.NULL
            gcdata.dead_threads_count = 0

        def thread_prepare():
            """Called just before thread.start_new_thread().  This
            allocates a new shadow stack to be used by the future
            thread.  If memory runs out, this raises a MemoryError
            (which can be handled by the caller instead of just getting
            ignored if it was raised in the newly starting thread).
            """
            if not gcdata._fresh_rootstack:
                gcdata._fresh_rootstack = self.allocate_stack()
                if not gcdata._fresh_rootstack:
                    raise MemoryError

        def thread_run():
            """Called whenever the current thread (re-)acquired the GIL.
            This should ensure that the shadow stack installed in
            gcdata.root_stack_top/root_stack_base is the one corresponding
            to the current thread.
            """
            aid = get_aid()
            if gcdata.active_thread != aid:
                switch_shadow_stacks(aid)

        def thread_die():
            """Called just before the final GIL release done by a dying
            thread.  After a thread_die(), no more gc operation should
            occur in this thread.
            """
            aid = get_aid()
            if aid == gcdata.main_thread:
                return   # ignore calls to thread_die() in the main thread
                         # (which can occur after a fork()).
            gcdata.thread_stacks.setitem(aid, llmemory.NULL)
            old = gcdata.root_stack_base
            if gcdata._fresh_rootstack == llmemory.NULL:
                gcdata._fresh_rootstack = old
            else:
                llmemory.raw_free(old)
            install_new_stack(gcdata.main_thread)
            # from time to time, rehash the dictionary to remove
            # old NULL entries
            gcdata.dead_threads_count += 1
            if (gcdata.dead_threads_count & 511) == 0:
                copy = copy_without_null_values(gcdata.thread_stacks)
                gcdata.thread_stacks.delete()
                gcdata.thread_stacks = copy

        def switch_shadow_stacks(new_aid):
            save_away_current_stack()
            install_new_stack(new_aid)
        switch_shadow_stacks._dont_inline_ = True

        def save_away_current_stack():
            old_aid = gcdata.active_thread
            # save root_stack_base on the top of the stack
            self.push_stack(gcdata.root_stack_base)
            # store root_stack_top into the dictionary
            gcdata.thread_stacks.setitem(old_aid, gcdata.root_stack_top)

        def install_new_stack(new_aid):
            # look for the new stack top
            top = gcdata.thread_stacks.get(new_aid, llmemory.NULL)
            if top == llmemory.NULL:
                # first time we see this thread.  It is an error if no
                # fresh new stack is waiting.
                base = gcdata._fresh_rootstack
                gcdata._fresh_rootstack = llmemory.NULL
                ll_assert(base != llmemory.NULL, "missing gc_thread_prepare")
                gcdata.root_stack_top = base
                gcdata.root_stack_base = base
            else:
                # restore the root_stack_base from the top of the stack
                gcdata.root_stack_top = top
                gcdata.root_stack_base = self.pop_stack()
            # done
            gcdata.active_thread = new_aid

        def collect_stack(aid, stacktop, callback):
            if stacktop != llmemory.NULL and aid != gcdata.active_thread:
                # collect all valid stacks from the dict (the entry
                # corresponding to the current thread is not valid)
                gc = self.gc
                rootstackhook = self.rootstackhook
                end = stacktop - sizeofaddr
                addr = end.address[0]
                while addr != end:
                    addr += rootstackhook(callback, gc, addr)

        def collect_more_stacks(callback):
            ll_assert(get_aid() == gcdata.active_thread,
                      "collect_more_stacks(): invalid active_thread")
            gcdata.thread_stacks.foreach(collect_stack, callback)

        def _free_if_not_current(aid, stacktop, _):
            if stacktop != llmemory.NULL and aid != gcdata.active_thread:
                end = stacktop - sizeofaddr
                base = end.address[0]
                llmemory.raw_free(base)

        def thread_after_fork(result_of_fork, opaqueaddr):
            # we don't need a thread_before_fork in this case, so
            # opaqueaddr == NULL.  This is called after fork().
            if result_of_fork == 0:
                # We are in the child process.  Assumes that only the
                # current thread survived, so frees the shadow stacks
                # of all the other ones.
                gcdata.thread_stacks.foreach(_free_if_not_current, None)
                # Clears the dict (including the current thread, which
                # was an invalid entry anyway and will be recreated by
                # the next call to save_away_current_stack()).
                gcdata.thread_stacks.clear()
                # Finally, reset the stored thread IDs, in case it
                # changed because of fork().  Also change the main
                # thread to the current one (because there is not any
                # other left).
                aid = get_aid()
                gcdata.main_thread = aid
                gcdata.active_thread = aid

        self.thread_setup = thread_setup
        self.thread_prepare_ptr = getfn(thread_prepare, [], annmodel.s_None)
        self.thread_run_ptr = getfn(thread_run, [], annmodel.s_None,
                                    inline=True)
        # no thread_start_ptr here
        self.thread_die_ptr = getfn(thread_die, [], annmodel.s_None)
        # no thread_before_fork_ptr here
        self.thread_after_fork_ptr = getfn(thread_after_fork,
                                           [annmodel.SomeInteger(),
                                            annmodel.SomeAddress()],
                                           annmodel.s_None)
        self.collect_stacks_from_other_threads = collect_more_stacks
