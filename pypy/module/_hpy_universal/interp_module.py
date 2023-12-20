from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import widen
from pypy.interpreter.error import oefmt
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.module import Module, init_extra_module_attrs
from pypy.module._hpy_universal.apiset import API, DEBUG
from pypy.module._hpy_universal import interp_extfunc, llapi
from pypy.module._hpy_universal.state import State
from pypy.module._hpy_universal.interp_cpy_compat import attach_legacy_methods

NON_DEFAULT_MESSAGE = ("This is not allowed because custom " 
    "HPy_mod_create slot cannot return a builtin module "
    "object and cannot make any use of any other data "
    "defined in the HPyModuleDef. Either do not define "
    "HPy_mod_create slot and let the runtime create a builtin "
    "module object from the provided HPyModuleDef, or do not define "
    "anything else but the HPy_mod_create slot.")

@specialize.arg(0)
def hpymod_create(handles, modname, hpydef):
    space = handles.space
    w_mod = Module(space, space.newtext(modname))
    kinds = llapi.cts.gettype("HPyDef_Kind")
    slots = llapi.cts.gettype("HPySlot_Slot")
    #
    if hpydef.c_size < 0:
        raise oefmt(space.w_SystemError,
            "HPy does not permit HPyModuleDef.size < 0")
    elif hpydef.c_size > 0:
        raise oefmt(space.w_SystemError,
            "Module state is not supported yet in HPy, set "
            "HPyModuleDef.size = 0 if module state is not needed")
    # add the functions defined in hpydef.c_legacy_methods
    if hpydef.c_legacy_methods:
        if space.config.objspace.hpy_cpyext_API:
            pymethods = rffi.cast(rffi.VOIDP, hpydef.c_legacy_methods)
            attach_legacy_methods(space, pymethods, w_mod, modname, None)
        else:
            raise oefmt(space.w_RuntimeError,
                "Module %s contains legacy methods, but _hpy_universal "
                "was compiled without cpyext support", modname)
    #
    # add the native HPy module-level defines
    if hpydef.c_defines:
        create_func = llapi.cts.cast("HPySlot *", 0)
        found_non_create = False
        p = hpydef.c_defines
        i = 0
        while p[i]:
            # hpy native methods
            kind = widen(p[i].c_kind)
            if kind == kinds.HPyDef_Kind_Slot:
                hpyslot = llapi.cts.cast("HPySlot *", p[i].c_meth)
                slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
                if slot_num == slots.HPy_mod_create:
                    if create_func:
                        raise oefmt(space.w_SystemError,
                            "Multiple definitions of the HPy_mod_create "
                            "slot in HPyModuleDef.defines.")
                    create_func = hpyslot
                elif slot_num != slots.HPy_mod_exec:
                    raise oefmt(space.w_SystemError,
                        "Unsupported slot in HPyModuleDef.defines (value: %d).",
                         slot_num)
                else:
                    found_non_create = True
            else:
                hpymeth = p[i].c_meth
                name = rffi.constcharp2str(hpymeth.c_name)
                sig = rffi.cast(lltype.Signed, hpymeth.c_signature)
                doc = get_doc(hpymeth.c_doc)
                w_extfunc = handles.w_ExtensionFunction(
                    space, handles, name, sig, doc, hpymeth.c_impl, w_mod)
                space.setattr(w_mod, space.newtext(w_extfunc.name), w_extfunc)
                found_non_create = True
            i += 1
        if create_func:
            if found_non_create:
                raise oefmt(space.w_SystemError,
                    "HPyModuleDef defines a HPy_mod_create slot and some "
                    "other slots or methods. %s", NON_DEFAULT_MESSAGE)
            if (hpydef.c_legacy_methods or hpydef.c_size > 0 or
                hpydef.c_doc or hpydef.c_globals):
                raise oefmt(space.w_SystemError,
                    "HPyModuleDef defines a HPy_mod_create slot and some "
                    "of the other fields are not set to their default "
                    "value. %s", NON_DEFAULT_MESSAGE)
            # fast-call directly to W_ExtensionFunctionMixin.call_o
            func = llapi.cts.cast("HPyFunc_o", create_func.c_impl)
            with handles.using(w_mod) as h_arg:
                h = func(handles.get_ctx(), h_arg, h_arg)
            if h == 0:
                space.fromcache(State).raise_current_exception()
            w_result = handles.deref(h)
            if w_result and isinstance(w_result, type(w_mod)):
                raise oefmt(space.w_SystemError,
                    "HPy_mod_create slot returned a builtin module object. "
                    "This is currently not supported.")
            # Throw away the w_mod and return the result of mod_create()
            return w_result
    if hpydef.c_doc:
        w_doc = space.newtext(rffi.constcharp2str(hpydef.c_doc))
    else:
        w_doc = space.w_None
    space.setattr(w_mod, space.newtext('__doc__'), w_doc)
    space.setattr(w_mod, space.newtext('__file__'), space.w_None)
    init_extra_module_attrs(space, w_mod)
    return w_mod

@specialize.arg(0)
def hpymod_exec_def(handles, w_mod, hpydef):
    """ Traverse the hpydef, and execute any HPy_mod_exec slot
    """
    kinds = llapi.cts.gettype("HPyDef_Kind")
    slots = llapi.cts.gettype("HPySlot_Slot")
    space = handles.space
    if hpydef.c_defines:
        p = hpydef.c_defines
        i = 0
        while p[i]:
            # hpy native methods
            kind = widen(p[i].c_kind)
            if kind == kinds.HPyDef_Kind_Slot:
                hpyslot = llapi.cts.cast("HPySlot *", p[i].c_meth)
                slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
                if slot_num == slots.HPy_mod_exec:
                    # fast-call directly to W_ExtensionFunctionMixin.call_o
                    func = llapi.cts.cast("HPyFunc_o", hpyslot.c_impl)
                    with handles.using(w_mod) as h_arg:
                        result = func(handles.get_ctx(), h_arg, h_arg)
                    if result != 0:
                        space.fromcache(State).raise_current_exception()
            i += 1

def get_doc(c_doc):
    if not c_doc:
        return None
    return rffi.constcharp2str(c_doc)

@API.func("HPy HPyGlobal_Load(HPyContext *ctx, HPyGlobal global)")
def HPyGlobal_Load(space, handles, ctx, h_global):
    state = State.get(space)
    d_globals = state.global_handles
    if h_global not in d_globals:
        if h_global:
            w_global = handles.deref(h_global)
            w_s = space.repr(w_global)
            s = space.text_w(w_s)
        else:
            s = "<None>"
        raise oefmt(space.w_ValueError, "unknown HPyGlobal* in HPyGlobal_Load (%s)", s)
    return handles.new(d_globals[h_global])

@API.func("void HPyGlobal_Store(HPyContext *ctx, HPyGlobal *global, HPy h)")
def HPyGlobal_Store(space, handles, ctx, p_global, h_obj):
    if h_obj:
        w_obj = handles.deref(h_obj)
    else:
        w_obj = space.w_None
    state = State.get(space)
    d_globals = state.global_handles
    # Release a potential already existing p_global[0]
    if p_global[0] in d_globals:
        d_globals.pop(p_global[0])
    h_new = handles.new(w_obj)
    d_globals[h_new] = w_obj
    p_global[0] = h_new
