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

curdir = os.getcwd()
os.chdir(os.path.dirname(__file__))

#With py.test --session=R the master server rsyncs the .so library too!?!
#So we always need to recompile the library if its platform (output of file libllvmjit.so)
#differs from the current (remote) platform.
#note: we can't do this in global scope because that will only be executed on the master server.
os.system('rm -rf libllvmjit.so build')

#We might want to generate an up-to-date version of the library always so running (tests)
#on a clean checkout will produce correct results.
os.system('python setup.py build_ext -i')

os.chdir(curdir)

#load the actual library
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

find_function = llvmjit.find_function
find_function.restype  = c_void_p
find_function.argtypes = [c_char_p]

execute = llvmjit.execute
execute.restype  = c_int
execute.argtypes = [c_void_p, c_int]

#helpers...
class FindFunction(object):
    def __init__(self, function_name):
        self.function = find_function(function_name)

    def __call__(self, param):  #XXX this does not seem to translate, how to do it instead?
        return execute(self.function, param)

