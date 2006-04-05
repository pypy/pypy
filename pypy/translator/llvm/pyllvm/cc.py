'''
Added this because ctypes on my computer was missing cdecl.
'''
from ctypes import *

class cdecl(object):
    def __init__(self, restype, libname, argtypes):
        d = __file__[:__file__.find("pyllvm")] + "llvmcapi/"
        #XXX does this load once or every time?
        try:
            self.library  = cdll.LoadLibrary(d + libname + ".so")
        except:
            raise Exception("llvmcapi not found: run 'python setup.py build_ext -i' in " + d)
        self.restype  = restype
        self.argtypes = argtypes

    def __call__(self, func):
        func._api_          = getattr(self.library, func.__name__)
        func._api_.restype  = self.restype
        func._api_.argtypes = self.argtypes
        return func
