from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython import rmodel, lltype 
from pypy.rpython.rstr import STR, string_repr, ll_strhash 

# ____________________________________________________________
#
#  pseudo implementation of RPython dictionary (this is per
#  dictvalue type): 
#
#    struct dictentry {
#        struct STR *key; 
#        ### XXX? int state; 
#        DICTVALUE value;  
#    }
#    
#    struct dicttable {
#        int num_used_entries;
#        Array *entries; 
#    }
#
#

class __extend__(annmodel.SomeDict):
    def rtyper_makerepr(self, rtyper):
        s_key = self.dictdef.dictkey.s_value 
        if isinstance(s_key, annmodel.SomeString): 
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
            self.DICTENTRY = lltype.Struct("dictentry", ("key", lltype.Ptr(STR)), 
                                                        ('value', self.DICTVALUE))
            self.DICTENTRYARRAY = lltype.GcArray(self.DICTENTRY)
            self.STRDICT.become(lltype.GcStruct("dicttable", 
                                ("num_used_entries", lltype.Signed), 
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

    #def rtype_len(self, hop):
    #    v_lst, = hop.inputargs(self)
    #    return hop.gendirectcall(ll_len, v_lst)

class __extend__(pairtype(StrDictRepr, rmodel.StringRepr)): 

    def rtype_getitem((r_dict, r_string), hop):
        v_dict, v_key = hop.inputargs(r_dict, string_repr) 
        return hop.gendirectcall(ll_strdict_getitem, v_dict, v_key)

    def rtype_setitem((r_dict, r_string), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, string_repr, r_dict.value_repr) 
        hop.gendirectcall(ll_strdict_setitem, v_dict, v_key, v_value)
    
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

def ll_strdict_len(d):
    return d.num_used_entries 

def ll_strdict_getitem(d, key): 
    return d.entries[0].value 

def ll_strdict_setitem(d, key, value): 
    d.entries[0].key = key 
    d.entries[0].value = value 

# ____________________________________________________________
#
#  Irregular operations.

def ll_newstrdict(DICTPTR):
    d = lltype.malloc(DICTPTR.TO)
    d.entries = lltype.malloc(DICTPTR.TO.entries.TO, 8)  # everything is zeroed
    d.num_used_entries = 0  # but still be explicit
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

if 0: 
    class ListIteratorRepr(Repr):

        def __init__(self, r_list):
            self.r_list = r_list
            self.lowleveltype = lltype.Ptr(GcStruct('listiter',
                                             ('list', r_list.lowleveltype),
                                             ('index', Signed)))

        def newiter(self, hop):
            v_lst, = hop.inputargs(self.r_list)
            citerptr = hop.inputconst(Void, self.lowleveltype)
            return hop.gendirectcall(ll_listiter, citerptr, v_lst)

        def rtype_next(self, hop):
            v_iter, = hop.inputargs(self)
            return hop.gendirectcall(ll_listnext, v_iter)

    def ll_listiter(ITERPTR, lst):
        iter = malloc(ITERPTR.TO)
        iter.list = lst
        iter.index = 0
        return iter

    def ll_listnext(iter):
        l = iter.list
        index = iter.index
        if index >= len(l.items):
            raise StopIteration
        iter.index = index + 1
        return l.items[index]
