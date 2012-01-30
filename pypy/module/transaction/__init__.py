
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Transaction module. XXX document me
    """

    interpleveldefs = {
        'set_num_threads': 'interp_transaction.set_num_threads',
        'add': 'interp_transaction.add',
        'run': 'interp_transaction.run',
        'add_epoll': 'interp_epoll.add_epoll',   # xxx linux only
    }

    appleveldefs = {
        'TransactionError': 'app_transaction.TransactionError',
    }

    def __init__(self, space, *args):
        "NOT_RPYTHON: patches space.threadlocals to use real threadlocals"
        from pypy.module.transaction import interp_transaction
        MixedModule.__init__(self, space, *args)
        interp_transaction.state.initialize(space)
        space.threadlocals = interp_transaction.state

    def startup(self, space):
        from pypy.module.transaction import interp_transaction
        interp_transaction.state.startup(space, space.wrap(self))
