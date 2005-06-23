from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std import slicetype
from pypy.objspace.std.strutil import string_to_int, string_to_long, ParseStringError
from pypy.rpython.rarithmetic import intmask
from pypy.module.unicodedata import unicodedb

class W_UnicodeObject(W_Object):
    from pypy.objspace.std.unicodetype import unicode_typedef as typedef

    def __init__(w_self, space, unicodechars):
        W_Object.__init__(w_self, space)
        w_self._value = unicodechars
        if len(unicodechars) == 0:
            w_self.w_hash = space.wrap(0)
        else:
            w_self.w_hash = None
    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self):
        # For faked functions taking unicodearguments.
        # Remove when we no longer need faking.
        return u''.join(w_self._value)

registerimplementation(W_UnicodeObject)

# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected unicode"))
    unistr = w_unistr._value
    result = ['\0'] * len(unistr)
    digits = [ '0', '1', '2', '3', '4',
               '5', '6', '7', '8', '9']
    for i in xrange(len(unistr)):
        uchr = ord(unistr[i])
        if unicodedb.isspace(uchr):
            result[i] = ' '
            continue
        try:
            result[i] = digits[unicodedb.decimal(uchr)]
        except KeyError:
            if 0 < uchr < 256:
                result[i] = chr(uchr)
            else:
                raise OperationError(space.w_UnicodeEncodeError, space.wrap('invalid decimal Unicode string'))
    return ''.join(result)

# string-to-unicode delegation
def delegate_String2Unicode(w_str):
    space = w_str.space
    w_uni =  space.call_function(space.w_unicode, w_str)
    assert isinstance(w_uni, W_UnicodeObject) # help the annotator!
    return w_uni

def str_w__Unicode(space, w_uni):
    return space.str_w(space.str(w_uni))

def repr__Unicode(space, w_uni):
    return space.wrap(repr(u''.join(w_uni._value)))

def str__Unicode(space, w_uni):
    return space.call_method(w_uni, 'encode')

def cmp__Unicode_Unicode(space, w_left, w_right):
    left = w_left._value
    right = w_right._value
    for i in range(min(len(left), len(right))):
        test = ord(left[i]) - ord(right[i])
        if test < 0:
            return space.wrap(-1)
        if test > 0:
            return space.wrap(1)
            
    test = len(left) - len(right)
    if test < 0:
        return space.wrap(-1)
    if test > 0:
        return space.wrap(1)
    return space.wrap(0)

def cmp__Unicode_ANY(space, w_left, w_right):
    try:
        w_right = space.call_function(space.w_unicode, w_right)
    except:
        return space.wrap(1)
    return space.cmp(w_left, w_right)

def ord__Unicode(space, w_uni):
    if len(w_uni._value) != 1:
        raise OperationError(space.w_TypeError, space.wrap('ord() expected a character'))
    return space.wrap(ord(w_uni._value[0]))

def add__Unicode_Unicode(space, w_left, w_right):
    left = w_left._value
    right = w_right._value
    leftlen = len(left)
    rightlen = len(right)
    result = [u'\0'] * (leftlen + rightlen)
    for i in range(leftlen):
        result[i] = left[i]
    for i in range(rightlen):
        result[i + leftlen] = right[i]
    return W_UnicodeObject(space, result)

def add__String_Unicode(space, w_left, w_right):
    return space.add(space.call_function(space.w_unicode, w_left) , w_right)

def add__Unicode_String(space, w_left, w_right):
    return space.add(w_left, space.call_function(space.w_unicode, w_right))

def contains__String_Unicode(space, w_container, w_item):
    return space.contains(space.call_function(space.w_unicode, w_container), w_item )

def _find(self, sub, start, end):
    if len(sub) == 0:
        return start
    if start >= end:
        return -1
    for i in range(start, end - len(sub) + 1):
        for j in range(len(sub)):
            if self[i + j]  != sub[j]:
                break
        else:
            return i
    return -1

def _rfind(self, sub, start, end):
    if len(sub) == 0:
        return end
    if end - start < len(sub):
        return -1
    for i in range(end - len(sub), start - 1, -1):
        for j in range(len(sub)):
            if self[i + j]  != sub[j]:
                break
        else:
            return i
    return -1

def contains__Unicode_Unicode(space, w_container, w_item):
    item = w_item._value
    container = w_container._value
    return space.newbool(_find(container, item, 0, len(container)) >= 0)

def unicode_join__Unicode_ANY(space, w_self, w_list):
    list = space.unpackiterable(w_list)
    delim = w_self._value
    totlen = 0
    if len(list) == 0:
        return W_UnicodeObject(space, [])
    values_list = [None] * len(list)
    values_list[0] = [u'\0']
    for i in range(len(list)):
        item = list[i]
        if space.is_true(space.isinstance(item, space.w_unicode)):
            pass
        elif space.is_true(space.isinstance(item, space.w_str)):
            item = space.call_function(space.w_unicode, item)
        else:
            w_msg = space.mod(space.wrap('sequence item %d: expected string or Unicode'),
                              space.wrap(i))
            raise OperationError(space.w_TypeError, w_msg)
        assert isinstance(item, W_UnicodeObject)
        item = item._value
        totlen += len(item)
        values_list[i] = item
    totlen += len(delim) * (len(values_list) - 1)
    if len(values_list) == 1:
        return W_UnicodeObject(space, values_list[0])
    # Allocate result
    result = [u'\0'] * totlen
    first = values_list[0]
    for i in range(len(first)):
        result[i] = first[i]
    offset = len(first)
    for i in range(1, len(values_list)):
        item = values_list[i]
        # Add delimiter
        for j in range(len(delim)):
            result[offset + j] = delim[j]
        offset += len(delim)
        # Add item from values_list
        for j in range(len(item)):
            result[offset + j] = item[j]
        offset += len(item)
    return W_UnicodeObject(space, result)


def hash__Unicode(space, w_uni):
    if w_uni.w_hash is None:
        chars = w_uni._value
        x = ord(chars[0]) << 7
        for c in chars:
            x = intmask((1000003 * x) ^ ord(c))
        h = intmask(x ^ len(chars))
        if h == -1:
            h = -2
        w_uni.w_hash = space.wrap(h)
    return w_uni.w_hash

def len__Unicode(space, w_uni):
    return space.wrap(len(w_uni._value))

def getitem__Unicode_ANY(space, w_uni, w_index):
    ival = space.int_w(w_index)
    uni = w_uni._value
    ulen = len(uni)
    if ival < 0:
        ival += ulen
    if ival < 0 or ival >= ulen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("unicode index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return W_UnicodeObject(space, [uni[ival]])

def getitem__Unicode_Slice(space, w_uni, w_slice):
    uni = w_uni._value
    length = len(uni)
    start, stop, step, sl = slicetype.indices4(space, w_slice, length)
    r = [uni[start + i*step] for i in range(sl)]
    return W_UnicodeObject(space, r)

def unicode_getslice__Unicode_ANY_ANY(space, w_uni, w_start, w_end):
    w_slice = space.call_function(space.w_slice, w_start, w_end)
    uni = w_uni._value
    length = len(uni)
    start, stop, step, sl = slicetype.indices4(space, w_slice, length)
    return W_UnicodeObject(space, uni[start:stop])

def mul__Unicode_ANY(space, w_uni, w_times):
    chars = w_uni._value
    charlen = len(chars)
    times = space.int_w(w_times)
    if times <= 0 or charlen == 0:
        return W_UnicodeObject(space, [])
    if times == 1:
        return space.call_function(space.w_unicode, w_uni)
    if charlen == 1:
        return W_UnicodeObject(space, [w_uni._value[0]] * times)

    try:
        result = [u'\0'] * (charlen * times)
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap('repeated string is too long'))
    for i in range(times):
        offset = i * charlen
        for j in range(charlen):
            result[offset + j] = chars[j]
    return W_UnicodeObject(space, result)

def mul__ANY_Unicode(space, w_times, w_uni):
    return space.mul(w_uni, w_times)

def _isspace(uchar):
    return unicodedb.isspace(ord(uchar))

def unicode_isspace__Unicode(space, w_unicode):
    if len(w_unicode._value) == 0:
        return space.w_False
    for uchar in w_unicode._value:
        if not unicodedb.isspace(ord(uchar)):
            return space.w_False
    return space.w_True

def unicode_isalpha__Unicode(space, w_unicode):
    if len(w_unicode._value) == 0:
        return space.w_False
    for uchar in w_unicode._value:
        if not unicodedb.isalpha(ord(uchar)):
            return space.w_False
    return space.w_True

def unicode_isalnum__Unicode(space, w_unicode):
    if len(w_unicode._value) == 0:
        return space.w_False
    for uchar in w_unicode._value:
        if not (unicodedb.isalpha(ord(uchar)) or
                unicodedb.isnumeric(ord(uchar))):
            return space.w_False
    return space.w_True

def unicode_isdecimal__Unicode(space, w_unicode):
    if len(w_unicode._value) == 0:
        return space.w_False
    for uchar in w_unicode._value:
        if not unicodedb.isdecimal(ord(uchar)):
            return space.w_False
    return space.w_True

def unicode_isdigit__Unicode(space, w_unicode):
    if len(w_unicode._value) == 0:
        return space.w_False
    for uchar in w_unicode._value:
        if not unicodedb.isdigit(ord(uchar)):
            return space.w_False
    return space.w_True

def unicode_isnumeric__Unicode(space, w_unicode):
    if len(w_unicode._value) == 0:
        return space.w_False
    for uchar in w_unicode._value:
        if not unicodedb.isnumeric(ord(uchar)):
            return space.w_False
    return space.w_True

def unicode_islower__Unicode(space, w_unicode):
    cased = False
    for uchar in w_unicode._value:
        if (unicodedb.isupper(ord(uchar)) or
            unicodedb.istitle(ord(uchar))):
            return space.w_False
        if not cased and unicodedb.islower(ord(uchar)):
            cased = True
    return space.newbool(cased)

def unicode_isupper__Unicode(space, w_unicode):
    cased = False
    for uchar in w_unicode._value:
        if (unicodedb.islower(ord(uchar)) or
            unicodedb.istitle(ord(uchar))):
            return space.w_False
        if not cased and unicodedb.isupper(ord(uchar)):
            cased = True
    return space.newbool(cased)

def unicode_istitle__Unicode(space, w_unicode):
    cased = False
    previous_is_cased = False
    for uchar in w_unicode._value:
        if (unicodedb.isupper(ord(uchar)) or
            unicodedb.istitle(ord(uchar))):
            if previous_is_cased:
                return space.w_False
            previous_is_cased = cased = True
        elif unicodedb.islower(ord(uchar)):
            if not previous_is_cased:
                return space.w_False
            previous_is_cased = cased = True
        else:
            previous_is_cased = False
    return space.newbool(cased)

def _strip(space, w_self, w_chars, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    u_chars = w_chars._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        while lpos < rpos and u_self[lpos] in u_chars:
           lpos += 1
       
    if right:
        while rpos > lpos and u_self[rpos - 1] in u_chars:
           rpos -= 1
           
    result = [u'\0'] * (rpos - lpos)
    for i in range(rpos - lpos):
        result[i] = u_self[lpos + i]
    return W_UnicodeObject(space, result)

def _strip_none(space, w_self, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        while lpos < rpos and _isspace(u_self[lpos]):
           lpos += 1
       
    if right:
        while rpos > lpos and _isspace(u_self[rpos - 1]):
           rpos -= 1
       
    result = [u'\0'] * (rpos - lpos)
    for i in range(rpos - lpos):
        result[i] = u_self[lpos + i]
    return W_UnicodeObject(space, result)

def unicode_strip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 1)
def unicode_strip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 1)
def unicode_strip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'strip',
                             space.call_function(space.w_unicode, w_chars))

def unicode_lstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 0)
def unicode_lstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 0)
def unicode_lstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'lstrip',
                             space.call_function(space.w_unicode, w_chars))

def unicode_rstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 0, 1)
def unicode_rstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 0, 1)
def unicode_rstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'rstrip',
                             space.call_function(space.w_unicode, w_chars))

def unicode_capitalize__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return W_UnicodeObject(space, [])
    result = [u'\0'] * len(input)
    result[0] = unichr(unicodedb.toupper(ord(input[0])))
    for i in range(1, len(input)):
        result[i] = unichr(unicodedb.tolower(ord(input[i])))
    return W_UnicodeObject(space, result)

def unicode_title__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return w_self
    result = [u'\0'] * len(input)

    previous_is_cased = 0
    for i in range(len(input)):
        unichar = ord(input[i])
        if previous_is_cased:
            result[i] = unichr(unicodedb.tolower(unichar))
        else:
            result[i] = unichr(unicodedb.totitle(unichar))
        previous_is_cased = unicodedb.iscased(unichar)
    return W_UnicodeObject(space, result)

def unicode_lower__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        result[i] = unichr(unicodedb.tolower(ord(input[i])))
    return W_UnicodeObject(space, result)

def unicode_upper__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        result[i] = unichr(unicodedb.toupper(ord(input[i])))
    return W_UnicodeObject(space, result)

def unicode_swapcase__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        unichar = ord(input[i])
        if unicodedb.islower(unichar):
            result[i] = unichr(unicodedb.toupper(unichar))
        elif unicodedb.isupper(unichar):
            result[i] = unichr(unicodedb.tolower(unichar))
        else:
            result[i] = input[i]
    return W_UnicodeObject(space, result)

def _normalize_index(length, index):
    if index < 0:
        index += length
        if index < 0:
            index = 0
    elif index > length:
        index = length
    return index

def unicode_endswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self = w_self._value
    start = _normalize_index(len(self), space.int_w(w_start))
    end = _normalize_index(len(self), space.int_w(w_end))

    substr = w_substr._value
    substr_len = len(substr)
    
    if end - start < substr_len:
        return space.w_False # substring is too long
    start = end - substr_len
    for i in range(substr_len):
        if self[start + i] != substr[i]:
            return space.w_False
    return space.w_True

def unicode_startswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self = w_self._value
    start = _normalize_index(len(self), space.int_w(w_start))
    end = _normalize_index(len(self), space.int_w(w_end))

    substr = w_substr._value
    substr_len = len(substr)
    
    if end - start < substr_len:
        return space.w_False # substring is too long
    
    for i in range(substr_len):
        if self[start + i] != substr[i]:
            return space.w_False
    return space.w_True

def unicode_center__Unicode_ANY(space, w_self, w_width):
    self = w_self._value
    width = space.int_w(w_width)
    padding = width - len(self)
    if padding < 0:
        return space.call_function(space.w_unicode, w_self)
    leftpad = padding // 2 + (padding & width & 1)
    result = [u' '] * width
    for i in range(len(self)):
        result[leftpad + i] = self[i]
    return W_UnicodeObject(space, result)


def unicode_ljust__Unicode_ANY(space, w_self, w_width):
    self = w_self._value
    width = space.int_w(w_width)
    padding = width - len(self)
    if padding < 0:
        return space.call_function(space.w_unicode, w_self)
    result = [u' '] * width
    for i in range(len(self)):
        result[i] = self[i]
    return W_UnicodeObject(space, result)

def unicode_rjust__Unicode_ANY(space, w_self, w_width):
    self = w_self._value
    width = space.int_w(w_width)
    padding = width - len(self)
    if padding < 0:
        return space.call_function(space.w_unicode, w_self)
    result = [u' '] * width
    for i in range(len(self)):
        result[padding + i] = self[i]
    return W_UnicodeObject(space, result)
    
def unicode_zfill__Unicode_ANY(space, w_self, w_width):
    self = w_self._value
    width = space.int_w(w_width)
    if len(self) == 0:
        return W_UnicodeObject(space, [u'0'] * width)
    padding = width - len(self)
    if padding <= 0:
        return space.call_function(space.w_unicode, w_self)
    result = [u'0'] * width
    for i in range(len(self)):
        result[padding + i] = self[i]
    # Move sign to first position
    if self[0] in (u'+', u'-'):
        result[0] = self[0]
        result[padding] = u'0'
    return W_UnicodeObject(space, result)

def unicode_splitlines__Unicode_ANY(space, w_self, w_keepends):
    self = w_self._value
    keepends = 0
    if space.int_w(w_keepends):
        keepends = 1
    if len(self) == 0:
        return space.newlist([])
    
    start = 0
    end = len(self)
    pos = 0
    lines = []
    while pos < end:
        if unicodedb.islinebreak(ord(self[pos])):
            if (self[pos] == u'\r' and pos + 1 < end and
                self[pos + 1] == u'\n'):
                # Count CRLF as one linebreak
                lines.append(W_UnicodeObject(space,
                                             self[start:pos + keepends * 2]))
                pos += 1
            else:
                lines.append(W_UnicodeObject(space,
                                             self[start:pos + keepends]))
            pos += 1
            start = pos
        else:
            pos += 1
    if not unicodedb.islinebreak(ord(self[end - 1])):
        lines.append(W_UnicodeObject(space, self[start:]))
    return space.newlist(lines)

def unicode_find__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self = w_self._value
    start = _normalize_index(len(self), space.int_w(w_start))
    end = _normalize_index(len(self), space.int_w(w_end))
    substr = w_substr._value
    return space.wrap(_find(self, substr, start, end))

def unicode_rfind__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self = w_self._value
    start = _normalize_index(len(self), space.int_w(w_start))
    end = _normalize_index(len(self), space.int_w(w_end))
    substr = w_substr._value
    return space.wrap(_rfind(self, substr, start, end))

def unicode_index__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self = w_self._value
    start = _normalize_index(len(self), space.int_w(w_start))
    end = _normalize_index(len(self), space.int_w(w_end))
    substr = w_substr._value
    index = _find(self, substr, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_rindex__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self = w_self._value
    start = _normalize_index(len(self), space.int_w(w_start))
    end = _normalize_index(len(self), space.int_w(w_end))
    substr = w_substr._value
    index = _rfind(self, substr, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_count__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self = w_self._value
    start = _normalize_index(len(self), space.int_w(w_start))
    end = _normalize_index(len(self), space.int_w(w_end))
    substr = w_substr._value
    count = 0
    while start <= end:
        index = _find(self, substr, start, end)
        if index < 0:
            break
        start = index + 1
        count += 1
    return space.wrap(count)


def unicode_split__Unicode_None_ANY(space, w_self, w_none, w_maxsplit):
    self = w_self._value
    maxsplit = space.int_w(w_maxsplit)
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    while maxsplit != 0 and start < end:
        index = start
        for index in range(start, end):
            if _isspace(self[index]):
                break
        else:
            break
        parts.append(W_UnicodeObject(space, self[start:index]))
        maxsplit -= 1
        # Eat whitespace
        for start in range(index + 1, end):
            if not _isspace(self[start]):
                break
        else:
            return space.newlist(parts)
    parts.append(W_UnicodeObject(space, self[start:]))
    return space.newlist(parts)


def unicode_split__Unicode_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
    self = w_self._value
    delim = w_delim._value
    maxsplit = space.int_w(w_maxsplit)
    delim_len = len(delim)
    if delim_len == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('empty separator'))
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    while maxsplit != 0:
        index = _find(self, delim, start, end)
        if index < 0:
            break
        parts.append(W_UnicodeObject(space, self[start:index]))
        start = index + delim_len
        maxsplit -= 1
    parts.append(W_UnicodeObject(space, self[start:]))
    return space.newlist(parts)

def _split(space, self, maxsplit):
    if len(self) == 0:
        return []
    if maxsplit == 0:
        return [W_UnicodeObject(space, self)]
    index = 0
    end = len(self)
    parts = [W_UnicodeObject(space, [])]
    maxsplit -= 1
    while maxsplit != 0:
        if index >= end:
            break
        parts.append(W_UnicodeObject(space, [self[index]]))
        index += 1
        maxsplit -= 1
    parts.append(W_UnicodeObject(space, self[index:]))
    return parts
    
def unicode_replace__Unicode_Unicode_Unicode_ANY(space, w_self, w_old,
                                                 w_new, w_maxsplit):
    if len(w_old._value):
        w_parts = space.call_method(w_self, 'split', w_old, w_maxsplit)
    else:
        self = w_self._value
        maxsplit = space.int_w(w_maxsplit)
        w_parts = space.newlist(_split(space, self, maxsplit))
    return space.call_method(w_new, 'join', w_parts)
    

'translate'
app = gateway.applevel(r'''
import sys

def unicode_expandtabs__Unicode_ANY(self, tabsize):
    parts = self.split(u'\t')
    result = [ parts[0] ]
    prevsize = 0
    for ch in parts[0]:
        prevsize += 1
        if ch in (u"\n", u"\r"):
            prevsize = 0
    for i in range(1, len(parts)):
        pad = tabsize - prevsize % tabsize
        result.append(u' ' * pad)
        nextpart = parts[i]
        result.append(nextpart)
        prevsize = 0
        for ch in nextpart:
            prevsize += 1
            if ch in (u"\n", u"\r"):
                prevsize = 0
    return u''.join(result)

def unicode_translate__Unicode_ANY(self, table):
    result = []
    for unichar in self:
        try:
            newval = table[ord(unichar)]
        except KeyError:
            result.append(unichar)
        else:
            if newval is None:
                continue
            elif isinstance(newval, int):
                if newval < 0 or newval > sys.maxunicode:
                    raise TypeError("character mapping must be in range(0x%x)"%(sys.maxunicode + 1,))
                result.append(unichr(newval))
            elif isinstance(newval, unicode):
                result.append(newval)
            else:
                raise TypeError("character mapping must return integer, None or unicode")
    return ''.join(result)

def mod__Unicode_ANY(format, values):
    import _formatting
    if isinstance(values, tuple):
        return _formatting.format(format, values, None, do_unicode=True)
    if hasattr(values, "keys"):
        return _formatting.format(format, (values,), values, do_unicode=True)
    return _formatting.format(format, (values,), None, do_unicode=True)

def unicode_encode__Unicode_ANY_ANY(unistr, encoding=None, errors=None):
    import codecs, sys
    if encoding is None:
        encoding = sys.getdefaultencoding()

    encoder = codecs.getencoder(encoding)
    if errors is None:
        retval, lenght = encoder(unistr)
    else:
        retval, length = encoder(unistr, errors)
    if not isinstance(retval,str):
        raise TypeError("encoder did not return a string object (type=%s)" %
                        type(retval).__name__)
    return retval

''')
unicode_expandtabs__Unicode_ANY = app.interphook('unicode_expandtabs__Unicode_ANY')
unicode_translate__Unicode_ANY = app.interphook('unicode_translate__Unicode_ANY')
mod__Unicode_ANY = app.interphook('mod__Unicode_ANY')

unicode_encode__Unicode_ANY_ANY = app.interphook('unicode_encode__Unicode_ANY_ANY')

import unicodetype
register_all(vars(), unicodetype)

# str.strip(unicode) needs to convert self to unicode and call unicode.strip
# we use the following magic to register strip_string_unicode as a String multimethod.
class str_methods:
    import stringtype
    W_UnicodeObject = W_UnicodeObject
    from pypy.objspace.std.stringobject import W_StringObject
    def str_strip__String_Unicode(space, w_self, w_chars):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'strip', w_chars)
    def str_lstrip__String_Unicode(space, w_self, w_chars):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'lstrip', w_chars)
        self = w_self._value
    def str_rstrip__String_Unicode(space, w_self, w_chars):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rstrip', w_chars)
    def str_count__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'count', w_substr, w_start, w_end)
    def str_find__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'find', w_substr, w_start, w_end)
    def str_rfind__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rfind', w_substr, w_start, w_end)
    def str_index__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'index', w_substr, w_start, w_end)
    def str_rindex__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rindex', w_substr, w_start, w_end)

    def str_replace__String_Unicode_Unicode_ANY(space, w_self, w_old, w_new, w_maxsplit):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'replace', w_old, w_new, w_maxsplit)

    def str_split__String_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'split', w_delim, w_maxsplit)
        
    register_all(vars(), stringtype)
