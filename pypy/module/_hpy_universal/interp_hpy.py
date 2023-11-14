from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rdynload import dlopen, dlsym, DLOpenError
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import widen

from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.error import raise_import_error
from pypy.interpreter.error import oefmt, OperationError

from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal.state import State
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal.interp_module import hpymod_create, hpymod_exec_def

# these imports have side effects, as they call @API.func()
from pypy.module._hpy_universal import (
    interp_builder,
    interp_bytes,
    interp_call,
    interp_capsule,
    interp_contextvars,
    interp_cpy_compat,
    interp_dict,
    interp_err,
    interp_eval,
    interp_field,
    interp_float,
    interp_import,
    interp_list,
    interp_long,
    interp_module,
    interp_number,
    interp_object,
    interp_slice,
    interp_state,
    interp_tracker,
    interp_tuple,
    interp_type,
    interp_unicode,
    )

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

def startup(space, w_mod):
    """
    Initialize _hpy_universal. This is called by moduledef.Module.__init__
    """
    from pypy.module._hpy_universal.interp_type import setup_hpy_storage
    state = State.get(space)
    state.setup(space)
    setup_hpy_storage()

    # do the following lines break test_ztranslation?
    manager = state.get_handle_manager(llapi.MODE_UNIVERSAL)
    hpydef_debug = llapi.HPyInit__debug()
    w_debug_mod = hpymod_create(manager, "_debug", hpydef_debug)
    hpymod_exec_def(manager, w_debug_mod, hpydef_debug)
    w_mod.setdictvalue(space, '_debug', w_debug_mod)

    hpydef_trace = llapi.HPyInit__trace()
    w_trace_mod = hpymod_create(manager, "_trace", hpydef_trace)
    hpymod_exec_def(manager, w_trace_mod, hpydef_trace)
    w_mod.setdictvalue(space, '_trace', w_trace_mod)
        

def load_version():
    # eval the content of _vendored/hpy/devel/version.py without importing it
    version_py = llapi.BASE_DIR.join('version.py').read()
    d = {}
    exec(version_py, d)
    return d['__version__'], d['__git_revision__']
HPY_VERSION, HPY_GIT_REV = load_version()

@unwrap_spec(name='text', path='fsencode', debug=bool, mode=int)
def descr_load(space, name, path, w_spec, debug=False, mode=-1):
    hmode = llapi.MODE_DEBUG if debug else llapi.MODE_UNIVERSAL
    if mode > 0:
        hmode = mode
    w_mod = do_load(space, name, path, hmode)
    space.setattr(w_mod, space.newtext("spec"), w_spec)
    return w_mod

@unwrap_spec(ext_name="text", path="fsencode")
def descr__load_bootstrap(space, w_name, ext_name, w_package, path, w_loader, w_spec, w_env):
    """Internal function intended to be used by the stub loader. This function
    will honor env var 'HPY' and correctly set the attributes of the module.
    """
    name = space.text_w(w_name)
    w_file = space.newtext(ext_name)

    hmode = get_hpy_mode_from_environ(space, name, w_env);
    w_mod = do_load(space, name, path, hmode)
    space.setattr(w_mod, space.newtext("__name__"), w_name)
    space.setattr(w_mod, space.newtext("__file__"), w_file)
    space.setattr(w_mod, space.newtext("__loader__"), w_loader)
    space.setattr(w_mod, space.newtext("__package__"), w_package)
    space.setattr(w_spec, space.newtext("origin"), space.newtext(path))
    space.setattr(w_mod, space.newtext("__spec__"), w_spec)
    return w_mod

def get_mode_from_value(value):
    if value.startswith("universal"):
        return llapi.MODE_UNIVERSAL
    elif value.startswith("debug"):
        return llapi.MODE_DEBUG
    elif value.startswith("trace"):
        return llapi.MODE_TRACE
    return llapi.MODE_INVALID
    
def get_hpy_mode_from_environ(space, name, w_env):
    """w_env is os.environ. w_env[HPY] is HPY_MODE
    HPY_MODE := MODE | (MODULE_NAME ':' MODE { ',' MODULE_NAME ':' MODE })
    MODULE_NAME := IDENTIFIER
    MODE := 'debug' | 'trace' | 'universal'
    """
    try:
        w_HPY = space.newtext("HPY")
        try:
            w_value = space.getitem(w_env, w_HPY)
        except OperationError:
            return llapi.MODE_UNIVERSAL
        value = space.text_w(w_value)
        res = llapi.MODE_INVALID
        if ":" not in value:
            res = get_mode_from_value(value)
        pieces = value.split(",")
        for p in pieces:
            if ":" in p:
                mod_name, mode = p.split(":")
                if mod_name == name:
                    res = get_mode_from_value(mode)
        if res == llapi.MODE_INVALID:
            raise oefmt(space.w_ValueError, "invalid HPY env value: %s", value)
        return res
    except Exception:
        return llapi.MODE_INVALID 
    

def validate_abi_tag(space, shortname, soname, req_major_version, req_minor_version):
    i = soname.find(".hpy")
    if i > 0:
        i += len(".hpy")
        if soname[i] >= "0" and soname[i] <= "9":
            # it is a number w/o sign and whitespace. In C we could use atio,
            # but here we need to scan for the end of the digits
            abi_tag = 0
            while (soname[i] >= "0" and soname[i] <= "9"):
                abi_tag *= 10
                abi_tag += int(soname[i])
                i += 1
                if (i >= len(soname)):
                    break
            if abi_tag == req_major_version:
                return True
            raise oefmt(space.w_RuntimeError,
                "HPy extension module '%s' at path '%s': mismatch between the "
                "HPy ABI tag encoded in the filename and the major version requested "
                "by the HPy extension itself. Major version tag parsed from "
                "filename: %d. Requested version: %d.%d.", shortname,
                soname, abi_tag, req_major_version, req_minor_version)
    raise oefmt(space.w_RuntimeError,       
         "HPy extension module '%s' at path '%s': could not find "
         "HPy ABI tag encoded in the filename. The extension claims to be compiled with "
         "HPy ABI version: %d.%d.", shortname, soname,
             req_major_version, req_minor_version)

def get_handle_manager(space, mode):
    # So the result can be pre-built
    state = State.get(space)
    if mode == llapi.MODE_DEBUG:
        return state.get_handle_manager(llapi.MODE_DEBUG)
    elif mode == llapi.MODE_UNIVERSAL:
        return state.get_handle_manager(llapi.MODE_UNIVERSAL)
    elif mode == llapi.MODE_TRACE:
        return state.get_handle_manager(llapi.MODE_TRACE)
    else:
        return state.get_handle_manager(llapi.MODE_INVALID)


def do_load(space, name, soname, mode):
    """This is hpy/hpy/universal/src/hpymodule.c:do_load
    """
    if space.config.objspace.hpy_cpyext_API:
        # Ensure cpyext is initialised, since the extension might call cpyext
        # functions
        space.getbuiltinmodule('cpyext')

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
        raise oefmt(space.w_RuntimeError,
            ("Error during loading of the HPy extension module at path "
            "'%s'. Cannot locate the required minimal HPy versions as symbols "
            "'%s' and `%s`. "), soname, minor_version_symbol_name,
            major_version_symbol_name)
    vgfp = llapi.VersionGetterFuncPtr
    required_minor_version = widen(rffi.cast(vgfp, minor_version_ptr)())
    required_major_version = widen(rffi.cast(vgfp, major_version_ptr)())
    if (required_major_version != llapi.HPY_ABI_VERSION or 
        required_minor_version > llapi.HPY_ABI_VERSION_MINOR):
        # For now, we have only one major version, but in the future at this
        # point we would decide which HPyContext to create
        raise oefmt(space.w_RuntimeError,
            ("HPy extension module '%s' requires unsupported version of the HPy "
             "runtime. Requested version: %d.%d. Current HPy version: %d.%d."),
            shortname, required_major_version, required_minor_version,
            llapi.HPY_ABI_VERSION, llapi.HPY_ABI_VERSION_MINOR)
    
    validate_abi_tag(space, shortname, soname, required_major_version, required_minor_version)    
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

    # Set up global trampoline ctx
    if mode == llapi.MODE_DEBUG:
        ctx = manager.ctx
    elif mode == llapi.MODE_UNIVERSAL:
        ctx = manager.ctx
    elif mode == llapi.MODE_TRACE:
        ctx = llapi.hpy_trace_get_ctx(manager.u_handles.ctx)
    else:
        # Cannot happen
        ctx = llapi.cts.cast("HPyContext *", 0)    
    rffi.cast(llapi.InitContextFuncPtr, initptr)(ctx)

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

    # specialize hpymod_create and hpymod_exec_def, which requires
    # a constant 'manager'
    state = State.get(space)
    if mode == llapi.MODE_DEBUG:
        manager = state.get_handle_manager(llapi.MODE_DEBUG)
        w_mod = hpymod_create(manager, name, hpydef)
        # find and call functions in the HPy_mod_exec slot
        hpymod_exec_def(manager, w_mod, hpydef)
    elif mode == llapi.MODE_UNIVERSAL:
        manager = state.get_handle_manager(llapi.MODE_UNIVERSAL)
        w_mod = hpymod_create(manager, name, hpydef)
        # find and call functions in the HPy_mod_exec slot
        hpymod_exec_def(manager, w_mod, hpydef)
    elif mode == llapi.MODE_TRACE:
        manager = state.get_handle_manager(llapi.MODE_TRACE)
        w_mod = hpymod_create(manager, name, hpydef)
        # find and call functions in the HPy_mod_exec slot
        hpymod_exec_def(manager, w_mod, hpydef)
    else:
        # Raises an error, but pretend it doesn't for translation
        manager = state.get_handle_manager(llapi.MODE_INVALID)
        w_mod = hpymod_create(manager, name, hpydef)
    return w_mod

def descr_get_version(space):
    w_ver = space.newtext(HPY_VERSION)
    w_git_rev = space.newtext(HPY_GIT_REV)
    return space.newtuple([w_ver, w_git_rev])

@API.func("HPy HPy_Dup(HPyContext *ctx, HPy h)")
def HPy_Dup(space, handles, ctx, h):
    if not h:
        return h
    return handles.dup(h)

@API.func("void HPy_Close(HPyContext *ctx, HPy h)")
def HPy_Close(space, handles, ctx, h):
    if h:
        handles.close(h)
