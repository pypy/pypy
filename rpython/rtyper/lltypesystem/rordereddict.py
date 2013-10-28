import sys
from rpython.tool.pairtype import pairtype
from rpython.flowspace.model import Constant
from rpython.rtyper.rdict import AbstractDictRepr, AbstractDictIteratorRepr
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib import objectmodel, jit, rgc
from rpython.rlib.debug import ll_assert
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rtyper import rmodel
from rpython.rtyper.error import TyperError
from rpython.rtyper.annlowlevel import llhelper


# ____________________________________________________________
#
#  generic implementation of RPython dictionary, with parametric DICTKEY and
#  DICTVALUE types. The basic implementation is a sparse array of indexes
#  plus a dense array of structs that contain keys and values. struct looks
#  like that:
#
#
#    struct dictentry {
#        DICTKEY key;
#        DICTVALUE value;
#        long f_hash;        # (optional) key hash, if hard to recompute
#        bool f_valid;      # (optional) the entry is filled
#    }
#
#    struct dicttable {
#        int num_items;
#        int num_used_items;
#        int resize_counter;
#        {byte, short, int, long} *indexes;
#        dictentry *entries;
#        lookup_function_no; # one of the four possible functions for different
#                         # size dicts
#        (Function DICTKEY, DICTKEY -> bool) *fnkeyeq;
#        (Function DICTKEY -> int) *fnkeyhash;
#    }
#
#

def ll_call_lookup_function(d, key, hash, flag):
    DICT = lltype.typeOf(d).TO
    fun = d.lookup_function_no
    if fun == FUNC_BYTE:
        return DICT.lookup_family.byte_lookup_function(d, key, hash, flag)
    elif fun == FUNC_SHORT:
        return DICT.lookup_family.short_lookup_function(d, key, hash, flag)
    elif IS_64BIT and fun == FUNC_INT:
        return DICT.lookup_family.int_lookup_function(d, key, hash, flag)
    elif fun == FUNC_LONG:
        return DICT.lookup_family.long_lookup_function(d, key, hash, flag)
    assert False

def get_ll_dict(DICTKEY, DICTVALUE, get_custom_eq_hash=None, DICT=None,
                ll_fasthash_function=None, ll_hash_function=None,
                ll_eq_function=None, method_cache={},
                dummykeyobj=None, dummyvalueobj=None, rtyper=None,
                setup_lookup_funcs=True):
    # get the actual DICT type. if DICT is None, it's created, otherwise
    # forward reference is becoming DICT
    if DICT is None:
        DICT = lltype.GcForwardReference()
    # compute the shape of the DICTENTRY structure
    entryfields = []
    entrymeths = {
        'allocate': lltype.typeMethod(_ll_malloc_entries),
        'delete': _ll_free_entries,
        'must_clear_key':   (isinstance(DICTKEY, lltype.Ptr)
                             and DICTKEY._needsgc()),
        'must_clear_value': (isinstance(DICTVALUE, lltype.Ptr)
                             and DICTVALUE._needsgc()),
        }

    # * the key
    entryfields.append(("key", DICTKEY))

    # * the state of the entry - trying to encode it as dummy objects
    if dummykeyobj:
        # all the state can be encoded in the key
        entrymeths['dummy_obj'] = dummykeyobj
        entrymeths['valid'] = ll_valid_from_key
        entrymeths['mark_deleted'] = ll_mark_deleted_in_key
        # the key is overwritten by 'dummy' when the entry is deleted
        entrymeths['must_clear_key'] = False

    elif dummyvalueobj:
        # all the state can be encoded in the value
        entrymeths['dummy_obj'] = dummyvalueobj
        entrymeths['valid'] = ll_valid_from_value
        entrymeths['mark_deleted'] = ll_mark_deleted_in_value
        # value is overwritten by 'dummy' when entry is deleted
        entrymeths['must_clear_value'] = False

    else:
        # we need a flag to know if the entry was ever used
        entryfields.append(("f_valid", lltype.Bool))
        entrymeths['valid'] = ll_valid_from_flag
        entrymeths['mark_deleted'] = ll_mark_deleted_in_flag

    # * the value
    entryfields.append(("value", DICTVALUE))

    if ll_fasthash_function is None:
        entryfields.append(("f_hash", lltype.Signed))
        entrymeths['hash'] = ll_hash_from_cache
    else:
        entrymeths['hash'] = ll_hash_recomputed
        entrymeths['fasthashfn'] = ll_fasthash_function

    # Build the lltype data structures
    DICTENTRY = lltype.Struct("dictentry", *entryfields)
    DICTENTRYARRAY = lltype.GcArray(DICTENTRY,
                                    adtmeths=entrymeths)
    fields =          [ ("num_items", lltype.Signed),
                        ("num_used_items", lltype.Signed),
                        ("resize_counter", lltype.Signed),
                        ("indexes", llmemory.GCREF),
                        ("lookup_function_no", lltype.Signed),
                        ("entries", lltype.Ptr(DICTENTRYARRAY)) ]
    if get_custom_eq_hash is not None:
        r_rdict_eqfn, r_rdict_hashfn = get_custom_eq_hash()
        fields.extend([ ("fnkeyeq", r_rdict_eqfn.lowleveltype),
                        ("fnkeyhash", r_rdict_hashfn.lowleveltype) ])
        adtmeths = {
            'keyhash':        ll_keyhash_custom,
            'keyeq':          ll_keyeq_custom,
            'r_rdict_eqfn':   r_rdict_eqfn,
            'r_rdict_hashfn': r_rdict_hashfn,
            'paranoia':       True,
            }
    else:
        # figure out which functions must be used to hash and compare
        ll_keyhash = ll_hash_function
        ll_keyeq = ll_eq_function
        ll_keyhash = lltype.staticAdtMethod(ll_keyhash)
        if ll_keyeq is not None:
            ll_keyeq = lltype.staticAdtMethod(ll_keyeq)
        adtmeths = {
            'keyhash':  ll_keyhash,
            'keyeq':    ll_keyeq,
            'paranoia': False,
            }
    adtmeths['KEY']   = DICTKEY
    adtmeths['VALUE'] = DICTVALUE
    adtmeths['lookup_function'] = lltype.staticAdtMethod(ll_call_lookup_function)
    adtmeths['allocate'] = lltype.typeMethod(_ll_malloc_dict)

    family = LookupFamily()
    adtmeths['lookup_family'] = family

    DICT.become(lltype.GcStruct("dicttable", adtmeths=adtmeths,
                                *fields))

    family.empty_array = DICTENTRYARRAY.allocate(0)
    if setup_lookup_funcs:
        _setup_lookup_funcs(DICT, rtyper, family)
    return DICT

def _setup_lookup_funcs(DICT, rtyper, family):
    DICTKEY = DICT.entries.TO.OF.key
    LOOKUP_FUNC = lltype.Ptr(lltype.FuncType([lltype.Ptr(DICT), DICTKEY,
                                              lltype.Signed, lltype.Signed],
                                              lltype.Signed))


    STORECLEAN_FUNC = lltype.Ptr(lltype.FuncType([lltype.Ptr(DICT),
                                                  lltype.Signed,
                                                  lltype.Signed],
                                                 lltype.Void))

    for name, T in [('byte', rffi.UCHAR),
                    ('short', rffi.USHORT),
                    ('int', rffi.UINT),
                    ('long', lltype.Unsigned)]:
        if name == 'int' and not IS_64BIT:
            continue
        lookupfn, storecleanfn = new_lookup_functions(LOOKUP_FUNC,
                                                      STORECLEAN_FUNC, T=T,
                                                      rtyper=rtyper)
        setattr(family, '%s_lookup_function' % name, lookupfn)
        setattr(family, '%s_insert_clean_function' % name, storecleanfn)

def llhelper_or_compile(rtyper, FUNCPTR, ll_func):
    # the check is for pseudo rtyper from tests
    if rtyper is None or not hasattr(rtyper, 'annotate_helper_fn'):
        return llhelper(FUNCPTR, ll_func)
    else:
        return rtyper.annotate_helper_fn(ll_func, FUNCPTR.TO.ARGS)

class LookupFamily:
    def _freeze_(self):
        return True


class DictRepr(AbstractDictRepr):

    def __init__(self, rtyper, key_repr, value_repr, dictkey, dictvalue,
                 custom_eq_hash=None):
        self.rtyper = rtyper
        self.finalized = False
        self.DICT = lltype.GcForwardReference()
        self.lowleveltype = lltype.Ptr(self.DICT)
        self.custom_eq_hash = custom_eq_hash is not None
        if not isinstance(key_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(key_repr)
            self._key_repr_computer = key_repr
        else:
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if not isinstance(value_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(value_repr)
            self._value_repr_computer = value_repr
        else:
            self.external_value_repr, self.value_repr = self.pickrepr(value_repr)
        self.dictkey = dictkey
        self.dictvalue = dictvalue
        self.dict_cache = {}
        self._custom_eq_hash_repr = custom_eq_hash
        # setup() needs to be called to finish this initialization

    def _externalvsinternal(self, rtyper, item_repr):
        return rmodel.externalvsinternal(self.rtyper, item_repr)

    def _setup_repr(self):
        if 'key_repr' not in self.__dict__:
            key_repr = self._key_repr_computer()
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if 'value_repr' not in self.__dict__:
            self.external_value_repr, self.value_repr = self.pickrepr(self._value_repr_computer())
        if isinstance(self.DICT, lltype.GcForwardReference):
            DICTKEY = self.key_repr.lowleveltype
            DICTVALUE = self.value_repr.lowleveltype
            # * we need an explicit flag if the key and the value is not
            #   able to store dummy values
            s_key   = self.dictkey.s_value
            s_value = self.dictvalue.s_value
            kwd = {}
            if self.custom_eq_hash:
                self.r_rdict_eqfn, self.r_rdict_hashfn = (
                    self._custom_eq_hash_repr())
                kwd['get_custom_eq_hash'] = self._custom_eq_hash_repr
            else:
                kwd['ll_hash_function'] = self.key_repr.get_ll_hash_function()
                kwd['ll_eq_function'] = self.key_repr.get_ll_eq_function()
                kwd['ll_fasthash_function'] = self.key_repr.get_ll_fasthash_function()
            kwd['dummykeyobj'] = self.key_repr.get_ll_dummyval_obj(self.rtyper,
                                                                   s_key)
            kwd['dummyvalueobj'] = self.value_repr.get_ll_dummyval_obj(
                self.rtyper, s_value)

            kwd['setup_lookup_funcs'] = False
            get_ll_dict(DICTKEY, DICTVALUE, DICT=self.DICT,
                        rtyper=self.rtyper, **kwd)

    def _setup_repr_final(self):
        if not self.finalized:
            family = self.lowleveltype.TO.lookup_family
            _setup_lookup_funcs(self.lowleveltype.TO, self.rtyper, family)
            self.finalized = True


    def convert_const(self, dictobj):
        from rpython.rtyper.lltypesystem import llmemory
        # get object from bound dict methods
        #dictobj = getattr(dictobj, '__self__', dictobj)
        if dictobj is None:
            return lltype.nullptr(self.DICT)
        if not isinstance(dictobj, (dict, objectmodel.r_dict)):
            raise TypeError("expected a dict: %r" % (dictobj,))
        try:
            key = Constant(dictobj)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            self.setup_final()
            l_dict = ll_newdict_size(self.DICT, len(dictobj))
            self.dict_cache[key] = l_dict
            r_key = self.key_repr
            if r_key.lowleveltype == llmemory.Address:
                raise TypeError("No prebuilt dicts of address keys")
            r_value = self.value_repr
            if isinstance(dictobj, objectmodel.r_dict):
                if self.r_rdict_eqfn.lowleveltype != lltype.Void:
                    l_fn = self.r_rdict_eqfn.convert_const(dictobj.key_eq)
                    l_dict.fnkeyeq = l_fn
                if self.r_rdict_hashfn.lowleveltype != lltype.Void:
                    l_fn = self.r_rdict_hashfn.convert_const(dictobj.key_hash)
                    l_dict.fnkeyhash = l_fn

                for dictkeycontainer, dictvalue in dictobj._dict.items():
                    llkey = r_key.convert_const(dictkeycontainer.key)
                    llvalue = r_value.convert_const(dictvalue)
                    _ll_dict_insertclean(l_dict, llkey, llvalue,
                                         dictkeycontainer.hash)
                return l_dict

            else:
                for dictkey, dictvalue in dictobj.items():
                    llkey = r_key.convert_const(dictkey)
                    llvalue = r_value.convert_const(dictvalue)
                    _ll_dict_insertclean(l_dict, llkey, llvalue,
                                         l_dict.keyhash(llkey))
                return l_dict

    def rtype_len(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_dict_len, v_dict)

    def rtype_bool(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_dict_bool, v_dict)

    def make_iterator_repr(self, *variant):
        return DictIteratorRepr(self, *variant)

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
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_dict_copy, v_dict)

    def rtype_method_update(self, hop):
        v_dic1, v_dic2 = hop.inputargs(self, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_dict_update, v_dic1, v_dic2)

    def _rtype_method_kvi(self, hop, ll_func):
        v_dic, = hop.inputargs(self)
        r_list = hop.r_result
        cLIST = hop.inputconst(lltype.Void, r_list.lowleveltype.TO)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_func, cLIST, v_dic)

    def rtype_method_keys(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_keys)

    def rtype_method_values(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_values)

    def rtype_method_items(self, hop):
        return self._rtype_method_kvi(hop, ll_dict_items)

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
        return hop.gendirectcall(ll_dict_clear, v_dict)

    def rtype_method_popitem(self, hop):
        v_dict, = hop.inputargs(self)
        r_tuple = hop.r_result
        cTUPLE = hop.inputconst(lltype.Void, r_tuple.lowleveltype)
        hop.exception_is_here()
        return hop.gendirectcall(ll_dict_popitem, cTUPLE, v_dict)

    def rtype_method_pop(self, hop):
        if hop.nb_args == 2:
            v_args = hop.inputargs(self, self.key_repr)
            target = ll_dict_pop
        elif hop.nb_args == 3:
            v_args = hop.inputargs(self, self.key_repr, self.value_repr)
            target = ll_dict_pop_default
        hop.exception_is_here()
        v_res = hop.gendirectcall(target, *v_args)
        return self.recast_value(hop.llops, v_res)

class __extend__(pairtype(DictRepr, rmodel.Repr)):

    def rtype_getitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        if not r_dict.custom_eq_hash:
            hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        v_res = hop.gendirectcall(ll_dict_getitem, v_dict, v_key)
        return r_dict.recast_value(hop.llops, v_res)

    def rtype_delitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        if not r_dict.custom_eq_hash:
            hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_dict_delitem, v_dict, v_key)

    def rtype_setitem((r_dict, r_key), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, r_dict.key_repr, r_dict.value_repr)
        if r_dict.custom_eq_hash:
            hop.exception_is_here()
        else:
            hop.exception_cannot_occur()
        hop.gendirectcall(ll_dict_setitem, v_dict, v_key, v_value)

    def rtype_contains((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        hop.exception_is_here()
        return hop.gendirectcall(ll_dict_contains, v_dict, v_key)

class __extend__(pairtype(DictRepr, DictRepr)):
    def convert_from_to((r_dict1, r_dict2), v, llops):
        # check that we don't convert from Dicts with
        # different key/value types
        if r_dict1.dictkey is None or r_dict2.dictkey is None:
            return NotImplemented
        if r_dict1.dictkey is not r_dict2.dictkey:
            return NotImplemented
        if r_dict1.dictvalue is None or r_dict2.dictvalue is None:
            return NotImplemented
        if r_dict1.dictvalue is not r_dict2.dictvalue:
            return NotImplemented
        return v

# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

DICTINDEX_LONG = lltype.Ptr(lltype.GcArray(lltype.Unsigned))
DICTINDEX_INT = lltype.Ptr(lltype.GcArray(rffi.UINT))
DICTINDEX_SHORT = lltype.Ptr(lltype.GcArray(rffi.USHORT))
DICTINDEX_BYTE = lltype.Ptr(lltype.GcArray(rffi.UCHAR))

IS_64BIT = sys.maxint != 2 ** 31 - 1

if IS_64BIT:
    FUNC_BYTE, FUNC_SHORT, FUNC_INT, FUNC_LONG = range(4)
else:
    FUNC_BYTE, FUNC_SHORT, FUNC_LONG = range(3)

def ll_malloc_indexes_and_choose_lookup(d, n):
    if n <= 256:
        d.indexes = lltype.cast_opaque_ptr(llmemory.GCREF,
                                           lltype.malloc(DICTINDEX_BYTE.TO, n,
                                                         zero=True))
        d.lookup_function_no = FUNC_BYTE
    elif n <= 65536:
        d.indexes = lltype.cast_opaque_ptr(llmemory.GCREF,
                                           lltype.malloc(DICTINDEX_SHORT.TO, n,
                                                         zero=True))
        d.lookup_function_no = FUNC_SHORT
    elif IS_64BIT and n <= 2 ** 32:
        d.indexes = lltype.cast_opaque_ptr(llmemory.GCREF,
                                           lltype.malloc(DICTINDEX_INT.TO, n,
                                                         zero=True))
        d.lookup_function_no = FUNC_INT
    else:
        d.indexes = lltype.cast_opaque_ptr(llmemory.GCREF,
                                           lltype.malloc(DICTINDEX_LONG.TO, n,
                                                         zero=True))
        d.lookup_function_no = FUNC_LONG

def ll_call_insert_clean_function(d, hash, i):
    DICT = lltype.typeOf(d).TO
    if d.lookup_function_no == FUNC_BYTE:
        DICT.lookup_family.byte_insert_clean_function(d, hash, i)
    elif d.lookup_function_no == FUNC_SHORT:
        DICT.lookup_family.short_insert_clean_function(d, hash, i)
    elif IS_64BIT and d.lookup_function_no == FUNC_INT:
        DICT.lookup_family.int_insert_clean_function(d, hash, i)
    elif d.lookup_function_no == FUNC_LONG:
        DICT.lookup_family.long_insert_clean_function(d, hash, i)
    else:
        assert False

def ll_valid_from_flag(entries, i):
    return entries[i].f_valid

def ll_valid_from_key(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    return entries[i].key != dummy

def ll_valid_from_value(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    return entries[i].value != dummy

def ll_mark_deleted_in_flag(entries, i):
    entries[i].f_valid = False

def ll_mark_deleted_in_key(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    entries[i].key = dummy

def ll_mark_deleted_in_value(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    entries[i].value = dummy

def ll_hash_from_cache(entries, i):
    return entries[i].f_hash

def ll_hash_recomputed(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    return ENTRIES.fasthashfn(entries[i].key)

def ll_keyhash_custom(d, key):
    DICT = lltype.typeOf(d).TO
    return objectmodel.hlinvoke(DICT.r_rdict_hashfn, d.fnkeyhash, key)

def ll_keyeq_custom(d, key1, key2):
    DICT = lltype.typeOf(d).TO
    return objectmodel.hlinvoke(DICT.r_rdict_eqfn, d.fnkeyeq, key1, key2)

def ll_dict_len(d):
    return d.num_items

def ll_dict_bool(d):
    # check if a dict is True, allowing for None
    return bool(d) and d.num_items != 0

def ll_dict_getitem(d, key):
    index = d.lookup_function(d, key, d.keyhash(key), FLAG_LOOKUP)
    if index != -1:
        return d.entries[index].value
    else:
        raise KeyError

def ll_dict_setitem(d, key, value):
    hash = d.keyhash(key)
    index = d.lookup_function(d, key, hash, FLAG_STORE)
    return _ll_dict_setitem_lookup_done(d, key, value, hash, index)

# It may be safe to look inside always, it has a few branches though, and their
# frequencies needs to be investigated.
@jit.look_inside_iff(lambda d, key, value, hash, i: jit.isvirtual(d) and jit.isconstant(key))
def _ll_dict_setitem_lookup_done(d, key, value, hash, i):
    ENTRY = lltype.typeOf(d.entries).TO.OF
    if i >= 0:
        entry = d.entries[i]
        entry.value = value
    else:
        if len(d.entries) == d.num_used_items:
            if ll_dict_grow(d):
                ll_call_insert_clean_function(d, hash, d.num_used_items)
        entry = d.entries[d.num_used_items]
        entry.key = key
        entry.value = value
        if hasattr(ENTRY, 'f_hash'):
            entry.f_hash = hash
        if hasattr(ENTRY, 'f_valid'):
            entry.f_valid = True
        d.num_used_items += 1
        d.num_items += 1
        rc = d.resize_counter - 3
        if rc <= 0:
            ll_dict_resize(d)
            rc = d.resize_counter - 3
            ll_assert(rc > 0, "ll_dict_resize failed?")
        d.resize_counter = rc

def _ll_dict_insertclean(d, key, value, hash):
    ENTRY = lltype.typeOf(d.entries).TO.OF
    ll_call_insert_clean_function(d, hash, d.num_used_items)
    entry = d.entries[d.num_used_items]
    entry.key = key
    entry.value = value
    if hasattr(ENTRY, 'f_hash'):
        entry.f_hash = hash
    if hasattr(ENTRY, 'f_valid'):
        entry.f_valid = True
    d.num_used_items += 1
    d.num_items += 1
    rc = d.resize_counter - 3
    d.resize_counter = rc

def _ll_len_of_d_indexes(d):
    # xxx Haaaack: returns len(d.indexes).  Works independently of
    # the exact type pointed to by d, using a forced cast...
    return len(rffi.cast(DICTINDEX_BYTE, d.indexes))

def _overallocate_entries_len(baselen):
    # This over-allocates proportional to the list size, making room
    # for additional growth.  The over-allocation is mild, but is
    # enough to give linear-time amortized behavior over a long
    # sequence of appends() in the presence of a poorly-performing
    # system malloc().
    # The growth pattern is:  0, 4, 8, 16, 25, 35, 46, 58, 72, 88, ...
    newsize = baselen + 1
    if newsize < 9:
        some = 3
    else:
        some = 6
    some += newsize >> 3
    return newsize + some

@jit.dont_look_inside
def ll_dict_grow(d):
    if d.num_items < d.num_used_items // 4:
        ll_dict_remove_deleted_items(d)
        return True

    new_allocated = _overallocate_entries_len(len(d.entries))

    # Detect an obscure case where the indexes numeric type is too
    # small to store all the entry indexes
    if (max(128, _ll_len_of_d_indexes(d)) - new_allocated
                   < MIN_INDEXES_MINUS_ENTRIES):
        ll_dict_remove_deleted_items(d)
        return True

    newitems = lltype.malloc(lltype.typeOf(d).TO.entries.TO, new_allocated)
    rgc.ll_arraycopy(d.entries, newitems, 0, 0, len(d.entries))
    d.entries = newitems
    return False

def ll_dict_remove_deleted_items(d):
    new_allocated = _overallocate_entries_len(d.num_items)
    if new_allocated < len(d.entries) // 2:
        newitems = lltype.malloc(lltype.typeOf(d).TO.entries.TO, new_allocated)
    else:
        newitems = d.entries
    #
    ENTRY = lltype.typeOf(d).TO.entries.TO.OF
    isrc = 0
    idst = 0
    while isrc < len(d.entries):
        if d.entries.valid(isrc):
            src = d.entries[isrc]
            dst = newitems[idst]
            dst.key = src.key
            dst.value = src.value
            if hasattr(ENTRY, 'f_hash'):
                dst.f_hash = src.f_hash
            if hasattr(ENTRY, 'f_valid'):
                assert src.f_valid
                dst.f_valid = True
            idst += 1
        isrc += 1
    d.entries = newitems
    assert d.num_items == idst
    d.num_used_items = idst

    ll_dict_reindex(d, _ll_len_of_d_indexes(d))


def ll_dict_delitem(d, key):
    index = d.lookup_function(d, key, d.keyhash(key), FLAG_DELETE)
    if index == -1:
        raise KeyError
    _ll_dict_del(d, index)

@jit.look_inside_iff(lambda d, i: jit.isvirtual(d) and jit.isconstant(i))
def _ll_dict_del(d, index):
    d.entries.mark_deleted(index)
    d.num_items -= 1
    # clear the key and the value if they are GC pointers
    ENTRIES = lltype.typeOf(d.entries).TO
    ENTRY = ENTRIES.OF
    entry = d.entries[index]
    if ENTRIES.must_clear_key:
        entry.key = lltype.nullptr(ENTRY.key.TO)
    if ENTRIES.must_clear_value:
        entry.value = lltype.nullptr(ENTRY.value.TO)
    #
    # The rest is commented out: like CPython we no longer shrink the
    # dictionary here.  It may shrink later if we try to append a number
    # of new items to it.  Unsure if this behavior was designed in
    # CPython or is accidental.  A design reason would be that if you
    # delete all items in a dictionary (e.g. with a series of
    # popitem()), then CPython avoids shrinking the table several times.
    #num_entries = len(d.entries)
    #if num_entries > DICT_INITSIZE and d.num_items <= num_entries / 4:
    #    ll_dict_resize(d)
    # A previous xxx: move the size checking and resize into a single
    # call which is opaque to the JIT when the dict isn't virtual, to
    # avoid extra branches.

def ll_dict_resize(d):
    # make a 'new_size' estimate and shrink it if there are many
    # deleted entry markers.  See CPython for why it is a good idea to
    # quadruple the dictionary size as long as it's not too big.
    num_items = d.num_items
    if num_items > 50000:
        new_estimate = num_items * 2
    else:
        new_estimate = num_items * 4
    new_size = DICT_INITSIZE
    while new_size <= new_estimate:
        new_size *= 2

    if new_size < _ll_len_of_d_indexes(d):
        ll_dict_remove_deleted_items(d)
    else:
        ll_dict_reindex(d, new_size)
ll_dict_resize.oopspec = 'dict.resize(d)'

def ll_dict_reindex(d, new_size):
    ll_malloc_indexes_and_choose_lookup(d, new_size)
    d.resize_counter = new_size * 2 - d.num_items * 3
    assert d.resize_counter > 0
    #
    entries = d.entries
    i = 0
    while i < d.num_used_items:
        if entries.valid(i):
            hash = entries.hash(i)
            ll_call_insert_clean_function(d, hash, i)
        i += 1
    #old_entries.delete() XXXX!

# ------- a port of CPython's dictobject.c's lookdict implementation -------
PERTURB_SHIFT = 5

FREE = 0
DELETED = 1
VALID_OFFSET = 2
MIN_INDEXES_MINUS_ENTRIES = VALID_OFFSET + 1

FLAG_LOOKUP = 0
FLAG_STORE = 1
FLAG_DELETE = 2
FLAG_DELETE_TRY_HARD = 3

def new_lookup_functions(LOOKUP_FUNC, STORECLEAN_FUNC, T, rtyper=None):
    INDEXES = lltype.Ptr(lltype.GcArray(T))

    def ll_kill_something(d):
        i = 0
        indexes = lltype.cast_opaque_ptr(INDEXES, d.indexes)
        while True:
            index = rffi.cast(lltype.Signed, indexes[i])
            if index >= VALID_OFFSET:
                indexes[i] = rffi.cast(T, DELETED)
                return index
            i += 1

    @jit.look_inside_iff(lambda d, key, hash, store_flag:
                         jit.isvirtual(d) and jit.isconstant(key))
    def ll_dict_lookup(d, key, hash, store_flag):
        entries = d.entries
        indexes = lltype.cast_opaque_ptr(INDEXES, d.indexes)
        mask = len(indexes) - 1
        i = r_uint(hash & mask)
        # do the first try before any looping
        ENTRIES = lltype.typeOf(entries).TO
        direct_compare = not hasattr(ENTRIES, 'no_direct_compare')
        index = rffi.cast(lltype.Signed, indexes[intmask(i)])
        if index >= VALID_OFFSET:
            checkingkey = entries[index - VALID_OFFSET].key
            if direct_compare and checkingkey == key:
                if store_flag == FLAG_DELETE:
                    indexes[i] = rffi.cast(T, DELETED)
                return index - VALID_OFFSET   # found the entry
            if d.keyeq is not None and entries.hash(index - VALID_OFFSET) == hash:
                # correct hash, maybe the key is e.g. a different pointer to
                # an equal object
                found = d.keyeq(checkingkey, key)
                #llop.debug_print(lltype.Void, "comparing keys", ll_debugrepr(checkingkey), ll_debugrepr(key), found)
                if d.paranoia:
                    if (entries != d.entries or lltype.cast_opaque_ptr(llmemory.GCREF, indexes) != d.indexes or
                        not entries.valid(index - VALID_OFFSET) or
                        entries[index - VALID_OFFSET].key != checkingkey):
                        # the compare did major nasty stuff to the dict: start over
                        return ll_dict_lookup(d, key, hash, store_flag)
                if found:
                    if store_flag == FLAG_DELETE:
                        indexes[i] = rffi.cast(T, DELETED)
                    return index - VALID_OFFSET
            deletedslot = -1
        elif index == DELETED:
            deletedslot = intmask(i)
        else:
            # pristine entry -- lookup failed
            if store_flag == FLAG_STORE:
                indexes[i] = rffi.cast(T, d.num_used_items + VALID_OFFSET)
            elif d.paranoia and store_flag == FLAG_DELETE_TRY_HARD:
                return ll_kill_something(d)
            return -1

        # In the loop, a deleted entry (everused and not valid) is by far
        # (factor of 100s) the least likely outcome, so test for that last.
        perturb = r_uint(hash)
        while 1:
            # compute the next index using unsigned arithmetic
            i = (i << 2) + i + perturb + 1
            i = i & mask
            index = rffi.cast(lltype.Signed, indexes[intmask(i)])
            if index == FREE:
                if store_flag == FLAG_STORE:
                    if deletedslot == -1:
                        deletedslot = intmask(i)
                    indexes[deletedslot] = rffi.cast(T, d.num_used_items +
                                                     VALID_OFFSET)
                elif d.paranoia and store_flag == FLAG_DELETE_TRY_HARD:
                    return ll_kill_something(d)
                return -1
            elif index >= VALID_OFFSET:
                checkingkey = entries[index - VALID_OFFSET].key
                if direct_compare and checkingkey == key:
                    if store_flag == FLAG_DELETE:
                        indexes[i] = rffi.cast(T, DELETED)
                    return index - VALID_OFFSET   # found the entry
                if d.keyeq is not None and entries.hash(index - VALID_OFFSET) == hash:
                    # correct hash, maybe the key is e.g. a different pointer to
                    # an equal object
                    found = d.keyeq(checkingkey, key)
                    if d.paranoia:
                        if (entries != d.entries or lltype.cast_opaque_ptr(llmemory.GCREF, indexes) != d.indexes or
                            not entries.valid(index - VALID_OFFSET) or
                            entries[index - VALID_OFFSET].key != checkingkey):
                            # the compare did major nasty stuff to the dict: start over
                            return ll_dict_lookup(d, key, hash, store_flag)
                    if found:
                        if store_flag == FLAG_DELETE:
                            indexes[i] = rffi.cast(T, DELETED)
                        return index - VALID_OFFSET
            elif deletedslot == -1:
                deletedslot = intmask(i)
            perturb >>= PERTURB_SHIFT

    def ll_dict_store_clean(d, hash, index):
        # a simplified version of ll_dict_lookup() which assumes that the
        # key is new, and the dictionary doesn't contain deleted entries.
        # It only finds the next free slot for the given hash.
        indexes = lltype.cast_opaque_ptr(INDEXES, d.indexes)
        mask = len(indexes) - 1
        i = r_uint(hash & mask)
        perturb = r_uint(hash)
        while rffi.cast(lltype.Signed, indexes[i]) != 0:
            i = (i << 2) + i + perturb + 1
            i = i & mask
            perturb >>= PERTURB_SHIFT
        indexes[i] = rffi.cast(T, index + VALID_OFFSET)

    return (llhelper_or_compile(rtyper, LOOKUP_FUNC, ll_dict_lookup),
            llhelper_or_compile(rtyper, STORECLEAN_FUNC, ll_dict_store_clean))

# ____________________________________________________________
#
#  Irregular operations.

DICT_INITSIZE = 8

def ll_newdict(DICT):
    d = DICT.allocate()
    d.entries = DICT.lookup_family.empty_array
    ll_malloc_indexes_and_choose_lookup(d, DICT_INITSIZE)
    d.num_items = 0
    d.num_used_items = 0
    d.resize_counter = DICT_INITSIZE * 2
    return d

def ll_newdict_size(DICT, orig_length_estimate):
    length_estimate = (orig_length_estimate // 2) * 3
    n = DICT_INITSIZE
    while n < length_estimate:
        n *= 2
    d = DICT.allocate()
    d.entries = DICT.entries.TO.allocate(orig_length_estimate)
    ll_malloc_indexes_and_choose_lookup(d, n)
    d.num_items = 0
    d.num_used_items = 0
    d.resize_counter = n * 2
    return d

# rpython.memory.lldict uses a dict based on Struct and Array
# instead of GcStruct and GcArray, which is done by using different
# 'allocate' and 'delete' adtmethod implementations than the ones below
def _ll_malloc_dict(DICT):
    return lltype.malloc(DICT)
def _ll_malloc_entries(ENTRIES, n):
    return lltype.malloc(ENTRIES, n, zero=True)
def _ll_free_entries(entries):
    pass


def rtype_r_dict(hop):
    r_dict = hop.r_result
    if not r_dict.custom_eq_hash:
        raise TyperError("r_dict() call does not return an r_dict instance")
    v_eqfn = hop.inputarg(r_dict.r_rdict_eqfn, arg=0)
    v_hashfn = hop.inputarg(r_dict.r_rdict_hashfn, arg=1)
    cDICT = hop.inputconst(lltype.Void, r_dict.DICT)
    hop.exception_cannot_occur()
    v_result = hop.gendirectcall(ll_newdict, cDICT)
    if r_dict.r_rdict_eqfn.lowleveltype != lltype.Void:
        cname = hop.inputconst(lltype.Void, 'fnkeyeq')
        hop.genop('setfield', [v_result, cname, v_eqfn])
    if r_dict.r_rdict_hashfn.lowleveltype != lltype.Void:
        cname = hop.inputconst(lltype.Void, 'fnkeyhash')
        hop.genop('setfield', [v_result, cname, v_hashfn])
    return v_result

# ____________________________________________________________
#
#  Iteration.

def get_ll_dictiter(DICTPTR):
    return lltype.Ptr(lltype.GcStruct('dictiter',
                                      ('dict', DICTPTR),
                                      ('index', lltype.Signed)))

class DictIteratorRepr(AbstractDictIteratorRepr):

    def __init__(self, r_dict, variant="keys"):
        self.r_dict = r_dict
        self.variant = variant
        self.lowleveltype = get_ll_dictiter(r_dict.lowleveltype)
        self.ll_dictiter = ll_dictiter
        self.ll_dictnext = ll_dictnext_group[variant]


def ll_dictiter(ITERPTR, d):
    iter = lltype.malloc(ITERPTR.TO)
    iter.dict = d
    iter.index = 0
    return iter

def _make_ll_dictnext(kind):
    # make three versions of the following function: keys, values, items
    @jit.look_inside_iff(lambda RETURNTYPE, iter: jit.isvirtual(iter)
                         and (iter.dict is None or
                              jit.isvirtual(iter.dict)))
    @jit.oopspec("dictiter.next%s(iter)" % kind)
    def ll_dictnext(RETURNTYPE, iter):
        # note that RETURNTYPE is None for keys and values
        dict = iter.dict
        if not dict:
            raise StopIteration

        entries = dict.entries
        index = iter.index
        assert index >= 0
        entries_len = dict.num_used_items
        while index < entries_len:
            entry = entries[index]
            is_valid = entries.valid(index)
            index = index + 1
            if is_valid:
                iter.index = index
                if RETURNTYPE is lltype.Void:
                    return None
                elif kind == 'items':
                    r = lltype.malloc(RETURNTYPE.TO)
                    r.item0 = recast(RETURNTYPE.TO.item0, entry.key)
                    r.item1 = recast(RETURNTYPE.TO.item1, entry.value)
                    return r
                elif kind == 'keys':
                    return entry.key
                elif kind == 'values':
                    return entry.value

        # clear the reference to the dict and prevent restarts
        iter.dict = lltype.nullptr(lltype.typeOf(iter).TO.dict.TO)
        raise StopIteration

    return ll_dictnext

ll_dictnext_group = {'keys'  : _make_ll_dictnext('keys'),
                     'values': _make_ll_dictnext('values'),
                     'items' : _make_ll_dictnext('items')}

# _____________________________________________________________
# methods

def ll_dict_get(dict, key, default):
    index = dict.lookup_function(dict, key, dict.keyhash(key), FLAG_LOOKUP)
    if index == -1:
        return default
    else:
        return dict.entries[index].value

def ll_dict_setdefault(dict, key, default):
    hash = dict.keyhash(key)
    index = dict.lookup_function(dict, key, hash, FLAG_STORE)
    if index == -1:
        _ll_dict_setitem_lookup_done(dict, key, default, hash, -1)
        return default
    else:
        return dict.entries[index].value

def ll_dict_copy(dict):
    DICT = lltype.typeOf(dict).TO
    newdict = DICT.allocate()
    newdict.entries = DICT.entries.TO.allocate(len(dict.entries))

    newdict.num_items = dict.num_items
    newdict.num_used_items = dict.num_used_items
    if hasattr(DICT, 'fnkeyeq'):
        newdict.fnkeyeq = dict.fnkeyeq
    if hasattr(DICT, 'fnkeyhash'):
        newdict.fnkeyhash = dict.fnkeyhash

    i = 0
    while i < newdict.num_used_items:
        d_entry = newdict.entries[i]
        entry = dict.entries[i]
        ENTRY = lltype.typeOf(newdict.entries).TO.OF
        d_entry.key = entry.key
        if hasattr(ENTRY, 'f_valid'):
            d_entry.f_valid = entry.f_valid
        d_entry.value = entry.value
        if hasattr(ENTRY, 'f_hash'):
            d_entry.f_hash = entry.f_hash
        i += 1

    ll_dict_reindex(newdict, _ll_len_of_d_indexes(dict))
    return newdict
ll_dict_copy.oopspec = 'dict.copy(dict)'

def ll_dict_clear(d):
    if d.num_used_items == 0:
        return
    DICT = lltype.typeOf(d).TO
    old_entries = d.entries
    d.entries = DICT.lookup_family.empty_array
    ll_malloc_indexes_and_choose_lookup(d, DICT_INITSIZE)
    d.num_items = 0
    d.num_used_items = 0
    d.resize_counter = DICT_INITSIZE * 2
    # old_entries.delete() XXX
ll_dict_clear.oopspec = 'dict.clear(d)'

def ll_dict_update(dic1, dic2):
    i = 0
    while i < dic2.num_used_items:
        entries = dic2.entries
        if entries.valid(i):
            entry = entries[i]
            hash = entries.hash(i)
            key = entry.key
            value = entry.value
            index = dic1.lookup_function(dic1, key, hash, FLAG_STORE)
            _ll_dict_setitem_lookup_done(dic1, key, value, hash, index)
        i += 1
ll_dict_update.oopspec = 'dict.update(dic1, dic2)'

# this is an implementation of keys(), values() and items()
# in a single function.
# note that by specialization on func, three different
# and very efficient functions are created.

def recast(P, v):
    if isinstance(P, lltype.Ptr):
        return lltype.cast_pointer(P, v)
    else:
        return v

def _make_ll_keys_values_items(kind):
    def ll_kvi(LIST, dic):
        res = LIST.ll_newlist(dic.num_items)
        entries = dic.entries
        dlen = dic.num_used_items
        items = res.ll_items()
        i = 0
        p = 0
        while i < dlen:
            if entries.valid(i):
                ELEM = lltype.typeOf(items).TO.OF
                if ELEM is not lltype.Void:
                    entry = entries[i]
                    if kind == 'items':
                        r = lltype.malloc(ELEM.TO)
                        r.item0 = recast(ELEM.TO.item0, entry.key)
                        r.item1 = recast(ELEM.TO.item1, entry.value)
                        items[p] = r
                    elif kind == 'keys':
                        items[p] = recast(ELEM, entry.key)
                    elif kind == 'values':
                        items[p] = recast(ELEM, entry.value)
                p += 1
            i += 1
        assert p == res.ll_length()
        return res
    ll_kvi.oopspec = 'dict.%s(dic)' % kind
    return ll_kvi

ll_dict_keys   = _make_ll_keys_values_items('keys')
ll_dict_values = _make_ll_keys_values_items('values')
ll_dict_items  = _make_ll_keys_values_items('items')

def ll_dict_contains(d, key):
    i = d.lookup_function(d, key, d.keyhash(key), FLAG_LOOKUP)
    return i != -1

def _ll_getnextitem(dic):
    if dic.num_items == 0:
        raise KeyError

    entries = dic.entries

    while True:
        i = dic.num_used_items - 1
        if entries.valid(i):
            break
        dic.num_used_items -= 1

    key = entries[i].key
    index = dic.lookup_function(dic, key, entries.hash(i),
                                FLAG_DELETE_TRY_HARD)
    # if the lookup function returned me a random strange thing,
    # don't care about deleting the item
    if index == dic.num_used_items - 1:
        dic.num_used_items -= 1
    else:
        assert index != -1
    return index

def ll_dict_popitem(ELEM, dic):
    i = _ll_getnextitem(dic)
    entry = dic.entries[i]
    r = lltype.malloc(ELEM.TO)
    r.item0 = recast(ELEM.TO.item0, entry.key)
    r.item1 = recast(ELEM.TO.item1, entry.value)
    _ll_dict_del(dic, i)
    return r

def ll_dict_pop(dic, key):
    index = dic.lookup_function(dic, key, dic.keyhash(key), FLAG_DELETE)
    if index == -1:
        raise KeyError
    value = dic.entries[index].value
    _ll_dict_del(dic, index)
    return value

def ll_dict_pop_default(dic, key, dfl):
    index = dic.lookup_function(dic, key, dic.keyhash(key), FLAG_DELETE)
    if index == -1:
        return dfl
    value = dic.entries[index].value
    _ll_dict_del(dic, index)
    return value
