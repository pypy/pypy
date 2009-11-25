# rtyping of memory address operations
from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.llmemory import NULL, Address, \
     cast_adr_to_int, fakeaddress
from pypy.rpython.rmodel import Repr, IntegerRepr
from pypy.rpython.rptr import PtrRepr
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rarithmetic import r_uint

class __extend__(annmodel.SomeAddress):
    def rtyper_makerepr(self, rtyper):
        return address_repr
    
    def rtyper_makekey(self):
        return self.__class__,

class __extend__(annmodel.SomeTypedAddressAccess):
    def rtyper_makerepr(self, rtyper):
        return TypedAddressAccessRepr(self.type)

    def rtyper_makekey(self):
        return self.__class__, self.type

class AddressRepr(Repr):
    lowleveltype = Address

    def convert_const(self, value):
        # note that llarena.fakearenaaddress is not supported as a constant
        # in graphs
        assert type(value) is fakeaddress
        return value

    def ll_str(self, a):
        from pypy.rpython.lltypesystem.rstr import ll_str
        id = cast_adr_to_int(a)
        return ll_str.ll_int2hex(r_uint(id), True)

    def rtype_getattr(self, hop):
        v_access = hop.inputarg(address_repr, 0)
        return v_access

    def rtype_is_true(self, hop):
        v_addr, = hop.inputargs(address_repr)
        c_null = hop.inputconst(address_repr, NULL)
        return hop.genop('adr_ne', [v_addr, c_null],
                         resulttype=lltype.Bool)

    def get_ll_eq_function(self):
        return None

    def get_ll_hash_function(self):
        return ll_addrhash

    get_ll_fasthash_function = get_ll_hash_function

def ll_addrhash(addr1):
    return cast_adr_to_int(addr1)

address_repr = AddressRepr()


class TypedAddressAccessRepr(Repr):
    lowleveltype = Address

    def __init__(self, typ):
        self.type = typ


class __extend__(pairtype(TypedAddressAccessRepr, IntegerRepr)):

    def rtype_getitem((r_acc, r_int), hop):
        c_type = hop.inputconst(lltype.Void, r_acc.type)
        v_addr, v_offs = hop.inputargs(hop.args_r[0], lltype.Signed)
        return hop.genop('raw_load', [v_addr, c_type, v_offs],
                         resulttype = r_acc.type)

    def rtype_setitem((r_acc, r_int), hop):
        c_type = hop.inputconst(lltype.Void, r_acc.type)
        v_addr, v_offs, v_value = hop.inputargs(hop.args_r[0], lltype.Signed, r_acc.type)
        return hop.genop('raw_store', [v_addr, c_type, v_offs, v_value])


class __extend__(pairtype(AddressRepr, IntegerRepr)):

    def rtype_add((r_addr, r_int), hop):
        if r_int.lowleveltype == lltype.Signed:
            v_addr, v_offs = hop.inputargs(Address, lltype.Signed)
            return hop.genop('adr_add', [v_addr, v_offs], resulttype=Address)

        return NotImplemented
    rtype_inplace_add = rtype_add

    def rtype_sub((r_addr, r_int), hop):
        if r_int.lowleveltype == lltype.Signed:
            v_addr, v_offs = hop.inputargs(Address, lltype.Signed)
            return hop.genop('adr_sub', [v_addr, v_offs], resulttype=Address)

        return NotImplemented
    rtype_inplace_sub = rtype_sub


class __extend__(pairtype(AddressRepr, AddressRepr)):

    def rtype_sub((r_addr1, r_addr2), hop):
        v_addr1, v_addr2 = hop.inputargs(Address, Address)
        return hop.genop('adr_delta', [v_addr1, v_addr2], resulttype=lltype.Signed)

    def rtype_eq((r_addr1, r_addr2), hop):
        v_addr1, v_addr2 = hop.inputargs(Address, Address)
        return hop.genop('adr_eq', [v_addr1, v_addr2], resulttype=lltype.Bool)

    def rtype_ne((r_addr1, r_addr2), hop):
        v_addr1, v_addr2 = hop.inputargs(Address, Address)
        return hop.genop('adr_ne', [v_addr1, v_addr2], resulttype=lltype.Bool)

    def rtype_lt((r_addr1, r_addr2), hop):
        v_addr1, v_addr2 = hop.inputargs(Address, Address)
        return hop.genop('adr_lt', [v_addr1, v_addr2], resulttype=lltype.Bool)

    def rtype_le((r_addr1, r_addr2), hop):
        v_addr1, v_addr2 = hop.inputargs(Address, Address)
        return hop.genop('adr_le', [v_addr1, v_addr2], resulttype=lltype.Bool)

    def rtype_gt((r_addr1, r_addr2), hop):
        v_addr1, v_addr2 = hop.inputargs(Address, Address)
        return hop.genop('adr_gt', [v_addr1, v_addr2], resulttype=lltype.Bool)

    def rtype_ge((r_addr1, r_addr2), hop):
        v_addr1, v_addr2 = hop.inputargs(Address, Address)
        return hop.genop('adr_ge', [v_addr1, v_addr2], resulttype=lltype.Bool)

# conversions

class __extend__(pairtype(PtrRepr, AddressRepr)):

    def convert_from_to((r_ptr, r_addr), v, llops):
        return llops.genop('cast_ptr_to_adr', [v], resulttype=Address)


