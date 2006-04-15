from pypy.rpython import extregistry
from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pairtype
from pypy.rpython.lltypesystem import lltype

from ctypes import pointer, POINTER, byref, c_int


def pointertype_compute_annotation(metatype, type):
    def compute_result_annotation(*arg_s):
        return annmodel.SomeCTypesObject(type,
                annmodel.SomeCTypesObject.OWNSMEMORY)
    return annmodel.SomeBuiltin(compute_result_annotation, 
                                methodname=type.__name__)

def pointertype_specialize_call(hop):
    r_ptr = hop.r_result
    v_result = r_ptr.allocate_instance(hop.llops)
    if len(hop.args_s):
        v_contentsbox, = hop.inputargs(r_ptr.r_contents)
        r_ptr.setcontents(hop.llops, v_result, v_contentsbox)
    return v_result

def pointerinstance_compute_annotation(type, instance):
    return annmodel.SomeCTypesObject(type,
            annmodel.SomeCTypesObject.OWNSMEMORY)

def pointerinstance_field_annotation(s_pointer, fieldname):
    assert fieldname == "contents"
    ptrtype = s_pointer.knowntype
    return annmodel.SomeCTypesObject(ptrtype._type_,
                                     annmodel.SomeCTypesObject.MEMORYALIAS)

def pointerinstance_get_repr(rtyper, s_pointer):
    from pypy.rpython.rctypes.rpointer import PointerRepr
    return PointerRepr(rtyper, s_pointer)

PointerType = type(POINTER(c_int))
extregistry.register_type(PointerType,
        compute_annotation=pointertype_compute_annotation,
        specialize_call=pointertype_specialize_call)

entry = extregistry.register_metatype(PointerType,
        compute_annotation=pointerinstance_compute_annotation,
        get_repr=pointerinstance_get_repr)
entry.get_field_annotation = pointerinstance_field_annotation

def pointerfn_compute_annotation(s_arg):
    assert isinstance(s_arg, annmodel.SomeCTypesObject)
    ctype = s_arg.knowntype
    result_ctype = POINTER(ctype)
    return annmodel.SomeCTypesObject(result_ctype,
                                     annmodel.SomeCTypesObject.OWNSMEMORY)

extregistry.register_value(pointer,
        compute_result_annotation=pointerfn_compute_annotation,
        # same rtyping for calling pointer() or calling a specific instance
        # of PointerType:
        specialize_call=pointertype_specialize_call)

# byref() is equivalent to pointer() -- the difference is only an
# optimization that is useful in ctypes but not in rctypes.
extregistry.register_value(byref,
        compute_result_annotation=pointerfn_compute_annotation,
        specialize_call=pointertype_specialize_call)

# constant-fold POINTER(CONSTANT_CTYPE) calls
def POINTER_compute_annotation(s_arg):
    from pypy.annotation.bookkeeper import getbookkeeper
    assert s_arg.is_constant(), "POINTER(%r): argument must be constant" % (
        s_arg,)
    RESTYPE = POINTER(s_arg.const)
    return getbookkeeper().immutablevalue(RESTYPE)

def POINTER_specialize_call(hop):
    assert hop.s_result.is_constant()
    return hop.inputconst(lltype.Void, hop.s_result.const)

extregistry.register_value(POINTER,
        compute_result_annotation=POINTER_compute_annotation,
        specialize_call=POINTER_specialize_call)
