import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import jit
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize

from pypy.interpreter.error import OperationError
from pypy.module._hpy_universal import llapi, handles
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal.bridge import BRIDGE, hpy_get_bridge

CONTEXT_FIELDS = unrolling_iterable(llapi.HPyContext.TO._names)
CONSTANT_NAMES = unrolling_iterable([name for name, _ in handles.CONSTANTS])
DUMMY_FUNC = lltype.FuncType([], lltype.Void)

@specialize.memo()
def make_missing_function(space, name):
    def missing_function():
        print ("oops! calling the slot '%s', "
               "which is not implemented" % (name,))
        raise OperationError(space.w_NotImplementedError, space.newtext(name))
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
        self.setup_ctx()
        if not self.space.config.translating:
            self.setup_bridge()

    def setup_ctx(self):
        space = self.space
        self.ctx = lltype.malloc(llapi.HPyContext.TO, flavor='raw', immortal=True)

        for name in CONTEXT_FIELDS:
            if name == 'c_ctx_version':
                continue
            if name.startswith('c_ctx_'):
                # this is a function pointer: assign a default value so we get
                # a reasonable error message if it's called without being
                # assigned to something else
                missing_function = make_missing_function(space, name)
                funcptr = llhelper(lltype.Ptr(DUMMY_FUNC), missing_function)
                setattr(self.ctx, name, rffi.cast(rffi.VOIDP, funcptr))
        i = 0
        for name in CONSTANT_NAMES:
            if name != 'NULL':
                h_struct = getattr(self.ctx, 'c_h_' + name)
                h_struct.c__i = i
            i = i + 1

        for func in API.all_functions:
            if func.cpyext and not space.config.objspace.hpy_cpyext_API:
                # ignore cpyext functions if hpy_cpyext_API is False
                continue
            funcptr = rffi.cast(rffi.VOIDP, func.get_llhelper(space))
            ctx_field = 'c_ctx_' + func.basename
            setattr(self.ctx, ctx_field, funcptr)

        self.ctx.c_ctx_Err_Occurred = rffi.cast(rffi.VOIDP, llapi.pypy_HPyErr_Occurred)
        self.ctx.c_ctx_Err_SetString = rffi.cast(rffi.VOIDP, llapi.pypy_HPyErr_SetString)

    def setup_bridge(self):
        """
        NOT_RPYTHON

        This function should be called only in the non-translated case
        """
        bridge = hpy_get_bridge()
        for func in BRIDGE.all_functions:
            funcptr = rffi.cast(rffi.VOIDP, func.get_llhelper(self.space))
            fieldname = 'c_' + func.__name__
            setattr(bridge, fieldname, funcptr)
