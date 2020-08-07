from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.function import descr_function_get, Method
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.objspace.std.typeobject import W_TypeObject

from pypy.module._hpy_universal import llapi, handles
from pypy.module._hpy_universal.state import State

METH_FLAGS = [
    llapi.HPy_METH_VARARGS,
    llapi.HPy_METH_KEYWORDS,
    llapi.HPy_METH_NOARGS,
    llapi.HPy_METH_O
]

class W_ExtensionFunction(W_Root):
    # XXX: should we have separate classes for each mode?
    _immutable_fields_ = ["flags", "name"]

    def __init__(self, space, hpymeth, w_self):
        self.hpymeth = hpymeth
        self.w_self = w_self
        self.name = rffi.constcharp2str(self.hpymeth.c_name)
        self.flags = rffi.cast(lltype.Signed, self.hpymeth.c_signature)
        if self.flags not in METH_FLAGS:
            raise oefmt(space.w_ValueError, "Unsupported HPyMeth signature")
        self.cfuncptr = self.hpymeth.c_impl

    def call_noargs(self, space, h_self):
        state = space.fromcache(State)
        func = llapi.cts.cast('HPyFunc_noargs', self.cfuncptr)
        h_result = func(state.ctx, h_self)
        # XXX check for exceptions
        return handles.consume(space, h_result)

    def call_o(self, space, h_self, w_arg):
        state = space.fromcache(State)
        with handles.using(space, w_arg) as h_arg:
            func = llapi.cts.cast('HPyFunc_o', self.cfuncptr)
            h_result = func(state.ctx, h_self, h_arg)
        # XXX check for exceptions
        return handles.consume(space, h_result)

    def call_varargs_kw(self, space, h_self, __args__, skip_args, has_keywords):
        # this function is more or less the equivalent of
        # ctx_CallRealFunctionFromTrampoline in cpython-universal
        n = len(__args__.arguments_w) - skip_args

        # XXX this looks inefficient: ideally, we would like the equivalent of
        # alloca(): do we have it in RPython? The alternative is to wrap
        # arguments_w in a tuple, convert to handle and pass it to a C
        # function whichs calls alloca() and the forwards everything to the
        # functpr
        with lltype.scoped_alloc(rffi.CArray(llapi.HPy), n) as args_h:
            i = 0
            while i < n:
                args_h[i] = handles.new(space, __args__.arguments_w[i + skip_args])
                i += 1

            if has_keywords:
                h_result = self.call_keywords(space, h_self, args_h, n, __args__)
            else:
                h_result = self.call_varargs(space, h_self, args_h, n)

            # XXX this should probably be in a try/finally. We should add a
            # test to check that we don't leak handles
            for i in range(n):
                handles.close(space, args_h[i])

        return handles.consume(space, h_result)

    def call_varargs(self, space, h_self, args_h, n):
        state = space.fromcache(State)
        fptr = llapi.cts.cast('HPyFunc_varargs', self.cfuncptr)
        return fptr(state.ctx, h_self, args_h, n)

    def call_keywords(self, space, h_self, args_h, n, __args__):
        state = space.fromcache(State)
        # XXX: if there are no keywords, should we pass HPy_NULL or an empty
        # dict?
        h_kw = 0
        if __args__.keywords:
            w_kw = space.newdict()
            for i in range(len(__args__.keywords)):
                key = __args__.keywords[i]
                w_value = __args__.keywords_w[i]
                space.setitem_str(w_kw, key, w_value)
            h_kw = handles.new(space, w_kw)

        fptr = llapi.cts.cast('HPyFunc_keywords', self.cfuncptr)
        try:
            return fptr(state.ctx, h_self, args_h, n, h_kw)
        finally:
            if h_kw:
                handles.consume(space, h_kw)


    def descr_call(self, space, __args__):
        with handles.using(space, self.w_self) as h_self:
            return self.call(space, h_self, __args__)

    def call(self, space, h_self, __args__, skip_args=0):
        flags = self.flags
        length = len(__args__.arguments_w) - skip_args

        if flags == llapi.HPy_METH_KEYWORDS:
            return self.call_varargs_kw(space, h_self, __args__, skip_args, has_keywords=True)

        if __args__.keywords:
            raise oefmt(space.w_TypeError,
                        "%s() takes no keyword arguments", self.name)

        if flags == llapi.HPy_METH_NOARGS:
            if length == 0:
                return self.call_noargs(space, h_self)
            raise oefmt(space.w_TypeError,
                        "%s() takes no arguments", self.name)

        if flags == llapi.HPy_METH_O:
            if length != 1:
                raise oefmt(space.w_TypeError,
                            "%s() takes exactly one argument (%d given)",
                            self.name, length)
            return self.call_o(space, h_self, __args__.arguments_w[skip_args])

        if flags == llapi.HPy_METH_VARARGS:
            return self.call_varargs_kw(space, h_self, __args__, skip_args, has_keywords=False)
        else:  # shouldn't happen!
            raise oefmt(space.w_RuntimeError, "unknown calling convention")



W_ExtensionFunction.typedef = TypeDef(
    'extension_function',
    __call__ = interp2app(W_ExtensionFunction.descr_call),
    )
W_ExtensionFunction.typedef.acceptable_as_base_class = False


class W_ExtensionMethod(W_ExtensionFunction):
    def __init__(self, space, hpymeth, w_objclass):
        W_ExtensionFunction.__init__(self, space, hpymeth, space.w_None)
        self.w_objclass = w_objclass

    def descr_call(self, space, __args__):
        # XXX: basically a copy of cpyext's W_PyCMethodObject.descr_call()
        if len(__args__.arguments_w) == 0:
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%8' of '%s' object needs an argument",
                self.name, self.w_objclass.getname(space))
        w_instance = __args__.arguments_w[0]
        # XXX: needs a stricter test
        if not space.isinstance_w(w_instance, self.w_objclass):
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%8' requires a '%s' object but received a '%T'",
                self.name, w_objclass.name, w_instance)
        #
        with handles.using(space, w_instance) as h_instance:
            return self.call(space, h_instance, __args__, skip_args=1)

W_ExtensionMethod.typedef = TypeDef(
    'method_descriptor_',
    __get__ = interp2app(descr_function_get),
    __call__ = interp2app(W_ExtensionMethod.descr_call),
    )
W_ExtensionMethod.typedef.acceptable_as_base_class = False
