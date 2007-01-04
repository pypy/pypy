from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.rctypes.implementation import CTypeController, getcontroller
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython.lltypesystem import lltype

from ctypes import pointer, POINTER, byref, c_int


PointerType = type(POINTER(c_int))


class PointerCTypeController(CTypeController):
    ready = 0

    def __init__(self, ctype):
        CTypeController.__init__(self, ctype)
        self.knowntype = rctypesobject.RPointer(None)

    def setup(self):
        if self.ready == 0:
            self.ready = 1
            self.contentscontroller = getcontroller(self.ctype._type_)
            self.knowntype.setpointertype(self.contentscontroller.knowntype,
                                          force=True)
            self.ready = 2

    def new(self, ptrto=None):
        obj = self.knowntype.allocate()
        if ptrto is not None:
            obj.set_contents(self.contentscontroller.unbox(ptrto))
        return obj
    new._annspecialcase_ = 'specialize:arg(0)'

    def initialize_prebuilt(self, obj, x):
        contentsbox = self.contentscontroller.convert(x.contents)
        self.setbox_contents(obj, contentsbox)

    def getitem(self, obj, index):
        contentsobj = obj.ref(index)
        return self.contentscontroller.return_value(contentsobj)
    getitem._annspecialcase_ = 'specialize:arg(0)'

    def setitem(self, obj, index, value):
        if index != 0:
            raise ValueError("assignment to pointer[x] with x != 0")
            # not supported by ctypes either
        contentsobj = obj.get_contents()
        self.contentscontroller.set_value(contentsobj, value)
    setitem._annspecialcase_ = 'specialize:arg(0)'

    def setboxitem(self, obj, index, valuebox):
        if index != 0:
            raise ValueError("assignment to pointer[x] with x != 0")
            # not supported by ctypes either
        contentsobj = obj.get_contents()
        contentsobj.copyfrom(valuebox)
    setitem._annspecialcase_ = 'specialize:arg(0)'

    def get_contents(self, obj):
        return self.contentscontroller.box(obj.get_contents())
    get_contents._annspecialcase_ = 'specialize:arg(0)'

    def setbox_contents(self, obj, contentsbox):
        obj.set_contents(contentsbox)
    setbox_contents._annspecialcase_ = 'specialize:arg(0)'

    def is_true(self, obj):
        return not obj.is_null()
    is_true._annspecialcase_ = 'specialize:arg(0)'

    def store_box(self, obj, valuebox):
        obj.set_contents(valuebox.ref(0))

PointerCTypeController.register_for_metatype(PointerType)
