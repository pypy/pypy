from pypy.rpython.rmodel import inputconst
from pypy.rpython.rtuple import AbstractTupleRepr, AbstractTupleIteratorRepr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem import rstr


class TupleRepr(AbstractTupleRepr):
    rstr_ll = rstr.LLHelpers

    def __init__(self, rtyper, items_r):
        AbstractTupleRepr.__init__(self, rtyper, items_r)
        self.lowleveltype = ootype.Record(dict(zip(self.fieldnames, self.lltypes)))

    def newtuple(cls, llops, r_tuple, items_v):
        # items_v should have the lowleveltype of the internal reprs
        if len(r_tuple.items_r) == 0:
            return inputconst(r_tuple, ()) # always the same empty tuple
        c1 = inputconst(ootype.Void, r_tuple.lowleveltype)
        v_result = llops.genop("new", [c1], resulttype=r_tuple.lowleveltype)
        for i in range(len(r_tuple.items_r)):
            cname = inputconst(ootype.Void, r_tuple.fieldnames[i])
            llops.genop("oosetfield", [v_result, cname, items_v[i]])
        return v_result
    newtuple = classmethod(newtuple)

    def instantiate(self):
        return ootype.new(self.lowleveltype)

    def getitem_internal(self, llops, v_tuple, index):
        # ! returns internal repr lowleveltype
        name = self.fieldnames[index]
        llresult = self.lltypes[index]
        cname = inputconst(ootype.Void, name)
        return  llops.genop("oogetfield", [v_tuple, cname], resulttype=llresult)

    def rtype_bltn_list(self, hop):
        from pypy.rpython.ootypesystem import rlist
        v_tup = hop.inputarg(self, 0)
        RESULT = hop.r_result.lowleveltype
        c_resulttype = inputconst(ootype.Void, RESULT)
        c_length = inputconst(ootype.Signed, len(self.items_r))
        if isinstance(RESULT, ootype.Array):
            v_list = hop.genop('oonewarray', [c_resulttype, c_length], resulttype=RESULT)
        else:
            assert isinstance(RESULT, ootype.List)
            v_list = hop.genop('new', [c_resulttype], resulttype=RESULT)
            c_resize = inputconst(ootype.Void, '_ll_resize')
            hop.genop('oosend', [c_resize, v_list, c_length], resulttype=ootype.Void)

        c_setitem = inputconst(ootype.Void, 'll_setitem_fast')
        
        for index in range(len(self.items_r)):
            name = self.fieldnames[index]
            r_item = self.items_r[index]
            c_name = hop.inputconst(ootype.Void, name)
            v_item = hop.genop("oogetfield", [v_tup, c_name], resulttype=r_item)
            v_item = hop.llops.convertvar(v_item, r_item, hop.r_result.item_repr)
            c_index = inputconst(ootype.Signed, index)
            hop.genop('oosend', [c_setitem, v_list, c_index, v_item], resulttype=ootype.Void)
            
        return v_list


def rtype_newtuple(hop):
    return TupleRepr._rtype_newtuple(hop)

newtuple = TupleRepr.newtuple

# ____________________________________________________________
#
#  Iteration.

class Length1TupleIteratorRepr(AbstractTupleIteratorRepr):

    def __init__(self, r_tuple):
        self.r_tuple = r_tuple
        self.lowleveltype = ootype.Record(
                {"iterable": r_tuple.lowleveltype, "index": ootype.Signed})
        self.ll_tupleiter = ll_tupleiter
        self.ll_tuplenext = ll_tuplenext

TupleRepr.IteratorRepr = Length1TupleIteratorRepr

def ll_tupleiter(ITERINST, tuple):
    iter = ootype.new(ITERINST)
    iter.iterable = tuple
    return iter

def ll_tuplenext(iter):
    # for iterating over length 1 tuples only!
    t = iter.iterable
    if t:
        iter.iterable = ootype.null(ootype.typeOf(t))
        return t.item0
    else:
        raise StopIteration

