from pypy.rlib.rctypes.implementation import CTypeController, getcontroller
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.unroll import unrolling_iterable

from ctypes import Structure

StructType = type(Structure)


class StructCTypeController(CTypeController):

    def __init__(self, ctype):
        CTypeController.__init__(self, ctype)

        # Map the field names to their controllers
        controllers = []
        fields = []
        for name, field_ctype in ctype._fields_:
            controller = getcontroller(field_ctype)
            controllers.append((name, controller))
            fields.append((name, controller.knowntype))
        self.fieldcontrollers = dict(controllers)
        external = getattr(ctype, '_external_', False)
        self.knowntype = rctypesobject.RStruct(ctype.__name__, fields,
                                               c_external = external)

        # Build a custom new() method where the setting of the fields
        # is unrolled
        unrolled_controllers = unrolling_iterable(controllers)

        def new(*args):
            obj = self.knowntype.allocate()
            if len(args) > len(fields):
                raise ValueError("too many arguments for this structure")
            for name, controller in unrolled_controllers:
                if args:
                    value = args[0]
                    args = args[1:]
                    itemobj = getattr(obj, 'ref_' + name)()
                    controller.set_value(itemobj, value)
            return obj

        self.new = new


    def getattr(self, obj, attr):
        controller = self.fieldcontrollers[attr]
        itemobj = getattr(obj, 'ref_' + attr)()
        return controller.return_value(itemobj)
    getattr._annspecialcase_ = 'specialize:arg(2)'

    def setattr(self, obj, attr, value):
        controller = self.fieldcontrollers[attr]
        itemobj = getattr(obj, 'ref_' + attr)()
        controller.set_value(itemobj, value)
    setattr._annspecialcase_ = 'specialize:arg(2)'


StructCTypeController.register_for_metatype(StructType)
