from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rclass, rdict
from pypy.rpython.lltypesystem.llmemory import weakref_create, weakref_deref
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rlib.rweakref import RWeakValueDictionary
from pypy.rlib import jit


class WeakValueDictRepr(Repr):
    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.lowleveltype = lltype.Ptr(WEAKDICT)
        self.dict_cache = {}

    def convert_const(self, weakdict):
        if not isinstance(weakdict, RWeakValueDictionary):
            raise TyperError("expected an RWeakValueDictionary: %r" % (
                weakdict,))
        try:
            key = Constant(weakdict)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            l_dict = ll_new_weakdict()
            self.dict_cache[key] = l_dict
            bk = self.rtyper.annotator.bookkeeper
            classdef = bk.getuniqueclassdef(weakdict._valueclass)
            r_key = rstr.string_repr
            r_value = getinstancerepr(self.rtyper, classdef)
            for dictkey, dictvalue in weakdict._dict.items():
                llkey = r_key.convert_const(dictkey)
                llvalue = r_value.convert_const(dictvalue)
                if llvalue:
                    llvalue = lltype.cast_pointer(rclass.OBJECTPTR, llvalue)
                    ll_set_nonnull(l_dict, llkey, llvalue)
            return l_dict

    def rtype_method_get(self, hop):
        v_d, v_key = hop.inputargs(self, rstr.string_repr)
        hop.exception_cannot_occur()
        v_result = hop.gendirectcall(ll_get, v_d, v_key)
        v_result = hop.genop("cast_pointer", [v_result],
                             resulttype=hop.r_result.lowleveltype)
        return v_result

    def rtype_method_set(self, hop):
        v_d, v_key, v_value = hop.inputargs(self, rstr.string_repr,
                                            hop.args_r[2])
        hop.exception_cannot_occur()
        if hop.args_s[2].is_constant() and hop.args_s[2].const is None:
            hop.gendirectcall(ll_set_null, v_d, v_key)
        else:
            v_value = hop.genop("cast_pointer", [v_value],
                                resulttype=rclass.OBJECTPTR)
            hop.gendirectcall(ll_set, v_d, v_key, v_value)


def specialize_make_weakdict(hop):
    hop.exception_cannot_occur()
    v_d = hop.gendirectcall(ll_new_weakdict)
    return v_d

# ____________________________________________________________


WEAKDICTENTRY = lltype.Struct("weakdictentry",
                              ("key", lltype.Ptr(rstr.STR)),
                              ("value", llmemory.WeakRefPtr))

def ll_valid(entries, i):
    return (bool(entries[i].value) and
            bool(weakref_deref(rclass.OBJECTPTR, entries[i].value)))

def ll_everused(entries, i):
    return bool(entries[i].value)

def ll_hash(entries, i):
    return str_fasthashfn(entries[i].key)
str_fasthashfn = rstr.string_repr.get_ll_fasthash_function()

entrymeths = {
    'allocate': lltype.typeMethod(rdict._ll_malloc_entries),
    'delete': rdict._ll_free_entries,
    'valid': ll_valid,
    'everused': ll_everused,
    'hash': ll_hash,
    }
WEAKDICTENTRYARRAY = lltype.GcArray(WEAKDICTENTRY,
                                    adtmeths=entrymeths,
                                    hints={'weakarray': 'value'})

ll_strhash = rstr.LLHelpers.ll_strhash

@jit.dont_look_inside
def ll_new_weakdict():
    d = lltype.malloc(WEAKDICT)
    d.entries = WEAKDICT.entries.TO.allocate(rdict.DICT_INITSIZE)
    d.num_items = 0
    d.num_pristine_entries = rdict.DICT_INITSIZE
    return d

@jit.dont_look_inside
def ll_get(d, llkey):
    hash = ll_strhash(llkey)
    i = rdict.ll_dict_lookup(d, llkey, hash)
    #llop.debug_print(lltype.Void, i, 'get')
    valueref = d.entries[i].value
    if valueref:
        return weakref_deref(rclass.OBJECTPTR, valueref)
    else:
        return lltype.nullptr(rclass.OBJECTPTR.TO)

@jit.dont_look_inside
def ll_set(d, llkey, llvalue):
    if llvalue:
        ll_set_nonnull(d, llkey, llvalue)
    else:
        ll_set_null(d, llkey)

@jit.dont_look_inside
def ll_set_nonnull(d, llkey, llvalue):
    hash = ll_strhash(llkey)
    valueref = weakref_create(llvalue)    # GC effects here, before the rest
    i = rdict.ll_dict_lookup(d, llkey, hash)
    everused = d.entries.everused(i)
    d.entries[i].key = llkey
    d.entries[i].value = valueref
    #llop.debug_print(lltype.Void, i, 'stored')
    if not everused:
        d.num_pristine_entries -= 1
        if d.num_pristine_entries <= len(d.entries) / 3:
            #llop.debug_print(lltype.Void, 'RESIZE')
            ll_weakdict_resize(d)

@jit.dont_look_inside
def ll_set_null(d, llkey):
    hash = ll_strhash(llkey)
    i = rdict.ll_dict_lookup(d, llkey, hash)
    if d.entries.everused(i):
        # If the entry was ever used, clean up its key and value.
        # We don't store a NULL value, but a dead weakref, because
        # the entry must still be marked as everused().
        d.entries[i].value = llmemory.dead_wref
        d.entries[i].key = lltype.nullptr(rstr.STR)
        #llop.debug_print(lltype.Void, i, 'zero')

def ll_weakdict_resize(d):
    # first set num_items to its correct, up-to-date value
    entries = d.entries
    num_items = 0
    for i in range(len(entries)):
        if entries.valid(i):
            num_items += 1
    d.num_items = num_items
    rdict.ll_dict_resize(d)

str_keyeq = lltype.staticAdtMethod(rstr.string_repr.get_ll_eq_function())

dictmeths = {
    'll_get': ll_get,
    'll_set': ll_set,
    'keyeq': str_keyeq,
    'paranoia': False,
    }

WEAKDICT = lltype.GcStruct("weakdict",
                           ("num_items", lltype.Signed),
                           ("num_pristine_entries", lltype.Signed),
                           ("entries", lltype.Ptr(WEAKDICTENTRYARRAY)),
                           adtmeths=dictmeths)
