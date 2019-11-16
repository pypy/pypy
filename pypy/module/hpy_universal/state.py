import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.annlowlevel import llhelper
from pypy.module.hpy_universal import llapi


class State:
    def __init__(self, space):
        "NOT_RPYTHON"
        self.space = space
        self.ctx = lltype.nullptr(rffi.VOIDP.TO)

    def setup(self):
        if self.ctx:
            return

        self.ctx = llapi._HPy_GetGlobalCtx()

        DUMMY_FUNC = lltype.FuncType([], lltype.Void)
        for name in llapi.HPyContext.TO._names:
            if name != 'ctx_version':
                def missing_function(name=name):
                    print ("oops! calling the slot %r, which is not implemented"
                           % (name,))
                    os._exit(1)
                funcptr = llhelper(lltype.Ptr(DUMMY_FUNC), missing_function)
                setattr(self.ctx, name, rffi.cast(rffi.VOIDP, funcptr))

        # XXX collect all these functions automatically
        from pypy.module.hpy_universal import interp_hpy
        space = self.space
        
        funcptr = interp_hpy.HPyModule_Create.get_llhelper(space)
        self.ctx.ctx_Module_Create = rffi.cast(rffi.VOIDP, funcptr)
        #
        funcptr = interp_hpy.HPyNone_Get.get_llhelper(space)
        self.ctx.ctx_None_Get = rffi.cast(rffi.VOIDP, funcptr)
