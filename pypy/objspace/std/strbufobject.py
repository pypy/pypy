from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.unicodeobject import delegate_String2Unicode
from pypy.rlib.rstring import StringBuilder
from pypy.interpreter.buffer import Buffer

class W_StringBufferObject(W_Object):
    from pypy.objspace.std.stringtype import str_typedef as typedef

    w_str = None

    def __init__(self, builder):
        self.builder = builder             # StringBuilder
        self.length = builder.getlength()

    def force(self):
        if self.w_str is None:
            s = self.builder.build()
            if self.length < len(s):
                s = s[:self.length]
            self.w_str = W_StringObject(s)
            return s
        else:
            return self.w_str._value

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r[:%d])" % (
            w_self.__class__.__name__, w_self.builder, w_self.length)

    def unwrap(self, space):
        return self.force()

    def str_w(self, space):
        return self.force()

registerimplementation(W_StringBufferObject)

# ____________________________________________________________

def joined2(str1, str2):
    builder = StringBuilder()
    builder.append(str1)
    builder.append(str2)
    return W_StringBufferObject(builder)

# ____________________________________________________________

def delegate_buf2str(space, w_strbuf):
    w_strbuf.force()
    return w_strbuf.w_str

def delegate_buf2unicode(space, w_strbuf):
    w_strbuf.force()
    return delegate_String2Unicode(space, w_strbuf.w_str)

def len__StringBuffer(space, w_self):
    return space.wrap(w_self.length)

def add__StringBuffer_String(space, w_self, w_other):
    if w_self.builder.getlength() != w_self.length:
        builder = StringBuilder()
        builder.append(w_self.force())
    else:
        builder = w_self.builder
    builder.append(w_other._value)
    return W_StringBufferObject(builder)

def str__StringBuffer(space, w_self):
    # you cannot get subclasses of W_StringBufferObject here
    assert type(w_self) is W_StringBufferObject
    return w_self

from pypy.objspace.std import stringtype
register_all(vars(), stringtype)
