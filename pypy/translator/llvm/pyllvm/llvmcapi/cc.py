'''
Added this because ctypes on my computer was missing cdecl.
'''
from ctypes import *

class cdecl(object):
    def __init__(self, restype, libname, argtypes):
        self.library  = cdll.load(libname + ".so")
        self.restype  = restype
        self.argtypes = argtypes

    def __call__(self, func):
        func._api_          = getattr(self.library, func.__name__)
        func._api_.restype  = self.restype
        func._api_.argtypes = self.argtypes
        return func
