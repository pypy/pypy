import sys

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    interpleveldefs = {
        'Connection'      : 'interp_connection.W_FileConnection',
        'SemLock'         : 'interp_semaphore.W_SemLock',

        'address_of_buffer' : 'interp_memory.address_of_buffer',
    }

    appleveldefs = {
    }

    if sys.platform == 'win32':
        interpleveldefs['PipeConnection'] = \
            'interp_connection.W_PipeConnection'
        interpleveldefs['win32'] = 'interp_win32.win32_namespace(space)'
