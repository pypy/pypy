"""
Global Interpreter Lock.
"""

# This module adds a global lock to an object space.
# If multiple threads try to execute simultaneously in this space,
# all but one will be blocked.  The other threads get a chance to run
# from time to time, using the executioncontext's XXX

from pypy.module.thread import ll_thread as thread
from pypy.interpreter.miscutils import Action
from pypy.module.thread.threadlocals import OSThreadLocals

class GILThreadLocals(OSThreadLocals):
    """A version of OSThreadLocals that enforces a GIL."""
    GIL = None

    def setup_threads(self, space):
        """Enable threads in the object space, if they haven't already been."""
        if self.GIL is None:
            self.GIL = thread.allocate_lock()
            self.enter_thread(space)   # setup the main thread
            # add the GIL-releasing callback as an action on the space
            space.pending_actions.append(GILReleaseAction(self))
            return True
        else:
            return False      # already set up

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
        GIL = self.GIL
        GIL.release()
        # Other threads can run here
        GIL.acquire(True)
    yield_thread._annspecialcase_ = 'specialize:yield_thread'

    def getGIL(self):
        return self.GIL    # XXX temporary hack!


class GILReleaseAction(Action):
    """An action called when the current thread is between two bytecodes
    (so that it's a good time to yield some time to other threads).
    """
    repeat = True

    def __init__(self, threadlocals):
        self.threadlocals = threadlocals

    def perform(self):
        self.threadlocals.yield_thread()
