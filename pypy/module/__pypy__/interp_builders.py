from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from rpython.rlib.rstring import UnicodeBuilder, StringBuilder
from rpython.tool.sourcetools import func_with_new_name


class W_BytesBuilder(W_Root):
    def __init__(self, space, size):
        if size < 0:
            self.builder = StringBuilder()
        else:
            self.builder = StringBuilder(size)

    @unwrap_spec(size=int)
    def descr__new__(space, w_subtype, size=-1):
        return W_BytesBuilder(space, size)

    @unwrap_spec(s='bytes')
    def descr_append(self, space, s):
        self.builder.append(s)

    @unwrap_spec(s='bytes', start=int, end=int)
    def descr_append_slice(self, space, s, start, end):
        if not 0 <= start <= end <= len(s):
            raise oefmt(space.w_ValueError, "bad start/stop")
        self.builder.append_slice(s, start, end)

    def descr_build(self, space):
        w_s = space.newbytes(self.builder.build())
        # after build(), we can continue to append more strings
        # to the same builder.  This is supported since
        # 2ff5087aca28 in RPython.
        return w_s

    def descr_len(self, space):
        if self.builder is None:
            raise oefmt(space.w_ValueError, "no length of built builder")
        return space.newint(self.builder.getlength())

W_BytesBuilder.typedef = TypeDef("StringBuilder",
    __new__ = interp2app(func_with_new_name(
                                W_BytesBuilder.descr__new__.im_func,
                                'BytesBuilder_new')),
    append = interp2app(W_BytesBuilder.descr_append),
    append_slice = interp2app(W_BytesBuilder.descr_append_slice),
    build = interp2app(W_BytesBuilder.descr_build),
    __len__ = interp2app(W_BytesBuilder.descr_len),
)
W_BytesBuilder.typedef.acceptable_as_base_class = False
W_StringBuilder = W_BytesBuilder

class W_UnicodeBuilder(W_Root):
    def __init__(self, space, size):
        if size < 0:
            self.builder = UnicodeBuilder()
        else:
            self.builder = UnicodeBuilder(size)

    @unwrap_spec(size=int)
    def descr__new__(space, w_subtype, size=-1):
        return W_UnicodeBuilder(space, size)

    @unwrap_spec(s=unicode)
    def descr_append(self, space, s):
        self.builder.append(s)

    @unwrap_spec(s=unicode, start=int, end=int)
    def descr_append_slice(self, space, s, start, end):
        if not 0 <= start <= end <= len(s):
            raise oefmt(space.w_ValueError, "bad start/stop")
        self.builder.append_slice(s, start, end)

    def descr_build(self, space):
        w_s = space.newunicode(self.builder.build())
        # after build(), we can continue to append more strings
        # to the same builder.  This is supported since
        # 2ff5087aca28 in RPython.
        return w_s

    def descr_len(self, space):
        if self.builder is None:
            raise oefmt(space.w_ValueError, "no length of built builder")
        return space.newint(self.builder.getlength())

W_UnicodeBuilder.typedef = TypeDef("UnicodeBuilder",
    __new__ = interp2app(func_with_new_name(
                                W_UnicodeBuilder.descr__new__.im_func,
                                'UnicodeBuilder_new')),
    append = interp2app(W_UnicodeBuilder.descr_append),
    append_slice = interp2app(W_UnicodeBuilder.descr_append_slice),
    build = interp2app(W_UnicodeBuilder.descr_build),
    __len__ = interp2app(W_UnicodeBuilder.descr_len),
)
W_UnicodeBuilder.typedef.acceptable_as_base_class = False
