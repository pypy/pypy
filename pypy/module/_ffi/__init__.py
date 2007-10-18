
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
        'StructureInstance'  : 'structure.W_StructureInstance',
        'ArrayInstance'      : 'array.W_ArrayInstance',
        '_get_type'          : 'interp_ffi._w_get_type',
    }

    appleveldefs = {
        'Structure'         : 'app_ffi.Structure',
        'Array'             : 'app_ffi.Array',
        #'StructureInstance' : 'app_ffi.StructureInstance',
    }
