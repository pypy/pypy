from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import llmemory
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
    assert isinstance(type, PointerType) or type == c_void_p, (
       "cast(p, %r): XXX can only cast between pointer types so far" % (type,))
    return annmodel.SomeCTypesObject(type,
                                     annmodel.SomeCTypesObject.OWNSMEMORY)

extregistry.register_value(cast,
    compute_result_annotation=cast_compute_result_annotation,
    )
