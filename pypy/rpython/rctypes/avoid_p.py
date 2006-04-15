from pypy.rpython import extregistry
from pypy.annotation import model as annmodel

from ctypes import c_void_p, c_int, POINTER, cast

PointerType = type(POINTER(c_int))


# c_void_p() as a function
def c_void_p_compute_result_annotation(s_arg=None):
    raise NotImplementedError("XXX calling c_void_p()")

extregistry.register_value(c_void_p,
    compute_result_annotation=c_void_p_compute_result_annotation,
    )

# c_void_p instances
def c_void_compute_annotation(the_type, instance):
    return annmodel.SomeCTypesObject(c_void_p,
                                     annmodel.SomeCTypesObject.OWNSMEMORY)

def c_void_p_get_repr(rtyper, s_void_p):
    from pypy.rpython.rctypes.rvoid_p import CVoidPRepr
    from pypy.rpython.lltypesystem import llmemory
    return CVoidPRepr(rtyper, s_void_p, llmemory.Address)

extregistry.register_type(c_void_p,
    compute_annotation = c_void_compute_annotation,
    get_repr           = c_void_p_get_repr,
    )

# cast() support
def cast_compute_result_annotation(s_arg, s_type):
    assert s_type.is_constant(), "cast(p, %r): argument 2 must be constant" % (
        s_type,)
    type = s_type.const

    def checkptr(ctype):
        assert isinstance(ctype, PointerType) or ctype == c_void_p, (
            "cast(): can only cast between pointers so far, not %r" % (ctype,))
    checkptr(s_arg.knowntype)
    checkptr(type)
    return annmodel.SomeCTypesObject(type,
                                     annmodel.SomeCTypesObject.OWNSMEMORY)

def cast_specialize_call(hop):
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

extregistry.register_value(cast,
    compute_result_annotation=cast_compute_result_annotation,
    specialize_call=cast_specialize_call,
    )
