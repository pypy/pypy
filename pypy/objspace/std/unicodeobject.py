from pypy.objspace.std.objspace import *
from pypy.objspace.std.fake import fake_type, wrap_exception
from pypy.objspace.std.stringobject import W_StringObject

W_UnicodeObject = fake_type(unicode)

# string-to-unicode delegation
def delegate__String(space, w_str):
    return W_UnicodeObject(space, unicode(space.str_w(w_str)))
delegate__String.result_class = W_UnicodeObject
delegate__String.priority = PRIORITY_CHANGE_TYPE

def eq__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) == space.unwrap(w_other))
    except:
        wrap_exception(space)

def ne__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) != space.unwrap(w_other))
    except:
        wrap_exception(space)


def lt__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) < space.unwrap(w_other))
    except:
        wrap_exception(space)

def gt__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) > space.unwrap(w_other))
    except:
        wrap_exception(space)

def le__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) <= space.unwrap(w_other))
    except:
        wrap_exception(space)

def ge__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) >= space.unwrap(w_other))
    except:
        wrap_exception(space)

def ord__Unicode(space, w_uni):
    try:
        return space.wrap(ord(w_uni.val))
    except:
        wrap_exception(space)

def add__Unicode_Unicode(space, w_left, w_right):
    return space.wrap(space.unwrap(w_left) + space.unwrap(w_right))

def contains__String_Unicode(space, w_left, w_right):
    return space.wrap(space.unwrap(w_right) in space.unwrap(w_left))

def contains__Unicode_Unicode(space, w_left, w_right):
    return space.wrap(space.unwrap(w_right) in space.unwrap(w_left))

# str.strip(unicode) needs to convert self to unicode and call unicode.strip
def str_strip__String_Unicode(space, w_self, w_chars ):
    self = w_self._value
    return space.wrap( unicode(self).strip( space.unwrap(w_chars) ) )
def str_lstrip__String_Unicode(space, w_self, w_chars ):
    self = w_self._value
    return space.wrap( unicode(self).lstrip( space.unwrap(w_chars) ) )
def str_rstrip__String_Unicode(space, w_self, w_chars ):
    self = w_self._value
    return space.wrap( unicode(self).rstrip( space.unwrap(w_chars) ) )
# we use the following magic to register strip_string_unicode as a String multimethod
import stringtype


register_all(vars(), stringtype)
