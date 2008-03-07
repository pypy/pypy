
""" Low-level interface to libffi
"""

from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._rawffi.interp_rawffi import W_CDLL
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module._rawffi.tracker import Tracker

class Module(MixedModule):
    applevelname = '_rawffi'

    interpleveldefs = {
        'CDLL'               : 'interp_rawffi.W_CDLL',
        'FuncPtr'            : 'interp_rawffi.W_FuncPtr',
        'Structure'          : 'structure.W_Structure',
        'StructureInstance'  : 'structure.W_StructureInstance',
        'StructureInstanceAutoFree' : 'structure.W_StructureInstanceAutoFree',
        'Array'              : 'array.W_Array',
        'ArrayInstance'      : 'array.W_ArrayInstance',
        'ArrayInstanceAutoFree' : 'array.W_ArrayInstanceAutoFree',
        'sizeof'             : 'interp_rawffi.sizeof',
        'alignment'          : 'interp_rawffi.alignment',
        'charp2string'       : 'interp_rawffi.charp2string',
        'charp2rawstring'    : 'interp_rawffi.charp2rawstring',
        'CallbackPtr'        : 'callback.W_CallbackPtr',
        '_num_of_allocated_objects' : 'tracker.num_of_allocated_objects',
    }

    appleveldefs = {
        'SegfaultException'  : 'error.SegfaultException',
    }
