'''
    Another go at using the LLVM JIT as a codegenerator for PyPy.
    
    For now we use the LLVM C++ API as little as possible!
    In future we might talk directly to the LLVM C++ API.

    This file contains the ctypes specification to use the llvmjit library!
'''
from pypy.rpython.rctypes import implementation

import ctypes
import os

path = os.path.join(os.path.dirname(__file__), 'libllvmjit.so')
llvmjit = ctypes.cdll.LoadLibrary(os.path.abspath(path))
class _FuncPtr(ctypes._CFuncPtr):
    _flags_ = ctypes._FUNCFLAG_CDECL
    # aaarghdistutilsunixaaargh (may need something different for standalone builds...)
    libraries = (os.path.join(os.path.dirname(path), 'llvmjit'),)
llvmjit._FuncPtr = _FuncPtr

#impls
testme = llvmjit.testme
testme.restype = ctypes.c_int
testme.argtypes = [ctypes.c_int]
