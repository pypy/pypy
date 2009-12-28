
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        'exit':                   'app_thread.exit',
        'exit_thread':            'app_thread.exit',   # obsolete synonym
        'error':                  'app_thread.error',
    }

    interpleveldefs = {
        'start_new_thread':       'os_thread.start_new_thread',
        'start_new':              'os_thread.start_new_thread', # obsolete syn.
        'get_ident':              'os_thread.get_ident',
        'stack_size':             'os_thread.stack_size',
        'allocate_lock':          'os_lock.allocate_lock',
        'allocate':               'os_lock.allocate_lock',  # obsolete synonym
        'LockType':               'os_lock.getlocktype(space)',
        '_local':                 'os_local.getlocaltype(space)',
    }

    def __init__(self, space, *args):
        "NOT_RPYTHON: patches space.threadlocals to use real threadlocals"
        from pypy.module.thread import gil
        MixedModule.__init__(self, space, *args)
        prev = space.threadlocals.getvalue()
        space.threadlocals = gil.GILThreadLocals()
        space.threadlocals.initialize(space)
        space.threadlocals.setvalue(prev)
