from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython.lltypesystem import lltype

from ctypes import pointer, POINTER, byref, c_int


PointerType = type(POINTER(c_int))

class CallEntry(CTypesCallEntry):
    "Annotation and rtyping of calls to POINTER types."
    _type_ = PointerType

    def specialize_call(self, hop):
        # delegate calls to the logic for calls to ctypes.pointer()
        return PointerFnEntry.specialize_call(hop)


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of pointer instances."
    _metatype_ = PointerType

    def get_field_annotation(self, s_pointer, fieldname):
        assert fieldname == "contents"
        ptrtype = self.type
        assert s_pointer.knowntype == ptrtype
        return SomeCTypesObject(ptrtype._type_, ownsmemory=False)

    def get_repr(self, rtyper, s_pointer):
        from pypy.rpython.rctypes.rpointer import PointerRepr
        return PointerRepr(rtyper, s_pointer)


class PointerFnEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to ctypes.pointer()."
    _about_ = pointer

    def compute_result_annotation(self, s_arg):
        assert isinstance(s_arg, SomeCTypesObject)
        ctype = s_arg.knowntype
        result_ctype = POINTER(ctype)
        return SomeCTypesObject(result_ctype, ownsmemory=True)

    def specialize_call(hop):
        r_ptr = hop.r_result
        hop.exception_cannot_occur()
        v_result = r_ptr.allocate_instance(hop.llops)
        if len(hop.args_s):
            v_contentsbox, = hop.inputargs(r_ptr.r_contents)
            r_ptr.setcontents(hop.llops, v_result, v_contentsbox)
        return v_result
    specialize_call = staticmethod(specialize_call)

# byref() is equivalent to pointer() -- the difference is only an
# optimization that is useful in ctypes but not in rctypes.
PointerFnEntry._register_value(byref)


class POINTERFnEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to ctypes.POINTER(): constant-folded."
    _about_ = POINTER

    def compute_result_annotation(self, s_arg):
        from pypy.annotation.bookkeeper import getbookkeeper
        assert s_arg.is_constant(), (
            "POINTER(%r): argument must be constant" % (s_arg,))
        RESTYPE = POINTER(s_arg.const)
        return getbookkeeper().immutablevalue(RESTYPE)

    def specialize_call(self, hop):
        assert hop.s_result.is_constant()
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Void, hop.s_result.const)
