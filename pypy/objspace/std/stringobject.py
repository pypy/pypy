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


EQ = 1
LE = 2
GE = 3
GT = 4
LT = 5
NE = 6

def string_richcompare(space, w_str1, w_str2, op):
    str1 = w_str1._value
    str2 = w_str2._value

    if space.is_true(space.is_(w_str1, w_str2)):
        if op == EQ or op == LE or op == GE:
            return space.w_True
        elif op == GT or op == LT or op == NE:
            return space.w_False
    if 0:
        pass
    else:
        if op == EQ:
            if str1.len == str2.len:
                for i in range(str1.len):
                    if ord(str1.charat(i)) != ord(str2.charat(i)):
                        return space.w_False
                return space.w_True
            else:
                return space.w_False
        else:
            if str1.len > str2.len:
                min_len = str2.len
            else:
                min_len = str1.len

            c = 0
            idx = 0
            if (min_len > 0):
                while (c == 0) and (idx < min_len):
                    c = ord(str1.charat(idx)) - ord(str2.charat(idx))
                    idx = idx + 1
            else:
                c = 0

        if (c == 0):
            if str1.len < str2.len:
                c = -1
            elif str1.len > str2.len:
                c = 1
            else:
                c = 0

        if op == LT:
            return space.newbool(c < 0)
        elif op == LE:
            return space.newbool(c <= 0)
        elif op == NE:
            return space.newbool(c != 0)
        elif op == GT:
            return space.newbool(c > 0)
        elif op == GE:
            return space.newbool(c >= 0)
        else:
            raise NotImplemented

def str_str_lt(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, LT)

StdObjSpace.lt.register(str_str_lt, W_StringObject, W_StringObject)

def str_str_le(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, LE)

StdObjSpace.le.register(str_str_le, W_StringObject, W_StringObject)

def str_str_eq(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, EQ)

StdObjSpace.eq.register(str_str_eq, W_StringObject, W_StringObject)

def str_str_ne(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, NE)
StdObjSpace.ne.register(str_str_ne, W_StringObject, W_StringObject)

def str_str_gt(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, GT)

StdObjSpace.gt.register(str_str_gt, W_StringObject, W_StringObject)

def str_str_ge(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, GE)

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
#    return space.gethelper(applicationfile).call(
#        "getitem_string_slice", [w_str, w_slice])
    w = space.wrap
    u = space.unwrap
    w_start, w_stop, w_step, w_sl = w_slice.indices(w(w_str._value.len))
    start = u(w_start)
    stop = u(w_stop)
    step = u(w_step)
    sl = u(w_sl)
    r = [None] * sl
    for i in range(sl):
        r[i] = space.getitem(w_str, w(start + i*step))
    w_r = space.newlist(r)
    w_empty = space.newstring([])
    return w_empty.join(w_r)

StdObjSpace.getitem.register(getitem_str_slice, 
                             W_StringObject, W_SliceObject)

def add_str_str(space, w_left, w_right):
    buf = CharArraySize(w_left._value.len + w_right._value.len)
    buf.setsubstring(0, w_left._value.value())
    buf.setsubstring(w_left._value.len, w_right._value.value())
    return W_StringObject(space, buf.value())

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
