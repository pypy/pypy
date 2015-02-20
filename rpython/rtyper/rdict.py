from rpython.annotator import model as annmodel
from rpython.rtyper import rmodel
from rpython.rtyper.lltypesystem import lltype


class __extend__(annmodel.SomeDict):
    def get_dict_repr(self):
        from rpython.rtyper.lltypesystem.rdict import DictRepr

        return DictRepr

    def rtyper_makerepr(self, rtyper):
        dictkey = self.dictdef.dictkey
        dictvalue = self.dictdef.dictvalue
        s_key = dictkey.s_value
        s_value = dictvalue.s_value
        force_non_null = self.dictdef.force_non_null
        if dictkey.custom_eq_hash:
            custom_eq_hash = lambda: (rtyper.getrepr(dictkey.s_rdict_eqfn),
                                      rtyper.getrepr(dictkey.s_rdict_hashfn))
        else:
            custom_eq_hash = None
        return self.get_dict_repr()(rtyper, lambda: rtyper.getrepr(s_key),
                        lambda: rtyper.getrepr(s_value), dictkey, dictvalue,
                        custom_eq_hash, force_non_null)

    def rtyper_makekey(self):
        self.dictdef.dictkey  .dont_change_any_more = True
        self.dictdef.dictvalue.dont_change_any_more = True
        return (self.__class__, self.dictdef.dictkey, self.dictdef.dictvalue)

class __extend__(annmodel.SomeOrderedDict):
    def get_dict_repr(self):
        from rpython.rtyper.lltypesystem.rordereddict import OrderedDictRepr

        return OrderedDictRepr

class AbstractDictRepr(rmodel.Repr):

    def pickrepr(self, item_repr):
        if self.custom_eq_hash:
            return item_repr, item_repr
        else:
            return self._externalvsinternal(self.rtyper, item_repr)

    pickkeyrepr = pickrepr

    def compact_repr(self):
        return 'DictR %s %s' % (self.key_repr.compact_repr(),
                                self.value_repr.compact_repr())

    def recast_value(self, llops, v):
        return llops.convertvar(v, self.value_repr, self.external_value_repr)

    def recast_key(self, llops, v):
        return llops.convertvar(v, self.key_repr, self.external_key_repr)


def rtype_newdict(hop):
    hop.inputargs()    # no arguments expected
    r_dict = hop.r_result
    cDICT = hop.inputconst(lltype.Void, r_dict.DICT)
    v_result = hop.gendirectcall(r_dict.ll_newdict, cDICT)
    return v_result


class AbstractDictIteratorRepr(rmodel.IteratorRepr):

    def newiter(self, hop):
        v_dict, = hop.inputargs(self.r_dict)
        citerptr = hop.inputconst(lltype.Void, self.lowleveltype)
        return hop.gendirectcall(self.ll_dictiter, citerptr, v_dict)

    def rtype_next(self, hop):
        variant = self.variant
        v_iter, = hop.inputargs(self)
        # record that we know about these two possible exceptions
        hop.has_implicit_exception(StopIteration)
        hop.has_implicit_exception(RuntimeError)
        hop.exception_is_here()
        v_index = hop.gendirectcall(self._ll_dictnext, v_iter)
        if variant == 'items' and hop.r_result.lowleveltype != lltype.Void:
            # this allocates the tuple for the result, directly in the function
            # where it will be used (likely).  This will let it be removed.
            c1 = hop.inputconst(lltype.Void, hop.r_result.lowleveltype.TO)
            cflags = hop.inputconst(lltype.Void, {'flavor': 'gc'})
            v_result = hop.genop('malloc', [c1, cflags],
                                 resulttype = hop.r_result.lowleveltype)
        DICT = self.lowleveltype.TO.dict
        c_dict = hop.inputconst(lltype.Void, 'dict')
        v_dict = hop.genop('getfield', [v_iter, c_dict], resulttype=DICT)
        ENTRIES = DICT.TO.entries
        c_entries = hop.inputconst(lltype.Void, 'entries')
        v_entries = hop.genop('getfield', [v_dict, c_entries],
                              resulttype=ENTRIES)
        if variant != 'values':
            KEY = ENTRIES.TO.OF.key
            c_key = hop.inputconst(lltype.Void, 'key')
            v_key = hop.genop('getinteriorfield', [v_entries, v_index, c_key],
                              resulttype=KEY)
        if variant != 'keys' and variant != 'reversed':
            VALUE = ENTRIES.TO.OF.value
            c_value = hop.inputconst(lltype.Void, 'value')
            v_value = hop.genop('getinteriorfield', [v_entries,v_index,c_value],
                                resulttype=VALUE)
        if variant == 'keys' or variant == 'reversed':
            return self.r_dict.recast_key(hop.llops, v_key)
        elif variant == 'values':
            return self.r_dict.recast_value(hop.llops, v_value)
        elif hop.r_result.lowleveltype == lltype.Void:
            return hop.inputconst(lltype.Void, None)
        else:
            assert variant == 'items'
            ITEM0 = v_result.concretetype.TO.item0
            ITEM1 = v_result.concretetype.TO.item1
            if ITEM0 != v_key.concretetype:
                v_key = hop.genop('cast_pointer', [v_key], resulttype=ITEM0)
            if ITEM1 != v_value.concretetype:
                v_value = hop.genop('cast_pointer', [v_value], resulttype=ITEM1)
            c_item0 = hop.inputconst(lltype.Void, 'item0')
            c_item1 = hop.inputconst(lltype.Void, 'item1')
            hop.genop('setfield', [v_result, c_item0, v_key])
            hop.genop('setfield', [v_result, c_item1, v_value])
            return v_result
