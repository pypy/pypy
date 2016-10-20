from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import unwrap_spec, TypeDef
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.pyobject import as_pyobj, make_typedescr, track_reference
from pypy.module.cpyext.api import PyObjectFields
from pypy.module.cpyext.api import bootstrap_function
from pypy.objspace.std.floatobject import W_FloatObject


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
        pass

class W_ArrayObject(W_Root):
    pass
W_ArrayObject.typedef = TypeDef("ndarray")

class W_Float64Object(W_FloatObject):
    def getclass(self, space):
        org = space.fromcache(Original)
        w_type = org.w_float64_type
        return w_type

def mything_realize(space, obj):
    intval = rffi.cast(lltype.Signed, rffi.cast(PyArrayObject, obj).foo)
    w_obj = W_ArrayObject(intval)
    track_reference(space, obj, w_obj)
    return w_obj

@bootstrap_function
def init_mything(space):
    make_typedescr(W_ArrayObject.typedef,
                   basestruct=mytype_object.TO,
                   realize=mything_realize)

@unwrap_spec(index=int)
def injected_getitem(space, w_self, index):
    py_obj = rffi.cast(PyArrayObject, as_pyobj(space, w_self))
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
    for key, value in injected_methods.items():
        dict_w[key] = space.wrap(value)

def inject_module(space, w_mod, name):
    assert name == 'numpy.core.multiarray'
    org = space.fromcache(Original)
    w_type = space.appexec([w_mod], """(mod):
        return mod.typeinfo['DOUBLE'][-1]
    """)
    org.w_float64_type = w_type
