import py
from pypy.annotation import model as annmodel
from pypy.tool.tls import tlsobject
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython import extregistry, controllerentry
from pypy.rpython.error import TyperError
from pypy.rpython.controllerentry import Controller, ControllerEntry
from pypy.rpython.controllerentry import ControllerEntryForPrebuilt
from pypy.rpython.controllerentry import SomeControlledInstance
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes import rcarithmetic as rcarith

try:
    import ctypes
    if ctypes.__version__ < '0.9.9.6':  # string comparison... good enough?
        raise ImportError("requires ctypes >= 0.9.9.6, got %s" % (
            ctypes.__version__,))
except ImportError, e:
    py.test.skip(str(e))


class CTypeController(Controller):

    def __init__(self, ctype):
        self.ctype = ctype
        self.instance_cache = {}

    def setup(self):
        pass

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
        if isinstance(x, self.ctype):
            key = "by_id", id(x)
        else:
            key = "by_value", x
            x = self.ctype(x)
        try:
            return self.instance_cache[key][0]
        except KeyError:
            obj = self.new()
            self.instance_cache[key] = obj, x     # keep 'x' alive
            self.initialize_prebuilt(obj, x)
            return obj

    return_value = Controller.box

    def store_box(self, obj, valuebox):
        obj.copyfrom(valuebox)

    def store_value(self, obj, value):
        raise TypeError("cannot store a value into a non-primitive ctype")
    store_value._annspecialcase_ = 'specialize:arg(0)'

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
        from pypy.rpython.rcontrollerentry import rtypedelegate
        if s_is_box(hop.args_s[2]):
            hop2 = revealbox(hop, 2)
            return rtypedelegate(self.setboxattr, hop2)
        else:
            return rtypedelegate(self.setattr, hop)

    def ctrl_setitem(self, s_obj, s_key, s_value):
        if s_is_box(s_value):
            return controllerentry.delegate(self.setboxitem,
                                            s_obj, s_key, s_value.s_real_obj)
        else:
            return controllerentry.delegate(self.setitem,
                                            s_obj, s_key, s_value)

    def rtype_setitem(self, hop):
        from pypy.rpython.rcontrollerentry import rtypedelegate
        if s_is_box(hop.args_s[2]):
            hop2 = revealbox(hop, 2)
            return rtypedelegate(self.setboxitem, hop2)
        else:
            return rtypedelegate(self.setitem, hop)


class CTypesCallEntry(ControllerEntry):
    def getcontroller(self, *args_s):
        ctype = self.instance
        return _build_controller(self._controller_, ctype)

class CTypesObjEntry(ControllerEntryForPrebuilt):
    def getcontroller(self):
        ctype = self.type
        return _build_controller(self._controller_, ctype)

TLS = tlsobject()
def _build_controller(cls, ctype):
    if hasattr(TLS, 'pending'):
        # recursive case
        controller = cls(ctype)
        TLS.pending.append(controller)
    else:
        # non-recursive case
        TLS.pending = []
        controller = cls(ctype)
        pending = TLS.pending
        del TLS.pending
        pending.append(controller)
        for c1 in pending:
            c1.setup()
    return controller

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
                           revealargs=[], revealresult=None,
                           register=True):

    class Entry(extregistry.ExtRegistryEntry):
        if register:
            _about_ = builtinfn

        def compute_result_annotation(self, *args_s):
            real_args_s = list(args_s)
            if annmodel.s_ImpossibleValue in real_args_s:
                return annmodel.s_ImpossibleValue   # temporarily hopefully
            for index in revealargs:
                s_controlled = args_s[index]
                if not isinstance(s_controlled, SomeControlledInstance):
                    raise TypeError("in call to %s:\nargs_s[%d] should be a "
                                    "ControlledInstance,\ngot instead %s" % (
                        builtinfn, index, s_controlled))
                real_args_s[index] = s_controlled.s_real_obj
            s_result = controllerentry.delegate(controllingfn, *real_args_s)
            if revealresult:
                result_ctype = revealresult(*args_s)
                controller = getcontroller(result_ctype)
                if s_result != annmodel.s_ImpossibleValue:
                    s_result = SomeControlledInstance(s_result, controller)
            return s_result

        def specialize_call(self, hop):
            from pypy.rpython.rcontrollerentry import rtypedelegate
            return rtypedelegate(controllingfn, hop, revealargs, revealresult)

    return Entry

# ____________________________________________________________
#
# Imports for side-effects

import pypy.rlib.rctypes.rprimitive
import pypy.rlib.rctypes.rarray
import pypy.rlib.rctypes.rpointer
import pypy.rlib.rctypes.rstruct
import pypy.rlib.rctypes.rbuiltin
import pypy.rlib.rctypes.rchar_p
