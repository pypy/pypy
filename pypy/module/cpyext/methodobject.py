from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.function import BuiltinFunction, descr_function_get
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import PyObject, from_ref, NullPointerException, \
        InvalidPointerException, make_ref
from pypy.module.cpyext.state import State
from pypy.rlib.objectmodel import we_are_translated


# XXX use Function as a parent class?
class W_PyCFunctionObject(Wrappable):
    acceptable_as_base_class = False
    def __init__(self, space, ml, w_self):
        self.space = space
        self.ml = ml
        self.w_self = w_self

    def call(self, w_self, args_tuple):
        space = self.space
        # Call the C function
        if w_self is None:
            w_self = self.w_self
        result = self.ml.c_ml_meth(make_ref(space, w_self), make_ref(space, args_tuple))
        try:
            if result:
                result.c_obj_refcnt -= 1 
            ret = from_ref(space, result)
        except NullPointerException:
            state = space.fromcache(State)
            state.check_and_raise_exception()
            assert False, "NULL returned but no exception set"
        except InvalidPointerException:
            if not we_are_translated():
                import sys
                print >>sys.stderr, "Calling a C function return an invalid PyObject" \
                        " pointer."
            raise
        return ret

class W_PyCMethodObject(W_PyCFunctionObject):
    def __init__(self, space, ml):
        self.space = space
        self.ml = ml


@unwrap_spec(ObjSpace, W_Root, Arguments)
def cfunction_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_kw = space.newdict()
    for key, w_value in kw_w:
        space.setitem(w_kw, space.wrap(key), w_value)
    args_tuple = space.newtuple([space.wrap(args_w), w_kw])
    #null = lltype.nullptr(PyObject.TO) # XXX for the moment
    ret = self.call(None, args_tuple)
    # XXX result.decref()
    return ret

@unwrap_spec(ObjSpace, W_Root, Arguments)
def cmethod_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_kw = space.newdict()
    for key, w_value in kw_w:
        space.setitem(w_kw, space.wrap(key), w_value)
    args_tuple = space.newtuple([space.wrap(args_w[1:]), w_kw])
    ret = self.call(args_w[0], args_tuple)
    # XXX result.decref()
    return ret


W_PyCFunctionObject.typedef = TypeDef(
    'builtin_function',
    __call__ = interp2app(cfunction_descr_call),
    __get__ = interp2app(descr_function_get),
    )

W_PyCMethodObject.typedef = TypeDef(
    'builtin_method',
    __get__ = interp2app(descr_function_get),
    __call__ = interp2app(cmethod_descr_call),
    )


def PyCFunction_NewEx(space, ml, w_self): # not directly the API sig
    return space.wrap(W_PyCFunctionObject(space, ml, w_self))


def PyDescr_NewMethod(space, pto, method):
    return space.wrap(W_PyCMethodObject(space, method))

