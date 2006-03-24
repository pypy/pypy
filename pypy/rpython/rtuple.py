import operator
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.rmodel import IteratorRepr
from pypy.rpython.rmodel import externalvsinternal
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.lltypesystem.lltype import \
     Ptr, GcStruct, Void, Signed, malloc, typeOf, nullptr
from pypy.rpython.rarithmetic import intmask

class __extend__(annmodel.SomeTuple):
    def rtyper_makerepr(self, rtyper):
        repr_class = rtyper.type_system.rtuple.TupleRepr
        return repr_class(rtyper, [rtyper.getrepr(s_item) for s_item in self.items])
    
    def rtyper_makekey_ex(self, rtyper):
        keys = [rtyper.makekey(s_item) for s_item in self.items]
        return tuple([self.__class__]+keys)

class AbstractTupleRepr(Repr):

    def __init__(self, rtyper, items_r):
        self.items_r = []
        self.external_items_r = []
        for item_r in items_r:
            external_repr, internal_repr = externalvsinternal(rtyper, item_r)
            self.items_r.append(internal_repr)
            self.external_items_r.append(external_repr)
        items_r = self.items_r
        self.fieldnames = ['item%d' % i for i in range(len(items_r))]
        self.lltypes = [r.lowleveltype for r in items_r]
        self.tuple_cache = {}

    def convert_const(self, value):
        assert isinstance(value, tuple) and len(value) == len(self.items_r)
        key = tuple([Constant(item) for item in value])
        try:
            return self.tuple_cache[key]
        except KeyError:
            p = self.instantiate()
            self.tuple_cache[key] = p
            for obj, r, name in zip(value, self.items_r, self.fieldnames):
                setattr(p, name, r.convert_const(obj))
            return p

    def rtype_len(self, hop):
        return hop.inputconst(Signed, len(self.items_r))


class __extend__(pairtype(AbstractTupleRepr, IntegerRepr)):

    def rtype_getitem((r_tup, r_int), hop):
        v_tuple, v_index = hop.inputargs(r_tup, Signed)
        if not isinstance(v_index, Constant):
            raise TyperError("non-constant tuple index")
        index = v_index.value
        v = r_tup.getitem(hop.llops, v_tuple, index)
        return hop.llops.convertvar(v, r_tup.items_r[index], r_tup.external_items_r[index])

