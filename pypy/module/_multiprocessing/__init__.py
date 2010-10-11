from pypy.interpreter.mixedmodule import MixedModule
import sys

class Module(MixedModule):

    interpleveldefs = {
        'Connection'      : 'interp_connection.W_FileConnection',
        'PipeConnection'  : 'interp_connection.W_PipeConnection',
        'SemLock'         : 'interp_semaphore.W_SemLock',
    }

    appleveldefs = {
    }

    if sys.platform == 'win32':
        interpleveldefs['win32'] = 'interp_win32.win32_namespace(space)'

    def startup(self, space):
        from pypy.module._multiprocessing.interp_semaphore import CounterState
        space.fromcache(CounterState).startup(space)
