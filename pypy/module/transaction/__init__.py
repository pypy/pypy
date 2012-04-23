
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Transaction module. XXX document me
    """

    interpleveldefs = {
        'set_num_threads': 'interp_transaction.set_num_threads',
        'add': 'interp_transaction.add',
        'run': 'interp_transaction.run',
        #'add_epoll': 'interp_epoll.add_epoll',        # xxx linux only
        #'remove_epoll': 'interp_epoll.remove_epoll',  # xxx linux only
        'local': 'interp_local.W_Local',
    }

    appleveldefs = {
        'TransactionError': 'app_transaction.TransactionError',
    }

    def __init__(self, space, *args):
        "NOT_RPYTHON: patches space.threadlocals to use real threadlocals"
        from pypy.module.transaction import interp_transaction
        MixedModule.__init__(self, space, *args)
        space.threadlocals = interp_transaction.getstate(space)

    def startup(self, space):
        from pypy.module.transaction import interp_transaction
        state = interp_transaction.getstate(space)
        state.startup(space.wrap(self))
