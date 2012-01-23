
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Transaction module. XXX document me
    """

    interpleveldefs = {
        'set_num_threads': 'interp_transaction.set_num_threads',
        'add': 'interp_transaction.add',
        'run': 'interp_transaction.run',
    }

    appleveldefs = {
        'TransactionError': 'app_transaction.TransactionError',
    }

    def startup(self, space):
        from pypy.module.transaction import interp_transaction
        interp_transaction.state.startup(space)

    def translating_for_checkmodule(self, space):
        from pypy.module.transaction import interp_transaction
        interp_transaction.state._freeze_()
        interp_transaction.state.space = space
        interp_transaction.state._freeze_ = lambda: None   # hack!
