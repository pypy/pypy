from pypy.tool.pairtype import pairtype
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

    def convert_const(self, value):
        real_value = self.controller.convert(value)
        return self.r_real_obj.convert_const(real_value)

    def reveal(self, r):
        if r is not self:
            raise TyperError("expected %r, got %r" % (self, r))
        return self.s_real_obj, self.r_real_obj

    def rtype_getattr(self, hop):
        return self.controller.rtype_getattr(hop)

    def rtype_setattr(self, hop):
        return self.controller.rtype_setattr(hop)

    def rtype_is_true(self, hop):
        return self.controller.rtype_is_true(hop)

    def rtype_simple_call(self, hop):
        return self.controller.rtype_call(hop)


class __extend__(pairtype(ControlledInstanceRepr, Repr)):

    def rtype_getitem((r_controlled, r_key), hop):
        return r_controlled.controller.rtype_getitem(hop)

    def rtype_setitem((r_controlled, r_key), hop):
        return r_controlled.controller.rtype_setitem(hop)

    def rtype_delitem((r_controlled, r_key), hop):
        return r_controlled.controller.rtype_delitem(hop)


def rtypedelegate(callable, hop, revealargs=[0], revealresult=False):
    bk = hop.rtyper.annotator.bookkeeper
    c_meth = Constant(callable)
    s_meth = bk.immutablevalue(callable)
    hop2 = hop.copy()
    for index in revealargs:
        r_controlled = hop2.args_r[index]
        if not isinstance(r_controlled, ControlledInstanceRepr):
            raise TyperError("args_r[%d] = %r, expected ControlledInstanceRepr"
                             % (index, r_controlled))
        s_new, r_new = r_controlled.s_real_obj, r_controlled.r_real_obj
        hop2.args_s[index], hop2.args_r[index] = s_new, r_new
        v = hop2.args_v[index]
        if isinstance(v, Constant):
            real_value = r_controlled.controller.convert(v.value)
            hop2.args_v[index] = Constant(real_value)
    if revealresult:
        r_controlled = hop2.r_result
        if not isinstance(r_controlled, ControlledInstanceRepr):
            raise TyperError("r_result = %r, expected ControlledInstanceRepr"
                             % (r_controlled,))
        s_new, r_new = r_controlled.s_real_obj, r_controlled.r_real_obj
        hop2.s_result, hop2.r_result = s_new, r_new
    hop2.v_s_insertfirstarg(c_meth, s_meth)
    hop2.forced_opname = 'simple_call'
    return hop2.dispatch()
