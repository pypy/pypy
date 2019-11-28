from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rdynload import dlopen, dlsym, DLOpenError
from rpython.rlib import rutf8

from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import raise_import_error
from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError, oefmt

from pypy.module.hpy_universal import llapi, handles, interp_extfunc
from pypy.module.hpy_universal.state import State
from pypy.module.hpy_universal.apiset import API
from pypy.module.cpyext.api import generic_cpy_call_dont_convert_result


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
            if not p[i].c_ml_flags & llapi._HPy_METH:
                # we need to add support for legacy methods through cpyext
                raise oefmt(space.w_NotImplementedError, "non-hpy method: %s",
                            rffi.constcharp2str(p[i].c_ml_name))
            w_extfunc = interp_extfunc.W_ExtensionFunction(p[i], w_mod)
            space.setattr(w_mod, space.newtext(w_extfunc.name), w_extfunc)
            i += 1
    #
    return handles.new(space, w_mod)


@API.func("HPy HPy_Dup(HPyContext ctx, HPy h)")
def HPy_Dup(space, ctx, h):
    return handles.dup(space, h)

@API.func("void HPy_Close(HPyContext ctx, HPy h)")
def HPy_Close(space, ctx, h):
    handles.close(space, h)

@API.func("HPy HPyLong_FromLong(HPyContext ctx, long value)")
def HPyLong_FromLong(space, ctx, value):
    w_obj = space.newint(rffi.cast(lltype.Signed, value))
    return handles.new(space, w_obj)

@API.func("long HPyLong_AsLong(HPyContext ctx, HPy h)")
def HPyLong_AsLong(space, ctx, h):
    w_obj = handles.deref(space, h)
    #w_obj = space.int(w_obj)     --- XXX write a test for this
    value = space.int_w(w_obj)
    result = rffi.cast(rffi.LONG, value)
    #if rffi.cast(lltype.Signed, result) != value: --- XXX on Windows 64
    #    ...
    return result

@API.func("HPy HPyNumber_Add(HPyContext ctx, HPy x, HPy y)")
def HPyNumber_Add(space, ctx, h1, h2):
    w_obj1 = handles.deref(space, h1)
    w_obj2 = handles.deref(space, h2)
    w_result = space.add(w_obj1, w_obj2)
    return handles.new(space, w_result)

@API.func("HPy HPyUnicode_FromString(HPyContext ctx, const char *utf8)")
def HPyUnicode_FromString(space, ctx, utf8):
    w_obj = _maybe_utf8_to_w(space, utf8)
    return handles.new(space, w_obj)

def _maybe_utf8_to_w(space, utf8):
    # should this be a method of space?
    s = rffi.charp2str(utf8)
    try:
        length = rutf8.check_utf8(s, allow_surrogates=False)
    except rutf8.CheckError:
        raise   # XXX do something
    return space.newtext(s, length)

@API.func("void HPyErr_SetString(HPyContext ctx, HPy type, const char *message)")
def HPyErr_SetString(space, ctx, h_exc_type, utf8):
   w_obj = _maybe_utf8_to_w(space, utf8)
   w_exc_type = handles.deref(space, h_exc_type)
   raise OperationError(w_exc_type, w_obj)


def create_hpy_module(space, name, origin, lib, initfunc):
    state = space.fromcache(State)
    initfunc = rffi.cast(llapi.HPyInitFunc, initfunc)
    h_module = generic_cpy_call_dont_convert_result(space, initfunc, state.ctx)
    return handles.consume(space, h_module)

def descr_load_from_spec(space, w_spec):
    name = space.text_w(space.getattr(w_spec, space.newtext("name")))
    origin = space.fsencode_w(space.getattr(w_spec, space.newtext("origin")))
    return descr_load(space, name, origin)

@unwrap_spec(name='text', libpath='fsencode')
def descr_load(space, name, libpath):
    state = space.fromcache(State)
    state.setup()
    try:
        with rffi.scoped_str2charp(libpath) as ll_libname:
            lib = dlopen(ll_libname, space.sys.dlopenflags)
    except DLOpenError as e:
        w_path = space.newfilename(libpath)
        raise raise_import_error(space,
            space.newfilename(e.msg), space.newtext(name), w_path)

    basename = name.split('.')[-1]
    init_name = 'HPyInit_' + basename
    try:
        initptr = dlsym(lib, init_name)
    except KeyError:
        msg = b"function %s not found in library %s" % (
            init_name, space.utf8_w(space.newfilename(libpath)))
        w_path = space.newfilename(libpath)
        raise raise_import_error(
            space, space.newtext(msg), space.newtext(name), w_path)
    return create_hpy_module(space, name, libpath, lib, initptr)
