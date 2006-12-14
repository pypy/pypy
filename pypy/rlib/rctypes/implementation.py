from pypy.annotation import model as annmodel
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython import extregistry, controllerentry
from pypy.rpython.controllerentry import Controller, ControllerEntry
from pypy.rpython.controllerentry import ControllerEntryForPrebuilt
from pypy.rpython.controllerentry import SomeControlledInstance
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes import rcarithmetic as rcarith

import ctypes
if ctypes.__version__ < '0.9.9.6':  # string comparison... good enough?
    raise ImportError("requires ctypes >= 0.9.9.6, got %s" % (
        ctypes.__version__,))


class CTypeController(Controller):

    def __init__(self, ctype):
        self.ctype = ctype
        self.instance_cache = {}

    def register_for_type(cls, ctype):
        class Entry(CTypesCallEntry):
            _about_ = ctype
            _controller_ = cls
        class Entry(CTypesObjEntry):
            _type_ = ctype
            _controller_ = cls
    register_for_type = classmethod(register_for_type)

    def register_for_metatype(cls, ctype):
        class Entry(CTypesCallEntry):
            _type_ = ctype
            _controller_ = cls
        class Entry(CTypesObjEntry):
            _metatype_ = ctype
            _controller_ = cls
    register_for_metatype = classmethod(register_for_metatype)

    def convert(self, x):
        assert isinstance(x, self.ctype)
        key = id(x)
        try:
            return self.instance_cache[key]
        except KeyError:
            obj = self.new()
            self.instance_cache[key] = obj
            self.initialize_prebuilt(obj, x)
            return obj

    def return_value(self, obj):
        return obj
    return_value._annspecialcase_ = 'specialize:arg(0)'

    # extension to the setattr/setitem support: if the new value is actually
    # a CTypeControlled instance as well, reveal it automatically (i.e. turn
    # it into an rctypesobject) and call a method with a different name.

    def setboxattr(self, obj, attr, value):
        return getattr(self, 'setbox_' + attr)(obj, value)
    setboxattr._annspecialcase_ = 'specialize:arg(2)'

    def ctrl_setattr(self, s_obj, s_attr, s_value):
        if s_is_box(s_value):
            return controllerentry.delegate(self.setboxattr,
                                            s_obj, s_attr, s_value.s_real_obj)
        else:
            return controllerentry.delegate(self.setattr,
                                            s_obj, s_attr, s_value)

    def rtype_setattr(self, hop):
        r_controlled_instance = hop.args_r[0]
        if s_is_box(hop.args_s[2]):
            hop2 = revealbox(hop, 2)
            return r_controlled_instance.rtypedelegate(self.setboxattr, hop2)
        else:
            return r_controlled_instance.rtypedelegate(self.setattr, hop)

    def ctrl_setitem(self, s_obj, s_key, s_value):
        if s_is_box(s_value):
            return controllerentry.delegate(self.setboxitem,
                                            s_obj, s_key, s_value.s_real_obj)
        else:
            return controllerentry.delegate(self.setitem,
                                            s_obj, s_key, s_value)

    def rtype_setitem(self, hop):
        r_controlled_instance = hop.args_r[0]
        if s_is_box(hop.args_s[2]):
            hop2 = revealbox(hop, 2)
            return r_controlled_instance.rtypedelegate(self.setboxitem, hop2)
        else:
            return r_controlled_instance.rtypedelegate(self.setitem, hop)


class CTypesCallEntry(ControllerEntry):
    def getcontroller(self, *args_s):
        ctype = self.instance
        return self._controller_(ctype)

class CTypesObjEntry(ControllerEntryForPrebuilt):
    def getcontroller(self):
        ctype = self.type
        return self._controller_(ctype)

def getcontroller(ctype):
    """Return the CTypeController instance corresponding to the given ctype."""
    entry = extregistry.lookup_type(ctype)
    return entry.getcontroller()

def s_is_box(s_value):
    return (isinstance(s_value, SomeControlledInstance) and
            isinstance(s_value.controller, CTypeController))

def revealbox(hop, argindex):
    hop2 = hop.copy()
    r_value = hop2.args_r[argindex]
    s_value, r_value = r_value.reveal(r_value)
    hop2.args_s[argindex] = s_value
    hop2.args_r[argindex] = r_value
    return hop2

def register_function_impl(builtinfn, controllingfn,
                           revealargs=[], revealresult=None):

    class Entry(extregistry.ExtRegistryEntry):
        _about_ = builtinfn

        def compute_result_annotation(self, *args_s):
            real_args_s = list(args_s)
            for index in revealargs:
                real_args_s[index] = args_s[index].s_real_obj
            if annmodel.s_ImpossibleValue in real_args_s:
                return annmodel.s_ImpossibleValue   # temporarily hopefully
            s_result = controllerentry.delegate(controllingfn, *real_args_s)
            if revealresult:
                result_ctype = revealresult(*args_s)
                controller = getcontroller(result_ctype)
                s_result = SomeControlledInstance(s_result, controller)
            return s_result

        def specialize_call(self, hop):
            import pdb; pdb.set_trace()

# ____________________________________________________________
#
# Imports for side-effects

import pypy.rlib.rctypes.rprimitive
import pypy.rlib.rctypes.rarray
import pypy.rlib.rctypes.rpointer
