from pypy.objspace.std.objspace import *
from intobject   import W_IntObject
from sliceobject import W_SliceObject
from listobject import W_ListObject
from instmethobject import W_InstMethObject
from pypy.interpreter.extmodule import make_builtin_func

from rarray import CharArrayFromStr, CharArraySize


applicationfile = StdObjSpace.AppFile(__name__)

class W_StringObject(W_Object):
    def __init__(w_self, space, str):
        W_Object.__init__(w_self, space)
        w_self._value = CharArrayFromStr(str)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value.value())

    def nonzero(w_self):
        return W_IntObject(self.space, w_self._value.len != 0)

    def hash(w_self):
        return W_IntObject(self, self._value.hash())

    def join(w_self, w_list):
        list = w_self.space.unpackiterable(w_list)
        if list:
            firstelem = 1
            listlen = 0
            reslen = 0  
            for w_item in list:
                reslen = reslen + w_item._value.len
                listlen = listlen + 1

            reslen = reslen + (listlen - 1) * w_self._value.len
            res = CharArraySize(reslen)

            pos = 0
            for w_item in list:
                if firstelem:
                    res.setsubstring(pos, w_item._value.value())
                    pos = pos + w_item._value.len 
                    firstelem = 0
                else:
                    res.setsubstring(pos, w_self._value.value())
                    pos = pos + w_self._value.len
                    res.setsubstring(pos, w_item._value.value())
                    pos = pos + w_item._value.len
            return W_StringObject(w_self.space, res.value())
        else:
            return W_StringObject(w_self.space, "")

    def splitByWhitespace(w_self):
        res = []
        inword = 0
        value = w_self._value.value()
        for ch in value:
            if ch.isspace():
                if inword:
                    inword = 0
            else:
                if inword:
                    res[-1] += ch
                else:
                    res.append(ch)
                    inword = 1
        for i in range(len(res)):
            res[i] = W_StringObject(w_self.space, res[i])
        return W_ListObject(w_self.space, res)

    def split(w_self, w_by=None):
        if w_by is w_self.space.w_None: return w_self.splitByWhitespace()
        res = []
        start = 0
        value = w_self._value.value()
        by = w_by._value.value()
        while 1:
            next = value.find(by, start)
            if next < 0:
                res.append(value[start:])
                break
            res.append(value[start:next])
            start = next + len(by)
        for i in range(len(res)):
            res[i] = W_StringObject(w_self.space, res[i])
        return W_ListObject(w_self.space, res)

def getattr_str(space, w_list, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('join'))):
        w_builtinfn = make_builtin_func(space, W_StringObject.join)
        return W_InstMethObject(space, w_list, w_builtinfn)
    elif space.is_true(space.eq(w_attr, space.wrap('split'))):
        w_builtinfn = make_builtin_func(space, W_StringObject.split)
        return W_InstMethObject(space, w_list, w_builtinfn)
    raise FailedToImplement(space.w_AttributeError)

StdObjSpace.getattr.register(getattr_str, W_StringObject, W_ANY)


def str_unwrap(space, w_str):
    return w_str._value.value()

StdObjSpace.unwrap.register(str_unwrap, W_StringObject)

def str_is_true(space, w_str):
    return w_str._value.len != 0

StdObjSpace.is_true.register(str_is_true, W_StringObject)

def str_str_lt(space, w_str1, w_str2):
    i = w_str1._value.value()
    j = w_str2._value.value()
    return space.newbool( i < j )
StdObjSpace.lt.register(str_str_lt, W_StringObject, W_StringObject)

def str_str_le(space, w_str1, w_str2):
    i = w_str1._value.value()
    j = w_str2._value.value()
    return space.newbool( i <= j )
StdObjSpace.le.register(str_str_le, W_StringObject, W_StringObject)

def str_str_eq(space, w_str1, w_str2):
    val1 = w_str1._value
    val2 = w_str2._value
    if val1.len == val2.len:
        for i in range(val1.len):
            if ord(val1.charat(i)) != ord(val2.charat(i)):
                return space.w_False
        return space.w_True           
    else:
        return space.w_False
StdObjSpace.eq.register(str_str_eq, W_StringObject, W_StringObject)

def str_str_ne(space, w_str1, w_str2):
    i = w_str1._value.value()
    j = w_str2._value.value()
    return space.newbool( i != j )
StdObjSpace.ne.register(str_str_ne, W_StringObject, W_StringObject)

def str_str_gt(space, w_str1, w_str2):
    i = w_str1._value.value()
    j = w_str2._value.value()
    return space.newbool( i > j )
StdObjSpace.gt.register(str_str_gt, W_StringObject, W_StringObject)

def str_str_ge(space, w_str1, w_str2):
    i = w_str1._value.value()
    j = w_str2._value.value()
    return space.newbool( i >= j )
StdObjSpace.ge.register(str_str_ge, W_StringObject, W_StringObject)


def getitem_str_int(space, w_str, w_int):
    ival = w_int.intval
    slen = w_str._value.len
    if ival < 0:
        ival += slen
    if ival < 0 or ival >= slen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("string index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return W_StringObject(space, w_str._value.charat(ival))

StdObjSpace.getitem.register(getitem_str_int, 
                             W_StringObject, W_IntObject)

def getitem_str_slice(space, w_str, w_slice):
    return applicationfile.call(space, "getitem_string_slice", [w_str, w_slice])

StdObjSpace.getitem.register(getitem_str_slice, 
                                W_StringObject, W_SliceObject)

def add_str_str(space, w_left, w_right):
    return W_StringObject(space, w_left._value.value() + w_right._value.value())

StdObjSpace.add.register(add_str_str, W_StringObject, W_StringObject)

def mod_str_ANY(space, w_left, w_right):
    notImplemented
 
def mod_str_tuple(space, w_format, w_args):
    notImplemented

def len_str(space, w_str):
    return space.wrap(w_str._value.len)

StdObjSpace.len.register(len_str, W_StringObject)

def str_str(space, w_str):
    return w_str

StdObjSpace.str.register(str_str, W_StringObject)
