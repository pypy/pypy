from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.rdynload import dlopen, dlsym, DLOpenError

from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import raise_import_error

from pypy.module.hpy_universal import llapi
from pypy.module.cpyext.api import generic_cpy_call_dont_convert_result


class State:
    def __init__(self, space):
        "NOT_RPYTHON"
        self.space = space
        self.ctx = llmemory.NULL

    def setup(self):
        if not self.ctx:
            #_HPy_FillFunction(0, HPy_ModuleCreate)
            self.ctx = llapi._HPy_GetGlobalCtx()


def create_hpy_module(space, name, origin, lib, initfunc):
    state = space.fromcache(State)
    initfunc = rffi.cast(llapi.HPyInitFuncPtr, initfunc)
    h_module = generic_cpy_call_dont_convert_result(space, initfunc, state.ctx)
    return from_hpy(h_module)

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
