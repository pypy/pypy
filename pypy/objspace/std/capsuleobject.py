# This is here to be used by cpyext and _hpy_universal.
# the destructor is a python function or None.

from pypy.interpreter.baseobjspace import W_Root
from rpython.rtyper.lltypesystem import rffi

class W_Capsule(W_Root):
    typedef = None
    def __init__(self, space, pointer, name, destructor, is_cpyext=True):
        self.space = space
        self.pointer = pointer
        self.name = name
        self.destructor = destructor
        if destructor:
            self.register_finalizer(space)
        self.context = rffi.cast(rffi.VOIDP, 0)

    def _finalize_(self):
        self.destructor(self)
