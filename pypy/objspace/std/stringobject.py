from pypy.objspace.std.objspace import *
from stringtype import W_StringType
from intobject   import W_IntObject
from sliceobject import W_SliceObject
from listobject import W_ListObject
from instmethobject import W_InstMethObject
from noneobject import W_NoneObject
from pypy.interpreter.extmodule import make_builtin_func

from rarray import CharArrayFromStr, CharArraySize


applicationfile = StdObjSpace.AppFile(__name__)

class W_StringObject(W_Object):
    delegate_once = {}
    statictype = W_StringType

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

    def _char_isspace(ch):
        return ord(ch) in (9, 10, 11, 12, 13, 32)  

    def is_generic(w_self, fun): 
        space = w_self.space   
        v = w_self._value
        if v.len == 0:
            return space.w_False
        if v.len == 1:
            c = v.charat(0)
            return space.newbool(fun(c))
        else:
            res = 1
            for idx in range(v.len):
                if not fun(v.charat(idx)):
                    return space.w_False
            return space.w_True

    def isspace(w_self):
       return is_generic(w_self, _char_isspace)
   ## XXX fixme

##    def isdigit(w_self):
##        pass

##    def isupper(w_self):
##        pass

##    def isupper(w_self):
##        pass
    
##    def islower(w_self):
##        pass

##    def istitle(w_self):
##        pass

##    def isalnum(w_self):
##        pass

##    def isalpha(w_self):
##        pass

##    isspace = implmethod().register(isspace)
##    isdigit = implmethod().register(isdigit)
##    isupper = implmethod().register(isupper)
##    islower = implmethod().register(islower)
##    istitle = implmethod().register(istitle)
##    isalnum = implmethod().register(isalnum)
##    isalpha = implmethod().register(isalpha)


def str_splitByWhitespace(space, w_self, w_none):
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
        res[i] = W_StringObject(space, res[i])
    return W_ListObject(space, res)

def str_split(space, w_self, w_by):
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

# XXX temporary hack
W_StringType.str_split.register(str_split, W_StringObject, W_StringObject)
W_StringType.str_split.register(str_splitByWhitespace,
                                           W_StringObject, W_NoneObject)
#We should erase the W_NoneObject, but register takes always
#the same number of parameters. So you have to call split with
#None as parameter instead of calling it without any parameter


def str_join(space, w_self, w_list):
    list = space.unpackiterable(w_list)
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
        return W_StringObject(space, res.value())
    else:
        return W_StringObject(space, "")

W_StringType.str_join.register(str_join, W_StringObject, W_ANY)


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
    return str_join(w_empty, w_r)

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

def str_repr(space, w_str):
    # XXX this is bogus -- mwh
    a = space.add
    q = space.wrap("'")
    return a(a(q, w_str), q)

StdObjSpace.repr.register(str_repr, W_StringObject)
