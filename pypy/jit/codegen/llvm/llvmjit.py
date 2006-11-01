'''
    Another go at using the LLVM JIT as a codegenerator for PyPy.
    
    For now we use the LLVM C++ API as little as possible!
    In future we might talk directly to the LLVM C++ API.

    This file contains the ctypes specification to use the llvmjit library!
'''

import ctypes
import os

path = os.path.join(os.path.dirname(__file__), 'llvmjit_.so')
llvmjit = ctypes.cdll.LoadLibrary(os.path.abspath(path))

def testme(n):
    return llvmjit.testme(n)
