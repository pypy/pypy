from pypy.rlib.rctypes.implementation import CTypeController
from pypy.rlib.rctypes import rctypesobject

from ctypes import c_char_p


class CCharPCTypeController(CTypeController):
    knowntype = rctypesobject.rc_char_p

    def new(self, initialvalue=None):
        obj = rctypesobject.rc_char_p.allocate()
        obj.set_value(initialvalue)
        return obj

    def initialize_prebuilt(self, obj, x):
        string = x.value
        obj.set_value(string)

    def get_value(self, obj):
        return obj.get_value()

    def set_value(self, obj, string):
        obj.set_value(string)

    # ctypes automatically unwraps the c_char_p() instances when
    # they are returned by most operations
    return_value = get_value
    store_value = set_value

    def default_ctype_value(self):
        return None

    def is_true(self, obj):
        return obj.get_value() is not None


CCharPCTypeController.register_for_type(c_char_p)
