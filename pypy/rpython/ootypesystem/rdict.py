from pypy.rpython.error import TyperError
from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.rdict import AbstractDictRepr, AbstractDictIteratorRepr,\
     rtype_newdict
from pypy.rpython.rpbc import MethodOfFrozenPBCRepr,\
     AbstractFunctionsPBCRepr, AbstractMethodsPBCRepr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rlist import ll_newlist
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.objectmodel import hlinvoke
from pypy.rpython import robject
from pypy.rlib import objectmodel
from pypy.rpython import rmodel
from pypy.rpython import llinterp


class DictRepr(AbstractDictRepr):
    def __init__(self, rtyper, key_repr, value_repr, dictkey, dictvalue,
                 custom_eq_hash=None, force_non_null=False):
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

        if self.custom_eq_hash:
            Dict = ootype.CustomDict
        else:
            Dict = ootype.Dict

        if already_computed:
            self.DICT = Dict(key_repr.lowleveltype, value_repr.lowleveltype)
        else:
            self.DICT = Dict()
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

        if self.custom_eq_hash:
            self.r_rdict_eqfn, self.r_rdict_hashfn = self._custom_eq_hash_repr()

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
        if self.custom_eq_hash:
            c_copy = hop.inputconst(ootype.Void, 'll_copy')
            return hop.genop('oosend', [c_copy, v_dict], resulttype=hop.r_result.lowleveltype)
        else:
            return hop.gendirectcall(ll_dict_copy, cDICT, v_dict)

    def rtype_method_update(self, hop):
        v_dict1, v_dict2 = hop.inputargs(self, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_dict_update, v_dict1, v_dict2)

    def rtype_method_keys(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_keys)

    def rtype_method_values(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_values)

    def rtype_method_items(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_items)

    def _rtype_method_kvi(self, hop, ll_func):
        v_dict, = hop.inputargs(self)
        r_list = hop.r_result
        cLIST = hop.inputconst(ootype.Void, r_list.lowleveltype)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_func, cLIST, v_dict)

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

    def rtype_method_popitem(self, hop):
        v_dict, = hop.inputargs(self)
        r_tuple = hop.r_result
        cTUPLE = hop.inputconst(ootype.Void, r_tuple.lowleveltype)
        hop.exception_is_here()
        return hop.gendirectcall(ll_popitem, cTUPLE, v_dict)

    def __get_func(self, interp, r_func, fn, TYPE):
        if isinstance(r_func, MethodOfFrozenPBCRepr):
            obj = r_func.r_im_self.convert_const(fn.im_self)
            r_func, nimplicitarg = r_func.get_r_implfunc()
        else:
            obj = None
        callable = r_func.get_unique_llfn().value
        func_name, interp_fn = llinterp.wrap_callable(interp, callable, obj, None)
        return ootype.static_meth(TYPE, func_name, _callable=interp_fn)
        

    def convert_const(self, dictobj):
        if dictobj is None:
            return self.DICT._defl()
        if not isinstance(dictobj, dict) and not isinstance(dictobj, objectmodel.r_dict):
            raise TyperError("expected a dict: %r" % (dictobj,))
        try:
            key = Constant(dictobj)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            l_dict = ll_newdict(self.DICT)
            if self.custom_eq_hash:
                interp = llinterp.LLInterpreter(self.rtyper)
                EQ_FUNC = ootype.StaticMethod([self.DICT._KEYTYPE, self.DICT._KEYTYPE], ootype.Bool)
                sm_eq = self.__get_func(interp, self.r_rdict_eqfn, dictobj.key_eq, EQ_FUNC)
                HASH_FUNC = ootype.StaticMethod([self.DICT._KEYTYPE], ootype.Signed)
                sm_hash = self.__get_func(interp, self.r_rdict_hashfn, dictobj.key_hash, HASH_FUNC)
                l_dict.ll_set_functions(sm_eq, sm_hash)

            self.dict_cache[key] = l_dict 
            r_key = self.key_repr
            r_value = self.value_repr

            if self.custom_eq_hash:
                for dictkeycont, dictvalue in dictobj._dict.items():
                    llkey = r_key.convert_const(dictkeycont.key)
                    llvalue = r_value.convert_const(dictvalue)
                    llhash = dictkeycont.hash
                    l_dictkeycont = objectmodel._r_dictkey_with_hash(l_dict._dict, llkey, llhash)
                    l_dict._dict._dict[l_dictkeycont] = llvalue
            else:
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
        vlist = hop.inputargs(r_dict, r_dict.key_repr, r_dict.value_repr)
        if not r_dict.custom_eq_hash:
            hop.exception_cannot_occur() # XXX: maybe should we move this inside send_message?
        return r_dict.send_message(hop, 'll_set', can_raise=r_dict.custom_eq_hash, v_args=vlist)

    def rtype_contains((r_dict, r_key), hop):
        vlist = hop.inputargs(r_dict, r_dict.key_repr)
        hop.exception_is_here()
        return r_dict.send_message(hop, 'll_contains', v_args=vlist)

def dum_ignore_me(): pass

def _get_call_args(hop, r_func, arg, params_annotation):
    if isinstance(r_func, AbstractFunctionsPBCRepr):
        fn = r_func.get_unique_llfn().value
        v_obj = hop.inputconst(ootype.Void, None)
        methodname = None
    elif isinstance(r_func, AbstractMethodsPBCRepr):
        fn = None
        v_obj = hop.inputarg(r_func, arg=arg)
        s_pbc_fn = hop.args_s[arg]
        methodname = r_func._get_method_name("simple_call", s_pbc_fn, params_annotation)
    elif isinstance(r_func, MethodOfFrozenPBCRepr):
        r_impl, nimplicitarg = r_func.get_r_implfunc()
        fn = r_impl.get_unique_llfn().value
        v_obj = hop.inputconst(ootype.Void, dum_ignore_me)
        methodname = None
    return fn, v_obj, methodname

def rtype_r_dict(hop, i_force_non_null=None):
    from pypy.rlib import jit

    r_dict = hop.r_result
    if not r_dict.custom_eq_hash:
        raise TyperError("r_dict() call does not return an r_dict instance")
    cDICT = hop.inputconst(ootype.Void, r_dict.DICT)
    hop.exception_cannot_occur()

    # the signature of oonewcustomdict is a bit complicated because we
    # can have three different ways to pass the equal (and hash)
    # callables:    
    #   1. pass a plain function: eqfn is a StaticMethod, v_eqobj
    #      and eq_method_name are None
    #   2. pass a bound method: eqfn is None, v_eqobj is the
    #      instance, eq_method_name is the name of the method,
    #   3. pass a method of a frozen PBC: eqfn is a StaticMethod, v_eqobj is a
    #      non-None Void value (to be ignored by all the backends except the
    #      llinterp), eq_method_name is None

    s_key = r_dict.dictkey.s_value
    eqfn, v_eqobj, eq_method_name =\
             _get_call_args(hop, r_dict.r_rdict_eqfn, 0, [s_key, s_key])
    hashfn, v_hashobj, hash_method_name =\
               _get_call_args(hop, r_dict.r_rdict_hashfn, 1, [s_key])

    @jit.dont_look_inside
    def ll_newcustomdict(DICT, v_eqobj, v_hashobj):
        from pypy.rpython.lltypesystem.lloperation import llop
        return llop.oonewcustomdict(DICT, DICT,
                                    eqfn, v_eqobj, eq_method_name,
                                    hashfn, v_hashobj, hash_method_name)
    ll_newcustomdict._dont_inline_ = True

    return hop.gendirectcall(ll_newcustomdict, cDICT, v_eqobj, v_hashobj)

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
    if d.ll_contains(key):
        return d.ll_get(key)
    else:
        raise KeyError

def ll_dict_delitem(d, key):
    if not d.ll_remove(key):
        raise KeyError

def ll_dict_get(d, key, default):
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

def _make_ll_keys_values_items(kind):
    def ll_dict_kvi(LIST, d):
        length = d.ll_length()
        result = LIST.ll_newlist(length)
        it = d.ll_get_items_iterator()
        i = 0
        while it.ll_go_next():
            if kind == 'keys':
                result.ll_setitem_fast(i, it.ll_current_key())
            elif kind == 'values':
                result.ll_setitem_fast(i, it.ll_current_value())
            elif kind == 'items':
                r = ootype.new(LIST.ITEM)
                r.item0 = it.ll_current_key()   # TODO: do we need casting?
                r.item1 = it.ll_current_value()
                result.ll_setitem_fast(i, r)
            i += 1
        assert i == length
        return result
    ll_dict_kvi.oopspec = 'dict.%s(d)' % kind
    return ll_dict_kvi

ll_dict_keys   = _make_ll_keys_values_items('keys')
ll_dict_values = _make_ll_keys_values_items('values')
ll_dict_items  = _make_ll_keys_values_items('items')

def ll_popitem(ELEM, d):
    it = d.ll_get_items_iterator()
    if it.ll_go_next():
        res = ootype.new(ELEM)
        key = res.item0 = it.ll_current_key()
        res.item1 = it.ll_current_value()
        d.ll_remove(key)
        return res
    raise KeyError

# ____________________________________________________________
#
#  Iteration.

class DictIteratorRepr(AbstractDictIteratorRepr):

    def __init__(self, r_dict, variant="keys"):
        self.r_dict = r_dict
        self.variant = variant
        self.lowleveltype = self._get_type()
        self.ll_dictiter = ll_dictiter
        self.ll_dictnext = ll_dictnext_group[variant]

    def _get_type(self):
        KEYTYPE = self.r_dict.key_repr.lowleveltype
        VALUETYPE = self.r_dict.value_repr.lowleveltype
        ITER = ootype.DictItemsIterator(KEYTYPE, VALUETYPE)
        return ootype.Record({"iterator": ITER})

def ll_dictiter(ITER, d):
    iter = ootype.new(ITER)
    iter.iterator = d.ll_get_items_iterator()
    return iter

def _make_ll_dictnext(kind):
    # make three versions of the following function: keys, values, items
    def ll_dictnext(RETURNTYPE, iter):
        # note that RETURNTYPE is None for keys and values
        it = iter.iterator
        if not it.ll_go_next():
            raise StopIteration

        if kind == 'keys':
            return it.ll_current_key()
        elif kind == 'values':
            return it.ll_current_value()
        elif kind == 'items':
            res = ootype.new(RETURNTYPE)
            res.item0 = it.ll_current_key()
            res.item1 = it.ll_current_value()
            return res
    ll_dictnext.oopspec = 'dictiter.next%s(iter)' % kind
    return ll_dictnext

ll_dictnext_group = {'keys'  : _make_ll_dictnext('keys'),
                     'values': _make_ll_dictnext('values'),
                     'items' : _make_ll_dictnext('items')}
