from rpython.rlib import jit
from rpython.rtyper.lltypesystem import rffi

from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

from pypy.module._cffi_backend import parse_c_type, realize_c_type
from pypy.module._cffi_backend import cffi_opcode, cglob
from pypy.module._cffi_backend.realize_c_type import getop, getarg
from pypy.module._cffi_backend.cdataobj import W_CData


class W_LibObject(W_Root):

    def __init__(self, ffi, libname):
        self.space = ffi.space
        self.ctx = ffi.ctxobj.ctx
        self.ffi = ffi
        self.dict_w = {}          # content, built lazily
        self.libname = libname    # some string that gives the name of the lib
        self.includes = []        # list of W_LibObjects included here

    def descr_repr(self):
        XXX

    @jit.elidable_promote()
    def _get_attr(self, attr):
        try:
            w_result = self.dict_w[attr]
        except KeyError:
            index = parse_c_type.search_in_globals(self.ctx, attr)
            if index < 0:
                return None     # no active caching, but still @elidable

            space = self.space
            g = self.ctx.c_globals[index]
            op = getop(g.c_type_op)
            if (op == cffi_opcode.OP_CPYTHON_BLTN_V or
                op == cffi_opcode.OP_CPYTHON_BLTN_N or
                op == cffi_opcode.OP_CPYTHON_BLTN_O):
                # A function: in the PyPy version, these are all equivalent
                # and 'g->address' is a pointer to a function of exactly the
                # C type specified
                type_index = getarg(g.c_type_op)
                opcodes = self.ctx.c_types
                w_ct = realize_c_type.realize_c_type_or_func(self.ffi, opcodes,
                                                             type_index)
                w_ct = realize_c_type.unwrap_fn_as_fnptr(w_ct)
                ptr = rffi.cast(rffi.CCHARP, g.c_address)
                w_result = W_CData(space, ptr, w_ct)
                #
            elif op == cffi_opcode.OP_GLOBAL_VAR:
                # A global variable of the exact type specified here
                type_index = getarg(g.c_type_op)
                opcodes = self.ctx.c_types
                w_ct = realize_c_type.realize_c_type(self.ffi, opcodes,
                                                     type_index)
                g_size = rffi.getintfield(g, 'c_size')
                if g_size != w_ct.size and g_size != 0 and w_ct.size > 0:
                    raise oefmt(self.ffi.w_FFIError,
                            "global variable '%s' should be %d bytes "
                            "according to the cdef, but is actually %d",
                            attr, w_ct.size, g_size)
                ptr = rffi.cast(rffi.CCHARP, g.c_address)
                w_result = cglob.W_GlobSupport(space, w_ct, ptr)
                #
            else:
                raise oefmt(space.w_NotImplementedError,
                            "in lib_build_attr: op=%d", op)

            self.dict_w[attr] = w_result
        return w_result

    def _no_such_attr(self, attr):
        raise oefmt(self.space.w_AttributeError,
                    "cffi lib '%s' has no function,"
                    " global variable or constant named '%s'",
                    self.libname, attr)

    def descr_getattribute(self, w_attr):
        space = self.space
        attr = space.str_w(w_attr)
        w_value = self._get_attr(attr)
        if w_value is None:
            raise self._no_such_attr(attr)
        elif isinstance(w_value, cglob.W_GlobSupport):
            w_value = w_value.read_global_var()
        return w_value


W_LibObject.typedef = TypeDef(
        'CompiledLib',
        __repr__ = interp2app(W_LibObject.descr_repr),
        __getattribute__ = interp2app(W_LibObject.descr_getattribute),
        )
W_LibObject.typedef.acceptable_as_base_class = False
