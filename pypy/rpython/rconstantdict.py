from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython import rmodel, lltype
from pypy.rpython.rarithmetic import r_uint 

# ____________________________________________________________
#
#  pseudo implementation of RPython dictionary (this is per
#  dictkey/dictvalue but dictkeys need to be primitive) 
#
#    struct dictentry {
#        DICTKEY key;   # primitive 
#        bool valid;    # to mark if the entry is filled 
#        DICTVALUE value;  
#    }
#    
#    struct dicttable {
#        int num_items; 
#        Array entries; 
#    }
#

class ConstantDictRepr(rmodel.Repr):

    def __init__(self, key_repr, value_repr): 
        self.CONSTANTDICT = lltype.ForwardReference()
        self.lowleveltype = lltype.Ptr(self.CONSTANTDICT) 
        self.key_repr = key_repr  
        self.value_repr = value_repr  
        self.dict_cache = {}

    def setup(self):
        if isinstance(self.CONSTANTDICT, lltype.ForwardReference):
            self.DICTKEY = self.key_repr.lowleveltype
            self.DICTVALUE = self.value_repr.lowleveltype
            self.DICTENTRY = lltype.Struct("dictentry", 
                        ("key", self.DICTKEY), 
                        ("valid", lltype.Bool), 
                        ('value', self.DICTVALUE))
            self.DICTENTRYARRAY = lltype.Array(self.DICTENTRY)
            self.CONSTANTDICT.become(lltype.Struct("dicttable", 
                                ("num_items", lltype.Signed), 
                                ("entries", self.DICTENTRYARRAY)))

    def convert_const(self, dictobj):
        dictobj = getattr(dictobj, '__self__', dictobj) # bound dict methods
        if not isinstance(dictobj, dict):
            raise TyperError("expected a dict: %r" % (dictobj,))
        try:
            key = Constant(dictobj)
            return self.dict_cache[key]
        except KeyError:
            self.setup()
            dictlen = len(dictobj)
            minentrylen = dictlen * 4 / 3
            entrylen = 1
            while entrylen < minentrylen: 
                entrylen *= 2
            result = lltype.malloc(self.CONSTANTDICT, entrylen, immortal=True)
            self.dict_cache[key] = result
            r_key = self.key_repr
            r_value = self.value_repr
            hashcompute = self.get_key_hash_function()
            for dictkey, dictvalue in dictobj.items():
                llkey = r_key.convert_const(dictkey)
                llvalue = r_value.convert_const(dictvalue)
                ll_constantdict_setnewitem(result, llkey, llvalue, hashcompute)
            return result

    def get_key_hash_function(self):
        if isinstance(self.key_repr, rmodel.IntegerRepr):
            return ll_hash_identity
        elif isinstance(self.key_repr, rmodel.CharRepr):
            return ll_hash_char
        else:
            raise TyperError("no easy hash function for %r" % (self.key_repr,))

    def rtype_len(self, hop):
        v_dict, = hop.inputargs(self)
        return hop.gendirectcall(ll_constantdict_len, v_dict)

    #def make_iterator_repr(self):
    #    return StrDictIteratorRepr(self)

    #def rtype_method_get(self, hop):
    #    v_dict, v_key, v_default = hop.inputargs(self, string_repr,
    #                                             self.value_repr)
    #    return hop.gendirectcall(ll_get, v_dict, v_key, v_default)

class __extend__(pairtype(ConstantDictRepr, rmodel.Repr)): 

    def rtype_getitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr) 
        hashcompute = r_dict.get_key_hash_function()
        chashcompute = hop.inputconst(lltype.Void, hashcompute)
        return hop.gendirectcall(ll_constantdict_getitem, v_dict, v_key,
                                 chashcompute)

# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

def ll_constantdict_len(d):
    return d.num_items 

def ll_constantdict_getitem(d, key, hashcompute): 
    entry = ll_constantdict_lookup(d, key, hashcompute)
    if entry.valid:
        return entry.value 
    else: 
        raise KeyError 

def ll_constantdict_setnewitem(d, key, value, hashcompute): 
    entry = ll_constantdict_lookup(d, key, hashcompute)
    assert not entry.valid 
    entry.key = key
    entry.valid = True 
    entry.value = value 
    d.num_items += 1

# the below is a port of CPython's dictobject.c's lookdict implementation 
PERTURB_SHIFT = 5

def ll_constantdict_lookup(d, key, hashcompute): 
    hash = hashcompute(key) 
    entries = d.entries
    mask = len(entries) - 1
    perturb = r_uint(hash) 
    i = r_uint(hash) 
    while 1: 
        entry = entries[i & mask]
        if not entry.valid: 
            return entry 
        if entry.key == key: 
            return entry
        perturb >>= PERTURB_SHIFT
        i = (i << 2) + i + perturb + 1

def ll_hash_identity(x): 
    return x

def ll_hash_char(x): 
    return ord(x) 
