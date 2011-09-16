from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.stringobject import W_StringObject, make_rsplit_with_delim
from pypy.objspace.std.ropeobject import W_RopeObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype, newformat
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.rlib.rarithmetic import intmask, ovfcheck
from pypy.rlib.objectmodel import compute_hash
from pypy.rlib.rstring import UnicodeBuilder
from pypy.rlib.runicode import unicode_encode_unicode_escape
from pypy.module.unicodedata import unicodedb
from pypy.tool.sourcetools import func_with_new_name

from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.stringtype import stringstartswith, stringendswith

class W_UnicodeObject(W_Object):
    from pypy.objspace.std.unicodetype import unicode_typedef as typedef
    _immutable_fields_ = ['_value']

    def __init__(w_self, unistr):
        assert isinstance(unistr, unicode)
        w_self._value = unistr

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self, space):
        # for testing
        return w_self._value

    def create_if_subclassed(w_self):
        if type(w_self) is W_UnicodeObject:
            return w_self
        return W_UnicodeObject(w_self._value)

    def str_w(w_self, space):
        return space.str_w(space.str(w_self))

W_UnicodeObject.EMPTY = W_UnicodeObject(u'')

registerimplementation(W_UnicodeObject)

# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise operationerrfmt(space.w_TypeError,
                              "expected unicode, got '%s'",
                              space.type(w_unistr).getname(space))
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
                w_encoding = space.wrap('decimal')
                w_start = space.wrap(i)
                w_end = space.wrap(i+1)
                w_reason = space.wrap('invalid decimal Unicode string')
                raise OperationError(space.w_UnicodeEncodeError, space.newtuple([w_encoding, w_unistr, w_start, w_end, w_reason]))
    return ''.join(result)

# string-to-unicode delegation
def delegate_String2Unicode(space, w_str):
    from pypy.objspace.std.unicodetype import unicode_from_string
    w_uni = unicode_from_string(space, w_str)
    assert isinstance(w_uni, W_UnicodeObject) # help the annotator!
    return w_uni

# checks if should trigger an unicode warning
def _unicode_string_comparison(space, w_uni, w_str, inverse, uni_from_str):
    try:
        w_uni2 = uni_from_str(space, w_str)
    except OperationError, e:
        if e.match(space, space.w_UnicodeDecodeError):
            if inverse:
                msg = "Unicode unequal comparison failed to convert both "  \
                      "arguments to Unicode - interpreting them as being unequal"
            else :
                msg = "Unicode equal comparison failed to convert both "    \
                      "arguments to Unicode - interpreting them as being unequal"
            space.warn(msg, space.w_UnicodeWarning)
            return space.newbool(inverse)
        raise
    result = space.eq(w_uni, w_uni2)
    if inverse:
        return space.not_(result)
    return result

def unicode_w__Unicode(space, w_uni):
    return w_uni._value

def str__Unicode(space, w_uni):
    from pypy.objspace.std.unicodetype import encode_object
    return encode_object(space, w_uni, None, None)

def eq__Unicode_Unicode(space, w_left, w_right):
    return space.newbool(w_left._value == w_right._value)

def eq__Unicode_String(space, w_uni, w_str):
    from pypy.objspace.std.unicodetype import unicode_from_string
    return _unicode_string_comparison(space, w_uni, w_str,
                    False, unicode_from_string)

eq__Unicode_Rope = eq__Unicode_String

def ne__Unicode_String(space, w_uni, w_str):
    from pypy.objspace.std.unicodetype import unicode_from_string
    return _unicode_string_comparison(space, w_uni, w_str,
                    True, unicode_from_string)

ne__Unicode_Rope = ne__Unicode_String

def lt__Unicode_Unicode(space, w_left, w_right):
    left = w_left._value
    right = w_right._value
    return space.newbool(left < right)

def ord__Unicode(space, w_uni):
    if len(w_uni._value) != 1:
        raise operationerrfmt(space.w_TypeError,
            "ord() expected a character, got a unicode of length %d",
            len(w_uni._value))
    return space.wrap(ord(w_uni._value[0]))

def getnewargs__Unicode(space, w_uni):
    return space.newtuple([W_UnicodeObject(w_uni._value)])

def add__Unicode_Unicode(space, w_left, w_right):
    return W_UnicodeObject(w_left._value + w_right._value)

def add__String_Unicode(space, w_left, w_right):
    # this function is needed to make 'abc'.__add__(u'def') return
    # u'abcdef' instead of NotImplemented.  This is what occurs on
    # top of CPython.
    from pypy.objspace.std.unicodetype import unicode_from_string
    # XXX fragile implementation detail: for "string + unicode subclass",
    # if the unicode subclass overrides __radd__(), then it will be
    # called (see test_str_unicode_concat_overrides).  This occurs as a
    # result of the following call to space.add() in which the first
    # argument is a unicode and the second argument a subclass of unicode
    # (and thus the usual logic about calling __radd__() first applies).
    return space.add(unicode_from_string(space, w_left) , w_right)

add__Rope_Unicode = add__String_Unicode

def add__Unicode_String(space, w_left, w_right):
    # this function is needed to make 'abc'.__radd__(u'def') return
    # u'defabc', although it's completely unclear if that's necessary
    # given that CPython doesn't even have a method str.__radd__().
    from pypy.objspace.std.unicodetype import unicode_from_string
    return space.add(w_left, unicode_from_string(space, w_right))
    # Note about "unicode + string subclass": look for
    # "cpython bug compatibility" in descroperation.py

add__Unicode_Rope = add__Unicode_String

def contains__String_Unicode(space, w_container, w_item):
    from pypy.objspace.std.unicodetype import unicode_from_string
    return space.contains(unicode_from_string(space, w_container), w_item )
contains__Rope_Unicode = contains__String_Unicode


def contains__Unicode_Unicode(space, w_container, w_item):
    item = w_item._value
    container = w_container._value
    return space.newbool(container.find(item) != -1)

def unicode_join__Unicode_ANY(space, w_self, w_list):
    list_w = space.unpackiterable(w_list)
    size = len(list_w)

    if size == 0:
        return W_UnicodeObject.EMPTY

    if size == 1:
        w_s = list_w[0]
        if space.is_w(space.type(w_s), space.w_unicode):
            return w_s

    return _unicode_join_many_items(space, w_self, list_w, size)

def _unicode_join_many_items(space, w_self, list_w, size):
    self = w_self._value
    sb = UnicodeBuilder()
    for i in range(size):
        if self and i != 0:
            sb.append(self)
        w_s = list_w[i]
        if isinstance(w_s, W_UnicodeObject):
            # shortcut for performance
            sb.append(w_s._value)
        else:
            try:
                sb.append(space.unicode_w(w_s))
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise operationerrfmt(space.w_TypeError,
                    "sequence item %d: expected string or Unicode", i)
    return space.wrap(sb.build())

def hash__Unicode(space, w_uni):
    s = w_uni._value
    if space.config.objspace.std.withrope:
        # be compatible with the special ropes hash
        # XXX no caching
        if len(s) == 0:
            return space.wrap(0)
        x = 0
        for c in s:
            x = intmask((1000003 * x) + ord(c))
        x <<= 1
        x ^= len(s)
        x ^= ord(s[0])
        h = intmask(x)
        return space.wrap(h)
    x = compute_hash(s)
    return space.wrap(x)

def len__Unicode(space, w_uni):
    return space.wrap(len(w_uni._value))

def getitem__Unicode_ANY(space, w_uni, w_index):
    ival = space.getindex_w(w_index, space.w_IndexError, "string index")
    uni = w_uni._value
    ulen = len(uni)
    if ival < 0:
        ival += ulen
    if ival < 0 or ival >= ulen:
        raise OperationError(space.w_IndexError,
                             space.wrap("unicode index out of range"))
    return W_UnicodeObject(uni[ival])

def getitem__Unicode_Slice(space, w_uni, w_slice):
    uni = w_uni._value
    length = len(uni)
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        r = u""
    elif step == 1:
        assert start >= 0 and stop >= 0
        r = uni[start:stop]
    else:
        r = u"".join([uni[start + i*step] for i in range(sl)])
    return W_UnicodeObject(r)

def getslice__Unicode_ANY_ANY(space, w_uni, w_start, w_stop):
    uni = w_uni._value
    start, stop = normalize_simple_slice(space, len(uni), w_start, w_stop)
    return W_UnicodeObject(uni[start:stop])

def mul__Unicode_ANY(space, w_uni, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if times <= 0:
        return W_UnicodeObject.EMPTY
    input = w_uni._value
    if len(input) == 1:
        result = input[0] * times
    else:
        result = input * times
    return W_UnicodeObject(result)

def mul__ANY_Unicode(space, w_times, w_uni):
    return mul__Unicode_ANY(space, w_uni, w_times)

def _isspace(uchar):
    return unicodedb.isspace(ord(uchar))

def make_generic(funcname):
    def func(space, w_self):
        v = w_self._value
        if len(v) == 0:
            return space.w_False
        for idx in range(len(v)):
            if not getattr(unicodedb, funcname)(ord(v[idx])):
                return space.w_False
        return space.w_True
    return func_with_new_name(func, "unicode_%s__Unicode" % (funcname, ))

unicode_isspace__Unicode = make_generic("isspace")
unicode_isalpha__Unicode = make_generic("isalpha")
unicode_isalnum__Unicode = make_generic("isalnum")
unicode_isdecimal__Unicode = make_generic("isdecimal")
unicode_isdigit__Unicode = make_generic("isdigit")
unicode_isnumeric__Unicode = make_generic("isnumeric")

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

    assert rpos >= 0
    result = u_self[lpos: rpos]
    return W_UnicodeObject(result)

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

    assert rpos >= 0
    result = u_self[lpos: rpos]
    return W_UnicodeObject(result)

def unicode_strip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 1)
def unicode_strip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 1)
def unicode_strip__Unicode_String(space, w_self, w_chars):
    from pypy.objspace.std.unicodetype import unicode_from_string
    return space.call_method(w_self, 'strip',
                             unicode_from_string(space, w_chars))
unicode_strip__Unicode_Rope = unicode_strip__Unicode_String

def unicode_lstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 0)
def unicode_lstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 0)
def unicode_lstrip__Unicode_String(space, w_self, w_chars):
    from pypy.objspace.std.unicodetype import unicode_from_string
    return space.call_method(w_self, 'lstrip',
                             unicode_from_string(space, w_chars))

unicode_lstrip__Unicode_Rope = unicode_lstrip__Unicode_String

def unicode_rstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 0, 1)
def unicode_rstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 0, 1)
def unicode_rstrip__Unicode_String(space, w_self, w_chars):
    from pypy.objspace.std.unicodetype import unicode_from_string
    return space.call_method(w_self, 'rstrip',
                             unicode_from_string(space, w_chars))

unicode_rstrip__Unicode_Rope = unicode_rstrip__Unicode_String

def unicode_capitalize__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return W_UnicodeObject.EMPTY
    result = [u'\0'] * len(input)
    result[0] = unichr(unicodedb.toupper(ord(input[0])))
    for i in range(1, len(input)):
        result[i] = unichr(unicodedb.tolower(ord(input[i])))
    return W_UnicodeObject(u''.join(result))

def unicode_title__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return w_self
    result = [u'\0'] * len(input)

    previous_is_cased = False
    for i in range(len(input)):
        unichar = ord(input[i])
        if previous_is_cased:
            result[i] = unichr(unicodedb.tolower(unichar))
        else:
            result[i] = unichr(unicodedb.totitle(unichar))
        previous_is_cased = unicodedb.iscased(unichar)
    return W_UnicodeObject(u''.join(result))

def unicode_lower__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        result[i] = unichr(unicodedb.tolower(ord(input[i])))
    return W_UnicodeObject(u''.join(result))

def unicode_upper__Unicode(space, w_self):
    input = w_self._value
    result = [u'\0'] * len(input)
    for i in range(len(input)):
        result[i] = unichr(unicodedb.toupper(ord(input[i])))
    return W_UnicodeObject(u''.join(result))

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
    return W_UnicodeObject(u''.join(result))

def _normalize_index(length, index):
    if index < 0:
        index += length
        if index < 0:
            index = 0
    elif index > length:
        index = length
    return index

def _convert_idx_params(space, w_self, w_sub, w_start, w_end, upper_bound=False):
    assert isinstance(w_sub, W_UnicodeObject)
    self = w_self._value
    sub = w_sub._value

    if space.is_w(w_start, space.w_None):
        w_start = space.wrap(0)
    if space.is_w(w_end, space.w_None):
        w_end = space.len(w_self)

    if upper_bound:
        start = slicetype.adapt_bound(space, len(self), w_start)
        end = slicetype.adapt_bound(space, len(self), w_end)
    else:
        start = slicetype.adapt_lower_bound(space, len(self), w_start)
        end = slicetype.adapt_lower_bound(space, len(self), w_end)
    return (self, sub, start, end)
_convert_idx_params._annspecialcase_ = 'specialize:arg(5)'

def unicode_endswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, substr, start, end = _convert_idx_params(space, w_self, w_substr,
                                                   w_start, w_end, True)
    return space.newbool(stringendswith(self, substr, start, end))

def unicode_startswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, substr, start, end = _convert_idx_params(space, w_self, w_substr,
                                                   w_start, w_end, True)
    # XXX this stuff can be waaay better for ootypebased backends if
    #     we re-use more of our rpython machinery (ie implement startswith
    #     with additional parameters as rpython)
    return space.newbool(stringstartswith(self, substr, start, end))

def unicode_startswith__Unicode_Tuple_ANY_ANY(space, w_unistr, w_prefixes,
                                              w_start, w_end):
    unistr, _, start, end = _convert_idx_params(space, w_unistr, space.wrap(u''),
                                                w_start, w_end, True)
    for w_prefix in space.fixedview(w_prefixes):
        prefix = space.unicode_w(w_prefix)
        if stringstartswith(unistr, prefix, start, end):
            return space.w_True
    return space.w_False

def unicode_endswith__Unicode_Tuple_ANY_ANY(space, w_unistr, w_suffixes,
                                            w_start, w_end):
    unistr, _, start, end = _convert_idx_params(space, w_unistr, space.wrap(u''),
                                             w_start, w_end, True)
    for w_suffix in space.fixedview(w_suffixes):
        suffix = space.unicode_w(w_suffix)
        if stringendswith(unistr, suffix, start, end):
            return space.w_True
    return space.w_False

def _to_unichar_w(space, w_char):
    try:
        unistr = space.unicode_w(w_char)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            msg = 'The fill character cannot be converted to Unicode'
            raise OperationError(space.w_TypeError, space.wrap(msg))
        else:
            raise

    if len(unistr) != 1:
        raise OperationError(space.w_TypeError, space.wrap('The fill character must be exactly one character long'))
    return unistr[0]

def unicode_center__Unicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._value
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - len(self)
    if padding < 0:
        return w_self.create_if_subclassed()
    leftpad = padding // 2 + (padding & width & 1)
    result = [fillchar] * width
    for i in range(len(self)):
        result[leftpad + i] = self[i]
    return W_UnicodeObject(u''.join(result))

def unicode_ljust__Unicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._value
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - len(self)
    if padding < 0:
        return w_self.create_if_subclassed()
    result = [fillchar] * width
    for i in range(len(self)):
        result[i] = self[i]
    return W_UnicodeObject(u''.join(result))

def unicode_rjust__Unicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._value
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - len(self)
    if padding < 0:
        return w_self.create_if_subclassed()
    result = [fillchar] * width
    for i in range(len(self)):
        result[padding + i] = self[i]
    return W_UnicodeObject(u''.join(result))

def unicode_zfill__Unicode_ANY(space, w_self, w_width):
    self = w_self._value
    width = space.int_w(w_width)
    if len(self) == 0:
        return W_UnicodeObject(u'0' * width)
    padding = width - len(self)
    if padding <= 0:
        return w_self.create_if_subclassed()
    result = [u'0'] * width
    for i in range(len(self)):
        result[padding + i] = self[i]
    # Move sign to first position
    if self[0] in (u'+', u'-'):
        result[0] = self[0]
        result[padding] = u'0'
    return W_UnicodeObject(u''.join(result))

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
                lines.append(W_UnicodeObject(self[start:pos + keepends * 2]))
                pos += 1
            else:
                lines.append(W_UnicodeObject(self[start:pos + keepends]))
            pos += 1
            start = pos
        else:
            pos += 1
    if not unicodedb.islinebreak(ord(self[end - 1])):
        lines.append(W_UnicodeObject(self[start:]))
    return space.newlist(lines)

def unicode_find__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, substr, start, end = _convert_idx_params(space, w_self, w_substr,
                                                   w_start, w_end)
    return space.wrap(self.find(substr, start, end))

def unicode_rfind__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, substr, start, end = _convert_idx_params(space, w_self, w_substr,
                                                   w_start, w_end)
    return space.wrap(self.rfind(substr, start, end))

def unicode_index__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, substr, start, end = _convert_idx_params(space, w_self, w_substr,
                                                   w_start, w_end)
    index = self.find(substr, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_rindex__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, substr, start, end = _convert_idx_params(space, w_self, w_substr,
                                           w_start, w_end)
    index = self.rfind(substr, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_count__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, substr, start, end = _convert_idx_params(space, w_self, w_substr,
                                                   w_start, w_end)
    return space.wrap(self.count(substr, start, end))

def unicode_split__Unicode_None_ANY(space, w_self, w_none, w_maxsplit):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._value
    length = len(value)
    i = 0
    while True:
        # find the beginning of the next word
        while i < length:
            if not _isspace(value[i]):
                break   # found
            i += 1
        else:
            break  # end of string, finished

        # find the end of the word
        if maxsplit == 0:
            j = length   # take all the rest of the string
        else:
            j = i + 1
            while j < length and not _isspace(value[j]):
                j += 1
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        # the word is value[i:j]
        res_w.append(W_UnicodeObject(value[i:j]))

        # continue to look from the character following the space after the word
        i = j + 1

    return space.newlist(res_w)

def unicode_split__Unicode_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
    self = w_self._value
    delim = w_delim._value
    maxsplit = space.int_w(w_maxsplit)
    delim_len = len(delim)
    if delim_len == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('empty separator'))
    parts = _split_with(self, delim, maxsplit)
    return space.newlist([W_UnicodeObject(part) for part in parts])


def unicode_rsplit__Unicode_None_ANY(space, w_self, w_none, w_maxsplit):
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._value
    i = len(value)-1
    while True:
        # starting from the end, find the end of the next word
        while i >= 0:
            if not _isspace(value[i]):
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
            while j >= 0 and not _isspace(value[j]):
                j -= 1
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        # the word is value[j+1:i+1]
        j1 = j + 1
        assert j1 >= 0
        res_w.append(W_UnicodeObject(value[j1:i+1]))

        # continue to look from the character before the space before the word
        i = j - 1

    res_w.reverse()
    return space.newlist(res_w)

def sliced(space, s, start, stop, orig_obj):
    assert start >= 0
    assert stop >= 0
    if start == 0 and stop == len(s) and space.is_w(space.type(orig_obj), space.w_unicode):
        return orig_obj
    return space.wrap( s[start:stop])

unicode_rsplit__Unicode_Unicode_ANY = make_rsplit_with_delim('unicode_rsplit__Unicode_Unicode_ANY',
                                                             sliced)

def _split_into_chars(self, maxsplit):
    if maxsplit == 0:
        return [self]
    index = 0
    end = len(self)
    parts = [u'']
    maxsplit -= 1
    while maxsplit != 0:
        if index >= end:
            break
        parts.append(self[index])
        index += 1
        maxsplit -= 1
    parts.append(self[index:])
    return parts

def _split_with(self, with_, maxsplit=-1):
    parts = []
    start = 0
    end = len(self)
    length = len(with_)
    while maxsplit != 0:
        index = self.find(with_, start, end)
        if index < 0:
            break
        parts.append(self[start:index])
        start = index + length
        maxsplit -= 1
    parts.append(self[start:])
    return parts

def unicode_replace__Unicode_Unicode_Unicode_ANY(space, w_self, w_old,
                                                 w_new, w_maxsplit):
    return _unicode_replace(space, w_self, w_old._value, w_new._value,
                            w_maxsplit)

def unicode_replace__Unicode_ANY_ANY_ANY(space, w_self, w_old, w_new,
                                         w_maxsplit):
    if not space.isinstance_w(w_old, space.w_unicode):
        old = unicode(space.bufferstr_w(w_old))
    else:
        old = space.unicode_w(w_old)
    if not space.isinstance_w(w_new, space.w_unicode):
        new = unicode(space.bufferstr_w(w_new))
    else:
        new = space.unicode_w(w_new)
    return _unicode_replace(space, w_self, old, new, w_maxsplit)

def _unicode_replace(space, w_self, old, new, w_maxsplit):
    if len(old):
        parts = _split_with(w_self._value, old, space.int_w(w_maxsplit))
    else:
        self = w_self._value
        maxsplit = space.int_w(w_maxsplit)
        parts = _split_into_chars(self, maxsplit)

    try:
        one = ovfcheck(len(parts) * len(new))
        ovfcheck(one + len(w_self._value))
    except OverflowError:
        raise OperationError(
            space.w_OverflowError,
            space.wrap("replace string is too long"))

    return W_UnicodeObject(new.join(parts))


def unicode_encode__Unicode_ANY_ANY(space, w_unistr,
                                    w_encoding=None,
                                    w_errors=None):

    from pypy.objspace.std.unicodetype import _get_encoding_and_errors
    from pypy.objspace.std.unicodetype import encode_object
    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    w_retval = encode_object(space, w_unistr, encoding, errors)
    return w_retval

def unicode_partition__Unicode_Unicode(space, w_unistr, w_unisub):
    unistr = w_unistr._value
    unisub = w_unisub._value
    if not unisub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = unistr.find(unisub)
    if pos == -1:
        return space.newtuple([w_unistr, W_UnicodeObject.EMPTY,
                               W_UnicodeObject.EMPTY])
    else:
        assert pos >= 0
        return space.newtuple([space.wrap(unistr[:pos]), w_unisub,
                               space.wrap(unistr[pos+len(unisub):])])

def unicode_rpartition__Unicode_Unicode(space, w_unistr, w_unisub):
    unistr = w_unistr._value
    unisub = w_unisub._value
    if not unisub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = unistr.rfind(unisub)
    if pos == -1:
        return space.newtuple([W_UnicodeObject.EMPTY,
                               W_UnicodeObject.EMPTY, w_unistr])
    else:
        assert pos >= 0
        return space.newtuple([space.wrap(unistr[:pos]), w_unisub,
                               space.wrap(unistr[pos+len(unisub):])])


def unicode_expandtabs__Unicode_ANY(space, w_self, w_tabsize):
    self = w_self._value
    tabsize  = space.int_w(w_tabsize)
    parts = _split_with(self, u'\t')
    result = [parts[0]]
    prevsize = 0
    for ch in parts[0]:
        prevsize += 1
        if ch == u"\n" or ch ==  u"\r":
            prevsize = 0
    totalsize = prevsize

    for i in range(1, len(parts)):
        pad = tabsize - prevsize % tabsize
        nextpart = parts[i]
        try:
            totalsize = ovfcheck(totalsize + pad)
            totalsize = ovfcheck(totalsize + len(nextpart))
            result.append(u' ' * pad)
        except OverflowError:
            raise OperationError(space.w_OverflowError, space.wrap('new string is too long'))
        result.append(nextpart)
        prevsize = 0
        for ch in nextpart:
            prevsize += 1
            if ch in (u"\n", u"\r"):
                prevsize = 0
    return space.wrap(u''.join(result))


def unicode_translate__Unicode_ANY(space, w_self, w_table):
    self = w_self._value
    w_sys = space.getbuiltinmodule('sys')
    maxunicode = space.int_w(space.getattr(w_sys, space.wrap("maxunicode")))
    result = []
    for unichar in self:
        try:
            w_newval = space.getitem(w_table, space.wrap(ord(unichar)))
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                result.append(unichar)
            else:
                raise
        else:
            if space.is_w(w_newval, space.w_None):
                continue
            elif space.isinstance_w(w_newval, space.w_int):
                newval = space.int_w(w_newval)
                if newval < 0 or newval > maxunicode:
                    raise OperationError(
                            space.w_TypeError,
                            space.wrap("character mapping must be in range(0x%x)" % (maxunicode + 1,)))
                result.append(unichr(newval))
            elif space.isinstance_w(w_newval, space.w_unicode):
                result.append(space.unicode_w(w_newval))
            else:
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("character mapping must return integer, None or unicode"))
    return W_UnicodeObject(u''.join(result))

def repr__Unicode(space, w_unicode):
    chars = w_unicode._value
    size = len(chars)
    s = unicode_encode_unicode_escape(chars, size, "strict", quotes=True)
    return space.wrap(s)

def mod__Unicode_ANY(space, w_format, w_values):
    return mod_format(space, w_format, w_values, do_unicode=True)

def unicode_format__Unicode(space, w_unicode, __args__):
    return newformat.format_method(space, w_unicode, __args__, True)

def format__Unicode_ANY(space, w_unicode, w_format_spec):
    if not space.isinstance_w(w_format_spec, space.w_unicode):
        w_format_spec = space.call_function(space.w_unicode, w_format_spec)
    from pypy.objspace.std.unicodetype import unicode_from_object
    w_unicode = unicode_from_object(space, w_unicode)
    spec = space.unicode_w(w_format_spec)
    formatter = newformat.unicode_formatter(space, spec)
    return formatter.format_string(space.unicode_w(w_unicode))


from pypy.objspace.std import unicodetype
register_all(vars(), unicodetype)

# str.strip(unicode) needs to convert self to unicode and call unicode.strip we
# use the following magic to register strip_string_unicode as a String
# multimethod.

# XXX couldn't string and unicode _share_ the multimethods that make up their
# methods?

class str_methods:
    from pypy.objspace.std import stringtype
    W_UnicodeObject = W_UnicodeObject
    from pypy.objspace.std.stringobject import W_StringObject
    from pypy.objspace.std.ropeobject import W_RopeObject
    def str_strip__String_Unicode(space, w_self, w_chars):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'strip', w_chars)
    str_strip__Rope_Unicode = str_strip__String_Unicode
    def str_lstrip__String_Unicode(space, w_self, w_chars):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'lstrip', w_chars)
    str_lstrip__Rope_Unicode = str_lstrip__String_Unicode
    def str_rstrip__String_Unicode(space, w_self, w_chars):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'rstrip', w_chars)
    str_rstrip__Rope_Unicode = str_rstrip__String_Unicode
    def str_count__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'count', w_substr, w_start, w_end)
    str_count__Rope_Unicode_ANY_ANY = str_count__String_Unicode_ANY_ANY
    def str_find__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'find', w_substr, w_start, w_end)
    str_find__Rope_Unicode_ANY_ANY = str_find__String_Unicode_ANY_ANY
    def str_rfind__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'rfind', w_substr, w_start, w_end)
    str_rfind__Rope_Unicode_ANY_ANY = str_rfind__String_Unicode_ANY_ANY
    def str_index__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'index', w_substr, w_start, w_end)
    str_index__Rope_Unicode_ANY_ANY = str_index__String_Unicode_ANY_ANY
    def str_rindex__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'rindex', w_substr, w_start, w_end)
    str_rindex__Rope_Unicode_ANY_ANY = str_rindex__String_Unicode_ANY_ANY
    def str_replace__String_Unicode_Unicode_ANY(space, w_self, w_old, w_new, w_maxsplit):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'replace', w_old, w_new, w_maxsplit)
    str_replace__Rope_Unicode_Unicode_ANY = str_replace__String_Unicode_Unicode_ANY
    def str_split__String_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'split', w_delim, w_maxsplit)
    str_split__Rope_Unicode_ANY = str_split__String_Unicode_ANY
    def str_rsplit__String_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
        from pypy.objspace.std.unicodetype import unicode_from_string
        return space.call_method(unicode_from_string(space, w_self),
                                 'rsplit', w_delim, w_maxsplit)
    str_rsplit__Rope_Unicode_ANY = str_rsplit__String_Unicode_ANY
    register_all(vars(), stringtype)
