from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import PyObject, from_ref, NullPointerException, \
        InvalidPointerException
from pypy.module.cpyext.state import State
from pypy.rlib.objectmodel import we_are_translated


class W_PyCFunctionObject(Wrappable):
    def __init__(self, ml, w_self, w_modname):
        self.ml = ml
        self.w_self = w_self
        self.w_modname = w_modname

@unwrap_spec(ObjSpace, W_Root, Arguments)
def cfunction_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    null = lltype.nullptr(PyObject.TO) # XXX for the moment

    # Call the C function
    result = self.ml.c_ml_meth(null, null)
    try:
        ret = from_ref(space, result)
    except NullPointerException:
        state = space.fromcache(State)
        exc_value = state.exc_value
        exc_type = state.exc_type
        assert exc_value is not None and exc_type is not None
        state.exc_value = None
        state.exc_type = None
        raise OperationError(exc_type, exc_value)
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

def PyCFunction_NewEx(space, ml, w_self, w_modname):
    return space.wrap(W_PyCFunctionObject(ml, w_self, w_modname))
