from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rdynload import dlopen, dlsym, DLOpenError

from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import raise_import_error
from pypy.interpreter.error import OperationError, oefmt

from pypy.module.cpyext.api import generic_cpy_call_dont_convert_result
from pypy.module.hpy_universal import llapi, handles
from pypy.module.hpy_universal.state import State
from pypy.module.hpy_universal.apiset import API

# these imports have side effects, as they call @API.func()
from pypy.module.hpy_universal import (
    interp_err, interp_long, interp_module, interp_number, interp_unicode, interp_float,
    interp_bytes, interp_dict, interp_list,
    )


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


@API.func("HPy HPy_Dup(HPyContext ctx, HPy h)")
def HPy_Dup(space, ctx, h):
    return handles.dup(space, h)

@API.func("void HPy_Close(HPyContext ctx, HPy h)")
def HPy_Close(space, ctx, h):
    handles.close(space, h)
