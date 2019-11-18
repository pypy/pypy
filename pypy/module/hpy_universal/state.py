import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import jit
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize
from pypy.module.hpy_universal import llapi, handles

CONTEXT_NAMES = unrolling_iterable(llapi.HPyContext.TO._names)
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

        for name in CONTEXT_NAMES:
            if name == 'c_ctx_version':
                continue
            if name.startswith('c_ctx_'):
                missing_function = make_missing_function(name)
                funcptr = llhelper(lltype.Ptr(DUMMY_FUNC), missing_function)
                setattr(self.ctx, name, rffi.cast(rffi.VOIDP, funcptr))
        i = 0
        for name in CONSTANT_NAMES:
            if name != 'NULL':
                setattr(self.ctx, 'c_h_' + name, i)
            i = i + 1

        # XXX collect all these functions automatically
        from pypy.module.hpy_universal import interp_hpy
        
        funcptr = interp_hpy.HPyModule_Create.get_llhelper(space)
        self.ctx.c_ctx_Module_Create = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPy_Dup.get_llhelper(space)
        self.ctx.c_ctx_Dup = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPy_Close.get_llhelper(space)
        self.ctx.c_ctx_Close = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPyLong_FromLong.get_llhelper(space)
        self.ctx.c_ctx_Long_FromLong = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPyLong_AsLong.get_llhelper(space)
        self.ctx.c_ctx_Long_AsLong = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPyNumber_Add.get_llhelper(space)
        self.ctx.c_ctx_Number_Add = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPyUnicode_FromString.get_llhelper(space)
        self.ctx.c_ctx_Unicode_FromString = rffi.cast(rffi.VOIDP, funcptr)
