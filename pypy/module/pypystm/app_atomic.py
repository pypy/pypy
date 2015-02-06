import pypystm

class Atomic(object):
    __enter__ = pypystm._atomic_enter
    __exit__  = pypystm._atomic_exit

class ExclusiveAtomic(object):
    __enter__ = pypystm._exclusive_atomic_enter
    __exit__ = pypystm._atomic_exit

atomic = Atomic()
exclusive_atomic = ExclusiveAtomic()
