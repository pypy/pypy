# This is here to be used by cpyext and _hpy_universal.
# the destructor is a python function or None.

from rpython.rtyper.lltypesystem import rffi
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

class W_Capsule(W_Root):
    def __init__(self, space, pointer, name, destructor, is_cpyext=True):
        self.space = space
        self.pointer = pointer
        self.name = name
        self.destructor = destructor
        if destructor:
            self.register_finalizer(space)
        self.context = rffi.cast(rffi.VOIDP, 0)

    def descr_repr(self, space):
        if self.name:
            quote = '"'
        else:
            quote = ""
        name = rffi.constcharp2str(self.name)
        addr = hex(rffi.cast(rffi.SIGNED, self.pointer))
        return space.newtext("capsule object %s%s%s at %s" %(quote, name, quote, addr))

    def _finalize_(self):
        if self.destructor:
            self.destructor(self)

    def set_destructor(self, destructor):
        self.destructor = destructor
        if destructor:
            self.register_finalizer(space)

W_Capsule.typedef = TypeDef(
   "PyCapsule",
    __doc__ = """
Capsule objects let you wrap a C "void *" pointer in a Python
object.  They're a way of passing data through the Python interpreter
without creating your own custom type.

Capsules are used for communication between extension modules.
They provide a way for an extension module to export a C interface
to other extension modules, so that extension modules can use the
Python import mechanism to link to one another.
""",
    __repr__ = interp2app(W_Capsule.descr_repr),
)
