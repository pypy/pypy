
""" Low-level interface to libffi
"""

from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._rawffi.interp_rawffi import W_CDLL
from pypy.rpython.lltypesystem import lltype, rffi

class Module(MixedModule):
    applevelname = '_rawffi'

    interpleveldefs = {
        'CDLL'               : 'interp_rawffi.W_CDLL',
        'FuncPtr'            : 'interp_rawffi.W_FuncPtr',
        'Structure'          : 'structure.W_Structure',
        'StructureInstance'  : 'structure.W_StructureInstance',
        'Array'              : 'array.W_Array',
        'ArrayInstance'      : 'array.W_ArrayInstance',
        'sizeof'             : 'interp_rawffi.sizeof',
        'alignment'          : 'interp_rawffi.alignment',
        'charp2string'       : 'interp_rawffi.charp2string',
        'CallbackPtr'        : 'callback.W_CallbackPtr',
    }

    appleveldefs = {
        'SegfaultException'  : 'error.SegfaultException',
    }
