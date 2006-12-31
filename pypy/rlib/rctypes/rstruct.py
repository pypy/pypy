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
            setattr(self, 'fieldcontroller_' + name, controller)
            controllers.append((name, controller))
            fields.append((name, controller.knowntype))
        external = getattr(ctype, '_external_', False)
        self.knowntype = rctypesobject.RStruct(ctype.__name__, fields,
                                               c_external = external)

        # Build a custom new() method where the setting of the fields
        # is unrolled
        unrolled_controllers = unrolling_iterable(controllers)

        def structnew(*args):
            obj = self.knowntype.allocate()
            if len(args) > len(fields):
                raise ValueError("too many arguments for this structure")
            for name, controller in unrolled_controllers:
                if args:
                    value = args[0]
                    args = args[1:]
                    if controller.is_box(value):
                        structsetboxattr(obj, name, value)
                    else:
                        structsetattr(obj, name, value)
            return obj

        self.new = structnew

        # Build custom getter and setter methods
        def structgetattr(obj, attr):
            controller = getattr(self, 'fieldcontroller_' + attr)
            itemobj = getattr(obj, 'ref_' + attr)()
            return controller.return_value(itemobj)
        structgetattr._annspecialcase_ = 'specialize:arg(1)'

        def structsetattr(obj, attr, value):
            controller = getattr(self, 'fieldcontroller_' + attr)
            itemobj = getattr(obj, 'ref_' + attr)()
            controller.store_value(itemobj, value)
        structsetattr._annspecialcase_ = 'specialize:arg(1)'

        def structsetboxattr(obj, attr, valuebox):
            controller = getattr(self, 'fieldcontroller_' + attr)
            itemobj = getattr(obj, 'ref_' + attr)()
            controller.store_box(itemobj, valuebox)
        structsetboxattr._annspecialcase_ = 'specialize:arg(1)'

        self.getattr = structgetattr
        self.setattr = structsetattr
        self.setboxattr = structsetboxattr


StructCTypeController.register_for_metatype(StructType)
