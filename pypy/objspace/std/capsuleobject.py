# This is here to be used by cpyext and _hpy_universal.
# the destructor is a python function or None.

from rpython.rtyper.lltypesystem import rffi
from rpython.tool.cparser import CTypeSpace
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

cts = CTypeSpace()
cts.parse_source("""

typedef void (*PyCapsule_Destructor)(void *);
typedef void (*HPyFunc_Capsule_Destructor)(const char *name, void *pointer, void *context);

typedef struct {
    void *cpy_trampoline;
    HPyFunc_Capsule_Destructor impl;
} HPyCapsule_Destructor;
""")


class W_Capsule(W_Root):
    def __init__(self, space, pointer, name):
        self.space = space
        self.pointer = pointer
        self.name = name
        self.context = rffi.cast(rffi.VOIDP, 0)
        if space.config.objspace.usemodules._hpy_universal:
            self.destructor_hpy = cts.cast("HPyCapsule_Destructor*", 0)
        else:
            self.destructor_hpy = None

    def descr_repr(self, space):
        if self.name:
            name = '"' + rffi.constcharp2str(self.name) + '"'
        else:
            name = ""
        addr = hex(rffi.cast(rffi.SIGNED, self.pointer))
        return space.newtext("capsule object %s at %s" %(name, addr))

    def _finalize_(self):
        if self.destructor_hpy:
            self.destructor_hpy.c_impl(self.name, self.pointer, self.context)

    def set_destructor_hpy(self, space, destructor):
        self.destructor_hpy = cts.cast("HPyCapsule_Destructor*", destructor)
        if self.destructor_hpy:
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
