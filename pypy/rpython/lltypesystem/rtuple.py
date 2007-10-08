from pypy.tool.pairtype import pairtype
from pypy.rpython.rmodel import inputconst
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.rtuple import AbstractTupleRepr, AbstractTupleIteratorRepr
from pypy.rpython.lltypesystem.lltype import \
     Ptr, GcStruct, Void, Signed, malloc, typeOf, nullptr
from pypy.rpython.lltypesystem.rtupletype import TUPLE_TYPE
from pypy.rpython.lltypesystem import rstr

# ____________________________________________________________
#
#  Concrete implementation of RPython tuples:
#
#    struct tuple {
#        type0 item0;
#        type1 item1;
#        type2 item2;
#        ...
#    }

class TupleRepr(AbstractTupleRepr):
    rstr_ll = rstr.LLHelpers

    def __init__(self, rtyper, items_r):
        AbstractTupleRepr.__init__(self, rtyper, items_r)
        self.lowleveltype = TUPLE_TYPE(self.lltypes)

    def newtuple(cls, llops, r_tuple, items_v):
        # items_v should have the lowleveltype of the internal reprs
        if len(r_tuple.items_r) == 0:
            return inputconst(Void, ())    # a Void empty tuple
        c1 = inputconst(Void, r_tuple.lowleveltype.TO)
        cflags = inputconst(Void, {'flavor': 'gc'})
        v_result = llops.genop('malloc', [c1, cflags],
                                         resulttype = r_tuple.lowleveltype)
        for i in range(len(r_tuple.items_r)):
            cname = inputconst(Void, r_tuple.fieldnames[i])
            llops.genop('setfield', [v_result, cname, items_v[i]])
        return v_result
    newtuple = classmethod(newtuple)

    def instantiate(self):
        if len(self.items_r) == 0:
            return dum_empty_tuple     # PBC placeholder for an empty tuple
        else:
            return malloc(self.lowleveltype.TO)

    def rtype_bltn_list(self, hop):
        from pypy.rpython.lltypesystem import rlist
        nitems = len(self.items_r)
        vtup = hop.inputarg(self, 0)
        LIST = hop.r_result.lowleveltype.TO
        cno = inputconst(Signed, nitems)
        vlist = hop.gendirectcall(LIST.ll_newlist, cno)
        v_func = hop.inputconst(Void, rlist.dum_nocheck)
        for index in range(nitems):
            name = self.fieldnames[index]
            ritem = self.items_r[index]
            cname = hop.inputconst(Void, name)
            vitem = hop.genop('getfield', [vtup, cname], resulttype = ritem)
            vitem = hop.llops.convertvar(vitem, ritem, hop.r_result.item_repr)
            cindex = inputconst(Signed, index)
            hop.gendirectcall(rlist.ll_setitem_nonneg, v_func, vlist, cindex, vitem)
        return vlist

    def getitem_internal(self, llops, v_tuple, index):
        """Return the index'th item, in internal repr."""
        name = self.fieldnames[index]
        llresult = self.lltypes[index]
        cname = inputconst(Void, name)
        return  llops.genop('getfield', [v_tuple, cname], resulttype = llresult)


def rtype_newtuple(hop):
    return TupleRepr._rtype_newtuple(hop)

newtuple = TupleRepr.newtuple

def dum_empty_tuple(): pass

#
# _________________________ Conversions _________________________

class __extend__(pairtype(PyObjRepr, TupleRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        vlist = []
        for i in range(len(r_to.items_r)):
            ci = inputconst(Signed, i)
            v_item = llops.gencapicall('PyTuple_GetItem_WithIncref', [v, ci],
                                       resulttype = pyobj_repr)
            v_converted = llops.convertvar(v_item, pyobj_repr,
                                           r_to.items_r[i])
            vlist.append(v_converted)
        return r_to.newtuple(llops, r_to, vlist)

class __extend__(pairtype(TupleRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        ci = inputconst(Signed, len(r_from.items_r))
        v_result = llops.gencapicall('PyTuple_New', [ci],
                                     resulttype = pyobj_repr)
        for i in range(len(r_from.items_r)):
            cname = inputconst(Void, r_from.fieldnames[i])
            v_item = llops.genop('getfield', [v, cname],
                                 resulttype = r_from.external_items_r[i].lowleveltype)
            v_converted = llops.convertvar(v_item, r_from.external_items_r[i],
                                           pyobj_repr)
            ci = inputconst(Signed, i)
            llops.gencapicall('PyTuple_SetItem_WithIncref', [v_result, ci,
                                                             v_converted])
        return v_result

# ____________________________________________________________
#
#  Iteration.

class Length1TupleIteratorRepr(AbstractTupleIteratorRepr):

    def __init__(self, r_tuple):
        self.r_tuple = r_tuple
        self.lowleveltype = Ptr(GcStruct('tuple1iter',
                                         ('tuple', r_tuple.lowleveltype)))
        self.ll_tupleiter = ll_tupleiter
        self.ll_tuplenext = ll_tuplenext

TupleRepr.IteratorRepr = Length1TupleIteratorRepr

def ll_tupleiter(ITERPTR, tuple):
    iter = malloc(ITERPTR.TO)
    iter.tuple = tuple
    return iter

def ll_tuplenext(iter):
    # for iterating over length 1 tuples only!
    t = iter.tuple
    if t:
        iter.tuple = nullptr(typeOf(t).TO)
        return t.item0
    else:
        raise StopIteration
