
""" App-level ctypes module for pypy
"""

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = '_ctypes'

    interpleveldefs = {
        '_CDLL'        : 'interp_ctypes.W_CDLL',
        'RTLD_LOCAL'   : 'space.wrap(interp_ctypes.RTLD_LOCAL)',
        'RTLD_GLOBAL'  : 'space.wrap(interp_ctypes.RTLD_GLOBAL)',
        'dlopen'       : 'interp_ctypes.dlopen',
        '_SimpleCData' : 'interp_ctypes.W_SimpleCData',
        'CFuncPtr'     : 'interp_ctypes.W_CFuncPtr',
    }

    appleveldefs = {}
