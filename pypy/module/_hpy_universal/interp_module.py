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
        if space.config.objspace.hpy_cpyext_API:
            pymethods = rffi.cast(rffi.VOIDP, hpydef.c_legacy_methods)
            attach_legacy_methods(space, pymethods, w_mod, modname)
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
            hpymeth = p[i].c_meth
            name = rffi.constcharp2str(hpymeth.c_name)
            sig = rffi.cast(lltype.Signed, hpymeth.c_signature)
            doc = get_doc(hpymeth.c_doc)
            w_extfunc = interp_extfunc.W_ExtensionFunction(
                space, name, sig, doc, hpymeth.c_impl, w_mod)
            space.setattr(w_mod, space.newtext(w_extfunc.name), w_extfunc)
            i += 1
    return handles.new(space, w_mod)


def get_doc(c_doc):
    if not c_doc:
        return None
    return rffi.constcharp2str(c_doc)
