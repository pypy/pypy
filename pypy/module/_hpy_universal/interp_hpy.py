from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rdynload import dlopen, dlsym, DLOpenError
from rpython.rlib.objectmodel import specialize

from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.error import raise_import_error
from pypy.interpreter.error import oefmt

from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal.state import State
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal.llapi import BASE_DIR
from pypy.module._hpy_universal.interp_module import _hpymodule_create

# these imports have side effects, as they call @API.func()
from pypy.module._hpy_universal import (
    interp_err,
    interp_long,
    interp_module,
    interp_number,
    interp_unicode,
    interp_float,
    interp_bytes,
    interp_call,
    interp_dict,
    interp_list,
    interp_tuple,
    interp_builder,
    interp_object,
    interp_cpy_compat,
    interp_type,
    interp_tracker,
    interp_import,
    interp_field,
    interp_state,
    )

MODE_INVALID = -1
MODE_UNIVERSAL = 0
MODE_DEBUG = 1
MODE_TRACE = 2

# ~~~ Some info on the debug mode ~~~
# XXX REVIEW for 0.9
#
# The following is an explation of what happens when you load a module
#
# 1. someone calls _hpy_universal.load(..., mode=MODE_XXX)
#
# 2. load() calls  get_context(mode) which returns a debug context
#    and later calls HPyInitGlobalContext_foo(ctx) to set up a global
#    context in the module
#
# 5. The net result is that depending on the value of mode at point (1), we
#    call the underlying C function with either dctx or uctx.
#
# 6. Argument passing works in the same way: handles are created by calling
#    self.handles.new, which in debug mode calls
#    llapi.hpy_debug_open_handle. The same for the return value, which calls
#    self.handles.consume which calls llapi.hpy_debug_close_handle.
#
# 7. We need to ensure that ALL python-to-C entry points use the correct
#    HandleManager/ctx: so the same applies for W_ExtensionMethod and
#    W_SlotWrapper.


def set_on_invalid_handle(space, w_f):
    raise oefmt(space.w_RuntimeError, "cannot use on_invalid_handle hook in PyPy")

@specialize.memo()
def get_set_on_invalid_handle(space):
    return interp2app(set_on_invalid_handle).spacebind(space)

def startup(space, w_mod):
    """
    Initialize _hpy_universal. This is called by moduledef.Module.__init__
    """
    from pypy.module._hpy_universal.interp_type import setup_hpy_storage
    state = State.get(space)
    state.setup(space)
    setup_hpy_storage()
    if 0 and not hasattr(space, 'is_fake_objspace'):
        # the following lines break test_ztranslation :(
        handles = state.get_handle_manager(debug=False)
        h_debug_mod = llapi.HPyInit__debug()
        w_debug_mod = handles.consume(h_debug_mod)
        w_set_on_invalid_handle = get_set_on_invalid_handle(space)
        w_debug_mod.setdictvalue(space, 'set_on_invalid_handle', w_set_on_invalid_handle)
        w_mod.setdictvalue(space, '_debug', w_debug_mod)

def load_version():
    # eval the content of _vendored/hpy/devel/version.py without importing it
    version_py = BASE_DIR.join('version.py').read()
    d = {}
    exec(version_py, d)
    return d['__version__'], d['__git_revision__']
HPY_VERSION, HPY_GIT_REV = load_version()


@specialize.arg(4)
def init_hpy_module(space, name, origin, lib, debug, initfunc_ptr):
    state = space.fromcache(State)
    handles = state.get_handle_manager(debug)
    initfunc_ptr = rffi.cast(llapi.HPyInitFunc, initfunc_ptr)
    h_module = initfunc_ptr(handles.ctx)
    error = state.clear_exception()
    if error:
        raise error
    if not h_module:
        raise oefmt(space.w_SystemError,
            "initialization of %s failed without raising an exception",
            name)
    return handles.consume(h_module)

def descr_load_from_spec(space, w_spec):
    name = space.text_w(space.getattr(w_spec, space.newtext("name")))
    origin = space.fsencode_w(space.getattr(w_spec, space.newtext("origin")))
    return descr_load(space, name, origin)

@unwrap_spec(name='text', path='fsencode', debug=bool, mode=int)
def descr_load(space, name, path, w_spec, debug=False, mode=-1):
    hmode = MODE_DEBUG if debug else MODE_UNIVERSAL
    if mode > 0:
        hmode = mode
    return do_load(space, name, path, hmode, w_spec)

def validate_abi_tag(shortname, soname, req_major_version, req_minor_version):
    i = soname.find(".hpy")
    if i > 0:
        i += len(".hpy")
        if soname[i] >= "0" and soname[i] <= "9":
            # it is a number w/o sign and whitespace, we can parse it
            abi_tag = int(soname[i])
            if abi_tag == req_major_version:
                return True
            raise RuntimeError(
                "HPy extension module '%s' at path '%s': mismatch between the "
                "HPy ABI tag encoded in the filename and the major version requested "
                "by the HPy extension itself. Major version tag parsed from "
                "filename: %d. Requested version: %d.%d." % (shortname,
                soname, abi_tag, req_major_version, req_minor_version))
    raise RuntimeError(       
         "HPy extension module '%s' at path '%s': could not find "
         "HPy ABI tag encoded in the filename. The extension claims to be compiled with "
         "HPy ABI version: %d.%d." % (shortname, soname,
             req_major_version, req_minor_version))


def get_handle_manager(space, mode):
    if mode == MODE_INVALID:
        raise RuntimeError("invalid moded")
    elif mode == MODE_TRACE:
        raise NotImplementedError("trace mode not implemented")
    state = State.get(space)
    return state.get_handle_manager(mode == MODE_DEBUG)


def do_load(space, name, soname, mode, spec):
    try:
        with rffi.scoped_str2charp(soname) as ll_libname:
            lib = dlopen(ll_libname, space.sys.dlopenflags)
    except DLOpenError as e:
        w_path = space.newfilename(soname)
        raise raise_import_error(space,
            space.newfilename(e.msg), space.newtext(name), w_path)

    shortname = name.split('.')[-1]
    minor_version_symbol_name = "get_required_hpy_minor_version_%s" % shortname
    major_version_symbol_name = "get_required_hpy_major_version_%s" % shortname
    try:
        minor_version_ptr = dlsym(lib, minor_version_symbol_name)
        major_version_ptr = dlsym(lib, major_version_symbol_name)
    except KeyError:
        raise oef
    except KeyError:
        raise oefmt(space.w_RuntimeError,
            ("Error during loading of the HPy extension module at path "
            "'%s'. Cannot locate the required minimal HPy versions as symbols "
            "'%s' and `%s`. "), soname, minor_version_symbol_name,
            major_version_symbol_name)
    vgfp = llapi.VersionGetterFuncPtr
    required_minor_version = rffi.cast(vgfp, minor_version_ptr)()
    required_major_version = rffi.cast(vgfp, major_version_ptr)()
    if (required_major_version != llapi.HPY_ABI_VERSION or 
        required_minor_version > llapi.HPY_ABI_VERSION_MINOR):
        # For now, we have only one major version, but in the future at this
        # point we would decide which HPyContext to create
        raise oefmt(space.w_RuntimeError,
            ("HPy extension module '%s' requires unsupported version of the HPy "
             "runtime. Requested version: %d.%d. Current HPy version: %d.%d."),
            shortname, required_major_version, required_minor_version,
            llapi.HPY_ABI_VERSION, llapi.HPY_ABI_VERSION_MINOR)
    
    validate_abi_tag(shortname, soname, required_major_version, required_minor_version)    
    manager = get_handle_manager(space, mode)

    init_ctx_name = "HPyInitGlobalContext_" + shortname
    try:
        initptr = dlsym(lib, init_ctx_name)
    except KeyError:
        msg = b"function %s not found in library %s" % (
            init_ctx_name, space.utf8_w(space.newfilename(soname)))
        w_path = space.newfilename(soname)
        raise raise_import_error(
            space, space.newtext(msg), space.newtext(name), w_path)

    if space.config.objspace.hpy_cpyext_API:
        # Ensure cpyext is initialised, since the extension might call cpyext
        # functions
        space.getbuiltinmodule('cpyext')

    # Set up global trampoline ctx
    rffi.cast(llapi.InitContextFuncPtr, initptr)(manager.ctx)

    init_name = 'HPyInit_' + shortname
    try:
        initptr = dlsym(lib, init_name)
    except KeyError:
        msg = b"function %s not found in library %s" % (
            init_name, space.utf8_w(space.newfilename(soname)))
        w_path = space.newfilename(soname)
        raise raise_import_error(
            space, space.newtext(msg), space.newtext(name), w_path)

    hpydef = rffi.cast(llapi.InitFuncPtr, initptr)()
    if not hpydef:
        raise oefmt(space.w_RuntimeError,
            ("Error during loading of the HPy extension module at "
            "path '%s'. Function '%s' returned NULL."), soname, init_name);

    w_mod = _hpymodule_create(manager, name, hpydef)
    # TODO: find and call a function in the HPy_mod_exec slot
    # PyModule_ExecDef(py_mod, pydef)
    return w_mod

def descr_get_version(space):
    w_ver = space.newtext(HPY_VERSION)
    w_git_rev = space.newtext(HPY_GIT_REV)
    return space.newtuple([w_ver, w_git_rev])

@API.func("HPy HPy_Dup(HPyContext *ctx, HPy h)")
def HPy_Dup(space, handles, ctx, h):
    return handles.dup(h)

@API.func("void HPy_Close(HPyContext *ctx, HPy h)")
def HPy_Close(space, handles, ctx, h):
    handles.close(h)
