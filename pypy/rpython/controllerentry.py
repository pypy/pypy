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


class Controller(object):
    __metaclass__ = cachedtype

    def _freeze_(self):
        return True

    def ctrl_new(self, *args_s):
        return delegate(self.new, *args_s)

    def ctrl_getattr(self, s_obj, s_attr):
        return delegate(self.getattr, s_obj, s_attr)

    def getattr(self, obj, attr):
        return getattr(self, 'get_' + attr)(obj)
    getattr._annspecialcase_ = 'specialize:arg(2)'


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


class __extend__(SomeControlledInstance):

    def getattr(s_cin, s_attr):
        assert s_attr.is_constant()
        return s_cin.controller.ctrl_getattr(s_cin.s_real_obj, s_attr)


class __extend__(pairtype(SomeControlledInstance, SomeControlledInstance)):

    def union((s_cin1, s_cin2)):
        if s_cin1.controller is not s_cin2.controller:
            raise annmodel.UnionError("different controller!")
        return SomeControlledInstance(annmodel.unionof(s_cin1.s_real_obj,
                                                       s_cin2.s_real_obj),
                                      s_cin1.controller)
