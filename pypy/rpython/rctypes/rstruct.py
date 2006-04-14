from ctypes import Structure
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin
from pypy.rpython import extregistry
from pypy.rpython.rmodel import inputconst
from pypy.rpython.rbuiltin import gen_cast_structfield_pointer
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes.rmodel import CTypesRefRepr, CTypesValueRepr
from pypy.rpython.rctypes.rmodel import genreccopy, reccopy
from pypy.rpython.rctypes.rprimitive import PrimitiveRepr

StructType = type(Structure)

class StructRepr(CTypesRefRepr):
    def __init__(self, rtyper, s_struct):
        struct_ctype = s_struct.knowntype
        
        # Find the repr and low-level type of the fields from their ctype
        self.r_fields = {}
        llfields = []
        for name, field_ctype in struct_ctype._fields_:
            r_field = rtyper.getrepr(SomeCTypesObject(field_ctype,
                                                SomeCTypesObject.MEMORYALIAS))
            self.r_fields[name] = r_field
            llfields.append((name, r_field.ll_type))

        # Here, self.c_data_type == self.ll_type
        external = getattr(struct_ctype, '_external_', False)
        extras = {'hints': {'c_name': struct_ctype.__name__,
                            'external': external}}
        c_data_type = lltype.Struct(struct_ctype.__name__, *llfields, **extras)

        super(StructRepr, self).__init__(rtyper, s_struct, c_data_type)

    def initialize_const(self, p, value):
        for name, r_field in self.r_fields.items():
            llitem = r_field.convert_const(getattr(value, name))
            if isinstance(r_field, CTypesRefRepr):
                # ByRef case
                reccopy(llitem.c_data, getattr(p.c_data, name))
            else:
                # ByValue case
                setattr(p.c_data, name, llitem.c_data[0])

    def get_c_data_of_field(self, llops, v_struct, fieldname):
        v_c_struct = self.get_c_data(llops, v_struct)
        r_field = self.r_fields[fieldname]
        if isinstance(r_field, CTypesRefRepr):
            # ByRef case
            c_fieldname = inputconst(lltype.Void, fieldname)
            return llops.genop('getsubstruct', [v_c_struct, c_fieldname],
                               lltype.Ptr(r_field.c_data_type))
        else:
            # ByValue case
            A = lltype.FixedSizeArray(r_field.ll_type, 1)
            return gen_cast_structfield_pointer(llops, lltype.Ptr(A),
                                                v_c_struct, fieldname)

    def get_field_value(self, llops, v_struct, fieldname):
        # ByValue case only
        r_field = self.r_fields[fieldname]
        assert isinstance(r_field, CTypesValueRepr)
        v_c_struct = self.get_c_data(llops, v_struct)
        c_fieldname = inputconst(lltype.Void, fieldname)
        return llops.genop('getfield', [v_c_struct, c_fieldname],
                           resulttype = r_field.ll_type)

    def set_field_value(self, llops, v_struct, fieldname, v_newvalue):
        # ByValue case only
        r_field = self.r_fields[fieldname]
        assert isinstance(r_field, CTypesValueRepr)
        v_c_struct = self.get_c_data(llops, v_struct)
        c_fieldname = inputconst(lltype.Void, fieldname)
        llops.genop('setfield', [v_c_struct, c_fieldname, v_newvalue])

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        name = s_attr.const
        r_field = self.r_fields[name]
        v_struct, v_attr = hop.inputargs(self, lltype.Void)
        if isinstance(r_field, CTypesRefRepr):
            # ByRef case
            v_c_data = self.get_c_data_of_field(hop.llops, v_struct, name)
            return r_field.return_c_data(hop.llops, v_c_data)
        else:
            # ByValue case (optimization; the above also works in this case)
            v_value = self.get_field_value(hop.llops, v_struct, name)
            return r_field.return_value(hop.llops, v_value)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        name = s_attr.const
        r_field = self.r_fields[name]
        v_struct, v_attr, v_item = hop.inputargs(self, lltype.Void, r_field)
        if isinstance(r_field, CTypesRefRepr):
            # ByRef case
            v_new_c_data = r_field.get_c_data(hop.llops, v_item)
            v_c_data = self.get_c_data_of_field(hop.llops, v_struct, name)
            # copy the whole structure's content over
            genreccopy(hop.llops, v_new_c_data, v_c_data)
        else:
            # ByValue case (optimization; the above also works in this case)
            v_newvalue = r_field.getvalue(hop.llops, v_item)
            self.set_field_value(hop.llops, v_struct, name, v_newvalue)

# ____________________________________________________________

def structtype_specialize_call(hop):
    r_struct = hop.r_result
    return hop.genop("malloc", [
        hop.inputconst(lltype.Void, r_struct.lowleveltype.TO), 
        ], resulttype=r_struct.lowleveltype,
    )

def structtype_compute_annotation(metatype, type):
    def compute_result_annotation(*arg_s):
        return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)
    return SomeBuiltin(compute_result_annotation, methodname=type.__name__)

extregistry.register_type(StructType, 
    compute_annotation=structtype_compute_annotation,
    specialize_call=structtype_specialize_call)

def struct_instance_compute_annotation(type, instance):
    return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)

def struct_instance_field_annotation(s_struct, fieldname):
    structtype = s_struct.knowntype
    for name, ctype in structtype._fields_:
        if name == fieldname:
            s_result = SomeCTypesObject(ctype, SomeCTypesObject.MEMORYALIAS)
            return s_result.return_annotation()
    raise AttributeError('%r has no field %r' % (structtype, fieldname))

def structtype_get_repr(rtyper, s_struct):
    return StructRepr(rtyper, s_struct)

entry = extregistry.register_metatype(StructType,
    compute_annotation=struct_instance_compute_annotation,
    get_repr=structtype_get_repr)
entry.get_field_annotation = struct_instance_field_annotation
