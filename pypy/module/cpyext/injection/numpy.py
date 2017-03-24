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
         ("flags", rffi.INT),
         ("weakreflist", PyObject),
        )))
    )

class Original:
    def __init__(self, space):
        self.injected_methods_w = []
        for key, value in injected_methods.items():
            self.injected_methods_w.append((key, value.spacebind(space)))

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

internal_arr1 = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw', immortal=True)
internal_arr2 = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw', immortal=True)
def injected_op(space, w_self, w_other, op):
    # translate array_op in multiarray.c from c to rpython
    if isinstance(w_self, W_ArrayObject):
        arr1 = rffi.cast(PyArrayObject, w_self.pyobj)
        data1 = rffi.cast(rffi.DOUBLEP, arr1.data)
        n1 = arr1.dimensions[0]
    else:
        data1 = internal_arr1
        data1[0] = space.float_w(w_self)
        n1 = 1
    if isinstance(w_other, W_ArrayObject):
        arr2 = rffi.cast(PyArrayObject, w_other.pyobj)
        data2 = rffi.cast(rffi.DOUBLEP, arr2.data)
        n2 = arr2.dimensions[0]
    else:
        data2 = internal_arr2
        data2[0] = space.float_w(w_other)
        n2 = 1
    if not (n1 == n2 or n1 == 1 or n2 == 1):
        raise oefmt(space.w_ValueError, 'dimension mismatch')
    m = max(n1, n2)
    org = space.fromcache(Original)
    ret = space.call(org.w_array_type, space.newtuple([space.newint(m)]))
    assert isinstance(ret, W_ArrayObject)
    r = rffi.cast(rffi.DOUBLEP, ret.pyobj.data)
    i1 = 0; i2 = 0
    for j in range(m):
        if i1 >= n1: i1 = 0
        if i2 >= n2: i2 = 0
        if op == 'mul':
            r[j] = data1[i1] * data2[i2]
        elif op == 'add':
            r[j] = data1[i1] + data2[i2]
        elif op == 'sub':
            r[j] = data1[i1] - data2[i2]
        elif op == 'div':
            if data2[i2] == 0:
                r[j] = float('nan')
            else:
                r[j] = data1[i1] / data2[i2]
        i1 += 1; i2 += 1
    return ret

def injected_mul(space, w_self, w_other):
    return injected_op(space, w_self, w_other, 'mul')

def injected_add(space, w_self, w_other):
    return injected_op(space, w_self, w_other, 'add')

def injected_sub(space, w_self, w_other):
    return injected_op(space, w_self, w_other, 'sub')

def injected_div(space, w_self, w_other):
    return injected_op(space, w_self, w_other, 'div')

injected_methods = {
    '__getitem__': interp2app(injected_getitem),
    '__mul__': interp2app(injected_mul),
    '__add__': interp2app(injected_add),
    '__sub__': interp2app(injected_sub),
    '__div__': interp2app(injected_div),
    '__rmul__': interp2app(injected_mul),
    '__radd__': interp2app(injected_add),
    '__rsub__': interp2app(injected_sub),
    '__rdiv__': interp2app(injected_div),
}

def inject_operator(space, name, dict_w, pto):
    assert name == 'numpy.ndarray'
    org = space.fromcache(Original)
    org.w_original_getitem = dict_w['__getitem__']
    org.w_original_mul = dict_w['__mul__']
    for key, w_value in org.injected_methods_w:
        dict_w[key] = w_value
    return W_ArrayObject.typedef

def inject_module(space, w_mod, name):
    assert name == 'numpy.core.multiarray'
    org = space.fromcache(Original)
    w_type = space.appexec([w_mod], """(mod):
        return mod.typeinfo['DOUBLE'][-1]
    """)
    w_array_type = space.getattr(w_mod, space.newtext('ndarray'))
    assert isinstance(w_array_type, W_TypeObject)
    assert isinstance(w_type, W_TypeObject)
    org.w_float64_type = w_type
    org.w_array_type = w_array_type
