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
        legacy_methoddefs = [] # for those using the old C-API calling convention
        while p[i].c_ml_name:
            if widen(p[i].c_ml_flags) & llapi._HPy_METH:
                # hpy native methods
                w_extfunc = interp_extfunc.W_ExtensionFunction(p[i], w_mod)
                space.setattr(w_mod, space.newtext(w_extfunc.name), w_extfunc)
            else:
                # legacy cpyext-based methods, to be processed later
                legacy_methoddefs.append(p[i])
            i += 1
        if legacy_methoddefs:
            attach_legacy_methods(space, legacy_methoddefs, w_mod, modname)
    #
    return handles.new(space, w_mod)


def attach_legacy_methods(space, hpymethods, w_mod, modname):
    from pypy.module.cpyext.methodobject import PyMethodDef, PyCFunction
    from pypy.module.cpyext.modsupport import convert_method_defs
    PyMethodDefP = rffi.CArrayPtr(PyMethodDef)

    # convert hpymethods into a C array of PyMethodDef
    dict_w = {}
    n = len(hpymethods)
    with lltype.scoped_alloc(PyMethodDefP.TO, n+1) as pymethods:
        for i in range(n):
            src = hpymethods[i] # HPyMethodDef
            dst = pymethods[i]  # PyMethodDef
            dst.c_ml_name = src.c_ml_name
            dst.c_ml_doc = src.c_ml_doc
            # for legacy methods, ml_meth contains a PyCFunction which can be
            # called using the old C-API/cpyext calling convention
            dst.c_ml_meth = rffi.cast(PyCFunction, src.c_ml_meth)
            rffi.setintfield(dst, 'c_ml_flags', widen(src.c_ml_flags) & ~llapi._HPy_METH)
        pymethods[n].c_ml_name = lltype.nullptr(rffi.CONST_CCHARP.TO)
        convert_method_defs(space, dict_w, pymethods, None, w_mod, modname)

    for key, w_func in dict_w.items():
        space.setattr(w_mod, space.newtext(key), w_func)
