from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr, inputconst
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.lltype import Ptr, GcStruct, Void, Signed

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

class __extend__(annmodel.SomeTuple):
    def rtyper_makerepr(self, rtyper):
        return TupleRepr([rtyper.getrepr(s_item) for s_item in self.items])
    
    def rtyper_makekey(self):
        keys = [s_item.rtyper_makekey() for s_item in self.items]
        return tuple(keys)


class TupleRepr(Repr):

    def __init__(self, items_r):
        self.items_r = items_r
        self.fieldnames = ['item%d' % i for i in range(len(items_r))]
        self.lltypes = [r.lowleveltype for r in items_r]
        fields = zip(self.fieldnames, self.lltypes)
        self.lowleveltype = Ptr(GcStruct('tuple%d' % len(items_r), *fields))

    def convert_const(self, value):
        assert isinstance(value, tuple) and len(value) == len(self.items_r)
        p = malloc(self.lowleveltype.TO)
        for obj, r, name in zip(value, self.items_r, self.fieldnames):
            setattr(p, name, r.convert_const(obj))
        return p

    def rtype_len(self, hop):
        return hop.inputconst(Signed, len(self.items_r))

    def rtype_bltn_list(self, hop):
        from pypy.rpython import rlist
        nitems = len(self.items_r)
        vtup = hop.inputarg(self, 0)
        c1 = inputconst(Void, hop.r_result.lowleveltype)
        c2 = inputconst(Signed, nitems)
        vlist = hop.gendirectcall(rlist.ll_newlist, c1, c2)
        for index in range(nitems):
            name = self.fieldnames[index]
            ritem = self.items_r[index]
            cname = hop.inputconst(Void, name)
            vitem = hop.genop('getfield', [vtup, cname], resulttype = ritem)
            vitem = hop.llops.convertvar(vitem, ritem, hop.r_result.item_repr)
            cindex = inputconst(Signed, index)
            hop.gendirectcall(rlist.ll_setitem_nonneg, vlist, cindex, vitem)
        return vlist
           
class __extend__(pairtype(TupleRepr, IntegerRepr)):

    def rtype_getitem((r_tup, r_int), hop):
        v_tuple, v_index = hop.inputargs(r_tup, Signed)
        if not isinstance(v_index, Constant):
            raise TyperError("non-constant tuple index")
        index = v_index.value
        name = r_tup.fieldnames[index]
        llresult = r_tup.lltypes[index]
        cname = hop.inputconst(Void, name)
        return hop.genop('getfield', [v_tuple, cname], resulttype = llresult)

class __extend__(pairtype(TupleRepr, TupleRepr)):
    
    def rtype_add((r_tup1, r_tup2), hop):
        v_tuple, v_tuple1 = hop.inputargs(r_tup1.items_r, r_tup2.items_r)
        items_r = r_tup1.items_r + r_tup2.items_r
        res = TupleRepr(items_r)
        vlist = v_tuple + v_tuple1
        return newtuple(hop.llops, res, vlist)
        

# ____________________________________________________________
#
#  Irregular operations.

def newtuple(llops, r_tuple, items_v):
    c1 = inputconst(Void, r_tuple.lowleveltype.TO)
    v_result = llops.genop('malloc', [c1], resulttype = r_tuple.lowleveltype)
    for i in range(len(r_tuple.items_r)):
        cname = inputconst(Void, r_tuple.fieldnames[i])
        llops.genop('setfield', [v_result, cname, items_v[i]])
    return v_result

def rtype_newtuple(hop):
    r_tuple = hop.r_result
    vlist = hop.inputargs(*r_tuple.items_r)
    return newtuple(hop.llops, r_tuple, vlist)

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
        return newtuple(llops, r_to, vlist)

class __extend__(pairtype(TupleRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        ci = inputconst(Signed, len(r_from.items_r))
        v_result = llops.gencapicall('PyTuple_New', [ci],
                                     resulttype = pyobj_repr)
        for i in range(len(r_from.items_r)):
            cname = inputconst(Void, r_from.fieldnames[i])
            v_item = llops.genop('getfield', [v, cname],
                                 resulttype = r_from.items_r[i].lowleveltype)
            v_converted = llops.convertvar(v_item, r_from.items_r[i],
                                           pyobj_repr)
            ci = inputconst(Signed, i)
            llops.gencapicall('PyTuple_SetItem_WithIncref', [v_result, ci,
                                                             v_converted])
        return v_result
