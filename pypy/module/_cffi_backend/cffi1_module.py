from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.entrypoint import entrypoint

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.module import Module
from pypy.module._cffi_backend import parse_c_type
from pypy.module._cffi_backend.ffi_obj import W_FFIObject
from pypy.module._cffi_backend.lib_obj import W_LibObject


VERSION_MIN    = 0x2601
VERSION_MAX    = 0x26FF

VERSION_EXPORT = 0x0A03

INITFUNCPTR = lltype.Ptr(lltype.FuncType([rffi.VOIDPP], lltype.Void))


def load_cffi1_module(space, name, path, initptr):
    # This is called from pypy.module.cpyext.api.load_extension_module()
    from pypy.module._cffi_backend.call_python import get_ll_cffi_call_python

    initfunc = rffi.cast(INITFUNCPTR, initptr)
    with lltype.scoped_alloc(rffi.VOIDPP.TO, 16, zero=True) as p:
        p[0] = rffi.cast(rffi.VOIDP, VERSION_EXPORT)
        p[1] = rffi.cast(rffi.VOIDP, get_ll_cffi_call_python())
        initfunc(p)
        version = rffi.cast(lltype.Signed, p[0])
        if not (VERSION_MIN <= version <= VERSION_MAX):
            raise oefmt(space.w_ImportError,
                "cffi extension module '%s' has unknown version %s",
                name, hex(version))
        src_ctx = rffi.cast(parse_c_type.PCTX, p[1])

    ffi = W_FFIObject(space, src_ctx)
    lib = W_LibObject(ffi, name)
    if src_ctx.c_includes:
        lib.make_includes_from(src_ctx.c_includes)

    w_name = space.wrap(name)
    module = Module(space, w_name)
    if path is not None:
        module.setdictvalue(space, '__file__', space.wrap(path))
    module.setdictvalue(space, 'ffi', space.wrap(ffi))
    module.setdictvalue(space, 'lib', space.wrap(lib))
    w_modules_dict = space.sys.get('modules')
    space.setitem(w_modules_dict, w_name, space.wrap(module))
    space.setitem(w_modules_dict, space.wrap(name + '.lib'), space.wrap(lib))
    return module


# ____________________________________________________________


EMBED_VERSION_MIN    = 0xB011
EMBED_VERSION_MAX    = 0xB0FF

STDERR = 2
INITSTRUCTPTR = lltype.Ptr(lltype.Struct('CFFI_INIT',
                                         ('name', rffi.CCHARP),
                                         ('func', rffi.VOIDP),
                                         ('code', rffi.CCHARP)))

def load_embedded_cffi_module(space, version, init_struct):
    from pypy.module._cffi_backend.embedding import declare_c_function
    declare_c_function()     # translation-time hint only:
                             # declare _cffi_carefully_make_gil()
    #
    version = rffi.cast(lltype.Signed, version)
    if not (VERSION_MIN <= version <= VERSION_MAX):
        raise oefmt(space.w_ImportError,
            "cffi embedded module has got unknown version tag %s",
            hex(version))
    #
    if space.config.objspace.usemodules.thread:
        from pypy.module.thread import os_thread
        os_thread.setup_threads(space)
    #
    name = rffi.charp2str(init_struct.name)
    module = load_cffi1_module(space, name, None, init_struct.func)
    code = rffi.charp2str(init_struct.code)
    compiler = space.createcompiler()
    pycode = compiler.compile(code, "<init code for '%s'>" % name, 'exec', 0)
    w_globals = module.getdict(space)
    space.call_method(w_globals, "setdefault", space.wrap("__builtins__"),
                      space.wrap(space.builtin))
    pycode.exec_code(space, w_globals, w_globals)


class Global:
    pass
glob = Global()

@entrypoint('main', [rffi.INT, rffi.VOIDP],
            c_name='_pypy_init_embedded_cffi_module')
def _pypy_init_embedded_cffi_module(version, init_struct):
    name = "?"
    try:
        init_struct = rffi.cast(INITSTRUCTPTR, init_struct)
        name = rffi.charp2str(init_struct.name)
        #
        space = glob.space
        try:
            load_embedded_cffi_module(space, version, init_struct)
            res = 0
        except OperationError, operr:
            operr.write_unraisable(space, "initialization of '%s'" % name,
                                   with_traceback=True)
            space.appexec([], """():
                import sys
                sys.stderr.write('pypy version: %s.%s.%s\n' %
                                 sys.pypy_version_info[:3])
                sys.stderr.write('sys.path: %r\n' % (sys.path,))
            """)
            res = -1
    except Exception, e:
        # oups! last-level attempt to recover.
        try:
            os.write(STDERR, "From initialization of '")
            os.write(STDERR, name)
            os.write(STDERR, "':\n")
            os.write(STDERR, str(e))
            os.write(STDERR, "\n")
        except:
            pass
        res = -1
    return rffi.cast(rffi.INT, res)
