import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import jit
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize
from pypy.module.hpy_universal import llapi

CONTEXT_NAMES = unrolling_iterable(llapi.HPyContext.TO._names)
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

        self.ctx = llapi._HPy_GetGlobalCtx()

        for name in CONTEXT_NAMES:
            if name != 'c_ctx_version':
                missing_function = make_missing_function(name)
                funcptr = llhelper(lltype.Ptr(DUMMY_FUNC), missing_function)
                setattr(self.ctx, name, rffi.cast(rffi.VOIDP, funcptr))

        # XXX collect all these functions automatically
        from pypy.module.hpy_universal import interp_hpy
        space = self.space
        
        funcptr = interp_hpy.HPyModule_Create.get_llhelper(space)
        self.ctx.c_ctx_Module_Create = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPyNone_Get.get_llhelper(space)
        self.ctx.c_ctx_None_Get = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPy_Dup.get_llhelper(space)
        self.ctx.c_ctx_Dup = rffi.cast(rffi.VOIDP, funcptr)
