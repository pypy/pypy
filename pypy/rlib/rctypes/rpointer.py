from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.rctypes.implementation import CTypeController, getcontroller
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython.lltypesystem import lltype

from ctypes import pointer, POINTER, byref, c_int


PointerType = type(POINTER(c_int))


class PointerCTypeController(CTypeController):

    def __init__(self, ctype):
        CTypeController.__init__(self, ctype)
        self.contentscontroller = getcontroller(ctype._type_)
        self.knowntype = rctypesobject.RPointer(
            self.contentscontroller.knowntype)

    def new(self, ptrto=None):
        obj = self.knowntype.allocate()
        if ptrto is not None:
            obj.set_contents(self.contentscontroller.unbox(ptrto))
        return obj

    def initialize_prebuilt(self, obj, x):
        contentsbox = self.contentscontroller.convert(x.contents)
        self.setbox_contents(obj, contentsbox)

    def getitem(self, obj, index):
        if index != 0:
            raise ValueError("can only access item 0 of pointers")
        contentsobj = obj.get_contents()
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

PointerCTypeController.register_for_metatype(PointerType)
