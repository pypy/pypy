from pypy.interpreter.mixedmodule import MixedModule
import sys

class Module(MixedModule):

    interpleveldefs = {
        'Connection'      : 'interp_connection.W_SocketConnection',
        'PipeConnection'  : 'interp_connection.W_PipeConnection',
    }

    appleveldefs = {
    }

    if sys.platform == 'win32':
        interpleveldefs['win32'] = 'interp_win32.win32_namespace(space)'
