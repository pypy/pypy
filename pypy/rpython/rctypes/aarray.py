from ctypes import ARRAY, c_int, c_char
from pypy.annotation.model import SomeCTypesObject, SomeString
from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.rpython.lltypesystem import lltype

ArrayType = type(ARRAY(c_int, 10))

class VarSizedArrayType(object):
    """Placeholder for ctypes array types whose size is not an
    annotation-time constant.
    """
    def __init__(self, itemtype):
        self._type_ = itemtype
        #self._length_ = unspecified
        self.__name__ = itemtype.__name__ + '_Array'

    def get_instance_annotation(self, *args_s):
        return SomeCTypesObject(self, ownsmemory=True)

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self._type_ == other._type_)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self._type_)


class CallEntry(CTypesCallEntry):
    "Annotation and rtyping of calls to array types."
    _type_ = ArrayType

    def specialize_call(self, hop):
        from pypy.rpython.error import TyperError
        from pypy.rpython.rmodel import inputconst
        r_array = hop.r_result
        hop.exception_cannot_occur()
        v_result = r_array.allocate_instance(hop.llops)
        if hop.nb_args > r_array.length:
            raise TyperError("too many arguments for an array of length %d" % (
                r_array.length,))
        items_v = hop.inputargs(*[r_array.r_item] * hop.nb_args)
        r_array.initializeitems(hop.llops, v_result, items_v)
        return v_result


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of array instances."
    _metatype_ = ArrayType, VarSizedArrayType

    def get_field_annotation(self, s_array, fieldname):
        assert fieldname == 'value'
        if self.type._type_ != c_char:
            raise Exception("only arrays of chars have a .value attribute")
        return SomeString()   # can_be_None = False

    def get_repr(self, rtyper, s_array):
        from pypy.rpython.rctypes.rarray import ArrayRepr
        return ArrayRepr(rtyper, s_array)
