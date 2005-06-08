import autopath
import sets

from pypy.objspace.flow.model import Variable, Constant
from pypy.objspace.flow.model import last_exception

from pypy.rpython import lltype

from pypy.annotation import model as annmodel

from pypy.translator.llvm import representation
from pypy.translator.llvm import typerepr

debug = True

class PointerRepr(representation.LLVMRepr):
    def __init__(self, ptr, gen):
        if debug:
            print "PointerRepr(%s)" % ptr
        self.ptr = ptr
        self.gen = gen
        self.type = gen.get_repr(ptr._TYPE)
        self.l_obj = gen.get_repr(ptr._obj)
        print self.l_obj, ptr._obj
        self.dependencies = sets.Set([self.l_obj, self.type])
    
    def llvmname(self):
        return self.l_obj.llvmname()

    def __getattr__(self, name):
        if debug:
            print "getattr called", name, self.l_obj.llvmname()
        if name.startswith("op_"):
            attr = getattr(self.l_obj, name, None)
            if attr is not None:
                return attr
        raise AttributeError, ("PointerRepr instance has no attribute %s" %
                               repr(name))


class PointerTypeRepr(typerepr.TypeRepr):
    def get(obj, gen):
        if obj.__class__ is lltype.Ptr:
            return PointerTypeRepr(obj, gen)
        return None
    get = staticmethod(get)
    
    def __init__(self, ptrtype, gen):
        if debug:
            print "PointerTypeRepr(%s)" % ptrtype
        self.ptrtype = ptrtype
        self.gen = gen
        self.l_to = gen.get_repr(ptrtype.TO)
        self.dependencies = sets.Set([self.l_to])

    def typename(self):
        return self.l_to.typename()

        