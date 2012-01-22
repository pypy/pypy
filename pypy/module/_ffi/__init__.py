from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._ffi import interp_ffi

class Module(MixedModule):

    interpleveldefs = {
        'CDLL':    'interp_ffi.W_CDLL',
        'types':   'interp_ffi.W_types',
        'FuncPtr': 'interp_ffi.W_FuncPtr',
        'get_libc':'interp_ffi.get_libc',
    }

    appleveldefs = {}
