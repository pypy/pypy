from pypy.objspace.std.objspace import *
from stringtype import W_StringType
from intobject   import W_IntObject
from sliceobject import W_SliceObject
from listobject import W_ListObject
from instmethobject import W_InstMethObject
from noneobject import W_NoneObject
from tupleobject import W_TupleObject

from rarray import CharArrayFromStr, CharArraySize

applicationfile = StdObjSpace.AppFile(__name__)

class W_StringObject(W_Object):
    statictype = W_StringType

    def __init__(w_self, space, str):
        W_Object.__init__(w_self, space)
        w_self._value = CharArrayFromStr(str)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value.value())


registerimplementation(W_StringObject)

def _isspace(ch):
    return ord(ch) in (9, 10, 11, 12, 13, 32)  

def _isdigit(ch):
    o = ord(ch)
    return o >= 48 and o <= 57

def _isalpha(ch):
    o = ord(ch)
    return (o>=97 and o<=122) or (o>=65 and o<=90)

def _isalnum(ch):
    o = ord(ch)
    return (o>=97 and o<=122) \
        or (o>=65 and o<=90) \
        or (o>=48 and o<=57)
def _isupper(ch):
    o = ord(ch)
    return (o>=65 and o<=90)

def _islower(ch):   
    o = ord(ch)
    return (o>=97 and o<=122)


def _is_generic(w_self, fun): 
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

def str_isspace__String(space, w_self):
    return _is_generic(w_self, _isspace)

def str_isdigit__String(space, w_self):
    return _is_generic(w_self, _isdigit)

def str_isalpha__String(space, w_self):
    return _is_generic(w_self, _isalpha)

def str_isalnum__String(space, w_self):
    return _is_generic(w_self, _isalnum)

def str_isupper__String(space, w_self):
    return _is_generic(w_self, _isupper)

def str_islower__String(space, w_self):
    return _is_generic(w_self, _islower)

def str_istitle(space, w_self):
    pass

def str_upper__String(space, w_self):
    up = W_StringObject(space, w_self._value.value())
    for i in range(up._value.len):
        ch = up._value.charat(i)
        if _islower(ch):
            o = ord(ch) - 32
            up._value.setcharat(i, chr(o))

    return up
    
def str_capitalize__String(space, w_self):
    w_str = W_StringObject(space, space.unwrap(w_self))
    buffer = w_str._value
    if buffer.len > 0:
        ch = buffer.charat(0)
        if _islower(ch):
            o = ord(ch) - 32
            buffer.setcharat(0, chr(o))
    return w_str
         
def str_title__String(space, w_self):
    w_str = W_StringObject(space, space.unwrap(w_self))
    buffer = w_str._value
    inword = 0

    for pos in range(0, buffer.len):
        ch = buffer.charat(pos)
        if ch.isspace():
            if inword:
                inword = 0
        else:
            if not inword:
                if _islower(ch):
                    o = ord(ch) - 32
                    buffer.setcharat(pos, chr(o))     
                inword = 1
    return w_str        

def str_split__String_None_Int(space, w_self, w_none, w_maxsplit=-1):
    res = []
    inword = 0
    value = w_self._value.value()
    maxsplit = space.unwrap(w_maxsplit)
    pos = 0

    for ch in value:
        if ch.isspace():
            if inword:
                inword = 0
        else:
            if inword:
                res[-1] += ch
            else:
                if maxsplit > -1:
                    if maxsplit == 0:
                        res.append(value[pos:])
                        break
                    maxsplit = maxsplit - 1
                res.append(ch)
                inword = 1
        pos = pos + 1

    for i in range(len(res)):
        res[i] = W_StringObject(space, res[i])
    return W_ListObject(space, res)

def str_split__String_String_Int(space, w_self, w_by, w_maxsplit=-1):
    res = []
    start = 0
    value = w_self._value.value()
    by = w_by._value.value()
    bylen = space.unwrap(space.len(w_by))
    maxsplit = space.unwrap(w_maxsplit)

    #if maxsplit is default, then you have no limit
    #of the length of the resulting array
    if maxsplit == -1:
        splitcount = 1
    else:
        splitcount = maxsplit

    while splitcount:             
        next = value.find(by, start)
        if next < 0:
            res.append(value[start:])
            start = w_self._value.len + 1      
            break
        res.append(value[start:next])
        start = next + bylen
        #decrese the counter only then, when
        #we don't have default maxsplit
        if maxsplit > -1:
            splitcount = splitcount - 1

    if start < w_self._value.len:             
        res.append(value[start:])

    for i in range(len(res)):
        res[i] = W_StringObject(w_self.space, res[i])
    return W_ListObject(w_self.space, res)

def str_join__String_ANY(space, w_self, w_list):
    list = space.unpackiterable(w_list)
    if list:
        firstelem = 1
        listlen = 0
        reslen = 0 
        #compute the length of the resulting string 
        for w_item in list:
            reslen = reslen + w_item._value.len
            listlen = listlen + 1

        reslen = reslen + (listlen - 1) * w_self._value.len

        #allocate the string buffer
        res = CharArraySize(reslen)

        pos = 0
        #fill in the string buffer"
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


def str_rjust__String_ANY(space, w_self, w_arg):
    u = space.unwrap

    u_arg = u(w_arg)
    u_self = u(w_self)
    
    d = u_arg - len(u_self)
    if d>0:
        u_self = d * ' ' + u_self
        
    return W_StringObject(space, u_self)


def str_ljust__String_ANY(space, w_self, w_arg):
    u = space.unwrap

    u_self = u(w_self)
    u_arg = u(w_arg)

    d = u_arg - len(u_self)
    if d>0:
        u_self += d * ' '
        
    return W_StringObject(space, u_self)

def unwrap__String(space, w_str):
    return w_str._value.value()

def is_true__String(space, w_str):
    return w_str._value.len != 0

def hash__String(space, w_str):
    return W_IntObject(space, w_str._value.hash())


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

def lt__String_String(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, LT)

def le__String_String(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, LE)

def eq__String_String(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, EQ)

def ne__String_String(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, NE)

def gt__String_String(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, GT)

def ge__String_String(space, w_str1, w_str2):
    return string_richcompare(space, w_str1, w_str2, GE)

def getitem__String_Int(space, w_str, w_int):
    ival = w_int.intval
    slen = w_str._value.len
    if ival < 0:
        ival += slen
    if ival < 0 or ival >= slen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("string index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return W_StringObject(space, w_str._value.charat(ival))

def getitem__String_Slice(space, w_str, w_slice):
    return space.gethelper(applicationfile).call(
        "getitem_string_slice", [w_str, w_slice])
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
    return str_join(space, w_empty, w_r)

def add__String_String(space, w_left, w_right):
    buf = CharArraySize(w_left._value.len + w_right._value.len)
    buf.setsubstring(0, w_left._value.value())
    buf.setsubstring(w_left._value.len, w_right._value.value())
    return W_StringObject(space, buf.value())

def mod_str_tuple(space, w_format, w_args):
    notImplemented

def len__String(space, w_str):
    return space.wrap(w_str._value.len)

def str__String(space, w_str):
    return w_str

def repr__String(space, w_str):
    # XXX this is bogus -- mwh
    return space.wrap(repr(space.unwrap(w_str)))
    a = space.add
    q = space.wrap("'")
    return a(a(q, w_str), q)

def ord__String(space, w_str):
    return space.wrap(ord(space.unwrap(w_str)))

def mod__String_ANY(space, w_str, w_item):
    return mod_str_tuple(space, w_str, space.newtuple([w_item]))

def mod__String_Tuple(space, w_str, w_tuple):
    return space.wrap(space.unwrap(w_str)%space.unwrap(w_tuple))


# register all methods 
register_all(vars(), W_StringType)


