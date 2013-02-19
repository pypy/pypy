"""
Software Transactional Memory emulation of the GIL.
"""

from pypy.module.thread.threadlocals import OSThreadLocals
from pypy.module.thread.error import wrap_thread_error
from pypy.interpreter.executioncontext import ExecutionContext
from rpython.rlib import rthread
from rpython.rlib import rstm
from rpython.rlib.objectmodel import invoke_around_extcall


ec_cache = rstm.ThreadLocalReference(ExecutionContext)


class STMThreadLocals(OSThreadLocals):

    def initialize(self, space):
        """NOT_RPYTHON: set up a mechanism to send to the C code the value
        set by space.actionflag.setcheckinterval()."""
        #
        # Set the default checkinterval to 200000, found by exploration to
        # be a good default value.  XXX do some more in-depth tests
        space.actionflag.setcheckinterval(200000)
        #
        def setcheckinterval_callback():
            self.configure_transaction_length(space)
        #
        assert space.actionflag.setcheckinterval_callback is None
        space.actionflag.setcheckinterval_callback = setcheckinterval_callback
        self.threads_running = False

    def clear_cache(self):
        ec_cache.set(None)

    def getvalue(self):
        value = ec_cache.get()
        if value is None:
            ident = rthread.get_ident()
            value = self._valuedict.get(ident, None)
            ec_cache.set(value)
        return value

    def setup_threads(self, space):
        self.threads_running = True
        self.configure_transaction_length(space)
        invoke_around_extcall(rstm.before_external_call,
                              rstm.after_external_call,
                              rstm.enter_callback_call,
                              rstm.leave_callback_call)

    def reinit_threads(self, space):
        self.setup_threads(space)

    def configure_transaction_length(self, space):
        if self.threads_running:
            interval = space.actionflag.getcheckinterval()
            rstm.set_transaction_length(interval)


class STMLock(rthread.Lock):
    def __init__(self, space, ll_lock):
        rthread.Lock.__init__(self, ll_lock)
        self.space = space

    def acquire(self, flag):
        if rstm.is_atomic():
            acquired = rthread.Lock.acquire(self, False)
            if flag and not acquired:
                raise wrap_thread_error(self.space,
                    "deadlock: an atomic transaction tries to acquire "
                    "a lock that is already acquired.  See pypy/doc/stm.rst.")
        else:
            acquired = rthread.Lock.acquire(self, flag)
        return acquired

def allocate_stm_lock(space):
    return STMLock(space, rthread.allocate_ll_lock())
