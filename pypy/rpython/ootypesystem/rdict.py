from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.rdict import AbstractDictRepr, AbstractDictIteratorRepr,\
     rtype_newdict, dum_variant, dum_keys, dum_values, dum_items
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rlist import ll_newlist
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
            self.DICT = ootype.Dict()
        self.lowleveltype = self.DICT

        self.dictkey = dictkey
        self.dictvalue = dictvalue
        self.dict_cache = {}
        self._custom_eq_hash_repr = custom_eq_hash
        # setup() needs to be called to finish this initialization

    def _externalvsinternal(self, rtyper, item_repr):
        return item_repr, item_repr

    def _setup_repr(self):
        if 'key_repr' not in self.__dict__:
            key_repr = self._key_repr_computer()
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if 'value_repr' not in self.__dict__:
            self.external_value_repr, self.value_repr = self.pickrepr(self._value_repr_computer())
            
        if not ootype.hasDictTypes(self.DICT):
            ootype.setDictTypes(self.DICT, self.key_repr.lowleveltype,
                    self.value_repr.lowleveltype)

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
        hop.exception_cannot_occur()
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

    def rtype_method_copy(self, hop):
        v_dict, = hop.inputargs(self)
        cDICT = hop.inputconst(ootype.Void, self.lowleveltype)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_dict_copy, cDICT, v_dict)

    def rtype_method_update(self, hop):
        v_dict1, v_dict2 = hop.inputargs(self, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_dict_update, v_dict1, v_dict2)

    def rtype_method_keys(self, hop):
        return self._rtype_method_kvi(hop, dum_keys)

    def rtype_method_values(self, hop):
        return self._rtype_method_kvi(hop, dum_values)

    def rtype_method_items(self, hop):
        return self._rtype_method_kvi(hop, dum_items)

    def _rtype_method_kvi(self, hop, spec):
        v_dict, = hop.inputargs(self)
        r_list = hop.r_result
        cLIST = hop.inputconst(ootype.Void, r_list.lowleveltype)
        c_func = hop.inputconst(ootype.Void, spec)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_dict_kvi, v_dict, cLIST, c_func)

    def rtype_method_iterkeys(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "keys").newiter(hop)

    def rtype_method_itervalues(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "values").newiter(hop)

    def rtype_method_iteritems(self, hop):
        hop.exception_cannot_occur()
        return DictIteratorRepr(self, "items").newiter(hop)

    def rtype_method_clear(self, hop):
        v_dict, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return self.send_message(hop, 'll_clear')

    def convert_const(self, dictobj):
        if dictobj is None:
            return self.DICT._defl()
        if not isinstance(dictobj, dict):
            raise TyperError("expected a dict: %r" % (dictobj,))
        try:
            key = Constant(dictobj)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            l_dict = ll_newdict(self.DICT)
            self.dict_cache[key] = l_dict 
            r_key = self.key_repr
            r_value = self.value_repr

            # XXX need handling of r_dict here
            for dictkey, dictvalue in dictobj.items():
                llkey = r_key.convert_const(dictkey)
                llvalue = r_value.convert_const(dictvalue)
                l_dict.ll_set(llkey, llvalue)
            return l_dict

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
##        hop.exception_is_here()
        return r_dict.send_message(hop, 'll_set', can_raise=True)

    def rtype_contains((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        hop.exception_cannot_occur()
        return r_dict.send_message(hop, 'll_contains')


def rtype_r_dict(hop):
    pass # TODO

def ll_newdict(DICT):
    return ootype.new(DICT)

def ll_dict_is_true(d):
    # check if a dict is True, allowing for None
    return bool(d) and d.ll_length() != 0

def ll_dict_copy(DICT, d):
    res = ootype.new(DICT)
    ll_dict_update(res, d)
    return res

def ll_dict_update(d1, d2):
    it = d2.ll_get_items_iterator()
    while it.ll_go_next():
        key = it.ll_current_key()
        value = it.ll_current_value()
        d1.ll_set(key, value)


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

def ll_dict_kvi(d, LIST, func):
    length = d.ll_length()
    result = ll_newlist(LIST, length)
    it = d.ll_get_items_iterator()
    i = 0
    while it.ll_go_next():
        if func is dum_keys:
            result.ll_setitem_fast(i, it.ll_current_key())
        elif func is dum_values:
            result.ll_setitem_fast(i, it.ll_current_value())
        if func is dum_items:
            r = ootype.new(LIST._ITEMTYPE)
            r.item0 = it.ll_current_key()   # TODO: do we need casting?
            r.item1 = it.ll_current_value()
            result.ll_setitem_fast(i, r)
        i += 1
    #assert i == length
    return result


# ____________________________________________________________
#
#  Iteration.

class DictIteratorRepr(AbstractDictIteratorRepr):

    def __init__(self, r_dict, variant="keys"):
        self.r_dict = r_dict
        self.variant = variant
        self.lowleveltype = self._get_type()
        self.ll_dictiter = ll_dictiter
        self.ll_dictnext = ll_dictnext

    def _get_type(self):
        KEYTYPE = self.r_dict.key_repr.lowleveltype
        VALUETYPE = self.r_dict.value_repr.lowleveltype
        ITER = ootype.DictItemsIterator(KEYTYPE, VALUETYPE)
        return ootype.Record({"iterator": ITER})


def ll_dictiter(ITER, d):
    iter = ootype.new(ITER)
    iter.iterator = d.ll_get_items_iterator()
    return iter

def ll_dictnext(iter, func, RETURNTYPE):
    it = iter.iterator
    if not it.ll_go_next():
        raise StopIteration

    if func is dum_keys:
        return it.ll_current_key()
    elif func is dum_values:
        return it.ll_current_value()
    elif func is dum_items:
        res = ootype.new(RETURNTYPE)
        res.item0 = it.ll_current_key()
        res.item1 = it.ll_current_value()
        return res

