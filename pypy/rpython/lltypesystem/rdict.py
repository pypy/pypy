from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.rdict import AbstractDictRepr, AbstractDictIteratorRepr,\
     rtype_newdict, dum_variant, dum_keys, dum_values, dum_items
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.objectmodel import hlinvoke
from pypy.rpython import robject
from pypy.rlib import objectmodel
from pypy.rpython import rmodel

# ____________________________________________________________
#
#  generic implementation of RPython dictionary, with parametric DICTKEY and
#  DICTVALUE types.
#
#  XXX for immutable dicts, the array should be inlined and
#      num_pristine_entries and everused are not needed.
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
#        int num_pristine_entries;  # never used entries
#        Array *entries;
#        (Function DICTKEY, DICTKEY -> bool) *fnkeyeq;
#        (Function DICTKEY -> int) *fnkeyhash;
#    }
#
#

class DictRepr(AbstractDictRepr):

    def __init__(self, rtyper, key_repr, value_repr, dictkey, dictvalue,
                 custom_eq_hash=None):
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
            self.DICTENTRY = lltype.Struct("dictentry", adtmeths=entrymeths,
                                           *entryfields)
            self.DICTENTRYARRAY = lltype.GcArray(self.DICTENTRY)
            fields =          [ ("num_items", lltype.Signed),
                                ("num_pristine_entries", lltype.Signed), 
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
            self.DICT.become(lltype.GcStruct("dicttable", adtmeths=adtmeths,
                                             *fields))


    def convert_const(self, dictobj):
        # get object from bound dict methods
        #dictobj = getattr(dictobj, '__self__', dictobj) 
        if dictobj is None:
            return lltype.nullptr(self.DICT)
        if not isinstance(dictobj, (dict, objectmodel.r_dict)):
            raise TyperError("expected a dict: %r" % (dictobj,))
        try:
            key = Constant(dictobj)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            l_dict = ll_newdict_size(self.DICT, len(dictobj))
            self.dict_cache[key] = l_dict 
            r_key = self.key_repr
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

    def _rtype_method_kvi(self, hop, spec):
        v_dic, = hop.inputargs(self)
        r_list = hop.r_result
        v_func = hop.inputconst(lltype.Void, spec)
        cLIST = hop.inputconst(lltype.Void, r_list.lowleveltype.TO)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_kvi, v_dic, cLIST, v_func)

    def rtype_method_keys(self, hop):
        return self._rtype_method_kvi(hop, dum_keys)

    def rtype_method_values(self, hop):
        return self._rtype_method_kvi(hop, dum_values)

    def rtype_method_items(self, hop):
        return self._rtype_method_kvi(hop, dum_items)

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

def ll_everused_from_flag(entry):
    return entry.f_everused

def ll_everused_from_key(entry):
    return bool(entry.key)

def ll_everused_from_value(entry):
    return bool(entry.value)

def ll_valid_from_flag(entry):
    return entry.f_valid

def ll_mark_deleted_in_flag(entry):
    entry.f_valid = False

def ll_valid_from_key(entry):
    ENTRY = lltype.typeOf(entry).TO
    dummy = ENTRY.dummy_obj.ll_dummy_value
    return entry.everused() and entry.key != dummy

def ll_mark_deleted_in_key(entry):
    ENTRY = lltype.typeOf(entry).TO
    dummy = ENTRY.dummy_obj.ll_dummy_value
    entry.key = dummy

def ll_valid_from_value(entry):
    ENTRY = lltype.typeOf(entry).TO
    dummy = ENTRY.dummy_obj.ll_dummy_value
    return entry.everused() and entry.value != dummy

def ll_mark_deleted_in_value(entry):
    ENTRY = lltype.typeOf(entry).TO
    dummy = ENTRY.dummy_obj.ll_dummy_value
    entry.value = dummy

def ll_hash_from_cache(entry):
    return entry.f_hash

def ll_hash_recomputed(entry):
    ENTRY = lltype.typeOf(entry).TO
    return ENTRY.fasthashfn(entry.key)

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
    entry = ll_dict_lookup(d, key, d.keyhash(key))
    if entry.valid():
        return entry.value 
    else: 
        raise KeyError 
ll_dict_getitem.oopspec = 'dict.getitem(d, key)'
ll_dict_getitem.oopargcheck = lambda d, key: bool(d)

def ll_dict_setitem(d, key, value):
    hash = d.keyhash(key)
    entry = ll_dict_lookup(d, key, hash)
    everused = entry.everused()
    valid    = entry.valid()
    # set up the new entry
    ENTRY = lltype.typeOf(entry).TO
    entry.value = value
    if valid:
        return
    entry.key = key
    if hasattr(ENTRY, 'f_hash'):  entry.f_hash = hash
    if hasattr(ENTRY, 'f_valid'): entry.f_valid = True
    d.num_items += 1
    if not everused:
        if hasattr(ENTRY, 'f_everused'): entry.f_everused = True
        d.num_pristine_entries -= 1
        if d.num_pristine_entries <= len(d.entries) / 3:
            ll_dict_resize(d)
ll_dict_setitem.oopspec = 'dict.setitem(d, key, value)'

def ll_dict_insertclean(d, key, value, hash):
    # Internal routine used by ll_dict_resize() to insert an item which is
    # known to be absent from the dict.  This routine also assumes that
    # the dict contains no deleted entries.  This routine has the advantage
    # of never calling d.keyhash() and d.keyeq(), so it cannot call back
    # to user code.  ll_dict_insertclean() doesn't resize the dict, either.
    entry = ll_dict_lookup_clean(d, hash)
    ENTRY = lltype.typeOf(entry).TO
    entry.value = value
    entry.key = key
    if hasattr(ENTRY, 'f_hash'):     entry.f_hash = hash
    if hasattr(ENTRY, 'f_valid'):    entry.f_valid = True
    if hasattr(ENTRY, 'f_everused'): entry.f_everused = True
    d.num_items += 1
    d.num_pristine_entries -= 1

def ll_dict_delitem(d, key):
    entry = ll_dict_lookup(d, key, d.keyhash(key))
    if not entry.valid():
        raise KeyError
    entry.mark_deleted()
    d.num_items -= 1
    # clear the key and the value if they are GC pointers
    ENTRY = lltype.typeOf(entry).TO
    if ENTRY.must_clear_key:
        key = entry.key   # careful about destructor side effects:
                          # keep key alive until entry.value has also
                          # been zeroed (if it must be)
        entry.key = lltype.nullptr(ENTRY.key.TO)
    if ENTRY.must_clear_value:
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
    d.entries = lltype.malloc(lltype.typeOf(old_entries).TO, new_size, zero=True)
    d.num_items = 0
    d.num_pristine_entries = new_size
    i = 0
    while i < old_size:
        entry = old_entries[i]
        if entry.valid():
            ll_dict_insertclean(d, entry.key, entry.value, entry.hash())
        i += 1

# ------- a port of CPython's dictobject.c's lookdict implementation -------
PERTURB_SHIFT = 5

def ll_dict_lookup(d, key, hash):
    DICT = lltype.typeOf(d).TO
    entries = d.entries
    mask = len(entries) - 1
    i = r_uint(hash & mask) 
    # do the first try before any looping 
    entry = entries[i]
    if entry.valid():
        checkingkey = entry.key
        if checkingkey == key:
            return entry   # found the entry
        if d.keyeq is not None and entry.hash() == hash:
            # correct hash, maybe the key is e.g. a different pointer to
            # an equal object
            found = d.keyeq(checkingkey, key)
            if DICT.paranoia:
                if (entries != d.entries or
                    not entry.valid() or entry.key != checkingkey):
                    # the compare did major nasty stuff to the dict: start over
                    return ll_dict_lookup(d, key, hash)
            if found:
                return entry   # found the entry
        freeslot = lltype.nullptr(lltype.typeOf(entry).TO)
    elif entry.everused():
        freeslot = entry
    else:
        return entry    # pristine entry -- lookup failed

    # In the loop, a deleted entry (everused and not valid) is by far
    # (factor of 100s) the least likely outcome, so test for that last.
    perturb = r_uint(hash) 
    while 1: 
        i = ((i << 2) + i + perturb + 1) & mask
        entry = entries[i]
        if not entry.everused():
            return freeslot or entry 
        elif entry.valid():
            checkingkey = entry.key
            if checkingkey == key:
                return entry
            if d.keyeq is not None and entry.hash() == hash:
                # correct hash, maybe the key is e.g. a different pointer to
                # an equal object
                found = d.keyeq(checkingkey, key)
                if DICT.paranoia:
                    if (entries != d.entries or
                        not entry.valid() or entry.key != checkingkey):
                        # the compare did major nasty stuff to the dict:
                        # start over
                        return ll_dict_lookup(d, key, hash)
                if found:
                    return entry   # found the entry
        elif not freeslot:
            freeslot = entry 
        perturb >>= PERTURB_SHIFT

def ll_dict_lookup_clean(d, hash):
    # a simplified version of ll_dict_lookup() which assumes that the
    # key is new, and the dictionary doesn't contain deleted entries.
    # It only find the next free slot for the given hash.
    entries = d.entries
    mask = len(entries) - 1
    i = r_uint(hash & mask) 
    entry = entries[i]
    perturb = r_uint(hash) 
    while entry.everused():
        i = ((i << 2) + i + perturb + 1) & mask
        entry = entries[i]
        perturb >>= PERTURB_SHIFT
    return entry

# ____________________________________________________________
#
#  Irregular operations.

DICT_INITSIZE = 8

def ll_newdict(DICT):
    d = lltype.malloc(DICT)
    d.entries = lltype.malloc(DICT.entries.TO, DICT_INITSIZE, zero=True)
    d.num_items = 0
    d.num_pristine_entries = DICT_INITSIZE
    return d
ll_newdict.oopspec = 'newdict()'

def ll_newdict_size(DICT, length_estimate):
    length_estimate = (length_estimate // 2) * 3
    n = DICT_INITSIZE
    while n < length_estimate:
        n *= 2
    d = lltype.malloc(DICT)
    d.entries = lltype.malloc(DICT.entries.TO, n, zero=True)
    d.num_items = 0
    d.num_pristine_entries = DICT_INITSIZE
    return d
ll_newdict_size.oopspec = 'newdict()'


def rtype_r_dict(hop):
    r_dict = hop.r_result
    if not r_dict.custom_eq_hash:
        raise TyperError("r_dict() call does not return an r_dict instance")
    v_eqfn, v_hashfn = hop.inputargs(r_dict.r_rdict_eqfn,
                                     r_dict.r_rdict_hashfn)
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
        self.ll_dictnext = ll_dictnext


def ll_dictiter(ITERPTR, d):
    iter = lltype.malloc(ITERPTR.TO)
    iter.dict = d
    iter.index = 0
    return iter

def ll_dictnext(iter, func, RETURNTYPE):
    dict = iter.dict
    if dict:
        entries = dict.entries
        index = iter.index
        entries_len = len(entries)
        while index < entries_len:
            entry = entries[index]
            index = index + 1
            if entry.valid():
                iter.index = index
                if RETURNTYPE is lltype.Void:
                    return None
                elif func is dum_items:
                    r = lltype.malloc(RETURNTYPE.TO)
                    r.item0 = recast(RETURNTYPE.TO.item0, entry.key)
                    r.item1 = recast(RETURNTYPE.TO.item1, entry.value)
                    return r
                elif func is dum_keys:
                    return entry.key
                elif func is dum_values:
                    return entry.value
        # clear the reference to the dict and prevent restarts
        iter.dict = lltype.nullptr(lltype.typeOf(iter).TO.dict.TO)
    raise StopIteration

# _____________________________________________________________
# methods

def ll_get(dict, key, default):
    entry = ll_dict_lookup(dict, key, dict.keyhash(key))
    if entry.valid():
        return entry.value
    else: 
        return default

def ll_setdefault(dict, key, default):
    entry = ll_dict_lookup(dict, key, dict.keyhash(key))
    if entry.valid():
        return entry.value
    else:
        ll_dict_setitem(dict, key, default)
        return default

def ll_copy(dict):
    DICT = lltype.typeOf(dict).TO
    dictsize = len(dict.entries)
    d = lltype.malloc(DICT)
    d.entries = lltype.malloc(DICT.entries.TO, dictsize, zero=True)
    d.num_items = dict.num_items
    d.num_pristine_entries = dict.num_pristine_entries
    if hasattr(DICT, 'fnkeyeq'):   d.fnkeyeq   = dict.fnkeyeq
    if hasattr(DICT, 'fnkeyhash'): d.fnkeyhash = dict.fnkeyhash
    i = 0
    while i < dictsize:
        d_entry = d.entries[i]
        entry = dict.entries[i]
        ENTRY = lltype.typeOf(entry).TO
        d_entry.key = entry.key
        if hasattr(ENTRY, 'f_valid'):    d_entry.f_valid    = entry.f_valid
        if hasattr(ENTRY, 'f_everused'): d_entry.f_everused = entry.f_everused
        d_entry.value = entry.value
        if hasattr(ENTRY, 'f_hash'):     d_entry.f_hash     = entry.f_hash
        i += 1
    return d

def ll_clear(d):
    if len(d.entries) == d.num_pristine_entries == DICT_INITSIZE:
        return
    DICT = lltype.typeOf(d).TO
    d.entries = lltype.malloc(DICT.entries.TO, DICT_INITSIZE, zero=True)
    d.num_items = 0
    d.num_pristine_entries = DICT_INITSIZE

def ll_update(dic1, dic2):
    entries = dic2.entries
    d2len = len(entries)
    i = 0
    while i < d2len:
        entry = entries[i]
        if entry.valid():
            ll_dict_setitem(dic1, entry.key, entry.value)
        i += 1

# this is an implementation of keys(), values() and items()
# in a single function.
# note that by specialization on func, three different
# and very efficient functions are created.

def recast(P, v):
    if isinstance(P, lltype.Ptr):
        return lltype.cast_pointer(P, v)
    else:
        return v

def ll_kvi(dic, LIST, func):
    res = LIST.ll_newlist(dic.num_items)
    entries = dic.entries
    dlen = len(entries)
    items = res.ll_items()
    i = 0
    p = 0
    while i < dlen:
        entry = entries[i]
        if entry.valid():
            ELEM = lltype.typeOf(items).TO.OF
            if ELEM is not lltype.Void:
                if func is dum_items:
                    r = lltype.malloc(ELEM.TO)
                    r.item0 = recast(ELEM.TO.item0, entry.key)
                    r.item1 = recast(ELEM.TO.item1, entry.value)
                    items[p] = r
                elif func is dum_keys:
                    items[p] = recast(ELEM, entry.key)
                elif func is dum_values:
                    items[p] = recast(ELEM, entry.value)
            p += 1
        i += 1
    return res

def ll_contains(d, key):
    entry = ll_dict_lookup(d, key, d.keyhash(key))
    return entry.valid()
ll_contains.oopspec = 'dict.contains(d, key)'
ll_contains.oopargcheck = lambda d, key: bool(d)
