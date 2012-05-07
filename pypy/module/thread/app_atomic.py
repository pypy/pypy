import thread

class Atomic(object):
    __enter__ = thread._atomic_enter
    __exit__  = thread._atomic_exit

atomic = Atomic()
