from pypy.rlib import _rffi_stacklet as _c
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib import rstacklet
from pypy.rlib.debug import ll_assert
from pypy.rpython.annlowlevel import llhelper


PTR_SUSPSTACK = lltype.Ptr(lltype.GcForwardReference())
SUSPSTACK = lltype.GcStruct('SuspStack',
                            ('handle', _c.handle),
                            ('shadowstack_stop', llmemory.Address), # low (old)
                            ('shadowstack_start', llmemory.Address),# high(new)
                            ('shadowstack_saved', lltype.Signed),   # number
                            ('shadowstack_prev', PTR_SUSPSTACK),
                            # copy of the shadowstack, but in reversed order:
                            # the first items here are the last items in the
                            # real shadowstack.  Only items 0 to saved-1 are
                            # set up; the rest is still in the real shadowstack
                            ('shadowstack_copy', lltype.Array(llmemory.GCREF)))
PTR_SUSPSTACK.TO.become(SUSPSTACK)
NULL_SUSPSTACK = lltype.nullptr(SUSPSTACK)

sizeofaddr = llmemory.sizeof(llmemory.Address)

def repr_suspstack(suspstack):
    return '<SuspStack %d: stop=%d, start=%d, saved=%d>' % (
        rffi.cast(lltype.Signed, suspstack.handle),
        rffi.cast(lltype.Signed, suspstack.shadowstack_stop),
        rffi.cast(lltype.Signed, suspstack.shadowstack_start),
        suspstack.shadowstack_saved)


# every thread has a 'current stack stop', which is like
# g_current_stack_stop in stacklet.c but about the shadowstack
rstacklet.StackletThread._current_shadowstack_stop = llmemory.NULL

# every thread has a 'stack chain' too, similar to g_stack_chain_head.
rstacklet.StackletThread._shadowstack_chain_head = NULL_SUSPSTACK


def root_stack_top():
    return llop.gc_adr_of_root_stack_top(llmemory.Address).address[0]

def set_root_stack_top(newaddr):
    llop.gc_adr_of_root_stack_top(llmemory.Address).address[0] = newaddr


def _new_runfn(h, arg):
    gcrootfinder.thrd._current_shadowstack_stop = root_stack_top()
    suspstack = gcrootfinder.attach_handle_on_suspstack(h)
    suspstack = gcrootfinder.runfn(suspstack, arg)
    return gcrootfinder.consume_suspstack(suspstack)


class StackletGcRootFinder(object):
    suspstack = NULL_SUSPSTACK

    def new(self, thrd, callback, arg):
        if thrd._current_shadowstack_stop == llmemory.NULL:
            thrd._current_shadowstack_stop = root_stack_top()
        self.allocate_source_suspstack(thrd)
        self.runfn = callback
        h = _c.new(thrd._thrd, llhelper(_c.run_fn, _new_runfn), arg)
        return self.get_result_suspstack(h)

    def switch(self, thrd, suspstack):
        self.allocate_source_suspstack(thrd)
        h = self.consume_suspstack(suspstack)
        h2 = _c.switch(thrd._thrd, h)
        return self.get_result_suspstack(h2)

    def allocate_source_suspstack(self, thrd):
        # Attach to 'self.suspstack' a SUSPSTACK that represents the
        # old, but still current, stacklet.  All that is left to
        # fill is 'self.suspstack.handle', done later by a call
        # to attach_handle_on_suspstack().
        rst = root_stack_top()
        if thrd._current_shadowstack_stop > rst:
            thrd._current_shadowstack_stop = rst
        count = (rst - thrd._current_shadowstack_stop) // sizeofaddr
        newsuspstack = lltype.malloc(SUSPSTACK, count)
        newsuspstack.shadowstack_stop = thrd._current_shadowstack_stop
        newsuspstack.shadowstack_start = rst
        newsuspstack.shadowstack_saved = 0
        newsuspstack.shadowstack_prev = thrd._shadowstack_chain_head
        thrd._shadowstack_chain_head = newsuspstack
        self.suspstack = newsuspstack
        self.thrd = thrd

    def attach_handle_on_suspstack(self, handle):
        s = self.suspstack
        self.suspstack = NULL_SUSPSTACK
        s.handle = handle
        print 'ATTACH HANDLE', repr_suspstack(s)
        return s

    def get_result_suspstack(self, h):
        #
        # Return from a new() or a switch(): 'h' is a handle, possibly
        # an empty one, that says from where we switched to.
        if not h:
            # oups, we didn't actually switch anywhere, but just got
            # an out-of-memory condition.  Restore the current suspstack.
            self.consume_suspstack(self.suspstack)
            self.suspstack = NULL_SUSPSTACK
            self.thrd = None
            raise MemoryError
        #
        if _c.is_empty_handle(h):
            self.thrd = None
            return NULL_SUSPSTACK
        else:
            # This is a return that gave us a real handle.  Store it.
            return self.attach_handle_on_suspstack(h)

    def consume_suspstack(self, suspstack):
        print 'CONSUME', repr_suspstack(suspstack)
        #
        # We want to switch to or return to 'suspstack'.  First get
        # how far we have to clean up the shadowstack.
        target = suspstack.shadowstack_stop
        #
        # Clean the shadowstack up to that position.
        self.clear_shadowstack(target, suspstack)
        #
        # Now restore data from suspstack.shadowstack_copy.
        self.restore_suspstack(suspstack)
        #
        # Set the new root stack bounds.
        self.thrd._current_shadowstack_stop = target
        set_root_stack_top(suspstack.shadowstack_start)
        #
        # Now the real shadowstack is ready for 'suspstack'.
        return suspstack.handle

    def clear_shadowstack(self, target_stop, targetsuspstack):
        # NB. see also g_clear_stack() in stacklet.c.
        #
        current = self.thrd._shadowstack_chain_head
        #
        # save and unlink suspstacks that are completely within
        # the area to clear.
        while bool(current) and current.shadowstack_stop >= target_stop:
            prev = current.shadowstack_prev
            current.shadowstack_prev = NULL_SUSPSTACK
            if current != targetsuspstack:
                # don't bother saving away targetsuspstack, because
                # it would be immediately restored
                self._save(current, current.shadowstack_stop)
            current = prev
        #
        # save a partial stack
        if bool(current) and current.shadowstack_start > target_stop:
            self._save(current, target_stop)
        #
        self.thrd._shadowstack_chain_head = current

    def _save(self, suspstack, stop):
        # See g_save() in stacklet.c.
        num1 = suspstack.shadowstack_saved
        num2 = (suspstack.shadowstack_start - stop) // sizeofaddr
        ll_assert(stop >= suspstack.shadowstack_stop, "stacklet+shadowstack#1")
        source = suspstack.shadowstack_start - num1 * sizeofaddr
        while num1 < num2:
            source -= sizeofaddr
            addr = source.address[0]
            gcref = llmemory.cast_adr_to_ptr(addr, llmemory.GCREF)
            suspstack.shadowstack_copy[num1] = gcref
            num1 += 1
        suspstack.shadowstack_saved = num1

    def restore_suspstack(self, suspstack):
        target = suspstack.shadowstack_start
        saved = suspstack.shadowstack_saved
        suspstack.shadowstack_saved = 0
        i = 0
        while i < saved:
            addr = llmemory.cast_ptr_to_adr(suspstack.shadowstack_copy[i])
            target -= sizeofaddr
            target.address[0] = addr
            i += 1

    def destroy(self, thrd, suspstack):
        h = suspstack.handle
        suspstack.handle = _c.null_handle
        _c.destroy(thrd._thrd, h)

    def is_empty_handle(self, suspstack):
        return not suspstack

    def get_null_handle(self):
        return NULL_SUSPSTACK


gcrootfinder = StackletGcRootFinder()
