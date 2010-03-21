from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import PyObject, from_ref, NullPointerException, \
        InvalidPointerException, make_ref
from pypy.module.cpyext.state import State
from pypy.rlib.objectmodel import we_are_translated


class W_PyCFunctionObject(Wrappable):
    def __init__(self, ml, w_self):
        self.ml = ml
        self.w_self = w_self

@unwrap_spec(ObjSpace, W_Root, Arguments)
def cfunction_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_kw = space.newdict()
    for key, w_value in kw_w:
        space.setitem(w_kw, space.wrap(key), w_value)
    args_tuple = space.newtuple([space.wrap(args_w), w_kw])
    #null = lltype.nullptr(PyObject.TO) # XXX for the moment

    # Call the C function
    result = self.ml.c_ml_meth(make_ref(space, self.w_self), make_ref(space, args_tuple))
    try:
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

    # XXX result.decref()
    return ret

W_PyCFunctionObject.typedef = TypeDef(
    'builtin_function_or_method',
    __call__ = interp2app(cfunction_descr_call),
    )

def PyCFunction_NewEx(space, ml, w_self):
    return space.wrap(W_PyCFunctionObject(ml, w_self))
