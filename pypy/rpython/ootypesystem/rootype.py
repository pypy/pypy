from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import Void, Class, Object
from pypy.tool.pairtype import pairtype

class __extend__(annmodel.SomeOOObject):
    def rtyper_makerepr(self, rtyper):
        return ooobject_repr
    def rtyper_makekey(self):
        return self.__class__,

class __extend__(annmodel.SomeOOClass):
    def rtyper_makerepr(self, rtyper):
        return ooclass_repr
    def rtyper_makekey(self):
        return self.__class__,

class __extend__(annmodel.SomeOOInstance):
    def rtyper_makerepr(self, rtyper):
        return OOInstanceRepr(self.ootype)
    def rtyper_makekey(self):
        return self.__class__, self.ootype

class __extend__(annmodel.SomeOOBoundMeth):
    def rtyper_makerepr(self, rtyper):
        return OOBoundMethRepr(self.ootype, self.name)
    def rtyper_makekey(self):
        return self.__class__, self.ootype, self.name

class __extend__(annmodel.SomeOOStaticMeth):
    def rtyper_makerepr(self, rtyper):
        return OOStaticMethRepr(self.method)
    def rtyper_makekey(self):
        return self.__class__, self.method


class OOObjectRepr(Repr):
    lowleveltype = Object

    def rtype_is_true(self, hop):
        vlist = hop.inputargs(self)
        return hop.genop('oononnull', vlist, resulttype=ootype.Bool)
    
ooobject_repr = OOObjectRepr()

class OOClassRepr(Repr):
    lowleveltype = Class

    def rtype_is_true(self, hop):
        vlist = hop.inputargs(self)
        return hop.genop('oononnull', vlist, resulttype=ootype.Bool)
    
ooclass_repr = OOClassRepr()

class OOInstanceRepr(Repr):
    def __init__(self, ootype):
        self.lowleveltype = ootype

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        s_inst = hop.args_s[0]
        _, meth = self.lowleveltype._lookup(attr)
        if meth is not None:
            # just return instance - will be handled by simple_call
            return hop.inputarg(hop.r_result, arg=0)
        self.lowleveltype._check_field(attr)
        vlist = hop.inputargs(self, Void)
        return hop.genop("oogetfield", vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        if self.lowleveltype is Void:
            return
        attr = hop.args_s[1].const
        self.lowleveltype._check_field(attr)
        vlist = hop.inputargs(self, Void, hop.args_r[2])
        return hop.genop('oosetfield', vlist)

    def rtype_is_true(self, hop):
        vlist = hop.inputargs(self)
        return hop.genop('oononnull', vlist, resulttype=ootype.Bool)

    def convert_const(self, value):
        if value is None:
            return ootype.null(self.lowleveltype)
        else:
            return Repr.convert_const(self, value)


class __extend__(pairtype(OOInstanceRepr, OOInstanceRepr)):
    def rtype_is_((r_ins1, r_ins2), hop):
        # NB. this version performs no cast to the common base class
        vlist = hop.inputargs(r_ins1, r_ins2)
        return hop.genop('oois', vlist, resulttype=ootype.Bool)

    rtype_eq = rtype_is_

    def rtype_ne(rpair, hop):
        v = rpair.rtype_eq(hop)
        return hop.genop("bool_not", [v], resulttype=ootype.Bool)


class __extend__(pairtype(OOObjectRepr, OOObjectRepr)):
    def rtype_is_((r_obj1, r_obj2), hop):
        vlist = hop.inputargs(r_obj1, r_obj2)
        return hop.genop('oois', vlist, resulttype=ootype.Bool)

    rtype_eq = rtype_is_

    def rtype_ne(rpair, hop):
        v = rpair.rtype_eq(hop)
        return hop.genop("bool_not", [v], resulttype=ootype.Bool)


class __extend__(pairtype(OOClassRepr, OOClassRepr)):
    def rtype_is_((r_obj1, r_obj2), hop):
        vlist = hop.inputargs(r_obj1, r_obj2)
        return hop.genop('oois', vlist, resulttype=ootype.Bool)

    rtype_eq = rtype_is_

    def rtype_ne(rpair, hop):
        v = rpair.rtype_eq(hop)
        return hop.genop("bool_not", [v], resulttype=ootype.Bool)


class OOBoundMethRepr(Repr):
    def __init__(self, ootype, name):
        self.lowleveltype = ootype
        self.name = name

    def rtype_simple_call(self, hop):
        TYPE = hop.args_r[0].lowleveltype
        _, meth = TYPE._lookup(self.name)
        if isinstance(meth, ootype._overloaded_meth):
            ARGS = tuple([repr.lowleveltype for repr in hop.args_r[1:]])
            desc = meth._get_desc(self.name, ARGS)
            cname = hop.inputconst(Void, desc)
        else:
            cname = hop.inputconst(Void, self.name)
        vlist = hop.inputargs(self, *hop.args_r[1:])
        hop.exception_is_here()
        return hop.genop("oosend", [cname]+vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_call_args(self, hop):
        from pypy.rpython.rbuiltin import call_args_expand
        hop, _ = call_args_expand(hop, takes_kwds=False)
        hop.swap_fst_snd_args()
        hop.r_s_popfirstarg()
        return self.rtype_simple_call(hop)


class OOStaticMethRepr(Repr):
    def __init__(self, METHODTYPE):
        self.lowleveltype = METHODTYPE

    def rtype_simple_call(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        cgraphs = hop.inputconst(ootype.Void, None)
        vlist.append(cgraphs)
        hop.exception_is_here()
        return hop.genop("indirect_call", vlist, resulttype = hop.r_result.lowleveltype)

    def rtype_call_args(self, hop):
        from pypy.rpython.rbuiltin import call_args_expand
        hop, _ = call_args_expand(hop, takes_kwds=False)
        hop.swap_fst_snd_args()
        hop.r_s_popfirstarg()
        return self.rtype_simple_call(hop)

    def rtype_simple_call(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        nexpected = len(self.lowleveltype.ARGS)
        nactual = len(vlist)-1
        if nactual != nexpected: 
            raise TyperError("argcount mismatch:  expected %d got %d" %
                            (nexpected, nactual))
        if isinstance(vlist[0], flowmodel.Constant):
            if hasattr(vlist[0].value, 'graph'):
                hop.llops.record_extra_call(vlist[0].value.graph)
            opname = 'direct_call'
        else:
            opname = 'indirect_call'
            vlist.append(hop.inputconst(ootype.Void, None))
        hop.exception_is_here()
        return hop.genop(opname, vlist, resulttype = self.lowleveltype.RESULT)


class __extend__(pairtype(OOInstanceRepr, OOBoundMethRepr)):

    def convert_from_to(_, v, llops):
        return v
