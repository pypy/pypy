"""
Global Interpreter Lock.
"""

# This module adds a global lock to an object space.
# If multiple threads try to execute simultaneously in this space,
# all but one will be blocked.  The other threads get a chance to run
# from time to time, using the executioncontext's XXX

import thread
from pypy.module.thread.threadlocals import OSThreadLocals


class GILThreadLocals(OSThreadLocals):
    """A version of OSThreadLocals that enforces a GIL."""

    def __init__(self):
        self.GIL = thread.allocate_lock()

    def enter_thread(self, space):
        "Notification that the current thread is just starting: grab the GIL."
        self.GIL.acquire(True)
        OSThreadLocals.enter_thread(self, space)

    def leave_thread(self, space):
        "Notification that the current thread is stopping: release the GIL."
        OSThreadLocals.leave_thread(self, space)
        self.GIL.release()

    def yield_thread(self):
        """Notification that the current thread is between two bytecodes:
        release the GIL for a little while."""
        self.GIL.release()
        # Other threads can run here
        self.GIL.acquire(True)
