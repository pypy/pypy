# -*- coding: latin-1 -*-

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.rlib.rarithmetic import ovfcheck, _hash_string
from pypy.rlib.objectmodel import we_are_translated
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std import slicetype
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.rlib.rstring import StringBuilder

from pypy.objspace.std.stringtype import sliced, joined, wrapstr, wrapchar, \
     stringendswith, stringstartswith, joined2

from pypy.objspace.std.formatting import mod_format

class W_StringObject(W_Object):
    from pypy.objspace.std.stringtype import str_typedef as typedef

    _immutable_ = True
    def __init__(w_self, str):
        w_self._value = str

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self, space):
        return w_self._value

registerimplementation(W_StringObject)

W_StringObject.EMPTY = W_StringObject('')
W_StringObject.PREBUILT = [W_StringObject(chr(i)) for i in range(256)]
del i

def _decode_ascii(space, s):
    try:
        return s.decode("ascii")
    except UnicodeDecodeError:
        for i in range(len(s)):
            if ord(s[i]) > 127:
                raise OperationError(
                    space.w_UnicodeDecodeError,
                    space.newtuple([
                    space.wrap('ascii'),
                    space.wrap(s),
                    space.wrap(i),
                    space.wrap(i+1),
                    space.wrap("ordinal not in range(128)")]))

def unicode_w__String(space, w_self):
    # XXX should this use the default encoding?
    return _decode_ascii(space, w_self._value)

def _is_generic(space, w_self, fun): 
    v = w_self._value
    if len(v) == 0:
        return space.w_False
    if len(v) == 1:
        c = v[0]
        return space.newbool(fun(c))
    else:
        for idx in range(len(v)):
            if not fun(v[idx]):
                return space.w_False
        return space.w_True
_is_generic._annspecialcase_ = "specialize:arg(2)"

def _upper(ch):
    if ch.islower():
        o = ord(ch) - 32
        return chr(o)
    else:
        return ch
    
def _lower(ch):
    if ch.isupper():
        o = ord(ch) + 32
        return chr(o)
    else:
        return ch

_isspace = lambda c: c.isspace()
_isdigit = lambda c: c.isdigit()
_isalpha = lambda c: c.isalpha()
_isalnum = lambda c: c.isalnum()

def str_isspace__String(space, w_self):
    return _is_generic(space, w_self, _isspace)

def str_isdigit__String(space, w_self):
    return _is_generic(space, w_self, _isdigit)

def str_isalpha__String(space, w_self):
    return _is_generic(space, w_self, _isalpha)

def str_isalnum__String(space, w_self):
    return _is_generic(space, w_self, _isalnum)

def str_isupper__String(space, w_self):
    """Return True if all cased characters in S are uppercase and there is
at least one cased character in S, False otherwise."""
    v = w_self._value
    if len(v) == 1:
        c = v[0]
        return space.newbool(c.isupper())
    cased = False
    for idx in range(len(v)):
        if v[idx].islower():
            return space.w_False
        elif not cased and v[idx].isupper():
            cased = True
    return space.newbool(cased)

def str_islower__String(space, w_self):
    """Return True if all cased characters in S are lowercase and there is
at least one cased character in S, False otherwise."""
    v = w_self._value
    if len(v) == 1:
        c = v[0]
        return space.newbool(c.islower())
    cased = False
    for idx in range(len(v)):
        if v[idx].isupper():
            return space.w_False
        elif not cased and v[idx].islower():
            cased = True
    return space.newbool(cased)

def str_istitle__String(space, w_self):
    """Return True if S is a titlecased string and there is at least one
character in S, i.e. uppercase characters may only follow uncased
characters and lowercase characters only cased ones. Return False
otherwise."""
    input = w_self._value
    cased = False
    previous_is_cased = False

    for pos in range(0, len(input)):
        ch = input[pos]
        if ch.isupper():
            if previous_is_cased:
                return space.w_False
            previous_is_cased = True
            cased = True
        elif ch.islower():
            if not previous_is_cased:
                return space.w_False
            cased = True
        else:
            previous_is_cased = False

    return space.newbool(cased)

def str_upper__String(space, w_self):
    self = w_self._value
    res = [' '] * len(self)
    for i in range(len(self)):
        ch = self[i]
        res[i] = _upper(ch)

    return space.wrap("".join(res))

def str_lower__String(space, w_self):
    self = w_self._value
    res = [' '] * len(self)
    for i in range(len(self)):
        ch = self[i]
        res[i] = _lower(ch)

    return space.wrap("".join(res))

def str_swapcase__String(space, w_self):
    self = w_self._value
    res = [' '] * len(self)
    for i in range(len(self)):
        ch = self[i]
        if ch.isupper():
            o = ord(ch) + 32
            res[i] = chr(o)
        elif ch.islower():
            o = ord(ch) - 32
            res[i] = chr(o)
        else:
            res[i] = ch

    return space.wrap("".join(res))

    
def str_capitalize__String(space, w_self):
    input = w_self._value
    buffer = [' '] * len(input)
    if len(input) > 0:
        ch = input[0]
        if ch.islower():
            o = ord(ch) - 32
            buffer[0] = chr(o)
        else:
            buffer[0] = ch

        for i in range(1, len(input)):
            ch = input[i]
            if ch.isupper():
                o = ord(ch) + 32
                buffer[i] = chr(o)
            else:
                buffer[i] = ch

    return space.wrap("".join(buffer))
         
def str_title__String(space, w_self):
    input = w_self._value
    buffer = [' '] * len(input)
    prev_letter=' '

    for pos in range(0, len(input)):
        ch = input[pos]
        if not prev_letter.isalpha():
            buffer[pos] = _upper(ch)
        else:
            buffer[pos] = _lower(ch)

        prev_letter = buffer[pos]

    return space.wrap("".join(buffer))

def str_split__String_None_ANY(space, w_self, w_none, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._value
    length = len(value)
    i = 0
    while True:
        # find the beginning of the next word
        while i < length:
            if not value[i].isspace():
                break   # found
            i += 1
        else:
            break  # end of string, finished

        # find the end of the word
        if maxsplit == 0:
            j = length   # take all the rest of the string
        else:
            j = i + 1
            while j < length and not value[j].isspace():
                j += 1
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        # the word is value[i:j]
        res_w.append(sliced(space, value, i, j))

        # continue to look from the character following the space after the word
        i = j + 1

    return space.newlist(res_w)


def str_split__String_String_ANY(space, w_self, w_by, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    start = 0
    value = w_self._value
    by = w_by._value
    bylen = len(by)
    if bylen == 0:
        raise OperationError(space.w_ValueError, space.wrap("empty separator"))

    while maxsplit != 0:
        next = value.find(by, start)
        if next < 0:
            break
        res_w.append(sliced(space, value, start, next))
        start = next + bylen
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res_w.append(sliced(space, value, start, len(value)))

    return space.newlist(res_w)

def str_rsplit__String_None_ANY(space, w_self, w_none, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._value
    i = len(value)-1
    while True:
        # starting from the end, find the end of the next word
        while i >= 0:
            if not value[i].isspace():
                break   # found
            i -= 1
        else:
            break  # end of string, finished

        # find the start of the word
        # (more precisely, 'j' will be the space character before the word)
        if maxsplit == 0:
            j = -1   # take all the rest of the string
        else:
            j = i - 1
            while j >= 0 and not value[j].isspace():
                j -= 1
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        # the word is value[j+1:i+1]
        j1 = j + 1
        assert j1 >= 0
        res_w.append(sliced(space, value, j1, i+1))

        # continue to look from the character before the space before the word
        i = j - 1

    res_w.reverse()
    return space.newlist(res_w)

def str_rsplit__String_String_ANY(space, w_self, w_by, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._value
    end = len(value)
    by = w_by._value
    bylen = len(by)
    if bylen == 0:
        raise OperationError(space.w_ValueError, space.wrap("empty separator"))

    while maxsplit != 0:
        next = value.rfind(by, 0, end)
        if next < 0:
            break
        res_w.append(sliced(space, value, next+bylen, end))
        end = next
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res_w.append(sliced(space, value, 0, end))
    res_w.reverse()
    return space.newlist(res_w)

def str_join__String_ANY(space, w_self, w_list):
    list_w = space.unpackiterable(w_list)
    str_w = space.str_w
    if list_w:
        self = w_self._value
        listlen = 0
        reslen = 0
        l = []
        for i in range(len(list_w)):
            w_s = list_w[i]
            if not space.is_true(space.isinstance(w_s, space.w_str)):
                if space.is_true(space.isinstance(w_s, space.w_unicode)):
                    w_u = space.call_function(space.w_unicode, w_self)
                    return space.call_method(w_u, "join", space.newlist(list_w))
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("sequence item %d: expected string, %s "
                               "found" % (i,
                                          space.type(w_s).getname(space, '?'))))
            l.append(space.str_w(w_s))
        return space.wrap(self.join(l))
    else:
        return W_StringObject.EMPTY

def str_rjust__String_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_arg = space.int_w(w_arg)
    u_self = w_self._value
    fillchar = space.str_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("rjust() argument 2 must be a single character"))
    
    d = u_arg - len(u_self)
    if d>0:
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_self = d * fillchar + u_self
        
    return space.wrap(u_self)


def str_ljust__String_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_self = w_self._value
    u_arg = space.int_w(w_arg)
    fillchar = space.str_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("ljust() argument 2 must be a single character"))

    d = u_arg - len(u_self)
    if d>0:
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_self += d * fillchar
        
    return space.wrap(u_self)

def _convert_idx_params(space, w_self, w_sub, w_start, w_end):
    self = w_self._value
    sub = w_sub._value
    start = slicetype.adapt_bound(space, len(self), w_start)
    end = slicetype.adapt_bound(space, len(self), w_end)

    assert start >= 0
    assert end >= 0

    return (self, sub, start, end)

def contains__String_String(space, w_self, w_sub):
    self = w_self._value
    sub = w_sub._value
    return space.newbool(self.find(sub) >= 0)

def str_find__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.find(sub, start, end)
    return space.wrap(res)

def str_rfind__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.rfind(sub, start, end)
    return space.wrap(res)

def str_partition__String_String(space, w_self, w_sub):
    self = w_self._value
    sub = w_sub._value
    if not sub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = self.find(sub)
    if pos == -1:
        return space.newtuple([w_self, space.wrap(''), space.wrap('')])
    else:
        return space.newtuple([sliced(space, self, 0, pos),
                               w_sub,
                               sliced(space, self, pos+len(sub), len(self))])

def str_rpartition__String_String(space, w_self, w_sub):
    self = w_self._value
    sub = w_sub._value
    if not sub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = self.rfind(sub)
    if pos == -1:
        return space.newtuple([space.wrap(''), space.wrap(''), w_self])
    else:
        return space.newtuple([sliced(space, self, 0, pos),
                               w_sub,
                               sliced(space, self, pos+len(sub), len(self))])


def str_index__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.find(sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))

    return space.wrap(res)


def str_rindex__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.rfind(sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return space.wrap(res)


def str_replace__String_String_String_ANY(space, w_self, w_sub, w_by, w_maxsplit=-1):
    input = w_self._value
    sub = w_sub._value
    by = w_by._value
    maxsplit = space.int_w(w_maxsplit)
    if maxsplit == 0:
        return space.wrap(input)

    #print "from replace, input: %s, sub: %s, by: %s" % (input, sub, by)

    if not sub:
        upper = len(input)
        if maxsplit > 0 and maxsplit < upper + 2:
            upper = maxsplit - 1
            assert upper >= 0
        substrings = [""]
        for i in range(upper):
            c = input[i]
            substrings.append(c)
        substrings.append(input[upper:])
        return space.wrap(by.join(substrings))
    startidx = 0
    substrings = []
    foundidx = input.find(sub, startidx)
    while foundidx >= 0 and maxsplit != 0:
        substrings.append(input[startidx:foundidx])
        startidx = foundidx + len(sub)        
        foundidx = input.find(sub, startidx)
        maxsplit = maxsplit - 1
    substrings.append(input[startidx:])
    return space.wrap(by.join(substrings))

def _strip(space, w_self, w_chars, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    u_chars = w_chars._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        #print "while %d < %d and -%s- in -%s-:"%(lpos, rpos, u_self[lpos],w_chars)
        while lpos < rpos and u_self[lpos] in u_chars:
           lpos += 1
       
    if right:
        while rpos > lpos and u_self[rpos - 1] in u_chars:
           rpos -= 1
       
    assert rpos >= lpos    # annotator hint, don't remove
    return sliced(space, u_self, lpos, rpos)

def _strip_none(space, w_self, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        #print "while %d < %d and -%s- in -%s-:"%(lpos, rpos, u_self[lpos],w_chars)
        while lpos < rpos and u_self[lpos].isspace():
           lpos += 1
       
    if right:
        while rpos > lpos and u_self[rpos - 1].isspace():
           rpos -= 1
       
    assert rpos >= lpos    # annotator hint, don't remove
    return sliced(space, u_self, lpos, rpos)

def str_strip__String_String(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=1, right=1)

def str_strip__String_None(space, w_self, w_chars):
    return _strip_none(space, w_self, left=1, right=1)
   
def str_rstrip__String_String(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=0, right=1)

def str_rstrip__String_None(space, w_self, w_chars):
    return _strip_none(space, w_self, left=0, right=1)

   
def str_lstrip__String_String(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, left=1, right=0)

def str_lstrip__String_None(space, w_self, w_chars):
    return _strip_none(space, w_self, left=1, right=0)



def str_center__String_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_self = w_self._value
    u_arg  = space.int_w(w_arg)
    fillchar = space.str_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("center() argument 2 must be a single character"))

    d = u_arg - len(u_self) 
    if d>0:
        offset = d//2
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_centered = offset * fillchar + u_self + (d - offset) * fillchar
    else:
        u_centered = u_self

    return wrapstr(space, u_centered)

def str_count__String_String_ANY_ANY(space, w_self, w_arg, w_start, w_end): 
    u_self, u_arg, u_start, u_end = _convert_idx_params(space, w_self, w_arg,
                                                        w_start, w_end)
    return wrapint(space, u_self.count(u_arg, u_start, u_end))

def str_endswith__String_String_ANY_ANY(space, w_self, w_suffix, w_start, w_end):
    (u_self, suffix, start, end) = _convert_idx_params(space, w_self,
                                                       w_suffix, w_start, w_end)
    return space.newbool(stringendswith(u_self, suffix, start, end))

def str_endswith__String_Tuple_ANY_ANY(space, w_self, w_suffixes, w_start, w_end):
    (u_self, _, start, end) = _convert_idx_params(space, w_self,
                                                  space.wrap(''), w_start, w_end)
    for w_suffix in space.viewiterable(w_suffixes):
        if space.is_true(space.isinstance(w_suffix, space.w_unicode)):
            w_u = space.call_function(space.w_unicode, w_self)
            return space.call_method(w_u, "endswith", w_suffixes, w_start,
                                     w_end)
        suffix = space.str_w(w_suffix) 
        if stringendswith(u_self, suffix, start, end):
            return space.w_True
    return space.w_False

def str_startswith__String_String_ANY_ANY(space, w_self, w_prefix, w_start, w_end):
    (u_self, prefix, start, end) = _convert_idx_params(space, w_self,
                                                       w_prefix, w_start, w_end)
    return space.newbool(stringstartswith(u_self, prefix, start, end))

def str_startswith__String_Tuple_ANY_ANY(space, w_self, w_prefixes, w_start, w_end):
    (u_self, _, start, end) = _convert_idx_params(space, w_self, space.wrap(''),
                                                  w_start, w_end)
    for w_prefix in space.viewiterable(w_prefixes):
        if space.is_true(space.isinstance(w_prefix, space.w_unicode)):
            w_u = space.call_function(space.w_unicode, w_self)
            return space.call_method(w_u, "startswith", w_prefixes, w_start,
                                     w_end)
        prefix = space.str_w(w_prefix)
        if stringstartswith(u_self, prefix, start, end):
            return space.w_True
    return space.w_False
    
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
    
    
def str_expandtabs__String_ANY(space, w_self, w_tabsize):   
    u_self = w_self._value
    u_tabsize  = space.int_w(w_tabsize)
    
    u_expanded = ""
    if u_self:
        split = u_self.split("\t") #XXX use pypy split
        u_expanded =oldtoken = split.pop(0)

        for token in split:  
            #print  "%d#%d -%s-" % (_tabindent(oldtoken,u_tabsize), u_tabsize, token)
            u_expanded += " " * _tabindent(oldtoken,u_tabsize) + token
            oldtoken = token
            
    return wrapstr(space, u_expanded)        
 
 
def str_splitlines__String_ANY(space, w_self, w_keepends):
    data = w_self._value
    u_keepends  = space.int_w(w_keepends)  # truth value, but type checked
    selflen = len(data)
    
    strs_w = []
    i = j = 0
    while i < selflen:
        # Find a line and append it
        while i < selflen and data[i] != '\n' and data[i] != '\r':
            i += 1
        # Skip the line break reading CRLF as one line break
        eol = i
        i += 1
        if i < selflen and data[i-1] == '\r' and data[i] == '\n':
            i += 1
        if u_keepends:
            eol = i
        strs_w.append(sliced(space, data, j, eol))
        j = i

    if j < selflen:
        strs_w.append(sliced(space, data, j, len(data)))

    return space.newlist(strs_w)

def str_zfill__String_ANY(space, w_self, w_width):
    input = w_self._value
    width = space.int_w(w_width)

    if len(input) >= width:
        # cannot return w_self, in case it is a subclass of str
        return space.wrap(input)

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

def str_w__String(space, w_str):
    return w_str._value

def hash__String(space, w_str):
    s = w_str._value
    if we_are_translated():
        x = hash(s)            # to use the hash cache in rpython strings
    else:
        x = _hash_string(s)    # to make sure we get the same hash as rpython
        # (otherwise translation will freeze W_DictObjects where we can't find
        #  the keys any more!)
    return wrapint(space, x)

def lt__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 < s2:
        return space.w_True
    else:
        return space.w_False    

def le__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 <= s2:
        return space.w_True
    else:
        return space.w_False

def eq__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 == s2:
        return space.w_True
    else:
        return space.w_False

def ne__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 != s2:
        return space.w_True
    else:
        return space.w_False

def gt__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 > s2:
        return space.w_True
    else:
        return space.w_False

def ge__String_String(space, w_str1, w_str2):
    s1 = w_str1._value
    s2 = w_str2._value
    if s1 >= s2:
        return space.w_True
    else:
        return space.w_False

def getitem__String_ANY(space, w_str, w_index):
    ival = space.getindex_w(w_index, space.w_IndexError, "string index")
    str = w_str._value
    slen = len(str)
    if ival < 0:
        ival += slen
    if ival < 0 or ival >= slen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("string index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return wrapchar(space, str[ival])

def getitem__String_Slice(space, w_str, w_slice):
    w = space.wrap
    s = w_str._value
    length = len(s)
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        return W_StringObject.EMPTY
    elif step == 1:
        assert start >= 0 and stop >= 0
        return sliced(space, s, start, stop)
    else:
        str = "".join([s[start + i*step] for i in range(sl)])
    return wrapstr(space, str)

def mul_string_times(space, w_str, w_times):
    try:
        mul = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if mul <= 0:
        return W_StringObject.EMPTY
    input = w_str._value
    input_len = len(input)
    try:
        buflen = ovfcheck(mul * input_len)
    except OverflowError:
        raise OperationError(
            space.w_OverflowError, 
            space.wrap("repeated string is too long: %d %d" % (input_len, mul)))
    # XXX maybe only do this when input has a big length
    return joined(space, [input] * mul)

def mul__String_ANY(space, w_str, w_times):
    return mul_string_times(space, w_str, w_times)

def mul__ANY_String(space, w_times, w_str):
    return mul_string_times(space, w_str, w_times)

def add__String_String(space, w_left, w_right):
    right = w_right._value
    left = w_left._value
    return joined2(space, left, right)

def len__String(space, w_str):
    return space.wrap(len(w_str._value))

def str__String(space, w_str):
    if type(w_str) is W_StringObject:
        return w_str
    return wrapstr(space, w_str._value)

def iter__String(space, w_list):
    from pypy.objspace.std import iterobject
    return iterobject.W_SeqIterObject(w_list)

def ord__String(space, w_str):
    u_str = w_str._value
    if len(u_str) != 1:
        raise OperationError(
            space.w_TypeError,
            space.wrap("ord() expected a character, but string "
                       "of length %d found"%(len(w_str._value),)))
    return space.wrap(ord(u_str))

def getnewargs__String(space, w_str):
    return space.newtuple([wrapstr(space, w_str._value)])

def repr__String(space, w_str):
    s = w_str._value

    buf = StringBuilder(50)

    quote = "'"
    if quote in s and '"' not in s:
        quote = '"'

    buf.append(quote)
    startslice = 0

    for i in range(len(s)):
        c = s[i]
        use_bs_char = False # character quoted by backspace

        if c == '\\' or c == quote:
            bs_char = c
            use_bs_char = True
        elif c == '\t':
            bs_char = 't'
            use_bs_char = True
        elif c == '\r':
            bs_char = 'r'
            use_bs_char = True
        elif c == '\n':
            bs_char = 'n'
            use_bs_char = True
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\x')
            buf.append("0123456789abcdef"[n>>4])
            buf.append("0123456789abcdef"[n&0xF])

        if use_bs_char:
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\')
            buf.append(bs_char)

    if len(s) != startslice:
        buf.append_slice(s, startslice, len(s))

    buf.append(quote)

    return space.wrap(buf.build())

   
def str_translate__String_ANY_ANY(space, w_string, w_table, w_deletechars=''):
    """charfilter - unicode handling is not implemented
    
    Return a copy of the string where all characters occurring 
    in the optional argument deletechars are removed, and the 
    remaining characters have been mapped through the given translation table, 
    which must be a string of length 256"""

    # XXX CPython accepts buffers, too, not sure what we should do
    table = space.str_w(w_table)
    if len(table) != 256:
        raise OperationError(
            space.w_ValueError,
            space.wrap("translation table must be 256 characters long"))

    string = w_string._value
    chars = []
    for char in string:
        w_char = W_StringObject.PREBUILT[ord(char)]
        if not space.is_true(space.contains(w_deletechars, w_char)):
             chars.append(table[ord(char)])
    return W_StringObject(''.join(chars))

def str_decode__String_ANY_ANY(space, w_string, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodetype import _get_encoding_and_errors, \
        unicode_from_string, decode_object
    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    if encoding is None and errors is None:
        return unicode_from_string(space, w_string)
    return decode_object(space, w_string, encoding, errors)

def str_encode__String_ANY_ANY(space, w_string, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodetype import _get_encoding_and_errors, \
        encode_object
    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    return encode_object(space, w_string, encoding, errors)

# CPython's logic for deciding if  ""%values  is
# an error (1 value, 0 %-formatters) or not
# (values is of a mapping type)
def mod__String_ANY(space, w_format, w_values):
    return mod_format(space, w_format, w_values, do_unicode=False)

def buffer__String(space, w_string):
    from pypy.interpreter.buffer import StringBuffer
    return space.wrap(StringBuffer(w_string._value))

# register all methods
from pypy.objspace.std import stringtype
register_all(vars(), stringtype)
