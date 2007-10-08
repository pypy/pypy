from pypy.annotation.model import SomeCTypesObject
from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pairtype
from pypy.rpython.error import TyperError
from pypy.rpython.rctypes.implementation import CTypesEntry
from pypy.rpython.lltypesystem import lltype

import ctypes


CFuncPtrType = type(ctypes.CFUNCTYPE(None))


class SomeCTypesFunc(annmodel.SomeBuiltin):
    """Stands for a known constant ctypes function.  Variables containing
    potentially multiple ctypes functions are regular SomeCTypesObjects.
    This is a separate annotation because some features are only supported
    for calls to constant functions, like _rctypes_pyerrchecker_ and
    functions with no declared argtypes.  It also produces better code:
    a direct_call instead of an indirect_call.
    """
    def normalized(self):
        ctype = normalized_func_ctype(self.const)
        return cto_union(ctype, ctype)    # -> SomeCTypesObject

class __extend__(pairtype(SomeCTypesFunc, SomeCTypesFunc)):
    def union((ctf1, ctf2)):
        ctype1 = normalized_func_ctype(ctf1.const)
        ctype2 = normalized_func_ctype(ctf2.const)
        return cto_union(ctype1, ctype2)

class __extend__(pairtype(SomeCTypesFunc, SomeCTypesObject)):
    def union((ctf1, cto2)):
        ctype1 = normalized_func_ctype(ctf1.const)
        return cto_union(ctype1, cto2.knowntype)

class __extend__(pairtype(SomeCTypesObject, SomeCTypesFunc)):
    def union((cto1, ctf2)):
        ctype2 = normalized_func_ctype(ctf2.const)
        return cto_union(cto1.knowntype, ctype2)


def normalized_func_ctype(cfuncptr):
    if getattr(cfuncptr, 'argtypes', None) is None:
        raise annmodel.UnionError("cannot merge two ctypes functions "
                                  "without declared argtypes")
    return ctypes.CFUNCTYPE(cfuncptr.restype,
                            *cfuncptr.argtypes)

def cto_union(ctype1, ctype2):
    if ctype1 != ctype2:
        raise annmodel.UnionError("a ctypes function object can only be "
                                  "merged with another function with the same "
                                  "signature")
    return SomeCTypesObject(ctype1, ownsmemory=True)


class CallEntry(CTypesEntry):
    """Annotation and rtyping of calls to external functions
    declared with ctypes.
    """
    _metatype_ = CFuncPtrType

    def compute_annotation(self):
        #self.ctype_object_discovered()
        func = self.instance
        analyser = self.compute_result_annotation
        methodname = getattr(func, '__name__', None)
        return SomeCTypesFunc(analyser, methodname=methodname)

    def get_instance_sample(self):
        if self.instance is not None:
            return self.instance
        else:
            return self.type()    # a sample NULL function object

    def compute_result_annotation(self, *args_s):
        """
        Answer the annotation of the external function's result
        """
        cfuncptr = self.get_instance_sample()
        result_ctype = cfuncptr.restype
        if result_ctype is None:
            return None
        if result_ctype is ctypes.py_object:
            raise Exception("ctypes functions cannot have restype=py_object; "
                            "set their restype to a subclass of py_object "
                            "and call apyobject.register_py_object_subclass")
            #... because then in ctypes you don't get automatic unwrapping.
            #    That would not be annotatable, for the same reason that
            #    reading the .value attribute of py_object is not annotatable
        s_result = SomeCTypesObject(result_ctype, ownsmemory=True)
        return s_result.return_annotation()

##    def object_seen(self, bookkeeper):
##        "Called when the annotator sees this ctypes function object."
##        # if the function is a Python callback, emulate a call to it
##        # so that the callback is properly annotated
##        if hasattr(self.instance, 'callback'):
##            callback = self.instance.callback
##            argtypes = self.instance.argtypes
##            restype  = self.instance.restype
##            s_callback = bookkeeper.immutablevalue(callback)
##            # the input arg annotations, which are automatically unwrapped
##            args_s = [bookkeeper.valueoftype(ctype).return_annotation()
##                      for ctype in argtypes]
##            uniquekey = (callback, argtypes, restype)
##            s_res = bookkeeper.emulate_pbc_call(uniquekey, s_callback, args_s)
##            # check the result type
##            if restype is None:
##                s_expected = annmodel.s_None
##            else:
##                s_expected = bookkeeper.valueoftype(restype)
##            # can also return the unwrapped version of the ctype,
##            # e.g. an int instead of a c_int
##            s_orelse = s_expected.return_annotation()
##            assert s_expected.contains(s_res) or s_orelse.contains(s_res), (
##                "%r should return a %s but returned %s" % (callback,
##                                                           restype,
##                                                           s_res))

    def specialize_call(self, hop):
        from pypy.rpython.rctypes.rfunc import get_funcptr_constant
        from pypy.rpython.rctypes.rfunc import rtype_funcptr_call
        cfuncptr = self.instance
        v_funcptr, args_r, r_res = get_funcptr_constant(hop.rtyper, cfuncptr,
                                                        hop.args_s)
        pyerrchecker = getattr(cfuncptr, '_rctypes_pyerrchecker_', None)
        return rtype_funcptr_call(hop, v_funcptr, args_r, r_res, pyerrchecker)

    def get_repr(self, rtyper, s_funcptr):
        # for variables containing ctypes function pointers
        from pypy.rpython.rctypes.rfunc import CFuncPtrRepr
        return CFuncPtrRepr(rtyper, s_funcptr)
