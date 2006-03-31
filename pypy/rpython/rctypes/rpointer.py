from pypy.rpython.rmodel import Repr
from pypy.rpython import extregistry
from pypy.annotation import model as annmodel

from ctypes import POINTER, c_int

class PointerRepr(Repr):
    """XXX: todo
    """
    def __init__(self, rtyper, ctype, ref_type):
        pass

def get_repr(rtyper, s_pointer):
    """XXX: todo
    """
    raise RuntimeError("foo")
        
def registerPointerType(ptrtype):
    """Adds a new pointer type to the extregistry.

    Since pointers can be created to primitive ctypes objects, arrays,
    structs and structs are not predefined each new pointer type is
    registered in the extregistry as it is identified.

    The new pointers that are created have a "contents" attribute
    which, when retrieved, in effect dereferences the pointer and
    returns the referenced value.
    """
    def compute_result_annotation(s_arg):
        return annmodel.SomeCTypesObject(ptrtype,
                annmodel.SomeCTypesObject.OWNSMEMORY)

    def specialize_call(hop):
        raise RuntimeError('foo')

    type_entry = extregistry.register_type(ptrtype,
                            specialize_call=specialize_call,
                            get_repr=get_repr)
    contentsType = annmodel.SomeCTypesObject(ptrtype._type_,
                                    annmodel.SomeCTypesObject.MEMORYALIAS)
    type_entry.fields_s = {'contents': contentsType}

    return extregistry.register_value(ptrtype,
                        compute_result_annotation=compute_result_annotation)

def POINTER_compute_annotation(metatype, the_type):
    """compute the annotation of POINTER() calls to create a ctypes
    pointer for the given type
    """

    def POINTER_compute_result_annotation(s_arg):
        """Called to compute the result annotation of
        POINTER(<ctypes type>).  This happens to return a new
        class which itself is treated as SomeBuiltin because when
        called it creates a new pointer.

        NOTE: To handle a myriad of possible pointer types, each
              ctypes type that is passed to POINTER() calls is itself
              registered if it isn't already.
        """
        ptrtype = POINTER(s_arg.const)

        if not extregistry.is_registered_type(ptrtype):
            entry = registerPointerType(ptrtype)
        else:
            entry = extregistry.lookup(ptrtype)

        return annmodel.SomeBuiltin(entry.compute_result_annotation,
                                    methodname=ptrtype.__name__)

    # annotation of POINTER (not the call) is SomeBuitin which provides
    # a way of computing the result annotation of POINTER(<ctypes type>)
    return annmodel.SomeBuiltin(POINTER_compute_result_annotation,
                                methodname=the_type.__name__)

# handles POINTER() calls
value_entry = extregistry.register_value(POINTER,
        compute_annotation=POINTER_compute_annotation)

def POINTER_specialize_call(hop):
    raise RuntimeError("foo")

extregistry.register_type(POINTER, specialize_call=POINTER_specialize_call)

#type_entry = extregistry.register_type(ptrmeta,
#        compute_annotation=compute_annotation,
#        get_repr=get_repr)
