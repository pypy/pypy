from __pypy__ import thread

class Atomic(object):
    __enter__ = thread._atomic_enter
    __exit__  = thread._atomic_exit

class ExclusiveAtomic(object):
    __enter__ = thread._exclusive_atomic_enter
    __exit__ = thread._atomic_exit

atomic = Atomic()
exclusive_atomic = ExclusiveAtomic()
