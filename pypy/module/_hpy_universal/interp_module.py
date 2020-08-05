from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import widen
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.module import Module
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal import handles
from pypy.module._hpy_universal import interp_extfunc
from pypy.module._hpy_universal.interp_cpy_compat import attach_legacy_methods


@API.func("HPy HPyModule_Create(HPyContext ctx, HPyModuleDef *def)")
def HPyModule_Create(space, ctx, hpydef):
    modname = rffi.constcharp2str(hpydef.c_m_name)
    w_mod = Module(space, space.newtext(modname))
    #
    # add the functions defined in hpydef.c_legacy_methods
    if hpydef.c_legacy_methods:
        p = hpydef.c_legacy_methods
        i = 0
        legacy_methoddefs = [] # for those using the old C-API calling convention
        while p[i].c_ml_name:
            # legacy cpyext-based methods, to be processed later
            legacy_methoddefs.append(p[i])
            i += 1
        if legacy_methoddefs:
            if space.config.objspace.hpy_cpyext_API:
                attach_legacy_methods(space, legacy_methoddefs, w_mod, modname)
            else:
                raise oefmt(space.w_RuntimeError,
                        "Module %s contains legacy methods, but _hpy_universal "
                        "was compiled without cpyext support", modname)
    #
    # add the native HPy defines
    if hpydef.c_defines:
        p = hpydef.c_defines
        i = 0
        while p[i]:
            # hpy native methods
            w_extfunc = interp_extfunc.W_ExtensionFunction(space, p[i].c_meth, w_mod)
            space.setattr(w_mod, space.newtext(w_extfunc.name), w_extfunc)
            i += 1
    return handles.new(space, w_mod)
