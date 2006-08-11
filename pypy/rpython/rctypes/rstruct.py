from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes.rmodel import CTypesRefRepr, CTypesValueRepr
from pypy.rpython.rctypes.rmodel import genreccopy_structfield, reccopy
from pypy.rpython.rctypes.rprimitive import PrimitiveRepr
from pypy.annotation.model import SomeCTypesObject


class StructRepr(CTypesRefRepr):
    def __init__(self, rtyper, s_struct, is_union=False):
        struct_ctype = s_struct.knowntype
        
        # Find the repr and low-level type of the fields from their ctype
        self.r_fields = {}
        llfields = []
        for name, field_ctype in struct_ctype._fields_:
            r_field = rtyper.getrepr(SomeCTypesObject(field_ctype,
                                                      ownsmemory=False))
            self.r_fields[name] = r_field
            llfields.append((cmangle(name), r_field.ll_type))

        # Here, self.c_data_type == self.ll_type
        external = getattr(struct_ctype, '_external_', False)
        extras = {'hints': {'c_name': struct_ctype.__name__,
                            'external': external}}
        if is_union:
            extras['hints']['union'] = True
        c_data_type = lltype.Struct(struct_ctype.__name__, *llfields, **extras)

        super(StructRepr, self).__init__(rtyper, s_struct, c_data_type)

    def get_content_keepalive_type(self):
        "An extra struct of keepalives, one per field."
        keepalives = []
        for name, field_ctype in self.ctype._fields_:
            r_field = self.r_fields[name]
            field_keepalive_type = r_field.get_content_keepalive_type()
            if field_keepalive_type:
                keepalives.append((cmangle(name), field_keepalive_type))
        if not keepalives:
            return None
        else:
            return lltype.Struct('keepalives', *keepalives)

    def initialize_const(self, p, value):
        for name, r_field in self.r_fields.items():
            llitem = r_field.convert_const(getattr(value, name))
            if isinstance(r_field, CTypesRefRepr):
                # ByRef case
                reccopy(llitem.c_data, getattr(p.c_data, cmangle(name)))
            else:
                # ByValue case
                setattr(p.c_data, cmangle(name), llitem.c_data[0])

    def get_c_data_of_field(self, llops, v_struct, fieldname):
        v_c_struct = self.get_c_data(llops, v_struct)
        r_field = self.r_fields[fieldname]
        c_fieldname = inputconst(lltype.Void, cmangle(fieldname))
        if isinstance(r_field, CTypesRefRepr):
            # ByRef case
            return llops.genop('getsubstruct', [v_c_struct, c_fieldname],
                               lltype.Ptr(r_field.c_data_type))
        else:
            # ByValue case
            P = lltype.Ptr(lltype.FixedSizeArray(r_field.ll_type, 1))
            return llops.genop('direct_fieldptr', [v_c_struct, c_fieldname],
                               resulttype = P)

    def get_field_value(self, llops, v_struct, fieldname):
        # ByValue case only
        r_field = self.r_fields[fieldname]
        assert isinstance(r_field, CTypesValueRepr)
        v_c_struct = self.get_c_data(llops, v_struct)
        c_fieldname = inputconst(lltype.Void, cmangle(fieldname))
        return llops.genop('getfield', [v_c_struct, c_fieldname],
                           resulttype = r_field.ll_type)

##    def set_field_value(self, llops, v_struct, fieldname, v_newvalue):
##        # ByValue case only
##        r_field = self.r_fields[fieldname]
##        assert isinstance(r_field, CTypesValueRepr)
##        v_c_struct = self.get_c_data(llops, v_struct)
##        c_fieldname = inputconst(lltype.Void, fieldname)
##        llops.genop('setfield', [v_c_struct, c_fieldname, v_newvalue])

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        name = s_attr.const
        r_field = self.r_fields[name]
        v_struct, v_attr = hop.inputargs(self, lltype.Void)
        hop.exception_cannot_occur()
        if isinstance(r_field, PrimitiveRepr):
            # primitive case (optimization; the below also works in this case)
            # NB. this optimization is invalid for PointerReprs!  See for
            # example:  s.p.contents = ...  to change the pointer field 'p'
            # of 's'.
            v_value = self.get_field_value(hop.llops, v_struct, name)
            return r_field.return_value(hop.llops, v_value)
        else:
            # ByRef case
            v_c_data = self.get_c_data_of_field(hop.llops, v_struct, name)
            return r_field.return_c_data(hop.llops, v_c_data)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        name = s_attr.const
        r_field = self.r_fields[name]
        v_struct, v_attr, v_item = hop.inputargs(self, lltype.Void, r_field)
        self.setfield(hop.llops, v_struct, name, v_item)

    def setfield(self, llops, v_struct, name, v_item):
        r_field = self.r_fields[name]
        v_newvalue = r_field.get_c_data_or_value(llops, v_item)
        # copy the new value (which might be a whole substructure)
        v_c_struct = self.get_c_data(llops, v_struct)
        genreccopy_structfield(llops, v_newvalue, v_c_struct, cmangle(name))
        # copy the keepalive information too
        v_newkeepalive = r_field.getkeepalive(llops, v_item)
        if v_newkeepalive is not None:
            v_keepalive_struct = self.getkeepalive(llops, v_struct)
            genreccopy_structfield(llops, v_newkeepalive,
                                   v_keepalive_struct, cmangle(name))

def cmangle(name):
    # obscure: names starting with '_' are not allowed in
    # lltype.Struct, so we prefix all names with 'c_'
    return 'c_' + name
