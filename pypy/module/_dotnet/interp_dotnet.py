from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.dotnet import CLR, box, unbox, NativeException, native_exc, new_array, init_array

# TODO: this code is not translatable

Type = CLR.System.Type
Object = CLR.System.Object
TargetInvocationException = NativeException(CLR.System.Reflection.TargetInvocationException)

import sys

class W_CliObject(Wrappable):
    def __init__(self, space, obj):
        self.space = space
        self.obj = obj

    def call_method(self, name, w_args):
        t = self.obj.GetType()
        meth = t.GetMethod(name) # TODO: overloading!
        args = self.rewrap_args(w_args)
        try:
            res = meth.Invoke(self.obj, args)
        except TargetInvocationException, e:
            inner = native_exc(e).get_InnerException()
            message = str(inner.get_Message())
            # TODO: use the appropriate exception, not StandardError
            raise OperationError(self.space.w_StandardError, self.space.wrap(message))
        return self.cli2py(res)
    call_method.unwrap_spec = ['self', str, W_Root]

    def rewrap_args(self, w_args):
        py_args = self.space.unpackiterable(w_args)
        res = new_array(Object, len(py_args))
        for i in range(len(py_args)):
            res[i] = self.py2cli(py_args[i])
        return res

    def py2cli(self, w_obj):
        space = self.space
        if space.is_true(space.isinstance(w_obj, self.space.w_int)):
            return box(space.int_w(w_obj))
        else:
            assert False

    def cli2py(self, obj):
        intval = unbox(obj, ootype.Signed) # TODO: support other types
        return self.space.wrap(intval)


def cli_object_new(space, w_subtype, typename):
    t = Type.GetType(typename)
    ctor = t.GetConstructor(init_array(Type))
    obj = ctor.Invoke(init_array(Object))
    return space.wrap(W_CliObject(space, obj))
cli_object_new.unwrap_spec = [ObjSpace, W_Root, str]


W_CliObject.typedef = TypeDef(
    '_CliObject_internal',
    __new__ = interp2app(cli_object_new),
    call_method = interp2app(W_CliObject.call_method),
    )
