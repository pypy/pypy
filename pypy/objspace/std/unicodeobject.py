from pypy.objspace.std.objspace import *
from pypy.objspace.std.fake import fake_type, wrap_exception
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.strutil import string_to_int, string_to_long

W_UnicodeObject = fake_type(unicode)

# Helper for converting int/long
import unicodedata
def unicode_to_decimal_w(space, w_unistr):
    result = []
    for uchr in space.unwrap(w_unistr):
        if uchr.isspace():
            result.append(' ')
            continue
        try:
            result.append(chr(ord('0') + unicodedata.decimal(uchr)))
            continue
        except ValueError:
            ch = ord(uchr)
            if 0 < ch < 256:
                result.append(chr(ch))
                continue
        raise OperationError(space.w_UnicodeEncodeError, space.wrap('invalid decimal Unicode string'))
    return ''.join(result)

# string-to-unicode delegation
def delegate_String2Unicode(w_str):
    space = w_str.space
    return W_UnicodeObject(space, unicode(space.str_w(w_str)))


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
        return space.wrap(ord(space.unwrap(w_uni)))
    except:
        wrap_exception(space)

def float__Unicode(space, w_uni):
    try:
        return space.wrap(float(unicode_to_decimal_w(space, w_uni)))
    except:
        wrap_exception(space)

def int__Unicode(space, w_uni):
    try:
        return space.wrap(string_to_int(unicode_to_decimal_w(space, w_uni)))
    except:
        wrap_exception(space)

def long__Unicode(space, w_uni):
    try:
        return space.wrap(string_to_long(unicode_to_decimal_w(space, w_uni)))
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
