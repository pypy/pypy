from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import unwrap_spec, TypeDef
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.pyobject import from_ref, make_typedescr,\
     track_reference, PyObject
from pypy.module.cpyext.api import PyObjectFields
from pypy.module.cpyext.api import bootstrap_function
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.typeobject import W_TypeObject


PyArrayObject = lltype.Ptr(lltype.Struct(
    'PyArrayObject',
    *(PyObjectFields + 
        (("data", rffi.CCHARP),
         ("nd", rffi.INT),
         ("dimensions", rffi.SIGNEDP),
         ("strides", rffi.SIGNEDP),
         ("base", rffi.VOIDP),
         ("descr", rffi.VOIDP),
        )))
    )

class Original:
    def __init__(self, space):
        self.injected_methods_w = []
        for key, value in injected_methods.items():
            self.injected_methods_w.append((key, space.wrap(value)))

class W_ArrayObject(W_Root):
    def getclass(self, space):
        if type(self) is W_ArrayObject:
            return space.fromcache(Original).w_array_type
        return W_Root.getclass(self, space)
W_ArrayObject.typedef = TypeDef("ndarray")
W_ArrayObject.typedef.injected_type = True
W_ArrayObject.typedef.acceptable_as_base_class = True

class W_Float64Object(W_FloatObject):
    def getclass(self, space):
        return space.fromcache(Original).w_float64_type

def array_realize(space, obj):
    w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
    w_obj = space.allocate_instance(W_ArrayObject, w_type)
    w_obj.pyobj = rffi.cast(PyArrayObject, obj)
    track_reference(space, obj, w_obj)
    return w_obj

@bootstrap_function
def init_mything(space):
    make_typedescr(W_ArrayObject.typedef,
                   basestruct=PyArrayObject.TO,
                   realize=array_realize)

@unwrap_spec(index=int)
def injected_getitem(space, w_self, index):
    assert isinstance(w_self, W_ArrayObject)
    py_obj = rffi.cast(PyArrayObject, w_self.pyobj)
    if index < 0 or index >= py_obj.dimensions[0]:
        raise oefmt(space.w_IndexError, "index out of bounds")
    data = rffi.cast(rffi.DOUBLEP, py_obj.data)
    return W_Float64Object(data[index])

injected_methods = {
    '__getitem__': interp2app(injected_getitem),
}

def inject_operator(space, name, dict_w, pto):
    assert name == 'numpy.ndarray'
    org = space.fromcache(Original)
    org.w_original_getitem = dict_w['__getitem__']
    for key, w_value in org.injected_methods_w:
        dict_w[key] = w_value
    return W_ArrayObject.typedef

def inject_module(space, w_mod, name):
    assert name == 'numpy.core.multiarray'
    org = space.fromcache(Original)
    w_type = space.appexec([w_mod], """(mod):
        return mod.typeinfo['DOUBLE'][-1]
    """)
    w_array_type = space.getattr(w_mod, space.wrap('ndarray'))
    assert isinstance(w_array_type, W_TypeObject)
    assert isinstance(w_type, W_TypeObject)
    org.w_float64_type = w_type
    org.w_array_type = w_array_type
