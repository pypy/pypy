"""The builtin str implementation"""

from pypy.interpreter.buffer import StringBuffer
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.unicodeobject import (unicode_from_string,
    decode_object, _get_encoding_and_errors)
from rpython.rlib.jit import we_are_jitted
from rpython.rlib.objectmodel import compute_hash, compute_unique_id
from rpython.rlib.rstring import StringBuilder


class W_AbstractBytesObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractBytesObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return space.str_w(self) is space.str_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(space.str_w(self)))

    def unicode_w(self, space):
        # Use the default encoding.
        w_defaultencoding = space.call_function(space.sys.get(
                                                'getdefaultencoding'))
        encoding, errors = _get_encoding_and_errors(space, w_defaultencoding,
                                                    space.w_None)
        if encoding is None and errors is None:
            return space.unicode_w(unicode_from_string(space, self))
        return space.unicode_w(decode_object(space, self, encoding, errors))


class W_BytesObject(W_AbstractBytesObject, StringMethods):
    _immutable_fields_ = ['_value']

    def __init__(self, str):
        self._value = str

    def __repr__(self):
        """ representation for debugging purposes """
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def unwrap(self, space):
        return self._value

    def str_w(self, space):
        return self._value

    def listview_str(self):
        return _create_list_from_string(self._value)

    def ord(self, space):
        if len(self._value) != 1:
            msg = "ord() expected a character, but string of length %d found"
            raise operationerrfmt(space.w_TypeError, msg, len(self._value))
        return space.wrap(ord(self._value[0]))

    def _new(self, value):
        return W_BytesObject(value)

    def _len(self):
        return len(self._value)

    def _val(self, space):
        return self._value

    def _op_val(self, space, w_other):
        return space.bufferstr_w(w_other)
        #return w_other._value

    def _chr(self, char):
        return str(char)

    _builder = StringBuilder

    def _isupper(self, ch):
        return ch.isupper()

    def _islower(self, ch):
        return ch.islower()

    def _istitle(self, ch):
        return ch.istitle()

    def _isspace(self, ch):
        return ch.isspace()

    def _isalpha(self, ch):
        return ch.isalpha()

    def _isalnum(self, ch):
        return ch.isalnum()

    def _isdigit(self, ch):
        return ch.isdigit()

    _iscased = _isalpha

    def _upper(self, ch):
        if ch.islower():
            o = ord(ch) - 32
            return chr(o)
        else:
            return ch

    def _lower(self, ch):
        if ch.isupper():
            o = ord(ch) + 32
            return chr(o)
        else:
            return ch

    def _newlist_unwrapped(self, space, lst):
        return space.newlist_str(lst)

    @staticmethod
    @unwrap_spec(w_object = WrappedDefault(""))
    def descr_new(space, w_stringtype, w_object):
        # NB. the default value of w_object is really a *wrapped* empty string:
        #     there is gateway magic at work
        w_obj = space.str(w_object)
        if space.is_w(w_stringtype, space.w_str):
            return w_obj  # XXX might be reworked when space.str() typechecks
        value = space.str_w(w_obj)
        w_obj = space.allocate_instance(W_BytesObject, w_stringtype)
        W_BytesObject.__init__(w_obj, value)
        return w_obj

    def descr_repr(self, space):
        s = self._value
        quote = "'"
        if quote in s and '"' not in s:
            quote = '"'
        return space.wrap(string_escape_encode(s, quote))

    def descr_str(self, space):
        if type(self) is W_BytesObject:
            return self
        return wrapstr(space, self._value)

    def descr_hash(self, space):
        x = compute_hash(self._value)
        return space.wrap(x)

    def descr_format(self, space, __args__):
        return newformat.format_method(space, self, __args__, is_unicode=False)

    def descr__format__(self, space, w_format_spec):
        if not space.isinstance_w(w_format_spec, space.w_str):
            w_format_spec = space.str(w_format_spec)
        spec = space.str_w(w_format_spec)
        formatter = newformat.str_formatter(space, spec)
        return formatter.format_string(self._value)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=False)

    def descr_buffer(self, space):
        return space.wrap(StringBuffer(self._value))

    # auto-conversion fun

    def descr_add(self, space, w_other):
        if space.isinstance_w(w_other, space.w_unicode):
            self_as_unicode = decode_object(space, self, None, None)
            #return self_as_unicode.descr_add(space, w_other)
            return space.add(self_as_unicode, w_other)
        return StringMethods.descr_add(self, space, w_other)

    def _startswith(self, space, value, w_prefix, start, end):
        if space.isinstance_w(w_prefix, space.w_unicode):
            self_as_unicode = decode_object(space, self, None, None)
            return self_as_unicode._startswith(space, value, w_prefix, start, end)
        return StringMethods._startswith(self, space, value, w_prefix, start, end)

    def _endswith(self, space, value, w_suffix, start, end):
        if space.isinstance_w(w_suffix, space.w_unicode):
            self_as_unicode = decode_object(space, self, None, None)
            return self_as_unicode._endswith(space, value, w_suffix, start, end)
        return StringMethods._endswith(self, space, value, w_suffix, start, end)

    def _join_return_one(self, space, w_obj):
        return (space.is_w(space.type(w_obj), space.w_str) or
                space.is_w(space.type(w_obj), space.w_unicode))

    def _join_check_item(self, space, w_obj):
        if space.isinstance_w(w_obj, space.w_str):
            return 0
        if space.isinstance_w(w_obj, space.w_unicode):
            return 2
        return 1

    def _join_autoconvert(self, space, list_w):
        # we need to rebuild w_list here, because the original
        # w_list might be an iterable which we already consumed
        w_list = space.newlist(list_w)
        w_u = space.call_function(space.w_unicode, self)
        return space.call_method(w_u, "join", w_list)


def _create_list_from_string(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_str
    return [s for s in value]

registerimplementation(W_BytesObject)

W_BytesObject.EMPTY = W_BytesObject('')
W_BytesObject.PREBUILT = [W_BytesObject(chr(i)) for i in range(256)]
del i


def wrapstr(space, s):
    if space.config.objspace.std.sharesmallstr:
        if space.config.objspace.std.withprebuiltchar:
            # share characters and empty string
            if len(s) <= 1:
                if len(s) == 0:
                    return W_BytesObject.EMPTY
                else:
                    s = s[0]     # annotator hint: a single char
                    return wrapchar(space, s)
        else:
            # only share the empty string
            if len(s) == 0:
                return W_BytesObject.EMPTY
    return W_BytesObject(s)

def wrapchar(space, c):
    if space.config.objspace.std.withprebuiltchar and not we_are_jitted():
        return W_BytesObject.PREBUILT[ord(c)]
    else:
        return W_BytesObject(c)

str_typedef = W_BytesObject.typedef = StdTypeDef(
    "str", basestring_typedef,
    __new__ = interp2app(W_BytesObject.descr_new),
    __doc__ = '''str(object) -> string

Return a nice string representation of the object.
If the argument is a string, the return value is the same object.''',

    __repr__ = interp2app(W_BytesObject.descr_repr),
    __str__ = interp2app(W_BytesObject.descr_str),
    __hash__ = interp2app(W_BytesObject.descr_hash),

    __eq__ = interp2app(W_BytesObject.descr_eq),
    __ne__ = interp2app(W_BytesObject.descr_ne),
    __lt__ = interp2app(W_BytesObject.descr_lt),
    __le__ = interp2app(W_BytesObject.descr_le),
    __gt__ = interp2app(W_BytesObject.descr_gt),
    __ge__ = interp2app(W_BytesObject.descr_ge),

    __len__ = interp2app(W_BytesObject.descr_len),
    #__iter__ = interp2app(W_BytesObject.descr_iter),
    __contains__ = interp2app(W_BytesObject.descr_contains),

    __add__ = interp2app(W_BytesObject.descr_add),
    __mul__ = interp2app(W_BytesObject.descr_mul),
    __rmul__ = interp2app(W_BytesObject.descr_mul),

    __getitem__ = interp2app(W_BytesObject.descr_getitem),
    __getslice__ = interp2app(W_BytesObject.descr_getslice),

    capitalize = interp2app(W_BytesObject.descr_capitalize),
    center = interp2app(W_BytesObject.descr_center),
    count = interp2app(W_BytesObject.descr_count),
    decode = interp2app(W_BytesObject.descr_decode),
    encode = interp2app(W_BytesObject.descr_encode),
    expandtabs = interp2app(W_BytesObject.descr_expandtabs),
    find = interp2app(W_BytesObject.descr_find),
    rfind = interp2app(W_BytesObject.descr_rfind),
    index = interp2app(W_BytesObject.descr_index),
    rindex = interp2app(W_BytesObject.descr_rindex),
    isalnum = interp2app(W_BytesObject.descr_isalnum),
    isalpha = interp2app(W_BytesObject.descr_isalpha),
    isdigit = interp2app(W_BytesObject.descr_isdigit),
    islower = interp2app(W_BytesObject.descr_islower),
    isspace = interp2app(W_BytesObject.descr_isspace),
    istitle = interp2app(W_BytesObject.descr_istitle),
    isupper = interp2app(W_BytesObject.descr_isupper),
    join = interp2app(W_BytesObject.descr_join),
    ljust = interp2app(W_BytesObject.descr_ljust),
    rjust = interp2app(W_BytesObject.descr_rjust),
    lower = interp2app(W_BytesObject.descr_lower),
    partition = interp2app(W_BytesObject.descr_partition),
    rpartition = interp2app(W_BytesObject.descr_rpartition),
    replace = interp2app(W_BytesObject.descr_replace),
    split = interp2app(W_BytesObject.descr_split),
    rsplit = interp2app(W_BytesObject.descr_rsplit),
    splitlines = interp2app(W_BytesObject.descr_splitlines),
    startswith = interp2app(W_BytesObject.descr_startswith),
    endswith = interp2app(W_BytesObject.descr_endswith),
    strip = interp2app(W_BytesObject.descr_strip),
    lstrip = interp2app(W_BytesObject.descr_lstrip),
    rstrip = interp2app(W_BytesObject.descr_rstrip),
    swapcase = interp2app(W_BytesObject.descr_swapcase),
    title = interp2app(W_BytesObject.descr_title),
    translate = interp2app(W_BytesObject.descr_translate),
    upper = interp2app(W_BytesObject.descr_upper),
    zfill = interp2app(W_BytesObject.descr_zfill),

    format = interp2app(W_BytesObject.descr_format),
    __format__ = interp2app(W_BytesObject.descr__format__),
    __mod__ = interp2app(W_BytesObject.descr_mod),
    __buffer__ = interp2app(W_BytesObject.descr_buffer),
    __getnewargs__ = interp2app(W_BytesObject.descr_getnewargs),
)


def string_escape_encode(s, quote):

    buf = StringBuilder(len(s) + 2)

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

    return buf.build()



#str_formatter_parser           = SMM('_formatter_parser', 1)
#str_formatter_field_name_split = SMM('_formatter_field_name_split', 1)
#
#def str_formatter_parser__ANY(space, w_str):
#    from pypy.objspace.std.newformat import str_template_formatter
#    tformat = str_template_formatter(space, space.str_w(w_str))
#    return tformat.formatter_parser()
#
#def str_formatter_field_name_split__ANY(space, w_str):
#    from pypy.objspace.std.newformat import str_template_formatter
#    tformat = str_template_formatter(space, space.str_w(w_str))
#    return tformat.formatter_field_name_split()
