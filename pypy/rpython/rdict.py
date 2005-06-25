from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython import rmodel, lltype, rstr
from pypy.rpython.rstr import STR, string_repr
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython import rlist

# ____________________________________________________________
#
#  pseudo implementation of RPython dictionary (this is per
#  dictvalue type): 
#
#    struct dictentry {
#        struct STR *key; 
#        DICTVALUE value;  
#    }
#    
#    struct dicttable {
#        int num_items;
#        int num_pristine_entries;  # never used entries
#        Array *entries; 
#    }
#
#

class __extend__(annmodel.SomeDict):
    def rtyper_makerepr(self, rtyper):
        s_key = self.dictdef.dictkey.s_value 
        if isinstance(s_key, annmodel.SomeString): 
            if s_key.can_be_none():
                raise rmodel.TyperError("cannot make repr of dict with "
                                        "string-or-None keys")
            dictvalue = self.dictdef.dictvalue 
            return StrDictRepr(lambda: rtyper.getrepr(dictvalue.s_value), 
                               dictvalue)
        else: 
            raise rmodel.TyperError("cannot make repr of %r" %(self.dictdef,))

    def rtyper_makekey(self):
        return (self.dictdef.dictkey, self.dictdef.dictvalue)

class StrDictRepr(rmodel.Repr):

    def __init__(self, value_repr, dictvalue=None): 
        self.STRDICT = lltype.GcForwardReference()
        self.lowleveltype = lltype.Ptr(self.STRDICT) 
        if not isinstance(value_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(value_repr)
            self._value_repr_computer = value_repr 
        else:
            self.value_repr = value_repr  
        self.dictvalue = dictvalue
        #self.dict_cache = {}
        # setup() needs to be called to finish this initialization

    def setup(self):
        if 'value_repr' not in self.__dict__:
            self.value_repr = self._value_repr_computer()
        if isinstance(self.STRDICT, lltype.GcForwardReference):
            self.DICTVALUE = self.value_repr.lowleveltype
            self.DICTENTRY = lltype.Struct("dictentry", 
                        ("key", lltype.Ptr(STR)), 
                        ('value', self.DICTVALUE))
            self.DICTENTRYARRAY = lltype.GcArray(self.DICTENTRY)
            self.STRDICT.become(lltype.GcStruct("dicttable", 
                                ("num_items", lltype.Signed), 
                                ("num_pristine_entries", lltype.Signed), 
                                ("entries", lltype.Ptr(self.DICTENTRYARRAY))))

    #def convert_const(self, dictobj):
    #    dictobj = getattr(dictobj, '__self__', dictobj) # for bound list methods
    #    if not isinstance(dictobj, list):
    #        raise TyperError("expected a list: %r" % (dictobj,))
    #    try:
    #        key = Constant(dictobj)
    #        return self.list_cache[key]
    #    except KeyError:
    #        self.setup()
    #        result = malloc(self.STRDICT, immortal=True)
    #        self.list_cache[key] = result
    #        result.items = malloc(self.STRDICT.items.TO, len(dictobj))
    #        r_item = self.value_repr
    #        for i in range(len(dictobj)):
    #            x = dictobj[i]
    #            result.items[i] = r_item.convert_const(x)
    #        return result

    def rtype_len(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_strdict_len, v_dict)

    def make_iterator_repr(self):
        return StrDictIteratorRepr(self)

    def rtype_method_get(self, hop):
        v_dict, v_key, v_default = hop.inputargs(self, string_repr,
                                                 self.value_repr)
        return hop.gendirectcall(ll_get, v_dict, v_key, v_default)

    def rtype_method_copy(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_copy, v_dict)

    def rtype_method_update(self, hop):
        v_dic1, v_dic2 = hop.inputargs(self, self)
        return hop.gendirectcall(ll_update, v_dic1, v_dic2)

    def _rtype_method_kvi(self, hop, spec):
        v_dic, = hop.inputargs(self)
        r_list = hop.r_result
        v_func = hop.inputconst(lltype.Void, spec)
        c1 = hop.inputconst(lltype.Void, r_list.lowleveltype)
        return hop.gendirectcall(ll_kvi, v_dic, c1, v_func)

    def rtype_method_keys(self, hop):
        return self._rtype_method_kvi(hop, dum_keys)

    def rtype_method_values(self, hop):
        return self._rtype_method_kvi(hop, dum_values)

    def rtype_method_items(self, hop):
        return self._rtype_method_kvi(hop, dum_items)

class __extend__(pairtype(StrDictRepr, rmodel.StringRepr)): 

    def rtype_getitem((r_dict, r_string), hop):
        v_dict, v_key = hop.inputargs(r_dict, string_repr)
        return hop.gendirectcall(ll_strdict_getitem, v_dict, v_key)

    def rtype_delitem((r_dict, r_string), hop):
        v_dict, v_key = hop.inputargs(r_dict, string_repr) 
        return hop.gendirectcall(ll_strdict_delitem, v_dict, v_key)

    def rtype_setitem((r_dict, r_string), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, string_repr, r_dict.value_repr) 
        hop.gendirectcall(ll_strdict_setitem, v_dict, v_key, v_value)

    def rtype_contains((r_dict, r_string), hop):
        v_dict, v_key = hop.inputargs(r_dict, string_repr)
        return hop.gendirectcall(ll_contains, v_dict, v_key)
        
class __extend__(pairtype(StrDictRepr, StrDictRepr)):
    def convert_from_to((r_dict1, r_dict2), v, llops):
        # check that we don't convert from StrDicts with
        # different value types 
        if r_dict1.dictvalue is None or r_dict2.dictvalue is None:
            return NotImplemented
        if r_dict1.dictvalue is not r_dict2.dictvalue:
            return NotImplemented
        return v

    #def rtype_add((self, _), hop):
    #    v_lst1, v_lst2 = hop.inputargs(self, self)
    #    return hop.gendirectcall(ll_concat, v_lst1, v_lst2)
#
#    def rtype_inplace_add((self, _), hop):
#        v_lst1, v_lst2 = hop.inputargs(self, self)
#        hop.gendirectcall(ll_extend, v_lst1, v_lst2)
#        return v_lst1

# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

deleted_entry_marker = lltype.malloc(STR, 0, immortal=True)

def ll_strdict_len(d):
    return d.num_items 

def ll_strdict_getitem(d, key): 
    entry = ll_strdict_lookup(d, key) 
    if entry.key and entry.key != deleted_entry_marker: 
        return entry.value 
    else: 
        raise KeyError 

def ll_strdict_setitem(d, key, value): 
    entry = ll_strdict_lookup(d, key)
    if not entry.key: 
        entry.key = key 
        entry.value = value 
        d.num_items += 1
        d.num_pristine_entries -= 1
        if d.num_pristine_entries <= len(d.entries) / 3:
            ll_strdict_resize(d)
    elif entry.key == deleted_entry_marker: 
        entry.key = key 
        entry.value = value 
        d.num_items += 1
    else:
        entry.value = value 

def ll_strdict_delitem(d, key): 
    entry = ll_strdict_lookup(d, key)
    if not entry.key or entry.key == deleted_entry_marker: 
         raise KeyError
    entry.key = deleted_entry_marker
    valuetype = lltype.typeOf(entry).TO.value
    if isinstance(valuetype, lltype.Ptr):
        entry.value = lltype.nullptr(valuetype.TO)
    d.num_items -= 1
    num_entries = len(d.entries)
    if num_entries > STRDICT_INITSIZE and d.num_items < num_entries / 4: 
        ll_strdict_resize(d) 

def ll_strdict_resize(d):
    old_entries = d.entries
    old_size = len(old_entries) 
    # make a 'new_size' estimate and shrink it if there are many
    # deleted entry markers
    new_size = old_size * 2
    while new_size > STRDICT_INITSIZE and d.num_items < new_size / 4:
        new_size /= 2
    d.entries = lltype.malloc(lltype.typeOf(old_entries).TO, new_size)
    d.num_pristine_entries = new_size - d.num_items
    i = 0
    while i < old_size:
        entry = old_entries[i]
        if entry.key and entry.key != deleted_entry_marker:
           new_entry = ll_strdict_lookup(d, entry.key)
           new_entry.key = entry.key
           new_entry.value = entry.value
        i += 1

# the below is a port of CPython's dictobject.c's lookdict implementation 
PERTURB_SHIFT = 5

def ll_strdict_lookup(d, key): 
    hash = rstr.ll_strhash(key) 
    entries = d.entries
    mask = len(entries) - 1
    i = r_uint(hash & mask) 

    # do the first try before any looping 
    entry = entries[i]
    if not entry.key or entry.key == key: 
        return entry 
    if entry.key == deleted_entry_marker: 
        freeslot = entry 
    else: 
        if entry.key.hash == hash and rstr.ll_streq(entry.key, key): 
            return entry 
        freeslot = lltype.nullptr(lltype.typeOf(entry).TO)

    # In the loop, key == deleted_entry_marker is by far (factor of 100s) the
    # least likely outcome, so test for that last.  
    perturb = r_uint(hash) 
    while 1: 
        i = (i << 2) + i + perturb + 1
        entry = entries[i & mask]
        if not entry.key: 
            return freeslot or entry 
        if entry.key == key or (entry.key.hash == hash and 
                                entry.key != deleted_entry_marker and
                                rstr.ll_streq(entry.key, key)): 
            return entry
        if entry.key == deleted_entry_marker and not freeslot:
            freeslot = entry 
        perturb >>= PERTURB_SHIFT

# ____________________________________________________________
#
#  Irregular operations.
STRDICT_INITSIZE = 8

def ll_newstrdict(DICTPTR):
    d = lltype.malloc(DICTPTR.TO)
    d.entries = lltype.malloc(DICTPTR.TO.entries.TO, STRDICT_INITSIZE)
    d.num_items = 0  # but still be explicit
    d.num_pristine_entries = STRDICT_INITSIZE 
    return d

def rtype_newdict(hop):
    r_dict = hop.r_result
    if not isinstance(r_dict, StrDictRepr):
        raise rmodel.TyperError("cannot create non-StrDicts, got %r" %(r_dict,))
    c1 = hop.inputconst(lltype.Void, r_dict.lowleveltype)
    v_result = hop.gendirectcall(ll_newstrdict, c1) 
    return v_result

# ____________________________________________________________
#
#  Iteration.

class StrDictIteratorRepr(rmodel.Repr):

    def __init__(self, r_dict):
        self.r_dict = r_dict
        self.lowleveltype = lltype.Ptr(lltype.GcStruct('strdictiter',
                                         ('dict', r_dict.lowleveltype),
                                         ('index', lltype.Signed)))

    def newiter(self, hop):
        v_dict, = hop.inputargs(self.r_dict)
        citerptr = hop.inputconst(lltype.Void, self.lowleveltype)
        return hop.gendirectcall(ll_strdictiter, citerptr, v_dict)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
        return hop.gendirectcall(ll_strdictnext, v_iter)

def ll_strdictiter(ITERPTR, d):
    iter = lltype.malloc(ITERPTR.TO)
    iter.dict = d
    iter.index = 0
    return iter

def ll_strdictnext(iter):
    entries = iter.dict.entries
    index = iter.index
    entries_len = len(entries)
    while index < entries_len:
        key = entries[index].key
        index = index + 1
        if key and key != deleted_entry_marker:
            iter.index = index
            return key
    iter.index = index
    raise StopIteration

# _____________________________________________________________
# methods

def ll_get(v_dict, v_key, v_default):
    entry = ll_strdict_lookup(v_dict, v_key) 
    if entry.key and entry.key != deleted_entry_marker: 
        return entry.value
    else: 
        return v_default

def ll_copy(v_dict):
    DICTPTR = lltype.typeOf(v_dict)
    d = lltype.malloc(DICTPTR.TO)
    d.entries = lltype.malloc(DICTPTR.TO.entries.TO, len(v_dict.entries))
    d.num_items = v_dict.num_items
    d.num_pristine_entries = v_dict.num_pristine_entries
    i = 0
    dictlen = len(d.entries)
    while i < dictlen:
        d_entry = d.entries[i]
        v_entry = v_dict.entries[i]
        d_entry.key = v_entry.key
        d_entry.value = v_entry.value
        i += 1
    return d

def ll_update(v_dic1, v_dic2):
    d2len =len(v_dic2.entries)
    entries = v_dic2.entries
    i = 0
    while i < d2len:
        entry = entries[i]
        if entry.key and entry.key != deleted_entry_marker:
            ll_strdict_setitem(v_dic1, entry.key, entry.value)
        i += 1

def dum_keys(): pass
def dum_values(): pass
def dum_items():pass

# this is an implementation of keys(), values() and items()
# in a single function.
# note that by specialization on v_func, three different
# and very efficient functions are created.

def ll_kvi(v_dic, LISTPTR, v_func):
    res = rlist.ll_newlist(LISTPTR, v_dic.num_items)
    dlen = len(v_dic.entries)
    entries = v_dic.entries
    items = res.items
    i = 0
    p = 0
    while i < dlen:
        entry = entries[i]
        key = entry.key
        if key and key != deleted_entry_marker:
            if v_func is dum_items:
                r = lltype.malloc(LISTPTR.TO.items.TO.OF.TO)
                r.item0 = key
                r.item1 = entry.value
                items[p] = r
            elif v_func is dum_keys:
                items[p] = key
            elif v_func is dum_values:
                items[p] = entry.value
            p += 1
        i += 1
    return res

def ll_contains(d, key): 
    entry = ll_strdict_lookup(d, key) 
    if entry.key and entry.key != deleted_entry_marker: 
        return True
    return False
