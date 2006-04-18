import operator
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.rmodel import IteratorRepr
from pypy.rpython.rmodel import externalvsinternal
from pypy.rpython.lltypesystem.lltype import Void, Signed 
from pypy.rpython.rarithmetic import intmask

class __extend__(annmodel.SomeTuple):
    def rtyper_makerepr(self, rtyper):
        repr_class = rtyper.type_system.rtuple.TupleRepr
        return repr_class(rtyper, [rtyper.getrepr(s_item) for s_item in self.items])
    
    def rtyper_makekey_ex(self, rtyper):
        keys = [rtyper.makekey(s_item) for s_item in self.items]
        return tuple([self.__class__]+keys)


_gen_eq_function_cache = {}
_gen_hash_function_cache = {}

def gen_eq_function(items_r):
    eq_funcs = [r_item.get_ll_eq_function() or operator.eq for r_item in items_r]
    key = tuple(eq_funcs)
    try:
        return _gen_eq_function_cache[key]
    except KeyError:
        miniglobals = {}
        source = """
def ll_eq(t1, t2):
    %s
    return True
"""
        body = []
        for i, eq_func in enumerate(eq_funcs):
            miniglobals['eq%d' % i] = eq_func
            body.append("if not eq%d(t1.item%d, t2.item%d): return False" % (i, i, i))
        body = ('\n'+' '*4).join(body)
        source = source % body
        exec source in miniglobals
        ll_eq = miniglobals['ll_eq']
        _gen_eq_function_cache[key] = ll_eq
        return ll_eq

def gen_hash_function(items_r):
    # based on CPython
    hash_funcs = [r_item.get_ll_hash_function() for r_item in items_r]
    key = tuple(hash_funcs)
    try:
        return _gen_hash_function_cache[key]
    except KeyError:
        miniglobals = {}
        source = """
def ll_hash(t):
    retval = 0x345678
    %s
    return retval
"""
        body = []
        mult = 1000003
        for i, hash_func in enumerate(hash_funcs):
            miniglobals['hash%d' % i] = hash_func
            body.append("retval = (retval ^ hash%d(t.item%d)) * %d" %
                        (i, i, mult))
            mult = intmask(mult + 82520 + 2*len(items_r))
        body = ('\n'+' '*4).join(body)
        source = source % body
        exec source in miniglobals
        ll_hash = miniglobals['ll_hash']
        _gen_hash_function_cache[key] = ll_hash
        return ll_hash


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

    def newtuple_cached(cls, hop, items_v):
        r_tuple = hop.r_result
        if hop.s_result.is_constant():
            return inputconst(r_tuple, hop.s_result.const)
        else:
            return cls.newtuple(hop.llops, r_tuple, items_v)
    newtuple_cached = classmethod(newtuple_cached)

    def _rtype_newtuple(cls, hop):
        r_tuple = hop.r_result
        vlist = hop.inputargs(*r_tuple.items_r)
        return cls.newtuple_cached(hop, vlist)
    _rtype_newtuple = classmethod(_rtype_newtuple)

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

    def compact_repr(self):
        return "TupleR %s" % ' '.join([llt._short_name() for llt in self.lltypes])

    def rtype_len(self, hop):
        return hop.inputconst(Signed, len(self.items_r))

    def get_ll_eq_function(self):
        return gen_eq_function(self.items_r)

    def get_ll_hash_function(self):
        return gen_hash_function(self.items_r)    

    def make_iterator_repr(self):
        if len(self.items_r) == 1:
            # subclasses are supposed to set the IteratorRepr attribute
            return self.IteratorRepr(self)
        raise TyperError("can only iterate over tuples of length 1 for now")


class __extend__(pairtype(AbstractTupleRepr, IntegerRepr)):

    def rtype_getitem((r_tup, r_int), hop):
        v_tuple, v_index = hop.inputargs(r_tup, Signed)
        if not isinstance(v_index, Constant):
            raise TyperError("non-constant tuple index")
        if hop.has_implicit_exception(IndexError):
            hop.exception_cannot_occur()
        index = v_index.value
        v = r_tup.getitem(hop.llops, v_tuple, index)
        return hop.llops.convertvar(v, r_tup.items_r[index], r_tup.external_items_r[index])

class __extend__(pairtype(AbstractTupleRepr, Repr)): 
    def rtype_contains((r_tup, r_item), hop):
        s_tup = hop.args_s[0]
        if not s_tup.is_constant():
            raise TyperError("contains() on non-const tuple") 
        t = s_tup.const
        typ = type(t[0]) 
        for x in t[1:]: 
            if type(x) is not typ: 
                raise TyperError("contains() on mixed-type tuple "
                                 "constant %r" % (t,))
        d = {}
        for x in t: 
            d[x] = None 
        hop2 = hop.copy()
        _, _ = hop2.r_s_popfirstarg()
        v_dict = Constant(d)
        s_dict = hop.rtyper.annotator.bookkeeper.immutablevalue(d)
        hop2.v_s_insertfirstarg(v_dict, s_dict)
        return hop2.dispatch()
 
class __extend__(pairtype(AbstractTupleRepr, AbstractTupleRepr)):
    
    def rtype_add((r_tup1, r_tup2), hop):
        v_tuple1, v_tuple2 = hop.inputargs(r_tup1, r_tup2)
        vlist = []
        for i in range(len(r_tup1.items_r)):
            vlist.append(r_tup1.getitem(hop.llops, v_tuple1, i))
        for i in range(len(r_tup2.items_r)):
            vlist.append(r_tup2.getitem(hop.llops, v_tuple2, i))
        return r_tup1.newtuple_cached(hop, vlist)
    rtype_inplace_add = rtype_add

    def convert_from_to((r_from, r_to), v, llops):
        if len(r_from.items_r) == len(r_to.items_r):
            if r_from.lowleveltype == r_to.lowleveltype:
                return v
            n = len(r_from.items_r)
            items_v = []
            for i in range(n):
                item_v = r_from.getitem(llops, v, i)
                item_v = llops.convertvar(item_v,
                                              r_from.items_r[i],
                                              r_to.items_r[i])
                items_v.append(item_v)
            return r_from.newtuple(llops, r_to, items_v)
        return NotImplemented
 

class AbstractTupleIteratorRepr(IteratorRepr):

    def newiter(self, hop):
        v_tuple, = hop.inputargs(self.r_tuple)
        citerptr = hop.inputconst(Void, self.lowleveltype)
        return hop.gendirectcall(self.ll_tupleiter, citerptr, v_tuple)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
        hop.has_implicit_exception(StopIteration) # record that we know about it
        hop.exception_is_here()
        v = hop.gendirectcall(self.ll_tuplenext, v_iter)
        return hop.llops.convertvar(v, self.r_tuple.items_r[0], self.r_tuple.external_items_r[0])

