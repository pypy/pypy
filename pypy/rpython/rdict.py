from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.objectmodel import hlinvoke
from pypy.rpython import robject
from pypy.rlib import objectmodel
from pypy.rpython import rmodel


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
            return rtyper.type_system.rdict.DictRepr(rtyper,
                                                     lambda: rtyper.getrepr(s_key),
                                                     lambda: rtyper.getrepr(s_value),
                                                     dictkey,
                                                     dictvalue,
                                                     custom_eq_hash)

    def rtyper_makekey(self):
        self.dictdef.dictkey  .dont_change_any_more = True
        self.dictdef.dictvalue.dont_change_any_more = True
        return (self.__class__, self.dictdef.dictkey, self.dictdef.dictvalue)



class AbstractDictRepr(rmodel.Repr):

    def pickrepr(self, item_repr):
        if self.custom_eq_hash:
            return item_repr, item_repr
        else:
            return self._externalvsinternal(self.rtyper, item_repr)

    pickkeyrepr = pickrepr

    def compact_repr(self):
        return 'DictR %s %s' % (self.key_repr.compact_repr(), self.value_repr.compact_repr())

    def recast_value(self, llops, v):
        return llops.convertvar(v, self.value_repr, self.external_value_repr)

    def recast_key(self, llops, v):
        return llops.convertvar(v, self.key_repr, self.external_key_repr)


def rtype_newdict(hop):
    hop.inputargs()    # no arguments expected
    r_dict = hop.r_result
    if r_dict == robject.pyobj_repr: # special case: SomeObject: SomeObject dicts!
        cdict = hop.inputconst(robject.pyobj_repr, dict)
        return hop.genop('simple_call', [cdict], resulttype = robject.pyobj_repr)
    cDICT = hop.inputconst(lltype.Void, r_dict.DICT)
    v_result = hop.gendirectcall(hop.rtyper.type_system.rdict.ll_newdict, cDICT)
    return v_result


class AbstractDictIteratorRepr(rmodel.IteratorRepr):

    def newiter(self, hop):
        v_dict, = hop.inputargs(self.r_dict)
        citerptr = hop.inputconst(lltype.Void, self.lowleveltype)
        return hop.gendirectcall(self.ll_dictiter, citerptr, v_dict)

    def rtype_next(self, hop):
        variant = self.variant
        v_iter, = hop.inputargs(self)
        if variant in ('keys', 'values'):
            c1 = hop.inputconst(lltype.Void, None)
        else:
            c1 = hop.inputconst(lltype.Void, hop.r_result.lowleveltype)
        # record that we know about these two possible exceptions
        hop.has_implicit_exception(StopIteration)
        hop.has_implicit_exception(RuntimeError)
        hop.exception_is_here()
        v = hop.gendirectcall(self.ll_dictnext, c1, v_iter)
        if variant == 'keys':
            return self.r_dict.recast_key(hop.llops, v)
        elif variant == 'values':
            return self.r_dict.recast_value(hop.llops, v)
        else:
            return v
    
