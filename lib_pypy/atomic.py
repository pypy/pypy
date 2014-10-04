"""
API for accessing the multithreading extensions of PyPy
"""
import thread

try:
    from __pypy__ import thread as _thread
    from __pypy__.thread import (atomic, getsegmentlimit,
                                 hint_commit_soon, is_atomic)
except ImportError:
    # Not a STM-enabled PyPy.  We can still provide a version of 'atomic'
    # that is good enough for our purposes.  With this limited version,
    # an atomic block in thread X will not prevent running thread Y, if
    # thread Y is not within an atomic block at all.
    atomic = thread.allocate_lock()

    def getsegmentlimit():
        return 1

    def hint_commit_soon():
        pass

    def is_atomic():
        return atomic.locked()
