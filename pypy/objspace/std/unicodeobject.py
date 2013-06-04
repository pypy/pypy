"""The builtin unicode implementation"""

from pypy.interpreter import unicodehelper
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.module.unicodedata import unicodedb
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.stringmethods import StringMethods
from rpython.rlib.objectmodel import compute_hash, compute_unique_id
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.rstring import UnicodeBuilder
from rpython.rlib.runicode import (str_decode_utf_8, str_decode_ascii,
    unicode_encode_utf_8, unicode_encode_ascii, make_unicode_escape_function)
from rpython.tool.sourcetools import func_with_new_name

__all__ = ['W_UnicodeObject', 'wrapunicode', 'plain_str2unicode',
           'encode_object', 'decode_object', 'unicode_from_object',
           'unicode_from_string', 'unicode_to_decimal_w']


class W_UnicodeObject(W_Object, StringMethods):
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

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_UnicodeObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return space.unicode_w(self) is space.unicode_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(space.unicode_w(self)))

    def str_w(self, space):
        return space.str_w(space.str(self))

    def unicode_w(self, space):
        return self._value

    def listview_unicode(w_self):
        return _create_list_from_unicode(w_self._value)

    def ord(self, space):
        if len(self._value) != 1:
            msg = "ord() expected a character, but string of length %d found"
            raise operationerrfmt(space.w_TypeError, msg, len(self._value))
        return space.wrap(ord(self._value[0]))

    def _new(self, value):
        return W_UnicodeObject(value)

    def _len(self):
        return len(self._value)

    def _val(self):
        return self._value

    def _op_val(self, space, w_other):
        return unicode_from_object2(space, w_other)._value
        #return w_other._value

    def _chr(self, char):
        return unicode(char)

    _builder = UnicodeBuilder

    def descr_repr(self, space):
        chars = self._value
        size = len(chars)
        s = _repr_function(chars, size, "strict")
        return space.wrap(s)

    def descr_str(self, space):
        return encode_object(space, self, None, None)

    def descr_hash(self, space):
        x = compute_hash(self._value)
        return space.wrap(x)

    def descr_format(self, space, __args__):
        return newformat.format_method(space, self, __args__, is_unicode=True)

    def descr__format__(self, space, w_format_spec):
        if not space.isinstance_w(w_format_spec, space.w_unicode):
            w_format_spec = space.call_function(space.w_unicode, w_format_spec)
        spec = space.unicode_w(w_format_spec)
        formatter = newformat.unicode_formatter(space, spec)
        return formatter.format_string(unicode_from_object(space, self))
        #return formatter.format_string(space.unicode_w(self))

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=True)

    def descr_translate(self, space, w_table):
        selfvalue = self._value
        w_sys = space.getbuiltinmodule('sys')
        maxunicode = space.int_w(space.getattr(w_sys, space.wrap("maxunicode")))
        result = []
        for unichar in selfvalue:
            try:
                w_newval = space.getitem(w_table, space.wrap(ord(unichar)))
            except OperationError, e:
                if e.match(space, space.w_LookupError):
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

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
        return encode_object(space, self, encoding, errors)

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def _join_check_item(self, space, w_obj):
        if (space.is_w(space.type(w_obj), space.w_str) or
            space.is_w(space.type(w_obj), space.w_unicode)):
            return 0
        return 1


def wrapunicode(space, uni):
    return W_UnicodeObject(uni)

def plain_str2unicode(space, s):
    try:
        return unicode(s)
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
        assert False, "unreachable"


#def unicode_formatter_parser__ANY(space, w_unicode):
#    from pypy.objspace.std.newformat import unicode_template_formatter
#    tformat = unicode_template_formatter(space, space.unicode_w(w_unicode))
#    return tformat.formatter_parser()
#
#def unicode_formatter_field_name_split__ANY(space, w_unicode):
#    from pypy.objspace.std.newformat import unicode_template_formatter
#    tformat = unicode_template_formatter(space, space.unicode_w(w_unicode))
#    return tformat.formatter_field_name_split()

# stuff imported from bytesobject for interoperability


# ____________________________________________________________

def getdefaultencoding(space):
    return space.sys.defaultencoding

def _get_encoding_and_errors(space, w_encoding, w_errors):
    if space.is_none(w_encoding):
        encoding = None
    else:
        encoding = space.str_w(w_encoding)
    if space.is_none(w_errors):
        errors = None
    else:
        errors = space.str_w(w_errors)
    return encoding, errors

def encode_object(space, w_object, encoding, errors):
    if encoding is None:
        # Get the encoder functions as a wrapped object.
        # This lookup is cached.
        w_encoder = space.sys.get_w_default_encoder()
    else:
        if errors is None or errors == 'strict':
            if encoding == 'ascii':
                u = space.unicode_w(w_object)
                eh = unicodehelper.encode_error_handler(space)
                return space.wrap(unicode_encode_ascii(
                        u, len(u), None, errorhandler=eh))
            if encoding == 'utf-8':
                u = space.unicode_w(w_object)
                eh = unicodehelper.encode_error_handler(space)
                return space.wrap(unicode_encode_utf_8(
                        u, len(u), None, errorhandler=eh,
                        allow_surrogates=True))
        from pypy.module._codecs.interp_codecs import lookup_codec
        w_encoder = space.getitem(lookup_codec(space, encoding), space.wrap(0))
    if errors is None:
        w_errors = space.wrap('strict')
    else:
        w_errors = space.wrap(errors)
    w_restuple = space.call_function(w_encoder, w_object, w_errors)
    w_retval = space.getitem(w_restuple, space.wrap(0))
    if not space.isinstance_w(w_retval, space.w_str):
        raise operationerrfmt(space.w_TypeError,
            "encoder did not return an string object (type '%s')",
            space.type(w_retval).getname(space))
    return w_retval

def decode_object(space, w_obj, encoding, errors):
    if encoding is None:
        encoding = getdefaultencoding(space)
    if errors is None or errors == 'strict':
        if encoding == 'ascii':
            # XXX error handling
            s = space.bufferstr_w(w_obj)
            eh = unicodehelper.decode_error_handler(space)
            return space.wrap(str_decode_ascii(
                    s, len(s), None, final=True, errorhandler=eh)[0])
        if encoding == 'utf-8':
            s = space.bufferstr_w(w_obj)
            eh = unicodehelper.decode_error_handler(space)
            return space.wrap(str_decode_utf_8(
                    s, len(s), None, final=True, errorhandler=eh,
                    allow_surrogates=True)[0])
    w_codecs = space.getbuiltinmodule("_codecs")
    w_decode = space.getattr(w_codecs, space.wrap("decode"))
    if errors is None:
        w_retval = space.call_function(w_decode, w_obj, space.wrap(encoding))
    else:
        w_retval = space.call_function(w_decode, w_obj, space.wrap(encoding),
                                       space.wrap(errors))
    return w_retval


def unicode_from_encoded_object(space, w_obj, encoding, errors):
    w_retval = decode_object(space, w_obj, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_unicode):
        raise operationerrfmt(space.w_TypeError,
            "decoder did not return an unicode object (type '%s')",
            space.type(w_retval).getname(space))
    return w_retval

def unicode_from_object(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    elif space.is_w(space.type(w_obj), space.w_str):
        w_res = w_obj
    else:
        w_unicode_method = space.lookup(w_obj, "__unicode__")
        # obscure workaround: for the next two lines see
        # test_unicode_conversion_with__str__
        if w_unicode_method is None:
            if space.isinstance_w(w_obj, space.w_unicode):
                return space.wrap(space.unicode_w(w_obj))
            w_unicode_method = space.lookup(w_obj, "__str__")
        if w_unicode_method is not None:
            w_res = space.get_and_call_function(w_unicode_method, w_obj)
        else:
            w_res = space.str(w_obj)
        if space.isinstance_w(w_res, space.w_unicode):
            return w_res
    return unicode_from_encoded_object(space, w_res, None, "strict")

# XXX refactor / rename / share with unicode_from_object
def unicode_from_object2(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    elif isinstance(w_obj, W_UnicodeObject):
        return W_UnicodeObject(w_obj._value)
    return unicode_from_encoded_object(space, w_obj, None, "strict")

def unicode_from_string(space, w_str):
    # this is a performance and bootstrapping hack
    encoding = getdefaultencoding(space)
    if encoding != 'ascii':
        return unicode_from_encoded_object(space, w_str, encoding, "strict")
    s = space.str_w(w_str)
    try:
        return W_UnicodeObject(s.decode("ascii"))
    except UnicodeDecodeError:
        # raising UnicodeDecodeError is messy, "please crash for me"
        return unicode_from_encoded_object(space, w_str, "ascii", "strict")

def unicode_decode__unitypedef_ANY_ANY(space, w_unicode, w_encoding=None,
                                       w_errors=None):
    return space.call_method(space.str(w_unicode), 'decode',
                             w_encoding, w_errors)


@unwrap_spec(w_string = WrappedDefault(""))
def descr_new_(space, w_unicodetype, w_string, w_encoding=None, w_errors=None):
    # NB. the default value of w_obj is really a *wrapped* empty string:
    #     there is gateway magic at work
    w_obj = w_string

    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    # convoluted logic for the case when unicode subclass has a __unicode__
    # method, we need to call this method
    if (space.is_w(space.type(w_obj), space.w_unicode) or
        (space.isinstance_w(w_obj, space.w_unicode) and
         space.findattr(w_obj, space.wrap('__unicode__')) is None)):
        if encoding is not None or errors is not None:
            raise OperationError(space.w_TypeError,
                                 space.wrap('decoding Unicode is not supported'))
        w_value = w_obj
    else:
        if encoding is None and errors is None:
            w_value = unicode_from_object(space, w_obj)
        else:
            w_value = unicode_from_encoded_object(space, w_obj,
                                                  encoding, errors)
        if space.is_w(w_unicodetype, space.w_unicode):
            return w_value

    assert isinstance(w_value, W_UnicodeObject)
    w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
    W_UnicodeObject.__init__(w_newobj, w_value._value)
    return w_newobj

# ____________________________________________________________

unicode_typedef = W_UnicodeObject.typedef = StdTypeDef(
    "unicode", basestring_typedef,
    __new__ = interp2app(descr_new_),
    __doc__ = '''unicode(string [, encoding[, errors]]) -> object

Create a new Unicode object from the given encoded string.
encoding defaults to the current default string encoding.
errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.''',

    __repr__ = interp2app(W_UnicodeObject.descr_repr),
    __str__ = interp2app(W_UnicodeObject.descr_str),
    __hash__ = interp2app(W_UnicodeObject.descr_hash),

    __eq__ = interp2app(W_UnicodeObject.descr_eq),
    __ne__ = interp2app(W_UnicodeObject.descr_ne),
    __lt__ = interp2app(W_UnicodeObject.descr_lt),
    __le__ = interp2app(W_UnicodeObject.descr_le),
    __gt__ = interp2app(W_UnicodeObject.descr_gt),
    __ge__ = interp2app(W_UnicodeObject.descr_ge),

    __len__ = interp2app(W_UnicodeObject.descr_len),
    #__iter__ = interp2app(W_UnicodeObject.descr_iter),
    __contains__ = interp2app(W_UnicodeObject.descr_contains),

    __add__ = interp2app(W_UnicodeObject.descr_add),
    __mul__ = interp2app(W_UnicodeObject.descr_mul),
    __rmul__ = interp2app(W_UnicodeObject.descr_mul),

    __getitem__ = interp2app(W_UnicodeObject.descr_getitem),
    __getslice__ = interp2app(W_UnicodeObject.descr_getslice),

    capitalize = interp2app(W_UnicodeObject.descr_capitalize),
    center = interp2app(W_UnicodeObject.descr_center),
    count = interp2app(W_UnicodeObject.descr_count),
    decode = interp2app(W_UnicodeObject.descr_decode),
    encode = interp2app(W_UnicodeObject.descr_encode),
    expandtabs = interp2app(W_UnicodeObject.descr_expandtabs),
    find = interp2app(W_UnicodeObject.descr_find),
    rfind = interp2app(W_UnicodeObject.descr_rfind),
    index = interp2app(W_UnicodeObject.descr_index),
    rindex = interp2app(W_UnicodeObject.descr_rindex),
    isalnum = interp2app(W_UnicodeObject.descr_isalnum),
    isalpha = interp2app(W_UnicodeObject.descr_isalpha),
    isdigit = interp2app(W_UnicodeObject.descr_isdigit),
    islower = interp2app(W_UnicodeObject.descr_islower),
    isspace = interp2app(W_UnicodeObject.descr_isspace),
    istitle = interp2app(W_UnicodeObject.descr_istitle),
    isupper = interp2app(W_UnicodeObject.descr_isupper),
    join = interp2app(W_UnicodeObject.descr_join),
    ljust = interp2app(W_UnicodeObject.descr_ljust),
    rjust = interp2app(W_UnicodeObject.descr_rjust),
    lower = interp2app(W_UnicodeObject.descr_lower),
    partition = interp2app(W_UnicodeObject.descr_partition),
    rpartition = interp2app(W_UnicodeObject.descr_rpartition),
    replace = interp2app(W_UnicodeObject.descr_replace),
    split = interp2app(W_UnicodeObject.descr_split),
    rsplit = interp2app(W_UnicodeObject.descr_rsplit),
    splitlines = interp2app(W_UnicodeObject.descr_splitlines),
    startswith = interp2app(W_UnicodeObject.descr_startswith),
    endswith = interp2app(W_UnicodeObject.descr_endswith),
    strip = interp2app(W_UnicodeObject.descr_strip),
    lstrip = interp2app(W_UnicodeObject.descr_lstrip),
    rstrip = interp2app(W_UnicodeObject.descr_rstrip),
    swapcase = interp2app(W_UnicodeObject.descr_swapcase),
    title = interp2app(W_UnicodeObject.descr_title),
    translate = interp2app(W_UnicodeObject.descr_translate),
    upper = interp2app(W_UnicodeObject.descr_upper),
    zfill = interp2app(W_UnicodeObject.descr_zfill),

    format = interp2app(W_UnicodeObject.descr_format),
    __format__ = interp2app(W_UnicodeObject.descr__format__),
    __mod__ = interp2app(W_UnicodeObject.descr_mod),
    __getnewargs__ = interp2app(W_UnicodeObject.descr_getnewargs),
)

unitypedef = unicode_typedef


def _create_list_from_unicode(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_unicode
    return [s for s in value]


W_UnicodeObject.EMPTY = W_UnicodeObject(u'')

registerimplementation(W_UnicodeObject)

# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise operationerrfmt(space.w_TypeError, "expected unicode, got '%T'",
                              w_unistr)
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

# checks if should trigger an unicode warning
def _unicode_string_comparison(space, w_uni, w_str, inverse, uni_from_str):
    try:
        w_uni2 = uni_from_str(space, w_str)
    except OperationError, e:
        if e.match(space, space.w_UnicodeDecodeError):
            msg = ("Unicode %s comparison failed to convert both arguments to "
                   "Unicode - interpreting them as being unequal" %
                   "unequal" if inverse else "equal")
            space.warn(space.wrap(msg), space.w_UnicodeWarning)
            return space.newbool(inverse)
        raise
    result = space.eq(w_uni, w_uni2)
    if inverse:
        return space.not_(result)
    return result

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


def unicode_capitalize__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return W_UnicodeObject.EMPTY
    builder = UnicodeBuilder(len(input))
    builder.append(unichr(unicodedb.toupper(ord(input[0]))))
    for i in range(1, len(input)):
        builder.append(unichr(unicodedb.tolower(ord(input[i]))))
    return W_UnicodeObject(builder.build())

def unicode_title__Unicode(space, w_self):
    input = w_self._value
    if len(input) == 0:
        return w_self

    builder = UnicodeBuilder(len(input))
    previous_is_cased = False
    for i in range(len(input)):
        unichar = ord(input[i])
        if previous_is_cased:
            builder.append(unichr(unicodedb.tolower(unichar)))
        else:
            builder.append(unichr(unicodedb.totitle(unichar)))
        previous_is_cased = unicodedb.iscased(unichar)
    return W_UnicodeObject(builder.build())

def unicode_lower__Unicode(space, w_self):
    input = w_self._value
    builder = UnicodeBuilder(len(input))
    for i in range(len(input)):
        builder.append(unichr(unicodedb.tolower(ord(input[i]))))
    return W_UnicodeObject(builder.build())

def unicode_upper__Unicode(space, w_self):
    input = w_self._value
    builder = UnicodeBuilder(len(input))
    for i in range(len(input)):
        builder.append(unichr(unicodedb.toupper(ord(input[i]))))
    return W_UnicodeObject(builder.build())

def unicode_swapcase__Unicode(space, w_self):
    input = w_self._value
    builder = UnicodeBuilder(len(input))
    for i in range(len(input)):
        unichar = ord(input[i])
        if unicodedb.islower(unichar):
            builder.append(unichr(unicodedb.toupper(unichar)))
        elif unicodedb.isupper(unichar):
            builder.append(unichr(unicodedb.tolower(unichar)))
        else:
            builder.append(input[i])
    return W_UnicodeObject(builder.build())

def _normalize_index(length, index):
    if index < 0:
        index += length
        if index < 0:
            index = 0
    elif index > length:
        index = length
    return index

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

#unicode_rsplit__Unicode_Unicode_ANY = make_rsplit_with_delim('unicode_rsplit__Unicode_Unicode_ANY',
#                                                             sliced)

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


def unicode_expandtabs__Unicode_ANY(space, w_self, tabsize):
    self = w_self._value
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

_repr_function, _ = make_unicode_escape_function(
    pass_printable=False, unicode_output=False, quotes=True, prefix='u')
