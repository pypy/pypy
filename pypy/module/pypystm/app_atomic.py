import pypystm

class Atomic(object):
    __enter__ = pypystm._atomic_enter
    __exit__  = pypystm._atomic_exit

class ExclusiveAtomic(object):
    __enter__ = pypystm._exclusive_atomic_enter
    __exit__ = pypystm._atomic_exit

class SingleTransaction(object):
    __enter__ = pypystm._single_transaction_enter
    __exit__ = pypystm._single_transaction_exit

atomic = Atomic()
exclusive_atomic = ExclusiveAtomic()
single_transaction = SingleTransaction()
