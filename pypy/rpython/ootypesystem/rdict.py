from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.rdict import AbstractDictRepr, AbstractDictIteratorRepr,\
     rtype_newdict, dum_variant, dum_keys, dum_values, dum_items
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rlist import ll_newlist
from pypy.rpython.ootypesystem.riterable import iterator_type
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython.objectmodel import hlinvoke
from pypy.rpython import robject
from pypy.rpython import objectmodel
from pypy.rpython import rmodel


class DictRepr(AbstractDictRepr):
    def __init__(self, rtyper, key_repr, value_repr, dictkey, dictvalue,
                 custom_eq_hash=None):
        self.rtyper = rtyper
        self.custom_eq_hash = custom_eq_hash is not None

        already_computed = True
        if not isinstance(key_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(key_repr)
            self._key_repr_computer = key_repr
            already_computed = False
        else:
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if not isinstance(value_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(value_repr)
            self._value_repr_computer = value_repr
            already_computed = False
        else:
            self.external_value_repr, self.value_repr = self.pickrepr(value_repr)

        if already_computed:
            self.DICT = ootype.Dict(key_repr.lowleveltype, value_repr.lowleveltype)
        else:
            self.DICT = ootype.ForwardReference()
        self.lowleveltype = self.DICT

        self.dictkey = dictkey
        self.dictvalue = dictvalue
        self.dict_cache = {}
        self._custom_eq_hash_repr = custom_eq_hash
        # setup() needs to be called to finish this initialization

    def _setup_repr(self):
        if 'key_repr' not in self.__dict__:
            key_repr = self._key_repr_computer()
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if 'value_repr' not in self.__dict__:
            self.external_value_repr, self.value_repr = self.pickrepr(self._value_repr_computer())
            
        if isinstance(self.DICT, ootype.ForwardReference):
            self.lowleveltype.become(ootype.Dict(self.key_repr.lowleveltype,
                                                 self.value_repr.lowleveltype))

    def send_message(self, hop, message, can_raise=False, v_args=None):
        if v_args is None:
            v_args = hop.inputargs(self, *hop.args_r[1:])
        c_name = hop.inputconst(ootype.Void, message)
        if can_raise:
            hop.exception_is_here()
        return hop.genop("oosend", [c_name] + v_args,
                resulttype=hop.r_result.lowleveltype)

    def make_iterator_repr(self, *variant):
        return DictIteratorRepr(self, *variant)

    def rtype_len(self, hop):
        v_dict, = hop.inputargs(self)
        return self.send_message(hop, 'll_length')

    def rtype_is_true(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_dict_is_true, v_dict)

    def rtype_method_get(self, hop):
        v_dict, v_key, v_default = hop.inputargs(self, self.key_repr,
                                                 self.value_repr)
        hop.exception_cannot_occur()
        v_res = hop.gendirectcall(ll_dict_get, v_dict, v_key, v_default)
        return self.recast_value(hop.llops, v_res)

    def rtype_method_setdefault(self, hop):
        v_dict, v_key, v_default = hop.inputargs(self, self.key_repr,
                                                 self.value_repr)
        hop.exception_cannot_occur()
        v_res = hop.gendirectcall(ll_dict_setdefault, v_dict, v_key, v_default)
        return self.recast_value(hop.llops, v_res)

    def rtype_method_keys(self, hop):
        hop.exception_cannot_occur()        
        return self.send_message(hop, 'll_keys')

    def rtype_method_values(self, hop):
        return self._rtype_method_vi(hop, dum_values)

    def rtype_method_items(self, hop):
        return self._rtype_method_vi(hop, dum_items)

    def _rtype_method_vi(self, hop, spec):
        v_dict, = hop.inputargs(self)
        r_list = hop.r_result
        cLIST = hop.inputconst(ootype.Void, r_list.lowleveltype)
        c_func = hop.inputconst(ootype.Void, spec)        
        return hop.gendirectcall(ll_dict_values_items, v_dict, cLIST, c_func)

    def rtype_method_iterkeys(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "keys").newiter(hop)

    def rtype_method_itervalues(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "values").newiter(hop)

    def rtype_method_iteritems(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "items").newiter(hop)


class __extend__(pairtype(DictRepr, rmodel.Repr)): 

    def rtype_getitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        if not r_dict.custom_eq_hash: # TODO: why only in this case?
            hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        v_res = hop.gendirectcall(ll_dict_getitem, v_dict, v_key)
        return r_dict.recast_value(hop.llops, v_res)

    def rtype_delitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        if not r_dict.custom_eq_hash: # TODO: why only in this case?
            hop.has_implicit_exception(KeyError)   # record that we know about it        
        hop.exception_is_here()
        return hop.gendirectcall(ll_dict_delitem, v_dict, v_key)

    def rtype_setitem((r_dict, r_key), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, r_dict.key_repr, r_dict.value_repr)
##        if r_dict.custom_eq_hash:
##            hop.exception_is_here()
##        else:
##            hop.exception_cannot_occur()
        hop.exception_is_here()
        return r_dict.send_message(hop, 'll_set', can_raise=True)

    def rtype_contains((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        return r_dict.send_message(hop, 'll_contains')



def ll_newdict(DICT):
    return ootype.new(DICT)

def ll_dict_is_true(d):
    # check if a dict is True, allowing for None
    return bool(d) and d.ll_length() != 0

def ll_dict_getitem(d, key):
    # TODO: this is inefficient because it does two lookups
    if d.ll_contains(key):
        return d.ll_get(key)
    else:
        raise KeyError

def ll_dict_delitem(d, key):
    if not d.ll_remove(key):
        raise KeyError

def ll_dict_get(d, key, default):
    # TODO: this is inefficient because it does two lookups
    if d.ll_contains(key):
        return d.ll_get(key)
    else:
        return default

def ll_dict_setdefault(d, key, default):
    try:
        return ll_dict_getitem(d, key)
    except KeyError:
        d.ll_set(key, default)
        return default

def ll_dict_values_items(d, LIST, func):
    keys = d.ll_keys()
    length = keys.ll_length()
    result = ll_newlist(LIST, length)
    i = 0
    while i < length:
        key = keys.ll_getitem_fast(i)
        value = d.ll_get(key)
        if func is dum_items:
            r = ootype.new(LIST._ITEMTYPE)
            r.item0 = key   # TODO: do we need casting?
            r.item1 = value
            result.ll_setitem_fast(i, r)
        elif func is dum_values:
            result.ll_setitem_fast(i, value)

        i += 1
    return result


# ____________________________________________________________
#
#  Iteration.

class DictIteratorRepr(AbstractDictIteratorRepr):

    def __init__(self, r_dict, variant="keys"):
        self.r_dict = r_dict
        self.variant = variant
        self.lowleveltype = iterator_type(r_dict, r_dict.key_repr)
        self.ll_dictiter = ll_dictiter
        self.ll_dictnext = ll_dictnext

def ll_dictiter(ITER, d):
    iter = ootype.new(ITER)
    iter.iterable = d
    iter.index = 0
    return iter

# TODO: this is very inefficient for values and items because it does
# a dict lookup at every iteration. Need to be refactored.
def ll_dictnext(iter, func, RETURNTYPE):
    d = iter.iterable
    keys = d.ll_keys()
    index = iter.index
    if index >= keys.ll_length():
        raise StopIteration
    iter.index = index + 1

    key = keys.ll_getitem_fast(index)
    if func is dum_keys:
        return key
    elif func is dum_values:
        return d.ll_get(key)
    elif func is dum_items:
        res = ootype.new(RETURNTYPE)
        res.item0 = key
        res.item1 = d.ll_get(key)
        return res
        
