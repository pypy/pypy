from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pairtype
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.annlowlevel import cachedtype


class ControllerEntry(ExtRegistryEntry):

    def compute_result_annotation(self, *args_s):
        cls = self.instance
        controller = self.getcontroller(*args_s)
        s_real_obj = controller.ctrl_new(*args_s)
        return SomeControlledInstance(s_real_obj, controller)

    def getcontroller(self, *args_s):
        return self._controller_()

    def specialize_call(self, hop):
        controller = hop.s_result.controller
        return controller.rtype_new(hop)


class ControllerEntryForPrebuilt(ExtRegistryEntry):

    def compute_annotation(self):
        controller = self.getcontroller()
        real_obj = controller.convert(self.instance)
        s_real_obj = self.bookkeeper.immutablevalue(real_obj)
        return SomeControlledInstance(s_real_obj, controller)

    def getcontroller(self):
        return self._controller_()


class Controller(object):
    __metaclass__ = cachedtype

    def _freeze_(self):
        return True

    def ctrl_new(self, *args_s):
        return delegate(self.new, *args_s)

    def rtype_new(self, hop):
        r_controlled_instance = hop.r_result
        return r_controlled_instance.rtypedelegate(self.new, hop,
                                                   revealargs=[],
                                                   revealresult=True)

    def getattr(self, obj, attr):
        return getattr(self, 'get_' + attr)(obj)
    getattr._annspecialcase_ = 'specialize:arg(2)'

    def ctrl_getattr(self, s_obj, s_attr):
        return delegate(self.getattr, s_obj, s_attr)

    def rtype_getattr(self, hop):
        r_controlled_instance = hop.args_r[0]
        return r_controlled_instance.rtypedelegate(self.getattr, hop)

    def setattr(self, obj, attr, value):
        return getattr(self, 'set_' + attr)(obj, value)
    setattr._annspecialcase_ = 'specialize:arg(2)'

    def ctrl_setattr(self, s_obj, s_attr, s_value):
        return delegate(self.setattr, s_obj, s_attr, s_value)

    def rtype_setattr(self, hop):
        r_controlled_instance = hop.args_r[0]
        return r_controlled_instance.rtypedelegate(self.setattr, hop)


def delegate(boundmethod, *args_s):
    bk = getbookkeeper()
    s_meth = bk.immutablevalue(boundmethod)
    return bk.emulate_pbc_call(bk.position_key, s_meth, args_s,
                               callback = bk.position_key)

# ____________________________________________________________

class SomeControlledInstance(annmodel.SomeObject):

    def __init__(self, s_real_obj, controller):
        self.s_real_obj = s_real_obj
        self.controller = controller
        self.knowntype = controller.knowntype

    def rtyper_makerepr(self, rtyper):
        from pypy.rpython.rcontrollerentry import ControlledInstanceRepr
        return ControlledInstanceRepr(rtyper, self.s_real_obj, self.controller)

    def rtyper_makekey_ex(self, rtyper):
        real_key = rtyper.makekey(self.s_real_obj)
        return self.__class__, real_key, self.controller


class __extend__(SomeControlledInstance):

    def getattr(s_cin, s_attr):
        assert s_attr.is_constant()
        return s_cin.controller.ctrl_getattr(s_cin.s_real_obj, s_attr)

    def setattr(s_cin, s_attr, s_value):
        assert s_attr.is_constant()
        s_cin.controller.ctrl_setattr(s_cin.s_real_obj, s_attr, s_value)


class __extend__(pairtype(SomeControlledInstance, SomeControlledInstance)):

    def union((s_cin1, s_cin2)):
        if s_cin1.controller is not s_cin2.controller:
            raise annmodel.UnionError("different controller!")
        return SomeControlledInstance(annmodel.unionof(s_cin1.s_real_obj,
                                                       s_cin2.s_real_obj),
                                      s_cin1.controller)
