from pypy.objspace.flow.model import Constant
from pypy.rpython.rmodel import Repr
from pypy.rpython.error import TyperError


class ControlledInstanceRepr(Repr):

    def __init__(self, rtyper, s_real_obj, controller):
        self.rtyper = rtyper
        self.s_real_obj = s_real_obj
        self.r_real_obj = rtyper.getrepr(s_real_obj)
        self.controller = controller
        self.lowleveltype = self.r_real_obj.lowleveltype

    def rtypedelegate(self, boundmethod, hop,
                      revealargs=[0], revealresult=False):
        bk = self.rtyper.annotator.bookkeeper
        c_meth = Constant(boundmethod)
        s_meth = bk.immutablevalue(boundmethod)
        hop2 = hop.copy()
        for index in revealargs:
            s_new, r_new = self.reveal(hop2.args_r[index])
            hop2.args_s[index], hop2.args_r[index] = s_new, r_new
        if revealresult:
            hop2.s_result, hop2.r_result = self.reveal(hop2.r_result)
        hop2.v_s_insertfirstarg(c_meth, s_meth)
        hop2.forced_opname = 'simple_call'
        return hop2.dispatch()

    def reveal(self, r):
        if r is not self:
            raise TyperError("expected %r, got %r" % (self, r))
        return self.s_real_obj, self.r_real_obj

    def rtype_getattr(self, hop):
        return self.controller.rtype_getattr(hop)

    def rtype_setattr(self, hop):
        return self.controller.rtype_setattr(hop)
