# This is here to be used by cpyext and _hpy_universal.
# the destructor is
# 
# typedef void (*HPyCapsule_Destructor)(const char *name, void *pointer, void *context);
# typedef void (*PyCapsule_Destructor)(void *obj);
# typedef struct {
#    PyCapsule_Destructor cpy_impl;
#    HPyCapsule_Destructor hpy_impl;
# } HPyCapsule_Destructor;
# If cpyext, the cpy_impl is called. If hpy, the hpy_impl is called. 

from pypy.interpreter.baseobjspace import W_Root
from rpython.rtyper.lltypesystem import rffi

class W_Capsule(W_Root):
    def __init__(self, space, pointer, name, destructor, is_cpyext=True):
        self.space = space
        self.pointer = pointer
        self.name = name
        self.destructor = rffi.cast(rffi.VOIDP, destructor)
        self.context = rffi.cast(rffi.VOIDP, 0)

    def _finalize_(self):
        pass

