import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import jit
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize
from pypy.module.hpy_universal import llapi, handles
from pypy.module.hpy_universal.apiset import API

CONTEXT_FIELDS = unrolling_iterable(llapi.HPyContext.TO._names)
CONSTANT_NAMES = unrolling_iterable([name for name, _ in handles.CONSTANTS])
DUMMY_FUNC = lltype.FuncType([], lltype.Void)

@specialize.memo()
def make_missing_function(name):
    def missing_function():
        print ("oops! calling the slot '%s', "
               "which is not implemented" % (name,))
        os._exit(1)
    return missing_function


class State:
    def __init__(self, space):
        "NOT_RPYTHON"
        self.space = space
        self.ctx = lltype.nullptr(llapi.HPyContext.TO)

    @jit.dont_look_inside
    def setup(self):
        if self.ctx:
            return

        space = self.space
        self.ctx = llapi._HPy_GetGlobalCtx()

        for name in CONTEXT_FIELDS:
            if name == 'c_ctx_version':
                continue
            if name.startswith('c_ctx_'):
                # this is a function pointer: assign a default value so we get
                # a reasonable error message if it's called without being
                # assigned to something else
                missing_function = make_missing_function(name)
                funcptr = llhelper(lltype.Ptr(DUMMY_FUNC), missing_function)
                setattr(self.ctx, name, rffi.cast(rffi.VOIDP, funcptr))
        i = 0
        for name in CONSTANT_NAMES:
            if name != 'NULL':
                h_struct = getattr(self.ctx, 'c_h_' + name)
                h_struct.c__i = i
            i = i + 1

        # XXX this is not RPython, we need a way to turn this into an
        # unrolling_iterable
        for func in API.all_functions:
            funcptr = rffi.cast(rffi.VOIDP, func.get_llhelper(space))
            ctx_field = 'c_ctx_' + func.basename
            setattr(self.ctx, ctx_field, funcptr)

        self.ctx.c_ctx_Arg_Parse = rffi.cast(rffi.VOIDP, llapi.DONT_CALL_ctx_Arg_Parse)
