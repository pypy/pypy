'''
Added this because ctypes on my computer was missing cdecl.
'''
from llvmcapi import *

class Method(object):
    def __init__(self, instance, method):
        self.instance = instance
        self.method   = method

    def __call__(self, *args):
        a = [self.instance]
        for arg in args:
            if isinstance(arg, Wrapper): #pass on value to actual C (not Python) object
                a.append(arg.instance)
            else:
                a.append(arg)
        return apply(self.method, a)

class Wrapper(object):
    def __getattr__(self, name):
        global_funcname = self.__class__.__name__ + "_" + name
        return Method(self.instance, globals()[global_funcname])
