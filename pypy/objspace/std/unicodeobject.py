from pypy.objspace.std.objspace import *
from pypy.objspace.std.fake import fake_type, wrap_exception
from pypy.objspace.std.stringobject import W_StringObject

W_UnicodeObject = fake_type(unicode)

# string-to-unicode delegation
def delegate__String(space, w_str):
    return W_UnicodeObject(space, unicode(space.unwrap(w_str)))
delegate__String.result_class = W_UnicodeObject
delegate__String.priority = PRIORITY_CHANGE_TYPE
delegate__String.can_fail = True

def eq__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) == space.unwrap(w_other))
    except:
        wrap_exception(space)

def lt__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(space.unwrap(w_uni) < space.unwrap(w_other))
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

register_all(vars())
