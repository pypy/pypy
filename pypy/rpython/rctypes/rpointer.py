from pypy.rpython.rmodel import Repr
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype
from pypy.annotation import model as annmodel

from ctypes import POINTER

class PointerRepr(Repr):
    """XXX: todo
    """
    def __init__(self, rtyper, s_pointer, s_contents):
        self.s_pointer = s_pointer
        self.s_contents = s_contents
        self.ctype = s_pointer.knowntype
        self.ref_ctype = s_contents.knowntype

        if not extregistry.is_registered_type(self.ref_ctype):
            raise TypeError("Unregistered referenced "
                            "type: %s" % (self.ref_ctype.__name__,))

        ref_entry = extregistry.lookup_type(self.ref_ctype)
        contents_repr = ref_entry.get_repr(rtyper, self.s_contents)

        ll_contents = lltype.Ptr(contents_repr.c_data_type)

        self.lowleveltype = lltype.Ptr(
            lltype.GcStruct("CtypesBox_%s" % (self.ctype.__name__,),
                ("c_data",
                    lltype.Struct("C_Data_%s" % (self.ctype.__name__),
                        ('value', ll_contents)
                    )
                ),
                ("keepalive", contents_repr.lowleveltype)
            )
        )

def registerPointerType(ptrtype):
    """Adds a new pointer type to the extregistry.

    Since pointers can be created to primitive ctypes objects, arrays,
    structs and structs are not predefined each new pointer type is
    registered in the extregistry as it is identified.

    The new pointers that are created have a "contents" attribute
    which, when retrieved, in effect dereferences the pointer and
    returns the referenced value.
    """
    def compute_result_annotation(s_self, s_arg):
        return annmodel.SomeCTypesObject(ptrtype,
                annmodel.SomeCTypesObject.OWNSMEMORY)

    def specialize_call(hop):
        raise RuntimeError('foo')

    contentsType = annmodel.SomeCTypesObject(ptrtype._type_,
                                    annmodel.SomeCTypesObject.MEMORYALIAS)

    def get_repr(rtyper, s_pointer):
        return PointerRepr(rtyper, s_pointer, contentsType)
        
    type_entry = extregistry.register_type(ptrtype,
                            specialize_call=specialize_call,
                            get_repr=get_repr)
    type_entry.fields_s = {'contents': contentsType}

    return extregistry.register_value(ptrtype,
                        compute_result_annotation=compute_result_annotation,
                        specialize_call=specialize_call)

def pointer_compute_annotation(metatype, the_type):
    """compute the annotation of POINTER() calls to create a ctypes
    pointer for the given type
    """

    def pointer_compute_result_annotation(s_arg):
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

        s_self = annmodel.SomeCTypesObject(ptrtype,
                            annmodel.SomeCTypesObject.OWNSMEMORY)
                        

        return annmodel.SomeBuiltin(entry.compute_result_annotation,
                s_self=s_self,
                methodname=ptrtype.__name__)

    # annotation of POINTER (not the call) is SomeBuitin which provides
    # a way of computing the result annotation of POINTER(<ctypes type>)
    return annmodel.SomeBuiltin(pointer_compute_result_annotation,
                                methodname=the_type.__name__)

def pointer_specialize_call(hop):
    raise RuntimeError("foo")

# handles POINTER() calls
value_entry = extregistry.register_value(POINTER,
        compute_annotation=pointer_compute_annotation,
        specialize_call=pointer_specialize_call)
