
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
        'get_libc'           : 'interp_rawffi.get_libc',
    }

    appleveldefs = {
        'SegfaultException'  : 'error.SegfaultException',
    }

    def buildloaders(cls):
        from pypy.module._rawffi import interp_rawffi

        if hasattr(interp_rawffi, 'FormatError'):
            Module.interpleveldefs['FormatError'] = 'interp_rawffi.FormatError'
        if hasattr(interp_rawffi, 'check_HRESULT'):
            Module.interpleveldefs['check_HRESULT'] = 'interp_rawffi.check_HRESULT'

        from pypy.rlib import libffi
        for name in ['FUNCFLAG_STDCALL', 'FUNCFLAG_CDECL', 'FUNCFLAG_PYTHONAPI',
                     ]:
            if hasattr(libffi, name):
                Module.interpleveldefs[name] = "space.wrap(%r)" % getattr(libffi, name)
                
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
