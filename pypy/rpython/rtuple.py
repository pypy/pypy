from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import *
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr

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


class TupleRepr(Repr):

    def __init__(self, items_r):
        self.items_r = items_r
        self.fieldnames = ['item%d' % i for i in range(len(items_r))]
        self.lltypes = [r.lowleveltype for r in items_r]
        fields = zip(self.fieldnames, self.lltypes)
        self.lowleveltype = Ptr(GcStruct('tuple%d' % len(items_r), *fields))

    def rtype_len(self, hop):
        return hop.inputconst(Signed, len(self.items_r))


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

# ____________________________________________________________
#
#  Irregular operations.

def rtype_newtuple(hop):
    nb_args = hop.nb_args
    r_tuple = hop.r_result
    c1 = hop.inputconst(Void, r_tuple.lowleveltype)
    v_result = hop.genop('malloc', [c1], resulttype = r_tuple.lowleveltype)
    for i in range(nb_args):
        cname = hop.inputconst(Void, r_tuple.fieldnames[i])
        v_item = hop.inputarg(r_tuple.items_r[i], arg=i)
        hop.genop('setfield', [v_result, cname, v_item])
    return v_result
