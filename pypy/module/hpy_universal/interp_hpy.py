from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rdynload import dlopen, dlsym, DLOpenError

from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import raise_import_error
from pypy.interpreter.module import Module

from pypy.module.hpy_universal import llapi, handles, interp_extfunc
from pypy.module.hpy_universal.state import State
from pypy.module.cpyext.api import generic_cpy_call_dont_convert_result


def apifunc(argtypes, restype, error):
    # XXX: at the moment, error is ignored. We should do something with it
    # and handle exceptions properly
    def decorate(fn):
        ll_functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
        def get_llhelper(space):
            def wrapper(*args):
                return fn(space, *args)
            return llhelper(ll_functype, wrapper)
        fn.get_llhelper = get_llhelper
        return fn
    return decorate


@apifunc([llapi.HPyContext, lltype.Ptr(llapi.HPyModuleDef)],
         llapi.HPy, error=0)
def HPyModule_Create(space, ctx, hpydef):
    modname = rffi.charp2str(hpydef.c_m_name)
    w_mod = Module(space, space.newtext(modname))
    #
    # add all the functions defined in hpydef.c_m_methods
    if hpydef.c_m_methods:
        p = hpydef.c_m_methods
        i = 0
        while p[i].c_ml_name:
            w_extfunc = interp_extfunc.W_ExtensionFunction(p[i])
            space.setattr(w_mod, space.newtext(w_extfunc.name), w_extfunc)
            i += 1
    #
    return handles.new(space, w_mod)


@apifunc([llapi.HPyContext], llapi.HPy, error=0)
def HPyNone_Get(space, ctx):
    return handles.new(space, space.w_None)


def create_hpy_module(space, name, origin, lib, initfunc):
    state = space.fromcache(State)
    initfunc = rffi.cast(llapi.HPyInitFuncPtr, initfunc)
    h_module = generic_cpy_call_dont_convert_result(space, initfunc, state.ctx)
    return handles.consume(space, h_module)

def descr_load_from_spec(space, w_spec):
    # XXX: this looks a lot like cpyext.api.create_extension_module()
    state = space.fromcache(State)
    state.setup()
    w_name = space.getattr(w_spec, space.newtext("name"))
    name = space.text_w(w_name)
    origin = space.text_w(space.getattr(w_spec, space.newtext("origin")))
    try:
        with rffi.scoped_str2charp(origin) as ll_libname:
            lib = dlopen(ll_libname, space.sys.dlopenflags)
    except DLOpenError as e:
        w_path = space.newfilename(origin)
        raise raise_import_error(space,
            space.newfilename(e.msg), w_name, w_path)

    basename = name.split('.')[-1]
    init_name = 'HPyInit_' + basename
    try:
        initptr = dlsym(lib, init_name)
    except KeyError:
        msg = b"function %s not found in library %s" % (
            init_name, space.utf8_w(space.newfilename(origin)))
        w_path = space.newfilename(origin)
        raise raise_import_error(
            space, space.newtext(msg), w_name, w_path)
    return create_hpy_module(space, name, origin, lib, initptr)
