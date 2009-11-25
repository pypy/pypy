from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pairtype
from pypy.annotation.binaryop import _make_none_union, SomePBC # SomePBC needed by _make_none_union
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.annlowlevel import cachedtype
from pypy.rpython.error import TyperError


class ControllerEntry(ExtRegistryEntry):

    def compute_result_annotation(self, *args_s, **kwds_s):
        controller = self.getcontroller(*args_s, **kwds_s)
        return controller.ctrl_new_ex(self.bookkeeper, *args_s, **kwds_s)

    def getcontroller(self, *args_s, **kwds_s):
        return self._controller_()

    def specialize_call(self, hop, **kwds_i):
        if hop.s_result == annmodel.s_ImpossibleValue:
            raise TyperError("object creation always raises: %s" % (
                hop.spaceop,))
        controller = hop.s_result.controller
        return controller.rtype_new(hop, **kwds_i)



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

    def ctrl_new(self, *args_s, **kwds_s):
        if kwds_s:
            raise TypeError("cannot handle keyword arguments in %s" % (
                self.new,))
        s_real_obj = delegate(self.new, *args_s)
        if s_real_obj == annmodel.s_ImpossibleValue:
            return annmodel.s_ImpossibleValue
        else:
            return SomeControlledInstance(s_real_obj, controller=self)

    def ctrl_new_ex(self, bookkeeper, *args_s, **kwds_s):
        return self.ctrl_new(*args_s, **kwds_s)

    def rtype_new(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.new, hop, revealargs=[], revealresult=True)

    def getattr(self, obj, attr):
        return getattr(self, 'get_' + attr)(obj)
    getattr._annspecialcase_ = 'specialize:arg(0, 2)'

    def ctrl_getattr(self, s_obj, s_attr):
        return delegate(self.getattr, s_obj, s_attr)

    def rtype_getattr(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.getattr, hop)

    def setattr(self, obj, attr, value):
        return getattr(self, 'set_' + attr)(obj, value)
    setattr._annspecialcase_ = 'specialize:arg(0, 2)'

    def ctrl_setattr(self, s_obj, s_attr, s_value):
        return delegate(self.setattr, s_obj, s_attr, s_value)

    def rtype_setattr(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.setattr, hop)

    def ctrl_getitem(self, s_obj, s_key):
        return delegate(self.getitem, s_obj, s_key)

    def rtype_getitem(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.getitem, hop)

    def ctrl_setitem(self, s_obj, s_key, s_value):
        return delegate(self.setitem, s_obj, s_key, s_value)

    def rtype_setitem(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.setitem, hop)

    def ctrl_delitem(self, s_obj, s_key):
        return delegate(self.delitem, s_obj, s_key)

    def rtype_delitem(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.delitem, hop)

    def ctrl_is_true(self, s_obj):
        return delegate(self.is_true, s_obj)

    def rtype_is_true(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.is_true, hop)

    def ctrl_call(self, s_obj, *args_s):
        return delegate(self.call, s_obj, *args_s)

    def rtype_call(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        return rtypedelegate(self.call, hop)


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
        from pypy.rpython.rcontrollerentry import ControlledInstanceRepr
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
        from pypy.rpython.rcontrollerentry import ControlledInstanceRepr
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
        from pypy.rpython.lltypesystem import lltype
        assert hop.s_result.is_constant()
        return hop.inputconst(lltype.Bool, hop.s_result.const)

# ____________________________________________________________

class SomeControlledInstance(annmodel.SomeObject):

    def __init__(self, s_real_obj, controller):
        self.s_real_obj = s_real_obj
        self.controller = controller
        self.knowntype = controller.knowntype

    def can_be_none(self):
        return self.controller.can_be_None

    def rtyper_makerepr(self, rtyper):
        from pypy.rpython.rcontrollerentry import ControlledInstanceRepr
        return ControlledInstanceRepr(rtyper, self.s_real_obj, self.controller)

    def rtyper_makekey_ex(self, rtyper):
        real_key = rtyper.makekey(self.s_real_obj)
        return self.__class__, real_key, self.controller

_make_none_union("SomeControlledInstance", "obj.s_real_obj, obj.controller", globals())

class __extend__(SomeControlledInstance):

    def getattr(s_cin, s_attr):
        assert s_attr.is_constant()
        return s_cin.controller.ctrl_getattr(s_cin.s_real_obj, s_attr)

    def setattr(s_cin, s_attr, s_value):
        assert s_attr.is_constant()
        s_cin.controller.ctrl_setattr(s_cin.s_real_obj, s_attr, s_value)

    def is_true(s_cin):
        return s_cin.controller.ctrl_is_true(s_cin.s_real_obj)

    def simple_call(s_cin, *args_s):
        return s_cin.controller.ctrl_call(s_cin.s_real_obj, *args_s)


class __extend__(pairtype(SomeControlledInstance, annmodel.SomeObject)):

    def getitem((s_cin, s_key)):
        return s_cin.controller.ctrl_getitem(s_cin.s_real_obj, s_key)

    def setitem((s_cin, s_key), s_value):
        s_cin.controller.ctrl_setitem(s_cin.s_real_obj, s_key, s_value)

    def delitem((s_cin, s_key)):
        s_cin.controller.ctrl_delitem(s_cin.s_real_obj, s_key)


class __extend__(pairtype(SomeControlledInstance, SomeControlledInstance)):

    def union((s_cin1, s_cin2)):
        if s_cin1.controller is not s_cin2.controller:
            raise annmodel.UnionError("different controller!")
        return SomeControlledInstance(annmodel.unionof(s_cin1.s_real_obj,
                                                       s_cin2.s_real_obj),
                                      s_cin1.controller)
