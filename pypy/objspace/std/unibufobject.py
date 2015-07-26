from pypy.objspace.std.unicodeobject import W_AbstractUnicodeObject
from pypy.objspace.std.unicodeobject import W_UnicodeObject, unicode_from_string
from pypy.objspace.std.strbufobject import copy_from_base_class
from pypy.interpreter.error import OperationError
from rpython.rlib.rstring import UnicodeBuilder


class W_UnicodeBufferObject(W_AbstractUnicodeObject):
    w_unicode = None

    def __init__(self, builder):
        self.builder = builder             # UnicodeBuilder
        self.length = builder.getlength()

    def force(self):
        if self.w_unicode is None:
            s = self.builder.build()
            if self.length < len(s):
                s = s[:self.length]
            self.w_unicode = W_UnicodeObject(s)
            return s
        else:
            return self.w_unicode._value

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r[:%d])" % (
            w_self.__class__.__name__, w_self.builder, w_self.length)

    def unwrap(self, space):
        return self.force()

    def unicode_w(self, space):
        return self.force()

    def descr_len(self, space):
        return space.wrap(self.length)

    def _new_concat_buffer(self, other):
        if self.builder.getlength() != self.length:
            builder = UnicodeBuilder()
            builder.append(self.force())
        else:
            builder = self.builder
        builder.append(other)
        return W_UnicodeBufferObject(builder)

    def descr_add(self, space, w_other):
        from pypy.objspace.std.bytesobject import W_AbstractBytesObject

        if isinstance(w_other, W_AbstractUnicodeObject):
            other = w_other.unicode_w(space)
            return self._new_concat_buffer(other)
        elif isinstance(w_other, W_AbstractBytesObject):
            other = unicode_from_string(space, w_other)._value
            return self._new_concat_buffer(other)
        else:
            self.force()
            return self.w_unicode.descr_add(space, w_other)

    def descr_unicode(self, space):
        # you cannot get subclasses of W_UnicodeBufferObject here
        assert type(self) is W_UnicodeBufferObject
        return self


copy_from_base_class(W_UnicodeObject, W_UnicodeBufferObject, 'w_unicode')
