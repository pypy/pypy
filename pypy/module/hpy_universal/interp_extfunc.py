from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, interp2app

from pypy.module.hpy_universal import llapi, handles
from pypy.module.hpy_universal.state import State
from pypy.module.cpyext.api import generic_cpy_call_dont_convert_result


class W_ExtensionFunction(W_Root):
    _immutable_fields_ = ["flags", "name"]

    def __init__(self, ml, w_self):
        self.ml = ml
        self.w_self = w_self
        self.name = rffi.charp2str(self.ml.c_ml_name)
        self.flags = rffi.cast(lltype.Signed, self.ml.c_ml_flags)
        # fetch the real HPy function pointer, by calling ml_meth, which
        # is a function that returns it and also the CPython-only trampoline
        with lltype.scoped_alloc(
                rffi.CArray(llapi._HPyCFunctionPtr), 1) as funcptr:
            with lltype.scoped_alloc(
                    rffi.CArray(llapi._HPy_CPyCFunctionPtr), 1)  \
                                                        as ignored_trampoline:
                ml.c_ml_meth(funcptr, ignored_trampoline)
                self.cfuncptr = funcptr[0]

    def call_keywords(self, space, __args__):
        raise NotImplementedError("later")

    def call_noargs(self, space):
        state = space.fromcache(State)
        with handles.using(space, self.w_self) as h_self:
            h_result = generic_cpy_call_dont_convert_result(space, self.cfuncptr,
                state.ctx, h_self, 0)
        # XXX check for exceptions
        return handles.consume(space, h_result)

    def call_o(self, space, w_arg):
        state = space.fromcache(State)
        with handles.using(space, self.w_self) as h_self:
            with handles.using(space, w_arg) as h_arg:
                h_result = generic_cpy_call_dont_convert_result(space,
                                           self.cfuncptr, state.ctx, h_self, h_arg)
        # XXX check for exceptions
        return handles.consume(space, h_result)

    def call_varargs(self, space, arguments_w):
        w_tuple = space.newtuple(arguments_w)
        # xxx here we just invoke call_o() with the w_tuple
        return self.call_o(space, w_tuple)

    def descr_call(self, space, __args__):
        flags = self.flags
        length = len(__args__.arguments_w)

        if flags & llapi.METH_KEYWORDS:
            return self.call_keywords(space, __args__)

        if __args__.keywords:
            raise oefmt(space.w_TypeError,
                        "%s() takes no keyword arguments", self.name)

        if flags & llapi.METH_NOARGS:
            if length == 0:
                return self.call_noargs(space)
            raise oefmt(space.w_TypeError,
                        "%s() takes no arguments", self.name)

        if flags & llapi.METH_O:
            if length != 1:
                raise oefmt(space.w_TypeError,
                            "%s() takes exactly one argument (%d given)",
                            self.name, length)
            return self.call_o(space, __args__.arguments_w[0])

        if flags & llapi.METH_VARARGS:
            return self.call_varargs(space, __args__.arguments_w)
        else:  # shouldn't happen!
            raise oefmt(space.w_RuntimeError, "unknown calling convention")



W_ExtensionFunction.typedef = TypeDef(
    'extension_function',
    __call__ = interp2app(W_ExtensionFunction.descr_call),
    )
W_ExtensionFunction.typedef.acceptable_as_base_class = False
