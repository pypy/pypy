'''
    Another go at using the LLVM JIT as a codegenerator for PyPy.
    
    For now we use the LLVM C++ API as little as possible!
    In future we might talk directly to the LLVM C++ API.

    This file contains the ctypes specification to use the llvmjit library!
'''
import autopath
from pypy.rpython.rctypes import implementation
from pypy.rpython.rctypes.tool.util import load_library

from ctypes import _CFuncPtr, _FUNCFLAG_CDECL
from ctypes import *
import os

newdir = os.path.dirname(__file__)
path = os.path.join(newdir, 'libllvmjit.so')
curdir = os.getcwd()
if newdir:
    os.chdir(newdir)

#With py.test --session=R the master server rsyncs the .so library too!?!
#So we always need to recompile the library if its platform (output of file libllvmjit.so)
#differs from the current (remote) platform.
#note: we can't do this in global scope because that will only be executed on the master server.
#os.system('rm -rf libllvmjit.so build')

#We might want to generate an up-to-date version of the library always so running (tests)
#on a clean checkout will produce correct results.
os.system('python setup.py build_ext -i')

os.chdir(curdir)

if not os.path.exists(path):
    import py
    py.test.skip("libllvmjit.so compilation failed (no llvm headers or llvm version not up to date?)")

#load the actual library
llvmjit = load_library(os.path.abspath(path))
class _FuncPtr(_CFuncPtr):
    _flags_ = _FUNCFLAG_CDECL
    # aaarghdistutilsunixaaargh (may need something different for standalone builds...)
    libraries = (os.path.join(os.path.dirname(path), 'llvmjit'),)
llvmjit._FuncPtr = _FuncPtr

MINIMAL_VERSION = 2.0

def llvm_version():
    v = os.popen('llvm-as -version 2>&1').read()
    v = ''.join([c for c in v if c.isdigit()])
    v = int(v) / 10.0
    return v

#ensure stable state (XXX this doesn't seem to get called when translated! We do it in parse!)
llvmjit.restart()

#exposed functions...
restart = llvmjit.restart

transform = llvmjit.transform
transform.restype  = c_int
transform.argtypes = [c_int]

parse = llvmjit.parse
parse.restype  = c_int
parse.argtypes = [c_char_p]

getNamedFunction = llvmjit.getNamedFunction
getNamedFunction.restype  = c_void_p
getNamedFunction.argtypes = [c_char_p]

getNamedGlobal = llvmjit.getNamedGlobal
getNamedGlobal.restype  = c_void_p
getNamedGlobal.argtypes = [c_char_p]

getPointerToFunction = llvmjit.getPointerToFunction
getPointerToFunction.restype = c_void_p 
getPointerToFunction.argtypes = [c_void_p]

getPointerToFunctionAsInt = llvmjit.getPointerToFunction
getPointerToFunctionAsInt.restype = c_int
getPointerToFunctionAsInt.argtypes = [c_void_p]

freeMachineCodeForFunction = llvmjit.freeMachineCodeForFunction
freeMachineCodeForFunction.restype  = c_int
freeMachineCodeForFunction.argtypes = [c_void_p]

recompile = llvmjit.recompile
recompile.restype  = c_int
recompile.argtypes = [c_void_p]

execute = llvmjit.execute
execute.restype  = c_int
execute.argtypes = [c_void_p, c_int]

get_global_data = llvmjit.get_global_data
get_global_data.restype = c_int
get_global_data.argtypes = []

set_global_data = llvmjit.set_global_data
set_global_data.argtypes = [c_int]

get_pointer_to_global_data = llvmjit.get_pointer_to_global_data
get_pointer_to_global_data.restype = POINTER(c_int)
get_pointer_to_global_data.argtypes = []

get_pointer_to_global_function = llvmjit.get_pointer_to_global_function
get_pointer_to_global_function.restype = c_void_p
get_pointer_to_global_function.argtypes = []

addGlobalMapping = llvmjit.addGlobalMapping
addGlobalMapping.argtypes = [c_void_p, c_void_p]

