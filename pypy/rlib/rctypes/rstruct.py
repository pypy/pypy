from pypy.rlib.rctypes.implementation import CTypeController, getcontroller
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython.extregistry import ExtRegistryEntry
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
        self.fieldcontrollers = controllers

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

    def initialize_prebuilt(self, obj, x):
        for name, controller in self.fieldcontrollers:
            fieldbox = controller.convert(getattr(x, name))
            self.setboxattr(obj, name, fieldbox)

    def insert_constructor_keywords(self, lst, prefix, kwds):
        lst = list(lst)
        kwds = kwds.copy()
        for index, (name, field_ctype) in enumerate(self.ctype._fields_):
            if prefix+name in kwds:
                value = kwds.pop(prefix+name)
                while len(lst) <= index:
                    lst.append(None)
                if lst[index] is not None:
                    raise TypeError("duplicate value for argument %r" % name)
                lst[index] = value
        if kwds:
            raise TypeError("unknown keyword(s): %r" % (kwds.keys(),))
        return lst

    def ctrl_new_ex(self, bookkeeper, *args_s, **kwds_s):
        if kwds_s:
            args_s = self.insert_constructor_keywords(args_s, 's_', kwds_s)
            for i in range(len(args_s)):
                if args_s[i] is None:
                    name, controller = self.fieldcontrollers[i]
                    x = controller.default_ctype_value()
                    args_s[i] = bookkeeper.immutablevalue(x)
        return CTypeController.ctrl_new(self, *args_s)

    def rtype_new(self, hop, **kwds_i):
        if kwds_i:
            lst = range(hop.nb_args)
            for key, index in kwds_i.items():
                lst[index] = None
            lst = self.insert_constructor_keywords(lst, 'i_', kwds_i)
            hop2 = hop.copy()
            hop2.nb_args = len(lst)
            hop2.args_v = []
            hop2.args_s = []
            hop2.args_r = []
            for i, index in enumerate(lst):
                if index is not None:
                    v = hop.args_v[index]
                    s = hop.args_s[index]
                    r = hop.args_r[index]
                else:
                    # must insert a default value
                    from pypy.objspace.flow.model import Constant
                    name, controller = self.fieldcontrollers[i]
                    x = controller.default_ctype_value()
                    v = Constant(x)
                    s = hop.rtyper.annotator.bookkeeper.immutablevalue(x)
                    r = hop.rtyper.getrepr(s)
                hop2.args_v.append(v)
                hop2.args_s.append(s)
                hop2.args_r.append(r)
            hop = hop2
        return CTypeController.rtype_new(self, hop)


StructCTypeController.register_for_metatype(StructType)

# ____________________________________________________________

def offsetof(Struct, fieldname):
    "Utility function that returns the offset of a field in a structure."
    return getattr(Struct, fieldname).offset

class OffsetOfFnEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to offsetof()"
    _about_ = offsetof

    def compute_result_annotation(self, s_Struct, s_fieldname):
        assert s_Struct.is_constant()
        assert s_fieldname.is_constant()
        ofs = offsetof(s_Struct.const, s_fieldname.const)
        assert ofs >= 0
        s_result = SomeInteger(nonneg=True)
        s_result.const = ofs
        return s_result

    def specialize_call(self, hop):
        ofs = hop.s_result.const
        return hop.inputconst(lltype.Signed, ofs)
