from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import unwrap_spec
from pypy.module.cpyext.pyobject import as_pyobj
from pypy.module.cpyext.api import PyObjectFields


mytype_object = lltype.Ptr(lltype.Struct(
    'mytype_object',
    *(PyObjectFields + (("foo", rffi.INT),))))


@unwrap_spec(index=int)
def injected_getitem(space, w_self, index):
    py_obj = as_pyobj(space, w_self)
    py_obj = rffi.cast(mytype_object, py_obj)
    return space.wrap(index * rffi.getintfield(py_obj, "foo"))


injected_methods = {
    '__getitem__': interp2app(injected_getitem),
}

def inject(space, name, dict_w, pto):
    assert name == 'test_module.test_mytype'
    for key, value in injected_methods.items():
        dict_w[key] = space.wrap(value)
