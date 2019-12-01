from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import widen
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.module import Module
from pypy.module.hpy_universal.apiset import API
from pypy.module.hpy_universal import llapi
from pypy.module.hpy_universal import handles
from pypy.module.hpy_universal import interp_extfunc


@API.func("HPy HPyModule_Create(HPyContext ctx, HPyModuleDef *def)")
def HPyModule_Create(space, ctx, hpydef):
    modname = rffi.constcharp2str(hpydef.c_m_name)
    w_mod = Module(space, space.newtext(modname))
    #
    # add all the functions defined in hpydef.c_m_methods
    if hpydef.c_m_methods:
        p = hpydef.c_m_methods
        i = 0
        while p[i].c_ml_name:
            if not widen(p[i].c_ml_flags) & llapi._HPy_METH:
                # we need to add support for legacy methods through cpyext
                raise oefmt(space.w_NotImplementedError, "non-hpy method: %s",
                            rffi.constcharp2str(p[i].c_ml_name))
            w_extfunc = interp_extfunc.W_ExtensionFunction(p[i], w_mod)
            space.setattr(w_mod, space.newtext(w_extfunc.name), w_extfunc)
            i += 1
    #
    return handles.new(space, w_mod)
