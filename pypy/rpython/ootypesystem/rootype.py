from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr
from pypy.rpython.ootypesystem.ootype import Void
from pypy.annotation.pairtype import pairtype

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

class OOInstanceRepr(Repr):
    def __init__(self, ootype):
        self.lowleveltype = ootype

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
	s_inst = hop.args_s[0]
	meth = self.lowleveltype._lookup(attr)
	if meth is not None:
	    # just return instance - will be handled by simple_call
	    return hop.inputarg(hop.r_result, arg=0)
	self.lowleveltype._check_field(attr)
	vlist = hop.inputargs(self, Void)
	return hop.genop("oogetfield", vlist,
			 resulttype = hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
	self.lowleveltype._check_field(attr)
        vlist = hop.inputargs(self, Void, hop.args_r[2])
        return hop.genop('oosetfield', vlist)

class OOBoundMethRepr(Repr):
    def __init__(self, ootype, name):
        self.lowleveltype = ootype
	self.name = name

    def rtype_simple_call(self, hop):
	vlist = hop.inputargs(self, *hop.args_r[1:])
        cname = hop.inputconst(Void, self.name)
	return hop.genop("oosend", [cname]+vlist,
			 resulttype = hop.r_result.lowleveltype)
	

class __extend__(pairtype(OOInstanceRepr, OOBoundMethRepr)):

    def convert_from_to(_, v, llops):
        return v
