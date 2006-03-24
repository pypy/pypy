from pypy.annotation.pairtype import pairtype
from pypy.objspace.flow.model import Constant
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.rmodel import externalvsinternal
from pypy.rpython.error import TyperError
from pypy.rpython.rtuple import AbstractTupleRepr
from pypy.rpython.ootypesystem import ootype


class TupleRepr(AbstractTupleRepr):

    def __init__(self, rtyper, items_r):
        AbstractTupleRepr.__init__(self, rtyper, items_r)
        self.lowleveltype = tuple_type(self.fieldnames, self.lltypes)

    def instantiate(self):
        return ootype.new(self.lowleveltype)

    def getitem(self, llops, v_tuple, index): # ! returns internal repr lowleveltype
        name = self.fieldnames[index]
        llresult = self.lltypes[index]
        cname = inputconst(ootype.Void, name)
        return  llops.genop("oogetfield", [v_tuple, cname], resulttype=llresult)


_tuple_types = {}

def tuple_type(fieldnames, fieldtypes):
    key = tuple(fieldtypes)
    if _tuple_types.has_key(key):
        return _tuple_types[key]
    else:
        fields = dict(zip(fieldnames, fieldtypes))
        INST = ootype.Instance("Tuple%s" % len(fieldnames), ootype.ROOT, fields)
        _tuple_types[key] = INST
        return INST
# ____________________________________________________________
#
#  Irregular operations.

def newtuple(llops, r_tuple, items_v): # items_v should have the lowleveltype of the internal reprs
    if len(r_tuple.items_r) == 0:
        return inputconst(r_tuple, ())    # always the same empty tuple
    c1 = inputconst(ootype.Void, r_tuple.lowleveltype)
    v_result = llops.genop("new", [c1], resulttype=r_tuple.lowleveltype)
    for i in range(len(r_tuple.items_r)):
        cname = inputconst(ootype.Void, r_tuple.fieldnames[i])
        llops.genop("oosetfield", [v_result, cname, items_v[i]])
    return v_result

def newtuple_cached(hop, items_v):
    r_tuple = hop.r_result
    if hop.s_result.is_constant():
        return inputconst(r_tuple, hop.s_result.const)
    else:
        return newtuple(hop.llops, r_tuple, items_v)

def rtype_newtuple(hop):
    r_tuple = hop.r_result
    vlist = hop.inputargs(*r_tuple.items_r)
    return newtuple_cached(hop, vlist)

