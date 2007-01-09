from pypy.annotation import model as annmodel
from pypy.rlib.rctypes.implementation import CTypeController, getcontroller
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython.lltypesystem import lltype

import ctypes

CFuncPtrType = type(ctypes.CFUNCTYPE(None))


class FuncPtrCTypeController(CTypeController):
    ready = 0

    def __init__(self, ctype):
        CTypeController.__init__(self, ctype)
        sample_instance = self.ctype()
        self.argtypes = sample_instance.argtypes
        self.restype  = sample_instance.restype
        self.knowntype = rctypesobject.RPointer(None)

    def setup(self):
        if self.ready == 0:
            self.ready = 1
            self.argscontrollers = [getcontroller(a) for a in self.argtypes]
            self.rescontroller = getcontroller(self.restype)
            argscls = [c.knowntype for c in self.argscontrollers]
            rescls = self.rescontroller.knowntype
            self.rfunctype = rctypesobject.RFuncType(argscls, rescls)
            self.knowntype.setpointertype(self.rfunctype, force=True)
            self.make_helpers()
            self.ready = 2

    def make_helpers(self):
        # XXX need stuff to unwrap pointer boxes to lltype pointers
        pass

    def real_ctype_of(fnptr):
        # in ctypes, most function pointers have argtypes and restype set
        # on the function pointer object itself, not on its class
        return ctypes.CFUNCTYPE(fnptr.restype, *fnptr.argtypes)
    real_ctype_of = staticmethod(real_ctype_of)

    def ctypecheck(self, x):
        return (isinstance(type(x), CFuncPtrType) and
                tuple(x.argtypes) == tuple(self.argtypes) and
                x.restype == self.restype)

    def new(self):
        obj = self.knowntype.allocate()
        return obj

    def initialize_prebuilt(self, ptrobj, cfuncptr):
        if not cfuncptr:   # passed as arg to functions expecting func pointers
            return
        # XXX this assumes it is an external function, correctly initialized
        # with includes and libraries attributes
        name = cfuncptr.__name__
        includes = getattr(cfuncptr, 'includes', ())
        libraries = getattr(cfuncptr, 'libraries', ())
        rlib = rctypesobject.RLibrary(libraries, includes)
        llinterp_friendly_version = getattr(cfuncptr,
                                            'llinterp_friendly_version',
                                            None)
        funcobj = self.rfunctype.fromlib(rlib, name, llinterp_friendly_version)
        ptrobj.set_contents(funcobj)

    def call(self, fnptrobj, *args):
        return fnptrobj.get_contents().call(*args)


FuncPtrCTypeController.register_for_metatype(CFuncPtrType)
