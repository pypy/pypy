from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.interpreter.error import oefmt
from pypy.interpreter.module import Module
from pypy.module._cffi_backend import parse_c_type
from pypy.module._cffi_backend.ffi_obj import W_FFIObject
from pypy.module._cffi_backend.lib_obj import W_LibObject


VERSION_MIN    = 0x2601
VERSION_MAX    = 0x26FF

VERSION_EXPORT = 0x0A02

initfunctype = lltype.Ptr(lltype.FuncType([rffi.VOIDPP], lltype.Void))


def load_cffi1_module(space, name, path, initptr):
    # This is called from pypy.module.cpyext.api.load_extension_module()
    initfunc = rffi.cast(initfunctype, initptr)
    with lltype.scoped_alloc(rffi.VOIDPP.TO, 2) as p:
        p[0] = rffi.cast(rffi.VOIDP, VERSION_EXPORT)
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
    module.setdictvalue(space, '__file__', space.wrap(path))
    module.setdictvalue(space, 'ffi', space.wrap(ffi))
    module.setdictvalue(space, 'lib', space.wrap(lib))
    w_modules_dict = space.sys.get('modules')
    space.setitem(w_modules_dict, w_name, space.wrap(module))
    space.setitem(w_modules_dict, space.wrap(name + '.lib'), space.wrap(lib))
