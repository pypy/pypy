
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        'atomic':                  'app_atomic.atomic',
        'exclusive_atomic':        'app_atomic.exclusive_atomic',
    }

    interpleveldefs = {
        '_atomic_enter':           'interp_atomic.atomic_enter',
        '_exclusive_atomic_enter': 'interp_atomic.exclusive_atomic_enter',
        '_atomic_exit':            'interp_atomic.atomic_exit',
        'getsegmentlimit':         'interp_atomic.getsegmentlimit',
        'hint_commit_soon':        'interp_atomic.hint_commit_soon',
        'is_atomic':               'interp_atomic.is_atomic',
        'error': 'space.fromcache(pypy.module.thread.error.Cache).w_error',

        'local': 'local.STMLocal',
        'count': 'count.count',
        'hashtable': 'hashtable.W_Hashtable',
        'time': 'time.time',
        'clock': 'time.clock',
        'stmset': 'stmset.W_STMSet',
        'stmdict': 'stmdict.W_STMDict',
    }
