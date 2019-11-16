from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rdynload import dlopen, dlsym, DLOpenError

from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import raise_import_error
from pypy.interpreter.module import Module

from pypy.module.hpy_universal import llapi, handles
from pypy.module.cpyext.api import generic_cpy_call_dont_convert_result
from pypy.module.cpyext.api import slot_function


class State:
    def __init__(self, space):
        "NOT_RPYTHON"
        self.space = space
        self.ctx = lltype.nullptr(rffi.VOIDP.TO)

    def setup(self):
        if not self.ctx:
            space = self.space
            funcptr = HPyModule_Create.api_func.get_llhelper(space)
            llapi._HPy_FillFunction(rffi.cast(rffi.INT_real, 0),
                                    rffi.cast(rffi.VOIDP, funcptr))
            self.ctx = llapi._HPy_GetGlobalCtx()


@slot_function([llapi.HPyContext, lltype.Ptr(llapi.HPyModuleDef)],
               llapi.HPy, error=0)
def HPyModule_Create(space, ctx, hpydef):
    modname = rffi.charp2str(hpydef.c_m_name)
    w_mod = Module(space, space.newtext(modname))
    return handles.new(space, w_mod)


def create_hpy_module(space, name, origin, lib, initfunc):
    state = space.fromcache(State)
    initfunc = rffi.cast(llapi.HPyInitFuncPtr, initfunc)
    h_module = generic_cpy_call_dont_convert_result(space, initfunc, state.ctx)
    return handles.consume(space, h_module)

@unwrap_spec(origin='fsencode', init_name='text')
def descr_load(space, origin, init_name):
    # XXX: this looks a lot like cpyext.api.create_extension_module()
    state = space.fromcache(State)
    state.setup()
    name = init_name[len('HPyInit_'):]
    try:
        with rffi.scoped_str2charp(origin) as ll_libname:
            lib = dlopen(ll_libname, space.sys.dlopenflags)
    except DLOpenError as e:
        w_path = space.newfilename(origin)
        w_name = space.newtext(name)
        raise raise_import_error(space,
            space.newfilename(e.msg), w_name, w_path)

    try:
        initptr = dlsym(lib, init_name)
    except KeyError:
        msg = b"function %s not found in library %s" % (
            init_name, space.utf8_w(space.newfilename(origin)))
        w_path = space.newfilename(origin)
        w_name = space.newtext(name)
        raise raise_import_error(
            space, space.newtext(msg), w_name, w_path)
    return create_hpy_module(space, name, origin, lib, initptr)
