from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.annotation.model import SomeCTypesObject

from ctypes import c_void_p, c_int, POINTER, cast

PointerType = type(POINTER(c_int))


class CallEntry(CTypesCallEntry):
    "Annotation and rtyping of calls to c_void_p."
    _about_ = c_void_p

    def specialize_call(self, hop):
        r_void_p = hop.r_result
        v_result = r_void_p.allocate_instance(hop.llops)
        return v_result


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of c_void_p instances."
    _type_ = c_void_p

    def get_repr(self, rtyper, s_void_p):
        from pypy.rpython.rctypes.rvoid_p import CVoidPRepr
        from pypy.rpython.lltypesystem import llmemory
        return CVoidPRepr(rtyper, s_void_p, llmemory.Address)


class CastFnEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to ctypes.cast()"
    _about_ = cast

    def checkptr(self, ctype):
        assert isinstance(ctype, PointerType) or ctype == c_void_p, (
            "cast(): can only cast between pointers so far, not %r" % (ctype,))

    def compute_result_annotation(self, s_arg, s_type):
        assert s_type.is_constant(), (
            "cast(p, %r): argument 2 must be constant" % (s_type,))
        type = s_type.const
        self.checkptr(s_arg.knowntype)
        self.checkptr(type)
        return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)

    def specialize_call(self, hop):
        from pypy.rpython.rctypes.rpointer import PointerRepr
        from pypy.rpython.rctypes.rvoid_p import CVoidPRepr
        from pypy.rpython.lltypesystem import lltype, llmemory
        assert isinstance(hop.args_r[0], (PointerRepr, CVoidPRepr))
        targetctype = hop.args_s[1].const
        v_box, c_targetctype = hop.inputargs(hop.args_r[0], lltype.Void)
        v_adr = hop.args_r[0].getvalue(hop.llops, v_box)
        if v_adr.concretetype != llmemory.Address:
            v_adr = hop.genop('cast_ptr_to_adr', [v_adr],
                              resulttype = llmemory.Address)

        if targetctype == c_void_p:
            # cast to void
            v_result = v_adr
        else:
            # cast to pointer
            v_result = hop.genop('cast_adr_to_ptr', [v_adr],
                                 resulttype = hop.r_result.ll_type)
        return hop.r_result.return_value(hop.llops, v_result)
