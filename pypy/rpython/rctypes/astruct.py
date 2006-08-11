from ctypes import Structure, Union
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.rpython.lltypesystem import lltype

StructType = type(Structure)
UnionType = type(Union)

# XXX this also implements Unions, but they are not properly emulated
#     by the llinterpreter.  They work in the generated C code, though.


class CallEntry(CTypesCallEntry):
    "Annotation and rtyping of calls to structure types."
    _type_ = StructType, UnionType

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.error import TyperError
        r_struct = hop.r_result
        hop.exception_cannot_occur()
        v_result = r_struct.allocate_instance(hop.llops)
        index_by_name = {}
        name_by_index = {}
        # collect the keyword arguments
        for key, index in kwds_i.items():
            assert key.startswith('i_')
            name = key[2:]
            assert index not in name_by_index
            index_by_name[name] = index
            name_by_index[index] = name
        # add the positional arguments
        ctype = self.instance
        fieldsiter = iter(ctype._fields_)
        for i in range(hop.nb_args):
            if i not in name_by_index:
                try:
                    name, _ = fieldsiter.next()
                except StopIteration:
                    raise TyperError("too many arguments in struct construction")
                if name in index_by_name:
                    raise TyperError("multiple values for field %r" % (name,))
                index_by_name[name] = i
                name_by_index[i] = name
        # initialize the fields from the arguments, as far as they are present
        for name, _ in ctype._fields_:
            if name in index_by_name:
                index = index_by_name[name]
                v_valuebox = hop.inputarg(r_struct.r_fields[name], arg=index)
                r_struct.setfield(hop.llops, v_result, name, v_valuebox)
        return v_result


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of structure instances."
    _metatype_ = StructType, UnionType

    def get_field_annotation(self, s_struct, fieldname):
        for name, ctype in self.type._fields_:
            if name == fieldname:
                s_result = SomeCTypesObject(ctype, ownsmemory=False)
                return s_result.return_annotation()
        raise AttributeError('%r has no field %r' % (self.type, fieldname))

    def get_repr(self, rtyper, s_struct):
        from pypy.rpython.rctypes.rstruct import StructRepr
        is_struct = isinstance(self.type, StructType)
        is_union  = isinstance(self.type, UnionType)
        assert is_struct ^ is_union
        return StructRepr(rtyper, s_struct, is_union)
