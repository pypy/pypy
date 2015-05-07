from rpython.rlib import jit
from rpython.rtyper.lltypesystem import rffi

from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

from pypy.module._cffi_backend import parse_c_type, realize_c_type, cffi_opcode
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

            g = self.ctx.c_globals[index]
            op = getop(g.c_type_op)
            if (op == cffi_opcode.OP_CPYTHON_BLTN_V or
                op == cffi_opcode.OP_CPYTHON_BLTN_N or
                op == cffi_opcode.OP_CPYTHON_BLTN_O):
                #
                type_index = getarg(g.c_type_op)
                opcodes = self.ctx.c_types
                w_ct = realize_c_type.realize_c_type_or_func(self.ffi, opcodes,
                                                             type_index)
                w_ct = realize_c_type.unwrap_fn_as_fnptr(w_ct)
                ptr = rffi.cast(rffi.CCHARP, g.c_address)
                w_result = W_CData(self.space, ptr, w_ct)
                #
            else:
                raise NotImplementedError("in lib_build_attr: op=%d" % op)
            
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
        #elif isinstance(w_value, Globxxx):
        #    ...
        return w_value


W_LibObject.typedef = TypeDef(
        'CompiledLib',
        __repr__ = interp2app(W_LibObject.descr_repr),
        __getattribute__ = interp2app(W_LibObject.descr_getattribute),
        )
W_LibObject.acceptable_as_base_class = False
