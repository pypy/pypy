"""
stringobject.py

Synopsis of implemented methods (* marks work in progress)

Py                PyPy

                  def _is_generic(w_self, fun):
                  def is_true__String(space, w_str):
                  def mod__String_ANY(space, w_str, w_item):def mod__String_Tuple(space, w_str, w_tuple):def mod_str_tuple(space, w_format, w_args):
                  def ord__String(space, w_str):
                  def string_richcompare(space, w_str1, w_str2, op):
                  def unwrap__String(space, w_str):
__add__           def add__String_String(space, w_left, w_right):
__class__
__contains__
__delattr__
__doc__
__eq__            def eq__String_String(space, w_str1, w_str2):
__ge__            def ge__String_String(space, w_str1, w_str2):
__getattribute__
__getitem__       def getitem__String_Int(space, w_str, w_int): def getitem__String_Slice(space, w_str, w_slice):
__getslice__
__gt__            def gt__String_String(space, w_str1, w_str2):
__hash__          def hash__String(space, w_str):
__init__
__le__            def le__String_String(space, w_str1, w_str2):
__len__           def len__String(space, w_str):
__lt__            def lt__String_String(space, w_str1, w_str2):
__mul__
__ne__            def ne__String_String(space, w_str1, w_str2):
__new__
__reduce__
__repr__          def repr__String(space, w_str): #fake
__rmul__
__setattr__
__str__           def str__String(space, w_str):
capitalize        def str_capitalize__String(space, w_self):
center            def str_center__String_Int(space, w_self):
count             def str_count__String_String(space, w_self): [optional arguments not supported now]
decode            !Unicode not supported now
encode            !Unicode not supported now
endswith          str_endswith__String_String    [optional arguments not supported now]
expandtabs        str_expandtabs__String_Int
find              OK, nur noch tests
index             OK, nur noch tests
isalnum           def str_isalnum__String(space, w_self): def _isalnum(ch):
isalpha           def str_isalpha__String(space, w_self): def _isalpha(ch):
isdigit           def str_isdigit__String(space, w_self): def _isdigit(ch):
islower           def str_islower__String(space, w_self): def _islower(ch):
isspace           def str_isspace__String(space, w_self): def _isspace(ch):
istitle           def str_istitle(space, w_self):
isupper           def str_isupper__String(space, w_self): def _isupper(ch):
join              def str_join__String_ANY(space, w_self, w_list):
ljust             def str_ljust__String_ANY(space, w_self, w_arg):
lower      
lstrip            def str_lstrip__String(space, w_self):
replace           *Tomek
rfind             OK, nur noch tests
rindex            OK, nur noch tests
rjust             def str_rjust__String_ANY(space, w_self, w_arg):
rstrip            def str_rstrip__String(space, w_self):
split             def str_split__String_None_Int(space, w_self, w_none, w_maxsplit=-1):def str_split__String_String_Int(space, w_self, w_by, w_maxsplit=-1):
splitlines        *Günter
startswith        *Günter
strip             def str_strip__String(space, w_self):
swapcase
title             def str_title__String(space, w_self):
translate
upper             def str_upper__String(space, w_self):
zfill
"""

from pypy.objspace.std.objspace import *
from stringtype import W_StringType
from intobject   import W_IntObject
from sliceobject import W_SliceObject
from listobject import W_ListObject
from instmethobject import W_InstMethObject
from noneobject import W_NoneObject
from tupleobject import W_TupleObject

applicationfile = StdObjSpace.AppFile(__name__)

class W_StringObject(W_Object):
    statictype = W_StringType

    def __init__(w_self, space, str):
        W_Object.__init__(w_self, space)
        w_self._value = str

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)


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


def _is_generic(self, fun): 
    space = w_self.space   
    v = space.unwrap(w_self)
    if len(v) == 0:
        return space.w_False
    if len(v) == 1:
        c = v[0]
        return space.newbool(fun(c))
    else:
        res = 1
        for idx in range(len(v)):
            if not fun(v[idx]):
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
    self = space.unwrap(w_self)
    res = [' '] * len(self)
    for i in range(len(self)):
        ch = self[i]
        if _islower(ch):
            o = ord(ch) - 32
            res[i] = chr(o)
        else:
            res[i] = ch

    return space.wrap("".join(res))

def str_lower__String(space, w_self):
    self = space.unwrap(w_self)
    res = [' '] * len(self)
    for i in range(len(self)):
        ch = self[i]
        if _isupper(ch):
            o = ord(ch) + 32
            res[i] = chr(o)
        else:
            res[i] = ch

    return space.wrap("".join(res))

    
def str_capitalize__String(space, w_self):
    input = space.unwrap(w_self)
    buffer = [' '] * len(input)
    if len(input) > 0:
        ch = input[0]
        if _islower(ch):
            o = ord(ch) - 32
            buffer[0] = chr(o)
        for i in range(1, len(input)):
            buffer[i] = input[i]
    return space.wrap("".join(buffer))
         
def str_title__String(space, w_self):
    u = space.unwrap
    input = u(w_self)
    buffer = [' '] * len(input)
    inword = 0

    for pos in range(0, len(input)):
        ch = input[pos]
        buffer[pos] = ch
        if ch.isspace():
            if inword:
                inword = 0
        else:
            if not inword:
                if _islower(ch):
                    o = ord(ch) - 32
                    buffer[pos] = chr(o)
                inword = 1
    return space.wrap("".join(buffer))

def str_split__String_None_Int(space, w_self, w_none, w_maxsplit=-1):
    res = []
    inword = 0
    u = space.unwrap
    value = u(w_self)
    maxsplit = u(w_maxsplit)
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
    u = space.unwrap
    res = []
    start = 0
    value = u(w_self)
    by = u(w_by)
    bylen = len(by)
    maxsplit = u(w_maxsplit)

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
            start = len(value) + 1      
            break
        res.append(value[start:next])
        start = next + bylen
        #decrese the counter only then, when
        #we don't have default maxsplit
        if maxsplit > -1:
            splitcount = splitcount - 1

    if start < len(value):             
        res.append(value[start:])

    for i in range(len(res)):
        res[i] = W_StringObject(w_self.space, res[i])
    return W_ListObject(w_self.space, res)

def str_join__String_ANY(space, w_self, w_list):
    u = space.unwrap
    list = space.unpackiterable(w_list)
    if list:
        self = u(w_self)
        firstelem = 1
        listlen = 0
        reslen = 0 
        #compute the length of the resulting string 
        for w_item in list:
            reslen = reslen + len(u(w_item))
            listlen = listlen + 1

        reslen = reslen + (listlen - 1) * len(self)

        #allocate the string buffer
        res = [' '] * reslen

        pos = 0
        #fill in the string buffer
        for w_item in list:
            item = u(w_item)
            if firstelem:
                for i in range(len(item)):
                    res[i+pos] = item[i]
                firstelem = 0
                pos = pos + len(item)
            else:
                for i in range(len(self)):
                    res[i+pos] = self[i]
                pos = pos + len(self)
                 
                for i in range(len(item)):
                    res[i+pos] = item[i]
                pos = pos + len(item)

        return space.wrap("".join(res))
    else:
        return space.wrap("")


def str_rjust__String_ANY(space, w_self, w_arg):
    u = space.unwrap

    u_arg = u(w_arg)
    u_self = u(w_self)
    
    d = u_arg - len(u_self)
    if d>0:
        u_self = d * ' ' + u_self
        
    return space.wrap(u_self)


def str_ljust__String_ANY(space, w_self, w_arg):
    u = space.unwrap

    u_self = u(w_self)
    u_arg = u(w_arg)

    d = u_arg - len(u_self)
    if d>0:
        u_self += d * ' '
        
    return space.wrap(u_self)

def str_find__String_String_Int_Int(space, w_self, w_sub, w_start=None, w_end=None):

    u = space.unwrap 
    res = _find(u(w_self), u(w_sub), u(w_start), u(w_end), 1)
    return space.wrap(res)

def str_rfind__String_String_Int_Int(space, w_self, w_sub, w_start=None, w_end=None):

    u = space.unwrap
    res = _find(u(w_self), u(w_sub), u(w_start), u(w_end), -1)
    return space.wrap(res)

def str_index__String_String_Int_Int(space, w_self, w_sub, w_start=None, w_end=None):

    u = space.unwrap
    res = _find(u(w_self), u(w_sub), u(w_start), u(w_end), 1)
    if res == -1:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))

    return space.wrap(res)


def str_rindex__String_String_Int_Int(space, w_self, w_sub, w_start=None, w_end=None):

    u = space.unwrap
    res = _find(u(w_self), u(w_sub), u(w_start), u(w_end), -1)
    if res == -1:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return space.wrap(res)


def _find(self, sub, start, end, dir):

    length = len(self)

    #adjust_indicies
    if (end > length):
        end = length
    elif (end < 0):
        end += length
    if (end < 0):
        end = 0
    if (start < 0):
        start += length
    if (start < 0):
        start = 0

    if dir > 0:
        if len(sub) == 0 and start < end:
            return start

        end = end - len(sub) + 1

        for i in range(start, end):
            match = 1
            for idx in range(len(sub)):
                if sub[idx] != self[idx+i]:
                    match = 0
                    break
            if match: 
                return i
        return -1
    else:
        if len(sub) == 0 and start < end:
            return last

        end = end - len(sub)

        for j in range(end, start+1, -1):
            match = 1
            for idx in range(len(sub)):
                if sub[idx] != self[idx+j]:
                    match = 0
                    break
            if match:
                return j
        return -1        



def str_strip__String(space, w_self):
    u = space.unwrap
    u_self = u(w_self)
    lpos = 0
    while u_self[lpos] == ' ':
       lpos += 1
       
    rpos = len(u_self)
    while u_self[rpos - 1] == ' ':
       rpos -= 1
       
    return space.wrap(u_self[lpos:rpos])
   
   
def str_rstrip__String(space, w_self):
    u_self = space.unwrap(w_self)
       
    rpos = len(u_self)
    while u_self[rpos - 1] == ' ':
       rpos -= 1
       
    return space.wrap(u_self[:rpos])
   
   
def str_lstrip__String(space, w_self):
    u_self = space.unwrap(w_self)
    lpos = 0
    while u_self[lpos] == ' ':
       lpos += 1
            
    return space.wrap(u_self[lpos:])
   

def str_center__String_Int(space, w_self, w_arg):
    u_self = space.unwrap(w_self)
    u_arg  = space.unwrap(w_arg)

    d = u_arg - len(u_self) 
    if d>0:
        offset = d//2
        u_centered = offset * ' ' + u_self + (d - offset) * ' ' 
    else:
        u_centered = u_self

    return W_StringObject(space, u_centered)
    
#[optional arguments not supported now]    
def str_count__String_String(space, w_self, w_arg): 
    u_self = space.unwrap(w_self)
    u_arg  = space.unwrap(w_arg)
    
    count = 0  
    if u_arg == "":
        count = len(u_self) +1 #behaves as in Python
    elif u_self == "":
        pass                   #behaves as in Python
    else:
        pos = 0
        while 1: 
           count += 1
           pos = u_self.find(u_arg, pos+1) #XXX use pypy find
           if pos == -1:
              break
       
    return W_IntObject(space, count)

#[optional arguments not supported now]    
def str_endswith__String_String(space, w_self, w_end): 
    u_self = space.unwrap(w_self)
    u_end  = space.unwrap(w_end)
    
    found = 0
    if u_end:
        endlen = len(u_end)
        if endlen <= len(u_self):
           found = (u_end == u_self[-endlen:]) 
    else:
        found = 1
        
    return W_IntObject(space, found)
    
    
#[optional arguments not supported now]    
def str_startswith__String_String(space, w_self, w_start): 
    u_self = space.unwrap(w_self)
    u_start  = space.unwrap(w_start)
    
    found = 0
    if u_start:
        startlen = len(u_start)
        if startlen <= len(u_self):
           found = (u_start == u_self[:startlen]) 
    else:
        found = 1
        
    return W_IntObject(space, found)    

def str_expandtabs__String_Int(space, w_self, w_tabsize):   
    u_self = space.unwrap(w_self)
    u_tabsize  = space.unwrap(w_tabsize)

    u_expanded = ""
    if u_self:
        for token in u_self.split("\t"): #XXX use pypy split
            if token:
                u_expanded += token
            else:
                u_expanded += " " * u_tabsize

    return W_StringObject(space, u_expanded)        
   
    
def unwrap__String(space, w_str):
    return w_str._value

def is_true__String(space, w_str):
    return len(space.unwrap(w_str)) != 0

def hash__String(space, w_str):
    return W_IntObject(space, hash(space.unwrap(w_str)))


EQ = 1
LE = 2
GE = 3
GT = 4
LT = 5
NE = 6


def string_richcompare(space, w_str1, w_str2, op):
    u = space.unwrap
    str1 = u(w_str1)
    str2 = u(w_str2)

    if space.is_true(space.is_(w_str1, w_str2)):
        if op == EQ or op == LE or op == GE:
            return space.w_True
        elif op == GT or op == LT or op == NE:
            return space.w_False
    if 0:
        pass
    else:
        if op == EQ:
            if len(str1) == len(str2):
                for i in range(len(str1)):
                    if ord(str1[i]) != ord(str2[i]):
                        return space.w_False
                return space.w_True
            else:
                return space.w_False
        else:
            if len(str1) > len(str2):
                min_len = len(str2)
            else:
                min_len = len(str1)

            c = 0
            idx = 0
            if (min_len > 0):
                while (c == 0) and (idx < min_len):
                    c = ord(str1[idx]) - ord(str2[idx])
                    idx = idx + 1
            else:
                c = 0

        if (c == 0):
            if len(str1) < len(str2):
                c = -1
            elif len(str1) > len(str2):
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
            return NotImplemented

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
    u = space.unwrap
    ival = w_int.intval
    str = u(w_str)
    slen = len(u(w_str))
    if ival < 0:
        ival += slen
    if ival < 0 or ival >= slen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("string index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return W_StringObject(space, str[ival])

def getitem__String_Slice(space, w_str, w_slice):
    return space.gethelper(applicationfile).call(
        "getitem_string_slice", [w_str, w_slice])
    w = space.wrap
    u = space.unwrap
    w_start, w_stop, w_step, w_sl = w_slice.indices(w(len(u(w_str._value))))
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
    u = space.unwrap
    right = u(w_right)
    left = u(w_left)
    buf = [' '] * (len(left) + len(right))
    for i in range(len(left)):
        buf[i] = left[i]
    for i in range(len(right)):
        buf[i+len(left)] = right[i]
    return space.wrap("".join(buf))

def mod_str_tuple(space, w_format, w_args):
    raise NotImplementedError

def len__String(space, w_str):
    return space.wrap(len(space.unwrap(w_str)))

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


