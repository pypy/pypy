# -*- Coding: Latin-1 -*-
"""
stringobject.py

Synopsis of implemented methods (* marks work in progress)

Py                PyPy

                  def _is_generic(w_self, fun):
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
__repr__          def repr__String(space, w_str):
__rmul__
__setattr__
__str__           def str__String(space, w_str):
capitalize        def str_capitalize__String(space, w_self):
center            def str_center__String_Int(space, w_self):
count             def str_count__String_String_Int_Int(space, w_self): [optional arguments not supported now]
decode            !Unicode not supported now
encode            !Unicode not supported now
endswith          str_endswith__String_String    [optional arguments not supported now]
expandtabs        str_expandtabs__String_Int
find              OK
index             OK
isalnum           def str_isalnum__String(space, w_self): def _isalnum(ch):
isalpha           def str_isalpha__String(space, w_self): def _isalpha(ch):
isdigit           def str_isdigit__String(space, w_self): def _isdigit(ch):
islower           def str_islower__String(space, w_self): def _islower(ch):
isspace           def str_isspace__String(space, w_self): def _isspace(ch):
istitle           def str_istitle(space, w_self):
isupper           def str_isupper__String(space, w_self): def _isupper(ch):
join              def str_join__String_ANY(space, w_self, w_list):
ljust             def str_ljust__String_ANY(space, w_self, w_arg):
lower             OK
lstrip            def str_lstrip__String_String(space, w_self, w_chars):
replace           OK
rfind             OK
rindex            OK
rjust             def str_rjust__String_ANY(space, w_self, w_arg):
rstrip            def str_rstrip__String_String(space, w_self, w_chars):
split             def str_split__String_None_Int(space, w_self, w_none, w_maxsplit=-1):def str_split__String_String_Int(space, w_self, w_by, w_maxsplit=-1):
splitlines        def str_splitlines__String_String(space, w_self, w_keepends):
startswith        str_startswith__String_String    [optional arguments not supported now]
strip             def str_strip__String_String(space, w_self, w_chars):
swapcase          OK
title             def str_title__String(space, w_self):
translate         OK
upper             def str_upper__String(space, w_self):
zfill             OK
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from stringtype import W_StringType
from intobject   import W_IntObject
from sliceobject import W_SliceObject
import slicetype
from listobject import W_ListObject
from noneobject import W_NoneObject
from tupleobject import W_TupleObject

# XXX consider reimplementing _value to be a list of characters
#     instead of a plain string


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

def _is_generic(w_self, fun): 
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

def str_istitle__String(space, w_self):
    input = space.unwrap(w_self)
    prev_letter='!'

    for pos in range(0, len(input)):
        ch = input[pos]
        if ch.isalpha():
            if (prev_letter.isalpha() and ch.isupper()) or \
               (not prev_letter.isalpha() and  ch.islower()):
                    return space.w_False
        prev_letter = ch

    return space.w_True

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

def str_swapcase__String(space, w_self):
    self = space.unwrap(w_self)
    res = [' '] * len(self)
    for i in range(len(self)):
        ch = self[i]
        if _isupper(ch):
            o = ord(ch) + 32
            res[i] = chr(o)
        elif _islower(ch):
            o = ord(ch) - 32
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
        else:
            buffer[0] = ch

        for i in range(1, len(input)):
            ch = input[i]
            if _isupper(ch):
                o = ord(ch) + 32
                buffer[i] = chr(o)
            else:
                buffer[i] = ch

    return space.wrap("".join(buffer))
         
def str_title__String(space, w_self):
    input = space.unwrap(w_self)
    buffer = [' '] * len(input)
    prev_letter=' '

    for pos in range(0, len(input)):
        ch = input[pos]
        if not prev_letter.isalpha():
            buffer[pos] = ch.upper()
        else:
             buffer[pos] = ch.lower()

        prev_letter = buffer[pos]

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
        next = _find(value, by, start, len(value), 1)
        #next = value.find(by, start)    #of course we cannot use 
                                         #the find method, 
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

def _convert_idx_params(space, w_self, w_sub, w_start, w_end):
    u = space.unwrap
    start = u(w_start)
    end = u(w_end)
    self = u(w_self)
    sub = u(w_sub)
    if start is None:
        start = 0
    if end is None:
        end = len(self)

    return (self, sub, start, end)


def str_find__String_String_ANY_ANY(space, w_self, w_sub, w_start=None, w_end=None):

    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = _find(self, sub, start, end, 1)
    return space.wrap(res)

def str_rfind__String_String_ANY_ANY(space, w_self, w_sub, w_start=None, w_end=None):

    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = _find(self, sub, start, end, -1)
    return space.wrap(res)

def str_index__String_String_ANY_ANY(space, w_self, w_sub, w_start=None, w_end=None):

    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = _find(self, sub, start, end, 1)

    if res == -1:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))

    return space.wrap(res)


def str_rindex__String_String_ANY_ANY(space, w_self, w_sub, w_start=None, w_end=None):

    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = _find(self, sub, start, end, -1)
    if res == -1:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return space.wrap(res)


def str_replace__String_String_String_Int(space, w_self, w_sub, w_by, w_maxsplit=-1):
    u = space.unwrap

    input = u(w_self)
    sub = u(w_sub)
    by = u(w_by)
    maxsplit = u(w_maxsplit)   #I don't use it now

    #print "from replace, input: %s, sub: %s, by: %s" % (input, sub, by)

    #what do we have to replace?
    startidx = 0
    endidx = len(input)
    indices = []
    foundidx = _find(input, sub, startidx, endidx, 1)
    while foundidx > -1 and (maxsplit == -1 or maxsplit > 0):
        indices.append(foundidx)
        if len(sub) == 0:
            #so that we go forward, even if sub is empty
            startidx = foundidx + 1
        else: 
            startidx = foundidx + len(sub)        
        foundidx = _find(input, sub, startidx, endidx, 1)
        if maxsplit != -1:
            maxsplit = maxsplit - 1
    indiceslen = len(indices)
    buf = [' '] * (len(input) - indiceslen * len(sub) + indiceslen * len(by))
    startidx = 0

    #ok, so do it
    bufpos = 0
    for i in range(indiceslen):
        for j in range(startidx, indices[i]):
            buf[bufpos] = input[j]
            bufpos = bufpos + 1
 
        for j in range(len(by)):
            buf[bufpos] = by[j]
            bufpos = bufpos + 1

        startidx = indices[i] + len(sub)

    for j in range(startidx, len(input)):
        buf[bufpos] = input[j]
        bufpos = bufpos + 1 
    return space.wrap("".join(buf))

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
            return end

        end = end - len(sub)

        for j in range(end, start-1, -1):
            match = 1
            for idx in range(len(sub)):
                if sub[idx] != self[idx+j]:
                    match = 0
                    break
            if match:
                return j
        return -1        


def _strip(space, w_self, w_chars, left, right):
    "internal function called by str_xstrip methods"
    u_self = space.unwrap(w_self)
    u_chars = space.unwrap(w_chars)
    
    if u_self == None or u_chars == None:
        return w_self
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        #print "while %d < %d and -%s- in -%s-:"%(lpos, rpos, u_self[lpos],w_chars)
        while lpos < rpos and u_self[lpos] in u_chars:
           lpos += 1
       
    if right:
        while rpos > 0 and u_self[rpos - 1] in u_chars:
           rpos -= 1
       
    return space.wrap(u_self[lpos:rpos])


def str_strip__String_String(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=1, right=1)

   
def str_rstrip__String_String(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=0, right=1)

   
def str_lstrip__String_String(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=1, right=0)
   

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
      
      
def str_count__String_String_ANY_ANY(space, w_self, w_arg, w_start, w_end): 
    u_self  = space.unwrap(w_self)
    u_arg   = space.unwrap(w_arg)
    u_start = space.unwrap(w_start)
    u_end   = space.unwrap(w_end)
    
    
    if u_end == None: 
        u_end = len(u_self)
    elif u_end < 0:
        u_end += len(u_self)
    
    if u_start == None: u_start = 0
    
    area =  u_self [u_start:u_end]
    
    count = 0  

    pos = -1
    while 1: 
       pos = _find(area, u_arg, pos+1, u_end, 1)
       #pos = area.find(u_arg, pos+1, u_end)
       if pos == -1:
          break
       count += 1
       
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
    
    
def _tabindent(u_token, u_tabsize):
    "calculates distance behind the token to the next tabstop"
    
    distance = u_tabsize
    if u_token:    
        distance = 0
        offset = len(u_token)

        while 1:
            #no sophisticated linebreak support now, '\r' just for passing adapted CPython test
            if u_token[offset-1] == "\n" or u_token[offset-1] == "\r":
                break;
            distance += 1
            offset -= 1
            if offset == 0:
                break
                
        #the same like distance = len(u_token) - (offset + 1)
        #print '<offset:%d distance:%d tabsize:%d token:%s>' % (offset, distance, u_tabsize, u_token)
        distance = (u_tabsize-distance) % u_tabsize
        if distance == 0:
            distance=u_tabsize

    return distance    
    
    
def str_expandtabs__String_Int(space, w_self, w_tabsize):   
    u_self = space.unwrap(w_self)
    u_tabsize  = space.unwrap(w_tabsize)
    
    u_expanded = ""
    if u_self:
        split = u_self.split("\t") #XXX use pypy split
        u_expanded =oldtoken = split.pop(0)

        for token in split:  
            #print  "%d#%d -%s-" % (_tabindent(oldtoken,u_tabsize), u_tabsize, token)
            u_expanded += " " * _tabindent(oldtoken,u_tabsize) + token
            oldtoken = token
            
    return W_StringObject(space, u_expanded)        
 
 
def str_splitlines__String_Int(space, w_self, w_keepends):
    u_self = space.unwrap(w_self)
    u_keepends  = space.unwrap(w_keepends)
    selflen = len(u_self)
    
    L = []
    pos = 0
    while 1:
        oldpos = pos
        pos = _find(u_self, '\n', pos, selflen, 1) + 1
        if pos  > oldpos:
            w_item = space.wrap(u_self[oldpos:pos])
            if not u_keepends:
                w_item = _strip(space, w_item, W_StringObject(space,'\n'), left=0, right=1)
            L.append(w_item)
        else:
            break    
    return W_ListObject(space, L)

def str_zfill__String_Int(space, w_self, w_width):
    u = space.unwrap
    input = u(w_self)
    width = u(w_width)

    if len(input) >= width:
        return w_self

    b = width - len(input)

    buf = [' '] * width
    if len(input) > 0 and (input[0] == '+' or input[0] == '-'):
        buf[0] = input[0]
        start = 1
        middle = width - len(input) + 1
    else:
        start = 0
        middle = width - len(input)

    for i in range(start, middle):
        buf[i] = '0'

    for i in range(middle, width):
        buf[i] = input[start]
        start = start + 1
    
    return space.wrap("".join(buf))
    
    
def app_str_translate__String_String_String(s, table, deletechars=''):
    """charfilter - unicode handling is not implemented
    
    Return a copy of the string where all characters occurring 
    in the optional argument deletechars are removed, and the 
    remaining characters have been mapped through the given translation table, 
    which must be a string of length 256"""

    if len(table) < 256:
        raise ValueError("translation table must be 256 characters long")

    L =  [ table[ord(s[i])] for i in range(len(s)) if s[i] not in deletechars ]
    return ''.join(L)

str_translate__String_String_String = gateway.app2interp(app_str_translate__String_String_String)

    
def unwrap__String(space, w_str):
    return w_str._value

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
    # XXX this is really too slow for slices with no step argument
    w = space.wrap
    length = len(w_str._value)
    start, stop, step, sl = slicetype.indices4(space, w_slice, length)
    r = [space.getitem(w_str, w(start + i*step)) for i in range(sl)]
    w_r = space.newlist(r)
    w_empty = space.newstring([])
    return str_join__String_ANY(space, w_empty, w_r)

def mul__String_Int(space, w_str, w_mul):
    u = space.unwrap
    input = u(w_str)
    mul = u(w_mul)

    buffer = [' '] * (mul*len(input))

    pos = 0
    for i in range(mul):
        for j in range(len(input)):
            buffer[pos] = input[j]
            pos = pos + 1

    return space.wrap("".join(buffer))

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
    # XXX implement me
    format = space.unwrap(w_format)
    args = space.unwrap(w_args)
    try:
        s = format % args
    except TypeError, e:
        raise OperationError(space.w_TypeError, space.wrap(str(e)))
    except ValueError, e:
        raise OperationError(space.w_ValueError, space.wrap(str(e)))
    return space.wrap(s)

def len__String(space, w_str):
    return space.wrap(len(space.unwrap(w_str)))

def str__String(space, w_str):
    return w_str


def iter__String(space, w_list):
    import iterobject
    return iterobject.W_SeqIterObject(space, w_list)


def app_repr__String(s):
    quote = "'"
    if quote in s and '"' not in s:
        quote = '"'

    repr = quote

    for c in s:
        if c == '\\' or c == quote: repr += '\\'+c
        elif c == '\t': repr += '\\t'
        elif c == '\r': repr += '\\r'
        elif c == '\n': repr += '\\n'
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            repr += '\\x'+"0123456789abcdef"[n>>4]+"0123456789abcdef"[n&0xF]
        else:
            repr += c

    repr += quote

    return repr

repr__String = gateway.app2interp(app_repr__String)

    
def ord__String(space, w_str):
    return space.wrap(ord(space.unwrap(w_str)))

def mod__String_ANY(space, w_str, w_item):
    return mod__String_Tuple(space, w_str, space.newtuple([w_item]))

def app_mod__String_ANY(format, values):
    pieces = []
    start = 0
    state = 0
    i = 0 
    index = -1
    len_format = len(format) 
    while i < len_format: 
        c = format[i]
        if state == 0:
            # just copy constant-pieces of the format
            if c=='%':
                pieces.append(format[start:i])
                state = 1
        else:
            if c=='%':
                pieces.append('%')
            else:
                if c == '(':
                    # read name 
                    j = format.find(')', i+1)
                    if j == -1:
                        raise ValueError, "incomplete format string"
                    if index >= 0:
                        raise TypeError, "format string mismatch"
                    name = format[i+1:j]
                    value = values[name]
                    index = -2 
                    i = j+1
                    c = format[i]
                else:
                    index += 1
                    if index < 0:
                        raise TypeError, "format string mismatch"
                    elif index == 0 and not isinstance(values, tuple):
                        values = tuple([values])
                    try:
                        value = values[index]
                    except IndexError:
                        raise TypeError, "not enough arguments for format string"
                 
                if c=='s':
                    pieces.append(str(value)) 
                elif c=='d':
                    pieces.append(str(int(value)))
                elif c=='x':
                    pieces.append(hex(int(value)))
                elif c=='r':
                    pieces.append(repr(value))
                else:
                    raise ValueError, "unsupported format character '%s' (%x) at index %d" % (
                            c, ord(c), i)
            state = 0
            start = i+1
        i += 1

    if state == 1:
        raise ValueError, "incomplete format"
    if index >= 0 and index < len(values) - 1:
        raise TypeError, 'not all arguments converted during string formatting'
    pieces.append(format[start:])
    return ''.join(pieces)

mod__String_ANY = gateway.app2interp(app_mod__String_ANY) 

# register all methods 
register_all(vars(), W_StringType)


