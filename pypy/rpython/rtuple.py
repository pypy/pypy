import operator
from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.rmodel import IteratorRepr
from pypy.rpython.rmodel import externalvsinternal
from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.lltypesystem.lltype import Void, Signed, Bool
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable

class __extend__(annmodel.SomeTuple):
    def rtyper_makerepr(self, rtyper):
        repr_class = rtyper.type_system.rtuple.TupleRepr
        return repr_class(rtyper, [rtyper.getrepr(s_item) for s_item in self.items])
    
    def rtyper_makekey_ex(self, rtyper):
        keys = [rtyper.makekey(s_item) for s_item in self.items]
        return tuple([self.__class__]+keys)


_gen_eq_function_cache = {}
_gen_cmp_function_cache = {}
_gen_hash_function_cache = {}
_gen_str_function_cache = {}

def gen_eq_function(items_r):
    eq_funcs = [r_item.get_ll_eq_function() or operator.eq for r_item in items_r]
    key = tuple(eq_funcs)
    try:
        return _gen_eq_function_cache[key]
    except KeyError:
        autounrolling_funclist = unrolling_iterable(enumerate(eq_funcs))

        def ll_eq(t1, t2):
            equal_so_far = True
            for i, eqfn in autounrolling_funclist:
                if not equal_so_far:
                    return False
                attrname = 'item%d' % i
                item1 = getattr(t1, attrname)
                item2 = getattr(t2, attrname)
                equal_so_far = eqfn(item1, item2)
            return equal_so_far

        _gen_eq_function_cache[key] = ll_eq
        return ll_eq
import os
def gen_cmp_function(items_r, op_funcs, eq_funcs, strict):
    """generates <= and >= comparison ll_op for tuples
    cmp_funcs is a tuple of (strict_comp, equality) functions
    works for != with strict==True
    """
    cmp_funcs = zip(op_funcs,eq_funcs)
    autounrolling_funclist = unrolling_iterable(enumerate(cmp_funcs))
    key = tuple(cmp_funcs), strict
    try:
        return _gen_cmp_function_cache[key]
    except KeyError:
        def ll_cmp(t1, t2):
            cmp_res = True
            for i, (cmpfn, eqfn) in autounrolling_funclist:
                attrname = 'item%d' % i
                item1 = getattr(t1, attrname)
                item2 = getattr(t2, attrname)
                cmp_res = cmpfn(item1, item2)
                if cmp_res:
                    # a strict compare is true we shortcut
                    return True
                eq_res = eqfn(item1, item2)
                if not eq_res:
                    # not strict and not equal we fail
                    return False
            # Everything's equal here
            if strict:
                return False
            else:
                return True
        _gen_cmp_function_cache[key] = ll_cmp
        return ll_cmp

def gen_gt_function(items_r, strict):
    gt_funcs = [r_item.get_ll_gt_function() or operator.gt for r_item in items_r]
    eq_funcs = [r_item.get_ll_eq_function() or operator.eq for r_item in items_r]
    return gen_cmp_function( items_r, gt_funcs, eq_funcs, strict )

def gen_lt_function(items_r, strict):
    lt_funcs = [r_item.get_ll_lt_function() or operator.lt for r_item in items_r]
    eq_funcs = [r_item.get_ll_eq_function() or operator.eq for r_item in items_r]
    return gen_cmp_function( items_r, lt_funcs, eq_funcs, strict )

def gen_hash_function(items_r):
    # based on CPython
    hash_funcs = [r_item.get_ll_hash_function() for r_item in items_r]
    key = tuple(hash_funcs)
    try:
        return _gen_hash_function_cache[key]
    except KeyError:
        autounrolling_funclist = unrolling_iterable(enumerate(hash_funcs))

        def ll_hash(t):
            retval = 0x345678
            mult = 1000003
            for i, hash_func in autounrolling_funclist:
                attrname = 'item%d' % i
                item = getattr(t, attrname)
                retval = intmask((retval ^ hash_func(item)) * intmask(mult))
                mult = mult + 82520 + 2*len(items_r)
            return retval

        _gen_hash_function_cache[key] = ll_hash
        return ll_hash

def gen_str_function(tuplerepr):
    items_r = tuplerepr.items_r
    str_funcs = [r_item.ll_str for r_item in items_r]
    key = tuplerepr.rstr_ll, tuple(str_funcs)
    try:
        return _gen_str_function_cache[key]
    except KeyError:
        autounrolling_funclist = unrolling_iterable(enumerate(str_funcs))

        constant = tuplerepr.rstr_ll.ll_constant
        start    = tuplerepr.rstr_ll.ll_build_start
        push     = tuplerepr.rstr_ll.ll_build_push
        finish   = tuplerepr.rstr_ll.ll_build_finish
        length = len(items_r)

        def ll_str(t):
            if length == 0:
                return constant("()")
            buf = start(2 * length + 1)
            push(buf, constant("("), 0)
            for i, str_func in autounrolling_funclist:
                attrname = 'item%d' % i
                item = getattr(t, attrname)
                if i > 0:
                    push(buf, constant(", "), 2 * i)
                push(buf, str_func(item), 2 * i + 1)
            if length == 1:
                push(buf, constant(",)"), 2 * length)
            else:
                push(buf, constant(")"), 2 * length)
            return finish(buf)

        _gen_str_function_cache[key] = ll_str
        return ll_str


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

    def getitem(self, llops, v_tuple, index):
        """Generate the operations to get the index'th item of v_tuple,
        in the external repr external_items_r[index]."""
        v = self.getitem_internal(llops, v_tuple, index)
        r_item = self.items_r[index]
        r_external_item = self.external_items_r[index]
        return llops.convertvar(v, r_item, r_external_item)

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
                if r.lowleveltype is not Void:
                    setattr(p, name, r.convert_const(obj))
            return p

    def compact_repr(self):
        return "TupleR %s" % ' '.join([llt._short_name() for llt in self.lltypes])

    def rtype_len(self, hop):
        return hop.inputconst(Signed, len(self.items_r))

    def get_ll_eq_function(self):
        return gen_eq_function(self.items_r)

    def get_ll_ge_function(self):
        return gen_gt_function(self.items_r, False)

    def get_ll_gt_function(self):
        return gen_gt_function(self.items_r, True)

    def get_ll_le_function(self):
        return gen_lt_function(self.items_r, False)

    def get_ll_lt_function(self):
        return gen_lt_function(self.items_r, True)

    def get_ll_hash_function(self):
        return gen_hash_function(self.items_r)

    ll_str = property(gen_str_function)

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
        return r_tup.getitem(hop.llops, v_tuple, index)

class __extend__(pairtype(AbstractTupleRepr, AbstractSliceRepr)):

    def rtype_getitem((r_tup, r_slice), hop):
        v_tup = hop.inputarg(r_tup, arg=0)
        s_slice = hop.args_s[1]
        start, stop, step = s_slice.constant_indices()
        indices = range(len(r_tup.items_r))[start:stop:step]
        assert len(indices) == len(hop.r_result.items_r)

        items_v = [r_tup.getitem_internal(hop.llops, v_tup, i)
                   for i in indices]
        return hop.r_result.newtuple(hop.llops, hop.r_result, items_v)

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
            vlist.append(r_tup1.getitem_internal(hop.llops, v_tuple1, i))
        for i in range(len(r_tup2.items_r)):
            vlist.append(r_tup2.getitem_internal(hop.llops, v_tuple2, i))
        return r_tup1.newtuple_cached(hop, vlist)
    rtype_inplace_add = rtype_add

    def rtype_eq((r_tup1, r_tup2), hop):
        # XXX assumes that r_tup2 is convertible to r_tup1
        v_tuple1, v_tuple2 = hop.inputargs(r_tup1, r_tup1)
        ll_eq = r_tup1.get_ll_eq_function()
        return hop.gendirectcall(ll_eq, v_tuple1, v_tuple2)

    def rtype_ge((r_tup1, r_tup2), hop):
        # XXX assumes that r_tup2 is convertible to r_tup1
        v_tuple1, v_tuple2 = hop.inputargs(r_tup1, r_tup1)
        ll_ge = r_tup1.get_ll_ge_function()
        return hop.gendirectcall(ll_ge, v_tuple1, v_tuple2)

    def rtype_gt((r_tup1, r_tup2), hop):
        # XXX assumes that r_tup2 is convertible to r_tup1
        v_tuple1, v_tuple2 = hop.inputargs(r_tup1, r_tup1)
        ll_gt = r_tup1.get_ll_gt_function()
        return hop.gendirectcall(ll_gt, v_tuple1, v_tuple2)

    def rtype_le((r_tup1, r_tup2), hop):
        # XXX assumes that r_tup2 is convertible to r_tup1
        v_tuple1, v_tuple2 = hop.inputargs(r_tup1, r_tup1)
        ll_le = r_tup1.get_ll_le_function()
        return hop.gendirectcall(ll_le, v_tuple1, v_tuple2)

    def rtype_lt((r_tup1, r_tup2), hop):
        # XXX assumes that r_tup2 is convertible to r_tup1
        v_tuple1, v_tuple2 = hop.inputargs(r_tup1, r_tup1)
        ll_lt = r_tup1.get_ll_lt_function()
        return hop.gendirectcall(ll_lt, v_tuple1, v_tuple2)

    def rtype_ne(tup1tup2, hop):
        v_res = tup1tup2.rtype_eq(hop)
        return hop.genop('bool_not', [v_res], resulttype=Bool)

    def convert_from_to((r_from, r_to), v, llops):
        if len(r_from.items_r) == len(r_to.items_r):
            if r_from.lowleveltype == r_to.lowleveltype:
                return v
            n = len(r_from.items_r)
            items_v = []
            for i in range(n):
                item_v = r_from.getitem_internal(llops, v, i)
                item_v = llops.convertvar(item_v,
                                              r_from.items_r[i],
                                              r_to.items_r[i])
                items_v.append(item_v)
            return r_from.newtuple(llops, r_to, items_v)
        return NotImplemented

    def rtype_is_((robj1, robj2), hop):
        raise TyperError("cannot compare tuples with 'is'")


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

