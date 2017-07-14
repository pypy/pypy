import sys

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    interpleveldefs = {
        'SemLock'         : 'interp_semaphore.W_SemLock',
        'sem_unlink'      : 'interp_semaphore.semaphore_unlink',
        'address_of_buffer' : 'interp_memory.address_of_buffer',
    }

    appleveldefs = {
    }

    if sys.platform == 'win32':
        interpleveldefs['win32'] = 'interp_win32.win32_namespace(space)'
        del interpleveldefs['sem_unlink']
