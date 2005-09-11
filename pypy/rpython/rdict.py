from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython import rmodel, lltype
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython.objectmodel import hlinvoke
from pypy.rpython import rlist
from pypy.rpython import robject
from pypy.rpython import objectmodel

# ____________________________________________________________
#
#  generic implementation of RPython dictionary, with parametric DICTKEY and
#  DICTVALUE types.
#
#  XXX this should be re-optimized for specific types of keys; e.g.
#      for string keys we don't need the two boolean flags but can use
#      a NULL and a special 'dummy' keys.  Similarily, for immutable dicts,
#      the array should be inlined and num_pristine_entries is not needed.
#
#    struct dictentry {
#        DICTKEY key;
#        bool valid;      # to mark if the entry is filled
#        bool everused;   # to mark if the entry is or has ever been filled
#        DICTVALUE value;
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

class __extend__(annmodel.SomeDict):
    def rtyper_makerepr(self, rtyper):
        dictkey   = self.dictdef.dictkey
        dictvalue = self.dictdef.dictvalue
        s_key     = dictkey  .s_value
        s_value   = dictvalue.s_value
        if (s_key.__class__ is annmodel.SomeObject and s_key.knowntype == object and
            s_value.__class__ is annmodel.SomeObject and s_value.knowntype == object):
            return robject.pyobj_repr
        else:
            if dictkey.custom_eq_hash:
                custom_eq_hash = lambda: (rtyper.getrepr(dictkey.s_rdict_eqfn),
                                          rtyper.getrepr(dictkey.s_rdict_hashfn))
            else:
                custom_eq_hash = None
            return DictRepr(lambda: rtyper.getrepr(s_key),
                            lambda: rtyper.getrepr(s_value),
                            dictkey,
                            dictvalue,
                            custom_eq_hash)

    def rtyper_makekey(self):
        return (self.__class__, self.dictdef.dictkey, self.dictdef.dictvalue)

class DictRepr(rmodel.Repr):

    def __init__(self, key_repr, value_repr, dictkey=None, dictvalue=None,
                 custom_eq_hash=None):
        self.DICT = lltype.GcForwardReference()
        self.lowleveltype = lltype.Ptr(self.DICT)
        if not isinstance(key_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(key_repr)
            self._key_repr_computer = key_repr 
        else:
            self.key_repr = key_repr  
        if not isinstance(value_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(value_repr)
            self._value_repr_computer = value_repr 
        else:
            self.value_repr = value_repr  
        self.dictkey = dictkey
        self.dictvalue = dictvalue
        self.dict_cache = {}
        self.custom_eq_hash = custom_eq_hash is not None
        self._custom_eq_hash_repr = custom_eq_hash
        # setup() needs to be called to finish this initialization

    def _setup_repr(self):
        if 'key_repr' not in self.__dict__:
            self.key_repr = self._key_repr_computer()
        if 'value_repr' not in self.__dict__:
            self.value_repr = self._value_repr_computer()
        if isinstance(self.DICT, lltype.GcForwardReference):
            self.DICTKEY = self.key_repr.lowleveltype
            self.DICTVALUE = self.value_repr.lowleveltype
            self.DICTENTRY = lltype.Struct("dictentry", 
                                ("key", self.DICTKEY),
                                ("valid", lltype.Bool),
                                ("everused", lltype.Bool),
                                ("value", self.DICTVALUE))
            self.DICTENTRYARRAY = lltype.GcArray(self.DICTENTRY)
            fields =          [ ("num_items", lltype.Signed),
                                ("num_pristine_entries", lltype.Signed), 
                                ("entries", lltype.Ptr(self.DICTENTRYARRAY)) ]
            if self.custom_eq_hash:
                self.r_rdict_eqfn, self.r_rdict_hashfn = self._custom_eq_hash_repr()
                fields.extend([ ("fnkeyeq", self.r_rdict_eqfn.lowleveltype),
                                ("fnkeyhash", self.r_rdict_hashfn.lowleveltype) ])
            self.DICT.become(lltype.GcStruct("dicttable", *fields))
        if 'll_keyhash' not in self.__dict__ and not self.custom_eq_hash:
            # figure out which functions must be used to hash and compare keys
            self.ll_keyeq   = self.key_repr.get_ll_eq_function()   # can be None
            self.ll_keyhash = self.key_repr.get_ll_hash_function()

    def convert_const(self, dictobj):
        # get object from bound dict methods
        #dictobj = getattr(dictobj, '__self__', dictobj) 
        if dictobj is None:
            return nullptr(self.DICT)
        if not isinstance(dictobj, (dict, objectmodel.r_dict)):
            raise TyperError("expected a dict: %r" % (dictobj,))
        try:
            key = Constant(dictobj)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            if isinstance(dictobj, objectmodel.r_dict):
                l_eqfn   = self.r_rdict_eqfn  .convert_const(dictobj.key_eq)
                l_hashfn = self.r_rdict_hashfn.convert_const(dictobj.key_hash)
                l_dict = ll_newdict_custom_eq_hash(l_eqfn, l_hashfn, self)
                # a dummy object with ll_keyeq and ll_keyhash methods to
                # pass to ll_dict_setitem()
                class Dummy:
                    custom_eq_hash = False
                    def ll_keyeq(self, key1, key2):
                        # theory: ll_dict_lookup() will only see new items,
                        # which are never equal to any existing one
                        return False
                    def ll_keyhash(self, key):
                        return self.currenthash

                self.dict_cache[key] = l_dict 
                r_key = self.key_repr
                r_value = self.value_repr
                for dictkeycontainer, dictvalue in dictobj._dict.items():
                    dummy = Dummy()
                    dummy.currenthash = dictkeycontainer.hash
                    llkey = r_key.convert_const(dictkeycontainer.key)
                    llvalue = r_value.convert_const(dictvalue)
                    ll_dict_setitem(l_dict, llkey, llvalue, dummy)
                return l_dict

            else:
                l_dict = ll_newdict(self)
                self.dict_cache[key] = l_dict 
                r_key = self.key_repr
                r_value = self.value_repr
                for dictkey, dictvalue in dictobj.items():
                    llkey = r_key.convert_const(dictkey)
                    llvalue = r_value.convert_const(dictvalue)
                    ll_dict_setitem(l_dict, llkey, llvalue, self)
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
        crepr = hop.inputconst(lltype.Void, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_get, v_dict, v_key, v_default, crepr)

    def rtype_method_copy(self, hop):
        v_dict, = hop.inputargs(self)
        crepr = hop.inputconst(lltype.Void, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_copy, v_dict, crepr)

    def rtype_method_update(self, hop):
        v_dic1, v_dic2 = hop.inputargs(self, self)
        crepr = hop.inputconst(lltype.Void, self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_update, v_dic1, v_dic2, crepr)

    def _rtype_method_kvi(self, hop, spec):
        v_dic, = hop.inputargs(self)
        r_list = hop.r_result
        v_func = hop.inputconst(lltype.Void, spec)
        c1 = hop.inputconst(lltype.Void, r_list.lowleveltype)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_kvi, v_dic, c1, v_func)

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
        crepr = hop.inputconst(lltype.Void, r_dict)
        hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_dict_getitem, v_dict, v_key, crepr)

    def rtype_delitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        crepr = hop.inputconst(lltype.Void, r_dict)
        hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_dict_delitem, v_dict, v_key, crepr)

    def rtype_setitem((r_dict, r_key), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, r_dict.key_repr, r_dict.value_repr)
        crepr = hop.inputconst(lltype.Void, r_dict)
        hop.gendirectcall(ll_dict_setitem, v_dict, v_key, v_value, crepr)

    def rtype_contains((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        crepr = hop.inputconst(lltype.Void, r_dict)
        return hop.gendirectcall(ll_contains, v_dict, v_key, crepr)
        
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

def dum_keys(): pass
def dum_values(): pass
def dum_items():pass
dum_variant = {"keys":   dum_keys,
               "values": dum_values,
               "items":  dum_items}

def ll_dict_len(d):
    return d.num_items 

def ll_dict_is_true(d):
    # check if a dict is True, allowing for None
    return bool(d) and d.num_items != 0

def ll_dict_getitem(d, key, dictrepr):
    entry = ll_dict_lookup(d, key, dictrepr)
    if entry.valid:
        return entry.value 
    else: 
        raise KeyError 

def ll_dict_setitem(d, key, value, dictrepr):
    entry = ll_dict_lookup(d, key, dictrepr)
    entry.value = value
    if entry.valid:
        return
    entry.key = key 
    entry.valid = True
    d.num_items += 1
    if not entry.everused:
        entry.everused = True
        d.num_pristine_entries -= 1
        if d.num_pristine_entries <= len(d.entries) / 3:
            ll_dict_resize(d, dictrepr)

def ll_dict_delitem(d, key, dictrepr):
    entry = ll_dict_lookup(d, key, dictrepr)
    if not entry.valid:
        raise KeyError
    entry.valid = False
    d.num_items -= 1
    # clear the key and the value if they are pointers
    keytype = lltype.typeOf(entry).TO.key
    if isinstance(keytype, lltype.Ptr):
        key = entry.key   # careful about destructor side effects
        entry.key = lltype.nullptr(keytype.TO)
    valuetype = lltype.typeOf(entry).TO.value
    if isinstance(valuetype, lltype.Ptr):
        entry.value = lltype.nullptr(valuetype.TO)
    num_entries = len(d.entries)
    if num_entries > DICT_INITSIZE and d.num_items < num_entries / 4:
        ll_dict_resize(d, dictrepr)

def ll_dict_resize(d, dictrepr):
    old_entries = d.entries
    old_size = len(old_entries) 
    # make a 'new_size' estimate and shrink it if there are many
    # deleted entry markers
    new_size = old_size * 2
    while new_size > DICT_INITSIZE and d.num_items < new_size / 4:
        new_size /= 2
    d.entries = lltype.malloc(lltype.typeOf(old_entries).TO, new_size)
    d.num_pristine_entries = new_size - d.num_items
    i = 0
    while i < old_size:
        entry = old_entries[i]
        if entry.valid:
           new_entry = ll_dict_lookup(d, entry.key, dictrepr)
           new_entry.key = entry.key
           new_entry.value = entry.value
           new_entry.valid = True
           new_entry.everused = True
        i += 1

# ------- a port of CPython's dictobject.c's lookdict implementation -------
PERTURB_SHIFT = 5

def ll_dict_lookup(d, key, dictrepr):
    if dictrepr.custom_eq_hash:
        hash = hlinvoke(dictrepr.r_rdict_hashfn, d.fnkeyhash, key)
    else:
        hash = dictrepr.ll_keyhash(key)
    entries = d.entries
    mask = len(entries) - 1
    i = r_uint(hash & mask) 

    """XXX MUTATION PROTECTION!"""

    # do the first try before any looping 
    entry = entries[i]
    if entry.valid:
        if entry.key == key:
            return entry   # found the entry
        if dictrepr.custom_eq_hash:
            res = hlinvoke(dictrepr.r_rdict_eqfn, d.fnkeyeq, entry.key, key)
        else:
            res = dictrepr.ll_keyeq is not None and dictrepr.ll_keyeq(entry.key, key)
        if res:
            return entry   # found the entry
        freeslot = lltype.nullptr(lltype.typeOf(entry).TO)
    elif entry.everused:
        freeslot = entry
    else:
        return entry    # pristine entry -- lookup failed

    # In the loop, a deleted entry (everused and not valid) is by far
    # (factor of 100s) the least likely outcome, so test for that last.
    perturb = r_uint(hash) 
    while 1: 
        i = ((i << 2) + i + perturb + 1) & mask
        entry = entries[i]
        if not entry.everused:
            return freeslot or entry 
        elif entry.valid:
            if entry.key == key:
                return entry
            if dictrepr.custom_eq_hash:
                res = hlinvoke(dictrepr.r_rdict_eqfn, d.fnkeyeq, entry.key, key)
            else:
                res = dictrepr.ll_keyeq is not None and dictrepr.ll_keyeq(entry.key, key)
            if res:
                return entry
        elif not freeslot:
            freeslot = entry 
        perturb >>= PERTURB_SHIFT

# ____________________________________________________________
#
#  Irregular operations.

DICT_INITSIZE = 8

def ll_newdict(dictrepr):
    assert not dictrepr.custom_eq_hash     # use ll_newdict_custom_eq_hash() instead
    d = lltype.malloc(dictrepr.DICT)
    d.entries = lltype.malloc(dictrepr.DICTENTRYARRAY, DICT_INITSIZE)
    d.num_items = 0  # but still be explicit
    d.num_pristine_entries = DICT_INITSIZE
    return d

def ll_newdict_custom_eq_hash(eqfn, hashfn, dictrepr):
    assert dictrepr.custom_eq_hash
    d = lltype.malloc(dictrepr.DICT)
    d.entries = lltype.malloc(dictrepr.DICTENTRYARRAY, DICT_INITSIZE)
    d.num_items = 0  # but still be explicit
    d.num_pristine_entries = DICT_INITSIZE
    d.fnkeyeq = eqfn
    d.fnkeyhash = hashfn
    return d

def ll_copy_extra_data(targetdict, sourcedict, dictrepr):
    if dictrepr.custom_eq_hash:
        targetdict.fnkeyeq   = sourcedict.fnkeyeq
        targetdict.fnkeyhash = sourcedict.fnkeyhash

def rtype_newdict(hop):
    hop.inputargs()    # no arguments expected
    r_dict = hop.r_result
    if r_dict == robject.pyobj_repr: # special case: SomeObject: SomeObject dicts!
        cdict = hop.inputconst(robject.pyobj_repr, dict)
        return hop.genop('simple_call', [cdict], resulttype = robject.pyobj_repr)
    crepr = hop.inputconst(lltype.Void, r_dict)
    v_result = hop.gendirectcall(ll_newdict, crepr)
    return v_result

def rtype_r_dict(hop):
    r_dict = hop.r_result
    if not r_dict.custom_eq_hash:
        raise TyperError("r_dict() call does not return an r_dict instance")
    v_eqfn, v_hashfn = hop.inputargs(r_dict.r_rdict_eqfn,
                                     r_dict.r_rdict_hashfn)
    crepr = hop.inputconst(lltype.Void, r_dict)
    hop.exception_cannot_occur()
    v_result = hop.gendirectcall(ll_newdict_custom_eq_hash,
                                 v_eqfn, v_hashfn, crepr)
    return v_result

# ____________________________________________________________
#
#  Iteration.

class DictIteratorRepr(rmodel.IteratorRepr):

    def __init__(self, r_dict, variant="keys"):
        self.r_dict = r_dict
        self.variant = variant
        self.lowleveltype = lltype.Ptr(lltype.GcStruct('dictiter',
                                         ('dict', r_dict.lowleveltype),
                                         ('index', lltype.Signed)))

    def newiter(self, hop):
        v_dict, = hop.inputargs(self.r_dict)
        citerptr = hop.inputconst(lltype.Void, self.lowleveltype)
        return hop.gendirectcall(ll_dictiter, citerptr, v_dict)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
        r_list = hop.r_result
        v_func = hop.inputconst(lltype.Void, dum_variant[self.variant])
        c1 = hop.inputconst(lltype.Void, r_list.lowleveltype)
        hop.has_implicit_exception(StopIteration) # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_dictnext, v_iter, v_func, c1)

def ll_dictiter(ITERPTR, d):
    iter = lltype.malloc(ITERPTR.TO)
    iter.dict = d
    iter.index = 0
    return iter

def ll_dictnext(iter, func, RETURNTYPE):
    entries = iter.dict.entries
    index = iter.index
    entries_len = len(entries)
    while index < entries_len:
        entry = entries[index]
        index = index + 1
        if entry.valid:
            iter.index = index
            if func is dum_items:
                r = lltype.malloc(RETURNTYPE.TO)
                r.item0 = entry.key
                r.item1 = entry.value
                return r
            elif func is dum_keys:
                return entry.key
            elif func is dum_values:
                return entry.value
    iter.index = index
    raise StopIteration

# _____________________________________________________________
# methods

def ll_get(dict, key, default, dictrepr):
    entry = ll_dict_lookup(dict, key, dictrepr) 
    if entry.valid:
        return entry.value
    else: 
        return default

def ll_copy(dict, dictrepr):
    dictsize = len(dict.entries)
    d = lltype.malloc(dictrepr.DICT)
    d.entries = lltype.malloc(dictrepr.DICTENTRYARRAY, dictsize)
    d.num_items = dict.num_items
    d.num_pristine_entries = dict.num_pristine_entries
    ll_copy_extra_data(d, dict, dictrepr)
    i = 0
    while i < dictsize:
        d_entry = d.entries[i]
        entry = dict.entries[i]
        d_entry.key = entry.key
        d_entry.value = entry.value
        d_entry.valid = entry.valid
        d_entry.everused = entry.everused
        i += 1
    return d

def ll_clear(d):
    if len(d.entries) == d.num_pristine_entries == DICT_INITSIZE:
        return
    DICTPTR = lltype.typeOf(d)
    d.entries = lltype.malloc(DICTPTR.TO.entries.TO, DICT_INITSIZE)
    d.num_items = 0
    d.num_pristine_entries = DICT_INITSIZE

def ll_update(dic1, dic2, dictrepr):
    # XXX warning, no protection against ll_dict_setitem mutating dic2
    d2len = len(dic2.entries)
    entries = dic2.entries
    i = 0
    while i < d2len:
        entry = entries[i]
        if entry.valid:
            ll_dict_setitem(dic1, entry.key, entry.value, dictrepr)
        i += 1

# this is an implementation of keys(), values() and items()
# in a single function.
# note that by specialization on func, three different
# and very efficient functions are created.

def ll_kvi(dic, LISTPTR, func):
    res = rlist.ll_newlist(LISTPTR, dic.num_items)
    dlen = len(dic.entries)
    entries = dic.entries
    items = res.items
    i = 0
    p = 0
    while i < dlen:
        entry = entries[i]
        if entry.valid:
            if func is dum_items:
                r = lltype.malloc(LISTPTR.TO.items.TO.OF.TO)
                r.item0 = entry.key
                r.item1 = entry.value
                items[p] = r
            elif func is dum_keys:
                items[p] = entry.key
            elif func is dum_values:
                items[p] = entry.value
            p += 1
        i += 1
    return res

def ll_contains(d, key, dictrepr):
    entry = ll_dict_lookup(d, key, dictrepr)
    return entry.valid
