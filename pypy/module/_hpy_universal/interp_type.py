from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.argument import Arguments
from pypy.objspace.std.typeobject import _create_new_type
from pypy.interpreter.error import oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles, llapi
from .interp_extfunc import W_ExtensionMethod
from .interp_slot import fill_slot


@API.func("void *_HPy_Cast(HPyContext ctx, HPy h)")
def _HPy_Cast(space, ctx, h):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy _HPy_New(HPyContext ctx, HPy h_type, void **data)")
def _HPy_New(space, ctx, h_type, data):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError


@API.func("HPy HPyType_FromSpec(HPyContext ctx, HPyType_Spec *spec)")
def HPyType_FromSpec(space, ctx, spec):
    w_dict = space.newdict()
    specname = rffi.constcharp2str(spec.c_name)
    dotpos = specname.rfind('.')
    if dotpos < 0:
        name = specname
        modname = None
    else:
        name = specname[dotpos + 1:]
        modname = specname[:dotpos]

    if modname is not None:
        space.setitem_str(w_dict, '__module__', space.newtext(modname))

    w_bases = space.newtuple([])
    __args__ = Arguments(space, [])

    w_result = _create_new_type(
        space, space.w_type, space.newtext(name), w_bases, w_dict, __args__)
    if spec.c_defines:
        p = spec.c_defines
        i = 0
        HPyDef_Kind = llapi.cts.gettype('HPyDef_Kind')
        while p[i]:
            kind = rffi.cast(lltype.Signed, p[i].c_kind)
            if kind == HPyDef_Kind.HPyDef_Kind_Slot:
                hpyslot = llapi.cts.cast('HPyDef_Slot*', p[i]).c_slot
                fill_slot(space, w_result, hpyslot)
            elif kind == HPyDef_Kind.HPyDef_Kind_Meth:
                hpymeth = p[i].c_meth
                w_extfunc = W_ExtensionMethod(space, hpymeth, w_result)
                w_result.setdictvalue(
                    space, rffi.constcharp2str(hpymeth.c_name), w_extfunc)
            else:
                raise oefmt(space.w_RuntimeError, "Unspported HPyDef kind!")
            i += 1
    return handles.new(space, w_result)

@API.func("HPy HPyType_GenericNew(HPyContext ctx, HPy type, HPy *args, HPy_ssize_t nargs, HPy kw)")
def HPyType_GenericNew(space, ctx, type, args, nargs, kw):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError
