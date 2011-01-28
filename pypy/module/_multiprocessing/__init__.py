from pypy.interpreter.mixedmodule import MixedModule
import sys

class Module(MixedModule):

    interpleveldefs = {
        'Connection'      : 'interp_connection.W_FileConnection',
        'PipeConnection'  : 'interp_connection.W_PipeConnection',
        'SemLock'         : 'interp_semaphore.W_SemLock',

        'address_of_buffer' : 'interp_memory.address_of_buffer',
    }

    appleveldefs = {
    }

    if sys.platform == 'win32':
        interpleveldefs['win32'] = 'interp_win32.win32_namespace(space)'
