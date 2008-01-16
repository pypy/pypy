
""" Low-level interface to libffi
"""

from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._ffi.interp_ffi import W_CDLL
from pypy.rpython.lltypesystem import lltype, rffi

class Module(MixedModule):
    applevelname = '_ffi'

    interpleveldefs = {
        'CDLL'               : 'interp_ffi.W_CDLL',
        'FuncPtr'            : 'interp_ffi.W_FuncPtr',
        'Structure'          : 'structure.W_Structure',
        'StructureInstance'  : 'structure.W_StructureInstance',
        'Array'              : 'array.W_Array',
        'ArrayInstance'      : 'array.W_ArrayInstance',
        '_get_type'          : 'interp_ffi._w_get_type',
        'sizeof'             : 'interp_ffi.sizeof',
        'alignment'          : 'interp_ffi.alignment',
        #'CallbackPtr'        : 'callback.W_CallbackPtr',
    }

    appleveldefs = {
        'SegfaultException'  : 'error.SegfaultException',
    }
