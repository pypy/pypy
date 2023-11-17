# This is here to be used by cpyext and _hpy_universal.
# the destructor is a python function or None.

from rpython.rtyper.lltypesystem import rffi
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app


class W_Capsule(W_Root):
    def __init__(self, space, pointer, name):
        from pypy.module.cpyext.api import cts as cts_cpyext
        self.space = space
        self.pointer = pointer
        self.name = name
        self.context = rffi.cast(rffi.VOIDP, 0)
        self.destructor_hpy = rffi.cast(rffi.VOIDP, 0)
        self.destructor_cpyext = cts_cpyext.cast("PyCapsule_Destructor", 0)

    def descr_repr(self, space):
        if self.name:
            name = '"' + rffi.constcharp2str(self.name) + '"'
        else:
            name = ""
        addr = hex(rffi.cast(rffi.SIGNED, self.pointer))
        return space.newtext("capsule object %s at %s" %(name, addr))

    def _finalize_(self):
        if self.destructor_hpy:
            from pypy.module._hpy_universal.llapi import cts as cts_hpy
            destructor_hpy = cts_hpy.cast("HPyCapsule_Destructor*", self.destructor_hpy)
            destructor_hpy.c_impl(self.name, self.pointer, self.context)
        elif self.destructor_cpyext:
            from pypy.module.cpyext.pyobject import make_ref
            pyobj = make_ref(self.space, self)
            self.destructor_cpyext(pyobj)

    def set_destructor_hpy(self, space, destructor):
        self.destructor_hpy = rffi.cast(rffi.VOIDP, destructor)
        if self.destructor_hpy:
            self.register_finalizer(space)

    def set_destructor_cpyext(self, space, destructor):
        self.destructor_cpyext = destructor
        if self.destructor_cpyext:
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
