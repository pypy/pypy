"""
Software Transactional Memory emulation of the GIL.
"""

from pypy.module.thread.threadlocals import OSThreadLocals
from pypy.module.thread.error import wrap_thread_error
from pypy.module.thread import ll_thread
from pypy.rlib import rstm
from pypy.rlib.objectmodel import invoke_around_extcall


class STMThreadLocals(OSThreadLocals):
    can_cache = False

    def initialize(self, space):
        pass

    def setup_threads(self, space):
        invoke_around_extcall(rstm.before_external_call,
                              rstm.after_external_call,
                              rstm.enter_callback_call,
                              rstm.leave_callback_call)

    def reinit_threads(self, space):
        self.setup_threads(space)


class STMLock(ll_thread.Lock):
    def __init__(self, space, ll_lock):
        ll_thread.Lock.__init__(self, ll_lock)
        self.space = space

    def acquire(self, flag):
        if rstm.is_atomic():
            acquired = ll_thread.Lock.acquire(self, False)
            if flag and not acquired:
                raise wrap_thread_error(self.space,
                    "deadlock: an atomic transaction tries to acquire "
                    "a lock that is already acquired.  See http://XXX.")
        else:
            acquired = ll_thread.Lock.acquire(self, flag)
        return acquired

def allocate_stm_lock(space):
    return STMLock(space, ll_thread.allocate_ll_lock())
