from rpython.rlib import rdynload
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.interpreter.error import oefmt
from pypy.interpreter.module import Module
from pypy.module._cffi_backend import parse_c_type
from pypy.module._cffi_backend.ffi_obj import W_FFIObject
from pypy.module._cffi_backend.lib_obj import W_LibObject


VERSION_MIN = 0x010000f0
VERSION_MAX = 0x0100ffff

initfunctype = lltype.Ptr(lltype.FuncType([rffi.VOIDPP], lltype.Void))


def load_cffi1_module(space, name, path, dll, initptr):
    try:
        initfunc = rffi.cast(initfunctype, initptr)
        with lltype.scoped_alloc(rffi.VOIDPP.TO, 2, zero=True) as p:
            initfunc(p)
            version = rffi.cast(lltype.Signed, p[0])
            if not (VERSION_MIN <= version <= VERSION_MAX):
                raise oefmt(space.w_ImportError,
                    "cffi extension module '%s' has unknown version %s",
                    name, hex(version))
            src_ctx = rffi.cast(parse_c_type.PCTX, p[1])
    except:
        rdynload.dlclose(dll)
        raise

    ffi = W_FFIObject(space, src_ctx)
    lib = W_LibObject(ffi, name)

    w_name = space.wrap(name)
    module = Module(space, w_name)
    module.setdictvalue(space, '__file__', space.wrap(path))
    module.setdictvalue(space, 'ffi', space.wrap(ffi))
    module.setdictvalue(space, 'lib', space.wrap(lib))
    space.setitem(space.sys.get('modules'), w_name, space.wrap(module))
