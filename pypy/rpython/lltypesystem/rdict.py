from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.rdict import AbstractDictRepr, AbstractDictIteratorRepr,\
     rtype_newdict
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rarithmetic import r_uint, intmask, LONG_BIT
from pypy.rlib.objectmodel import hlinvoke
from pypy.rpython import robject
from pypy.rlib import objectmodel, jit
from pypy.rpython import rmodel
from pypy.rpython.error import TyperError

HIGHEST_BIT = intmask(1 << (LONG_BIT - 1))
MASK = intmask(HIGHEST_BIT - 1)

# ____________________________________________________________
#
#  generic implementation of RPython dictionary, with parametric DICTKEY and
#  DICTVALUE types.
#
#  XXX for immutable dicts, the array should be inlined and
#      resize_counter and everused are not needed.
#
#    struct dictentry {
#        DICTKEY key;
#        bool f_valid;      # (optional) the entry is filled
#        bool f_everused;   # (optional) the entry is or has ever been filled
#        DICTVALUE value;
#        int f_hash;        # (optional) key hash, if hard to recompute
#    }
#
#    struct dicttable {
#        int num_items;
#        int resize_counter;
#        Array *entries;
#        (Function DICTKEY, DICTKEY -> bool) *fnkeyeq;
#        (Function DICTKEY -> int) *fnkeyhash;
#    }
#
#

class DictRepr(AbstractDictRepr):

    def __init__(self, rtyper, key_repr, value_repr, dictkey, dictvalue,
                 custom_eq_hash=None, force_non_null=False):
        self.rtyper = rtyper
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
        self.force_non_null = force_non_null
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
            self.DICTKEY = self.key_repr.lowleveltype
            self.DICTVALUE = self.value_repr.lowleveltype

            # compute the shape of the DICTENTRY structure
            entryfields = []
            entrymeths = {
                'allocate': lltype.typeMethod(_ll_malloc_entries),
                'delete': _ll_free_entries,
                'must_clear_key':   (isinstance(self.DICTKEY, lltype.Ptr)
                                     and self.DICTKEY._needsgc()),
                'must_clear_value': (isinstance(self.DICTVALUE, lltype.Ptr)
                                     and self.DICTVALUE._needsgc()),
                }

            # * the key
            entryfields.append(("key", self.DICTKEY))

            # * if NULL is not a valid ll value for the key or the value
            #   field of the entry, it can be used as a marker for
            #   never-used entries.  Otherwise, we need an explicit flag.
            s_key   = self.dictkey.s_value
            s_value = self.dictvalue.s_value
            nullkeymarker = not self.key_repr.can_ll_be_null(s_key)
            nullvaluemarker = not self.value_repr.can_ll_be_null(s_value)
            if self.force_non_null:
                if not nullkeymarker:
                    rmodel.warning("%s can be null, but forcing non-null in dict key" % s_key)
                    nullkeymarker = True
                if not nullvaluemarker:
                    rmodel.warning("%s can be null, but forcing non-null in dict value" % s_value)
                    nullvaluemarker = True
            dummykeyobj = self.key_repr.get_ll_dummyval_obj(self.rtyper,
                                                            s_key)
            dummyvalueobj = self.value_repr.get_ll_dummyval_obj(self.rtyper,
                                                                s_value)

            # * the state of the entry - trying to encode it as dummy objects
            if nullkeymarker and dummykeyobj:
                # all the state can be encoded in the key
                entrymeths['everused'] = ll_everused_from_key
                entrymeths['dummy_obj'] = dummykeyobj
                entrymeths['valid'] = ll_valid_from_key
                entrymeths['mark_deleted'] = ll_mark_deleted_in_key
                # the key is overwritten by 'dummy' when the entry is deleted
                entrymeths['must_clear_key'] = False

            elif nullvaluemarker and dummyvalueobj:
                # all the state can be encoded in the value
                entrymeths['everused'] = ll_everused_from_value
                entrymeths['dummy_obj'] = dummyvalueobj
                entrymeths['valid'] = ll_valid_from_value
                entrymeths['mark_deleted'] = ll_mark_deleted_in_value
                # value is overwritten by 'dummy' when entry is deleted
                entrymeths['must_clear_value'] = False

            else:
                # we need a flag to know if the entry was ever used
                # (we cannot use a NULL as a marker for this, because
                # the key and value will be reset to NULL to clear their
                # reference)
                entryfields.append(("f_everused", lltype.Bool))
                entrymeths['everused'] = ll_everused_from_flag

                # can we still rely on a dummy obj to mark deleted entries?
                if dummykeyobj:
                    entrymeths['dummy_obj'] = dummykeyobj
                    entrymeths['valid'] = ll_valid_from_key
                    entrymeths['mark_deleted'] = ll_mark_deleted_in_key
                    # key is overwritten by 'dummy' when entry is deleted
                    entrymeths['must_clear_key'] = False
                elif dummyvalueobj:
                    entrymeths['dummy_obj'] = dummyvalueobj
                    entrymeths['valid'] = ll_valid_from_value
                    entrymeths['mark_deleted'] = ll_mark_deleted_in_value
                    # value is overwritten by 'dummy' when entry is deleted
                    entrymeths['must_clear_value'] = False
                else:
                    entryfields.append(("f_valid", lltype.Bool))
                    entrymeths['valid'] = ll_valid_from_flag
                    entrymeths['mark_deleted'] = ll_mark_deleted_in_flag

            # * the value
            entryfields.append(("value", self.DICTVALUE))

            # * the hash, if needed
            if self.custom_eq_hash:
                fasthashfn = None
            else:
                fasthashfn = self.key_repr.get_ll_fasthash_function()
            if fasthashfn is None:
                entryfields.append(("f_hash", lltype.Signed))
                entrymeths['hash'] = ll_hash_from_cache
            else:
                entrymeths['hash'] = ll_hash_recomputed
                entrymeths['fasthashfn'] = fasthashfn

            # Build the lltype data structures
            self.DICTENTRY = lltype.Struct("dictentry", *entryfields)
            self.DICTENTRYARRAY = lltype.GcArray(self.DICTENTRY,
                                                 adtmeths=entrymeths)
            fields =          [ ("num_items", lltype.Signed),
                                ("resize_counter", lltype.Signed),
                                ("entries", lltype.Ptr(self.DICTENTRYARRAY)) ]
            if self.custom_eq_hash:
                self.r_rdict_eqfn, self.r_rdict_hashfn = self._custom_eq_hash_repr()
                fields.extend([ ("fnkeyeq", self.r_rdict_eqfn.lowleveltype),
                                ("fnkeyhash", self.r_rdict_hashfn.lowleveltype) ])
                adtmeths = {
                    'keyhash':        ll_keyhash_custom,
                    'keyeq':          ll_keyeq_custom,
                    'r_rdict_eqfn':   self.r_rdict_eqfn,
                    'r_rdict_hashfn': self.r_rdict_hashfn,
                    'paranoia':       True,
                    }
            else:
                # figure out which functions must be used to hash and compare
                ll_keyhash = self.key_repr.get_ll_hash_function()
                ll_keyeq = self.key_repr.get_ll_eq_function()  # can be None
                ll_keyhash = lltype.staticAdtMethod(ll_keyhash)
                if ll_keyeq is not None:
                    ll_keyeq = lltype.staticAdtMethod(ll_keyeq)
                adtmeths = {
                    'keyhash':  ll_keyhash,
                    'keyeq':    ll_keyeq,
                    'paranoia': False,
                    }
            adtmeths['KEY']   = self.DICTKEY
            adtmeths['VALUE'] = self.DICTVALUE
            adtmeths['allocate'] = lltype.typeMethod(_ll_malloc_dict)
            self.DICT.become(lltype.GcStruct("dicttable", adtmeths=adtmeths,
                                             *fields))


    def convert_const(self, dictobj):
        from pypy.rpython.lltypesystem import llmemory
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
                    ll_dict_insertclean(l_dict, llkey, llvalue,
                                        dictkeycontainer.hash)
                return l_dict

            else:
                for dictkey, dictvalue in dictobj.items():
                    llkey = r_key.convert_const(dictkey)
                    llvalue = r_value.convert_const(dictvalue)
                    ll_dict_insertclean(l_dict, llkey, llvalue,
                                        l_dict.keyhash(llkey))
                return l_dict

    def rtype_len(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_dict_len, v_dict)

    def rtype_is_true(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_dict_is_true, v_dict)

    def make_iterator_repr(self, *variant):
        return DictIteratorRepr(self, *variant)

    def rtype_method_get(self, hop):
        v_dict, v_key, v_default = hop.inputargs(self, self.key_repr,
                                                 self.value_repr)
        hop.exception_cannot_occur()
        v_res = hop.gendirectcall(ll_get, v_dict, v_key, v_default)
        return self.recast_value(hop.llops, v_res)

    def rtype_method_setdefault(self, hop):
        v_dict, v_key, v_default = hop.inputargs(self, self.key_repr,
                                                 self.value_repr)
        hop.exception_cannot_occur()
        v_res = hop.gendirectcall(ll_setdefault, v_dict, v_key, v_default)
        return self.recast_value(hop.llops, v_res)

    def rtype_method_copy(self, hop):
        v_dict, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_copy, v_dict)

    def rtype_method_update(self, hop):
        v_dic1, v_dic2 = hop.inputargs(self, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_update, v_dic1, v_dic2)

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
        return hop.gendirectcall(ll_clear, v_dict)

    def rtype_method_popitem(self, hop):
        v_dict, = hop.inputargs(self)
        r_tuple = hop.r_result
        cTUPLE = hop.inputconst(lltype.Void, r_tuple.lowleveltype)
        hop.exception_is_here()
        return hop.gendirectcall(ll_popitem, cTUPLE, v_dict)

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
        return hop.gendirectcall(ll_contains, v_dict, v_key)

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

def ll_everused_from_flag(entries, i):
    return entries[i].f_everused

def ll_everused_from_key(entries, i):
    return bool(entries[i].key)

def ll_everused_from_value(entries, i):
    return bool(entries[i].value)

def ll_valid_from_flag(entries, i):
    return entries[i].f_valid

def ll_mark_deleted_in_flag(entries, i):
    entries[i].f_valid = False

def ll_valid_from_key(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    return entries.everused(i) and entries[i].key != dummy

def ll_mark_deleted_in_key(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    entries[i].key = dummy

def ll_valid_from_value(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    return entries.everused(i) and entries[i].value != dummy

def ll_mark_deleted_in_value(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    dummy = ENTRIES.dummy_obj.ll_dummy_value
    entries[i].value = dummy

def ll_hash_from_cache(entries, i):
    return entries[i].f_hash

def ll_hash_recomputed(entries, i):
    ENTRIES = lltype.typeOf(entries).TO
    return ENTRIES.fasthashfn(entries[i].key)

@jit.dont_look_inside
def ll_get_value(d, i):
    return d.entries[i].value

def ll_keyhash_custom(d, key):
    DICT = lltype.typeOf(d).TO
    return hlinvoke(DICT.r_rdict_hashfn, d.fnkeyhash, key)

def ll_keyeq_custom(d, key1, key2):
    DICT = lltype.typeOf(d).TO
    return hlinvoke(DICT.r_rdict_eqfn, d.fnkeyeq, key1, key2)

def ll_dict_len(d):
    return d.num_items

def ll_dict_is_true(d):
    # check if a dict is True, allowing for None
    return bool(d) and d.num_items != 0

def ll_dict_getitem(d, key):
    i = ll_dict_lookup(d, key, d.keyhash(key))
    if not i & HIGHEST_BIT:
        return ll_get_value(d, i)
    else:
        raise KeyError

def ll_dict_setitem(d, key, value):
    hash = d.keyhash(key)
    i = ll_dict_lookup(d, key, hash)
    return _ll_dict_setitem_lookup_done(d, key, value, hash, i)

@jit.dont_look_inside
def _ll_dict_setitem_lookup_done(d, key, value, hash, i):
    valid = (i & HIGHEST_BIT) == 0
    i = i & MASK
    everused = d.entries.everused(i)
    # set up the new entry
    ENTRY = lltype.typeOf(d.entries).TO.OF
    entry = d.entries[i]
    entry.value = value
    if valid:
        return
    entry.key = key
    if hasattr(ENTRY, 'f_hash'):  entry.f_hash = hash
    if hasattr(ENTRY, 'f_valid'): entry.f_valid = True
    d.num_items += 1
    if not everused:
        if hasattr(ENTRY, 'f_everused'): entry.f_everused = True
        d.resize_counter -= 3
        if d.resize_counter <= 0:
            ll_dict_resize(d)

def ll_dict_insertclean(d, key, value, hash):
    # Internal routine used by ll_dict_resize() to insert an item which is
    # known to be absent from the dict.  This routine also assumes that
    # the dict contains no deleted entries.  This routine has the advantage
    # of never calling d.keyhash() and d.keyeq(), so it cannot call back
    # to user code.  ll_dict_insertclean() doesn't resize the dict, either.
    i = ll_dict_lookup_clean(d, hash)
    ENTRY = lltype.typeOf(d.entries).TO.OF
    entry = d.entries[i]
    entry.value = value
    entry.key = key
    if hasattr(ENTRY, 'f_hash'):     entry.f_hash = hash
    if hasattr(ENTRY, 'f_valid'):    entry.f_valid = True
    if hasattr(ENTRY, 'f_everused'): entry.f_everused = True
    d.num_items += 1
    d.resize_counter -= 3

def ll_dict_delitem(d, key):
    i = ll_dict_lookup(d, key, d.keyhash(key))
    if i & HIGHEST_BIT:
        raise KeyError
    _ll_dict_del(d, i)

@jit.dont_look_inside
def _ll_dict_del(d, i):
    d.entries.mark_deleted(i)
    d.num_items -= 1
    # clear the key and the value if they are GC pointers
    ENTRIES = lltype.typeOf(d.entries).TO
    ENTRY = ENTRIES.OF
    entry = d.entries[i]
    if ENTRIES.must_clear_key:
        entry.key = lltype.nullptr(ENTRY.key.TO)
    if ENTRIES.must_clear_value:
        entry.value = lltype.nullptr(ENTRY.value.TO)
    num_entries = len(d.entries)
    if num_entries > DICT_INITSIZE and d.num_items < num_entries / 4:
        ll_dict_resize(d)

def ll_dict_resize(d):
    old_entries = d.entries
    old_size = len(old_entries)
    # make a 'new_size' estimate and shrink it if there are many
    # deleted entry markers
    new_size = old_size * 2
    while new_size > DICT_INITSIZE and d.num_items < new_size / 4:
        new_size /= 2
    d.entries = lltype.typeOf(old_entries).TO.allocate(new_size)
    d.num_items = 0
    d.resize_counter = new_size * 2
    i = 0
    while i < old_size:
        if old_entries.valid(i):
            hash = old_entries.hash(i)
            entry = old_entries[i]
            ll_dict_insertclean(d, entry.key, entry.value, hash)
        i += 1
    old_entries.delete()
ll_dict_resize.oopspec = 'dict.resize(d)'

# ------- a port of CPython's dictobject.c's lookdict implementation -------
PERTURB_SHIFT = 5

def ll_dict_lookup(d, key, hash):
    entries = d.entries
    ENTRIES = lltype.typeOf(entries).TO
    direct_compare = not hasattr(ENTRIES, 'no_direct_compare')
    mask = len(entries) - 1
    i = hash & mask
    # do the first try before any looping
    if entries.valid(i):
        checkingkey = entries[i].key
        if direct_compare and checkingkey == key:
            return i   # found the entry
        if d.keyeq is not None and entries.hash(i) == hash:
            # correct hash, maybe the key is e.g. a different pointer to
            # an equal object
            found = d.keyeq(checkingkey, key)
            if d.paranoia:
                if (entries != d.entries or
                    not entries.valid(i) or entries[i].key != checkingkey):
                    # the compare did major nasty stuff to the dict: start over
                    return ll_dict_lookup(d, key, hash)
            if found:
                return i   # found the entry
        freeslot = -1
    elif entries.everused(i):
        freeslot = i
    else:
        return i | HIGHEST_BIT # pristine entry -- lookup failed

    # In the loop, a deleted entry (everused and not valid) is by far
    # (factor of 100s) the least likely outcome, so test for that last.
    perturb = r_uint(hash)
    while 1:
        # compute the next index using unsigned arithmetic
        i = r_uint(i)
        i = (i << 2) + i + perturb + 1
        i = intmask(i) & mask
        # keep 'i' as a signed number here, to consistently pass signed
        # arguments to the small helper methods.
        if not entries.everused(i):
            if freeslot == -1:
                freeslot = i
            return freeslot | HIGHEST_BIT
        elif entries.valid(i):
            checkingkey = entries[i].key
            if direct_compare and checkingkey == key:
                return i
            if d.keyeq is not None and entries.hash(i) == hash:
                # correct hash, maybe the key is e.g. a different pointer to
                # an equal object
                found = d.keyeq(checkingkey, key)
                if d.paranoia:
                    if (entries != d.entries or
                        not entries.valid(i) or entries[i].key != checkingkey):
                        # the compare did major nasty stuff to the dict:
                        # start over
                        return ll_dict_lookup(d, key, hash)
                if found:
                    return i   # found the entry
        elif freeslot == -1:
            freeslot = i
        perturb >>= PERTURB_SHIFT

def ll_dict_lookup_clean(d, hash):
    # a simplified version of ll_dict_lookup() which assumes that the
    # key is new, and the dictionary doesn't contain deleted entries.
    # It only finds the next free slot for the given hash.
    entries = d.entries
    mask = len(entries) - 1
    i = hash & mask
    perturb = r_uint(hash)
    while entries.everused(i):
        i = r_uint(i)
        i = (i << 2) + i + perturb + 1
        i = intmask(i) & mask
        perturb >>= PERTURB_SHIFT
    return i

# ____________________________________________________________
#
#  Irregular operations.

DICT_INITSIZE = 8

def ll_newdict(DICT):
    d = DICT.allocate()
    d.entries = DICT.entries.TO.allocate(DICT_INITSIZE)
    d.num_items = 0
    d.resize_counter = DICT_INITSIZE * 2
    return d
ll_newdict.oopspec = 'newdict()'

def ll_newdict_size(DICT, length_estimate):
    length_estimate = (length_estimate // 2) * 3
    n = DICT_INITSIZE
    while n < length_estimate:
        n *= 2
    d = DICT.allocate()
    d.entries = DICT.entries.TO.allocate(n)
    d.num_items = 0
    d.resize_counter = n * 2
    return d
ll_newdict_size.oopspec = 'newdict()'

# pypy.rpython.memory.lldict uses a dict based on Struct and Array
# instead of GcStruct and GcArray, which is done by using different
# 'allocate' and 'delete' adtmethod implementations than the ones below
def _ll_malloc_dict(DICT):
    return lltype.malloc(DICT)
def _ll_malloc_entries(ENTRIES, n):
    return lltype.malloc(ENTRIES, n, zero=True)
def _ll_free_entries(entries):
    pass


def rtype_r_dict(hop, i_force_non_null=None):
    r_dict = hop.r_result
    if not r_dict.custom_eq_hash:
        raise TyperError("r_dict() call does not return an r_dict instance")
    v_eqfn = hop.inputarg(r_dict.r_rdict_eqfn, arg=0)
    v_hashfn = hop.inputarg(r_dict.r_rdict_hashfn, arg=1)
    if i_force_non_null is not None:
        assert i_force_non_null == 2
        hop.inputarg(lltype.Void, arg=2)
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

class DictIteratorRepr(AbstractDictIteratorRepr):

    def __init__(self, r_dict, variant="keys"):
        self.r_dict = r_dict
        self.variant = variant
        self.lowleveltype = lltype.Ptr(lltype.GcStruct('dictiter',
                                         ('dict', r_dict.lowleveltype),
                                         ('index', lltype.Signed)))
        self.ll_dictiter = ll_dictiter
        self.ll_dictnext = ll_dictnext_group[variant]


def ll_dictiter(ITERPTR, d):
    iter = lltype.malloc(ITERPTR.TO)
    iter.dict = d
    iter.index = 0
    return iter

def _make_ll_dictnext(kind):
    # make three versions of the following function: keys, values, items
    def ll_dictnext(RETURNTYPE, iter):
        # note that RETURNTYPE is None for keys and values
        dict = iter.dict
        if dict:
            entries = dict.entries
            index = iter.index
            entries_len = len(entries)
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
    ll_dictnext.oopspec = 'dictiter.next%s(iter)' % kind
    return ll_dictnext

ll_dictnext_group = {'keys'  : _make_ll_dictnext('keys'),
                     'values': _make_ll_dictnext('values'),
                     'items' : _make_ll_dictnext('items')}

# _____________________________________________________________
# methods

def ll_get(dict, key, default):
    i = ll_dict_lookup(dict, key, dict.keyhash(key))
    if not i & HIGHEST_BIT:
        return ll_get_value(dict, i)
    else:
        return default

def ll_setdefault(dict, key, default):
    hash = dict.keyhash(key)
    i = ll_dict_lookup(dict, key, hash)
    if not i & HIGHEST_BIT:
        return ll_get_value(dict, i)
    else:
        _ll_dict_setitem_lookup_done(dict, key, default, hash, i)
        return default

def ll_copy(dict):
    DICT = lltype.typeOf(dict).TO
    dictsize = len(dict.entries)
    d = DICT.allocate()
    d.entries = DICT.entries.TO.allocate(dictsize)
    d.num_items = dict.num_items
    d.resize_counter = dict.resize_counter
    if hasattr(DICT, 'fnkeyeq'):   d.fnkeyeq   = dict.fnkeyeq
    if hasattr(DICT, 'fnkeyhash'): d.fnkeyhash = dict.fnkeyhash
    i = 0
    while i < dictsize:
        d_entry = d.entries[i]
        entry = dict.entries[i]
        ENTRY = lltype.typeOf(d.entries).TO.OF
        d_entry.key = entry.key
        if hasattr(ENTRY, 'f_valid'):    d_entry.f_valid    = entry.f_valid
        if hasattr(ENTRY, 'f_everused'): d_entry.f_everused = entry.f_everused
        d_entry.value = entry.value
        if hasattr(ENTRY, 'f_hash'):     d_entry.f_hash     = entry.f_hash
        i += 1
    return d
ll_copy.oopspec = 'dict.copy(dict)'

def ll_clear(d):
    if (len(d.entries) == DICT_INITSIZE and
        d.resize_counter == DICT_INITSIZE * 2):
        return
    old_entries = d.entries
    d.entries = lltype.typeOf(old_entries).TO.allocate(DICT_INITSIZE)
    d.num_items = 0
    d.resize_counter = DICT_INITSIZE * 2
    old_entries.delete()
ll_clear.oopspec = 'dict.clear(d)'

def ll_update(dic1, dic2):
    entries = dic2.entries
    d2len = len(entries)
    i = 0
    while i < d2len:
        if entries.valid(i):
            entry = entries[i]
            hash = entries.hash(i)
            key = entry.key
            j = ll_dict_lookup(dic1, key, hash)
            _ll_dict_setitem_lookup_done(dic1, key, entry.value, hash, j)
        i += 1
ll_update.oopspec = 'dict.update(dic1, dic2)'

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
        dlen = len(entries)
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

def ll_contains(d, key):
    i = ll_dict_lookup(d, key, d.keyhash(key))
    return not i & HIGHEST_BIT

POPITEMINDEX = lltype.Struct('PopItemIndex', ('nextindex', lltype.Signed))
global_popitem_index = lltype.malloc(POPITEMINDEX, zero=True, immortal=True)

def _ll_getnextitem(dic):
    entries = dic.entries
    ENTRY = lltype.typeOf(entries).TO.OF
    dmask = len(entries) - 1
    if hasattr(ENTRY, 'f_hash'):
        if entries.valid(0):
            return 0
        base = entries[0].f_hash
    else:
        base = global_popitem_index.nextindex
    counter = 0
    while counter <= dmask:
        i = (base + counter) & dmask
        counter += 1
        if entries.valid(i):
            break
    else:
        raise KeyError
    if hasattr(ENTRY, 'f_hash'):
        entries[0].f_hash = base + counter
    else:
        global_popitem_index.nextindex = base + counter
    return i

@jit.dont_look_inside
def ll_popitem(ELEM, dic):
    i = _ll_getnextitem(dic)
    entry = dic.entries[i]
    r = lltype.malloc(ELEM.TO)
    r.item0 = recast(ELEM.TO.item0, entry.key)
    r.item1 = recast(ELEM.TO.item1, entry.value)
    _ll_dict_del(dic, i)
    return r
