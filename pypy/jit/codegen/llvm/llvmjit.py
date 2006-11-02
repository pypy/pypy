'''
    Another go at using the LLVM JIT as a codegenerator for PyPy.
    
    For now we use the LLVM C++ API as little as possible!
    In future we might talk directly to the LLVM C++ API.

    This file contains the ctypes specification to use the llvmjit library!
'''
from pypy.rpython.rctypes import implementation

from ctypes import _CFuncPtr, _FUNCFLAG_CDECL
from ctypes import *
import os

path = os.path.join(os.path.dirname(__file__), 'libllvmjit.so')
llvmjit = cdll.LoadLibrary(os.path.abspath(path))
class _FuncPtr(_CFuncPtr):
    _flags_ = _FUNCFLAG_CDECL
    # aaarghdistutilsunixaaargh (may need something different for standalone builds...)
    libraries = (os.path.join(os.path.dirname(path), 'llvmjit'),)
llvmjit._FuncPtr = _FuncPtr

#exposed functions...
restart = llvmjit.restart

compile = llvmjit.compile
compile.restype  = c_int
compile.argtypes = [c_char_p]

compile_src = llvmjit.compile_src
compile_src.restype  = c_int
compile_src.argtypes = [c_char_p]

execute = llvmjit.execute
execute.restype  = c_int
execute.argtypes = [c_char_p, c_int]
