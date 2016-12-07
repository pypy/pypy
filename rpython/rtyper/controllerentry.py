from rpython.annotator import model as annmodel
from rpython.tool.pairtype import pairtype
from rpython.annotator.bookkeeper import getbookkeeper
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.annlowlevel import cachedtype
from rpython.rtyper.error import TyperError


class ControllerEntry(ExtRegistryEntry):

    def compute_result_annotation(self, *args_s, **kwds_s):
        controller = self.getcontroller(*args_s, **kwds_s)
        if kwds_s:
            raise TypeError("cannot handle keyword arguments in %s" % (
                self.new,))
        s_real_obj = delegate(controller.new, *args_s)
        if s_real_obj == annmodel.s_ImpossibleValue:
            return annmodel.s_ImpossibleValue
        else:
            return SomeControlledInstance(s_real_obj, controller)

    def getcontroller(self, *args_s, **kwds_s):
        return self._controller_()

    def specialize_call(self, hop, **kwds_i):
        from rpython.rtyper.rcontrollerentry import rtypedelegate
        if hop.s_result == annmodel.s_ImpossibleValue:
            raise TyperError("object creation always raises: %s" % (
                hop.spaceop,))
        assert not kwds_i
        controller = hop.s_result.controller
        return rtypedelegate(controller.new, hop, revealargs=[],
            revealresult=True)


def controlled_instance_box(controller, obj):
    XXX  # only for special-casing by ExtRegistryEntry below

def controlled_instance_unbox(controller, obj):
    XXX  # only for special-casing by ExtRegistryEntry below

def controlled_instance_is_box(controller, obj):
    XXX  # only for special-casing by ExtRegistryEntry below


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
    can_be_None = False

    def _freeze_(self):
        return True

    def box(self, obj):
        return controlled_instance_box(self, obj)
    box._annspecialcase_ = 'specialize:arg(0)'

    def unbox(self, obj):
        return controlled_instance_unbox(self, obj)
    unbox._annspecialcase_ = 'specialize:arg(0)'

    def is_box(self, obj):
        return controlled_instance_is_box(self, obj)
    is_box._annspecialcase_ = 'specialize:arg(0)'

    def getattr(self, obj, attr):
        return getattr(self, 'get_' + attr)(obj)
    getattr._annspecialcase_ = 'specialize:arg(0, 2)'

    def setattr(self, obj, attr, value):
        return getattr(self, 'set_' + attr)(obj, value)
    setattr._annspecialcase_ = 'specialize:arg(0, 2)'


def delegate(boundmethod, *args_s):
    bk = getbookkeeper()
    s_meth = bk.immutablevalue(boundmethod)
    return bk.emulate_pbc_call(bk.position_key, s_meth, args_s,
                               callback = bk.position_key)

class BoxEntry(ExtRegistryEntry):
    _about_ = controlled_instance_box

    def compute_result_annotation(self, s_controller, s_real_obj):
        if s_real_obj == annmodel.s_ImpossibleValue:
            return annmodel.s_ImpossibleValue
        else:
            assert s_controller.is_constant()
            controller = s_controller.const
            return SomeControlledInstance(s_real_obj, controller=controller)

    def specialize_call(self, hop):
        from rpython.rtyper.rcontrollerentry import ControlledInstanceRepr
        if not isinstance(hop.r_result, ControlledInstanceRepr):
            raise TyperError("box() should return ControlledInstanceRepr,\n"
                             "got %r" % (hop.r_result,))
        hop.exception_cannot_occur()
        return hop.inputarg(hop.r_result.r_real_obj, arg=1)

class UnboxEntry(ExtRegistryEntry):
    _about_ = controlled_instance_unbox

    def compute_result_annotation(self, s_controller, s_obj):
        if s_obj == annmodel.s_ImpossibleValue:
            return annmodel.s_ImpossibleValue
        else:
            assert isinstance(s_obj, SomeControlledInstance)
            return s_obj.s_real_obj

    def specialize_call(self, hop):
        from rpython.rtyper.rcontrollerentry import ControlledInstanceRepr
        if not isinstance(hop.args_r[1], ControlledInstanceRepr):
            raise TyperError("unbox() should take a ControlledInstanceRepr,\n"
                             "got %r" % (hop.args_r[1],))
        hop.exception_cannot_occur()
        v = hop.inputarg(hop.args_r[1], arg=1)
        return hop.llops.convertvar(v, hop.args_r[1].r_real_obj, hop.r_result)

class IsBoxEntry(ExtRegistryEntry):
    _about_ = controlled_instance_is_box

    def compute_result_annotation(self, s_controller, s_obj):
        if s_obj == annmodel.s_ImpossibleValue:
            return annmodel.s_ImpossibleValue
        else:
            assert s_controller.is_constant()
            controller = s_controller.const
            result = (isinstance(s_obj, SomeControlledInstance) and
                      s_obj.controller == controller)
            return self.bookkeeper.immutablevalue(result)

    def specialize_call(self, hop):
        from rpython.rtyper.lltypesystem import lltype
        assert hop.s_result.is_constant()
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Bool, hop.s_result.const)

# ____________________________________________________________

class SomeControlledInstance(annmodel.SomeObject):

    def __init__(self, s_real_obj, controller):
        self.s_real_obj = s_real_obj
        self.controller = controller
        self.knowntype = controller.knowntype

    def can_be_none(self):
        return self.controller.can_be_None

    def noneify(self):
        return SomeControlledInstance(self.s_real_obj, self.controller)

    def rtyper_makerepr(self, rtyper):
        from rpython.rtyper.rcontrollerentry import ControlledInstanceRepr
        return ControlledInstanceRepr(rtyper, self.s_real_obj, self.controller)

    def rtyper_makekey(self):
        real_key = self.s_real_obj.rtyper_makekey()
        return self.__class__, real_key, self.controller

    def getattr(self, s_attr):
        assert s_attr.is_constant()
        ctrl = self.controller
        return delegate(ctrl.getattr, self.s_real_obj, s_attr)

    def setattr(self, s_attr, s_value):
        assert s_attr.is_constant()
        ctrl = self.controller
        return delegate(ctrl.setattr, self.s_real_obj, s_attr, s_value)

    def bool(self):
        ctrl = self.controller
        return delegate(ctrl.bool, self.s_real_obj)

    def simple_call(self, *args_s):
        return delegate(self.controller.call, self.s_real_obj, *args_s)


class __extend__(pairtype(SomeControlledInstance, annmodel.SomeObject)):

    def getitem((s_cin, s_key)):
        return delegate(s_cin.controller.getitem, s_cin.s_real_obj, s_key)

    def setitem((s_cin, s_key), s_value):
        delegate(s_cin.controller.setitem, s_cin.s_real_obj, s_key, s_value)

    def delitem((s_cin, s_key)):
        delegate(s_cin.controller.delitem, s_cin.s_real_obj, s_key)


class __extend__(pairtype(SomeControlledInstance, SomeControlledInstance)):

    def union((s_cin1, s_cin2)):
        if s_cin1.controller is not s_cin2.controller:
            raise annmodel.UnionError("different controller!")
        return SomeControlledInstance(annmodel.unionof(s_cin1.s_real_obj,
                                                       s_cin2.s_real_obj),
                                      s_cin1.controller)
