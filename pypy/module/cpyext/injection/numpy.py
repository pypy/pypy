from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import unwrap_spec, TypeDef
from pypy.module.cpyext.pyobject import as_pyobj, make_typedescr, track_reference
from pypy.module.cpyext.api import PyObjectFields
from pypy.interpreter import typedef
from pypy.objspace.std.intobject import W_IntObject
from pypy.module.cpyext.api import bootstrap_function

PyArrayObject = lltype.Ptr(lltype.Struct(
    'PyArrayObject',
    *(PyObjectFields + 
        (("data", rffi.CHARP),
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

class W_ArrayObject(object):
    pass

W_ArrayObject.typedef = TypeDef("ndarray")

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
