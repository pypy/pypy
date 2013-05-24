"""The builtin unicode implementation"""

from sys import maxint
from pypy.interpreter import unicodehelper
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.module.unicodedata import unicodedb
from pypy.objspace.std import newformat, slicetype
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.bytesobject import (W_StringObject,
    make_rsplit_with_delim, stringendswith, stringstartswith)
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from rpython.rlib import jit
from rpython.rlib.objectmodel import (compute_hash, compute_unique_id,
    specialize)
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.rstring import UnicodeBuilder
from rpython.rlib.runicode import (str_decode_utf_8, str_decode_ascii,
    unicode_encode_utf_8, unicode_encode_ascii, make_unicode_escape_function)
from rpython.tool.sourcetools import func_with_new_name


class W_AbstractUnicodeObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractUnicodeObject):
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


class W_UnicodeObject(W_AbstractUnicodeObject):
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

    def str_w(self, space):
        return space.str_w(space.str(self))

    def unicode_w(self, space):
        return self._value

    def listview_unicode(w_self):
        return _create_list_from_unicode(w_self._value)


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


unicode_capitalize = SMM('capitalize', 1,
                         doc='S.capitalize() -> unicode\n\nReturn a'
                             ' capitalized version of S, i.e. make the first'
                             ' character\nhave upper case.')
unicode_center     = SMM('center', 3, defaults=(' ',),
                         doc='S.center(width[, fillchar]) -> unicode\n\nReturn'
                             ' S centered in a Unicode string of length width.'
                             ' Padding is\ndone using the specified fill'
                             ' character (default is a space)')
unicode_count      = SMM('count', 4, defaults=(0, maxint),
                         doc='S.count(sub[, start[, end]]) -> int\n\nReturn'
                             ' the number of occurrences of substring sub in'
                             ' Unicode string\nS[start:end].  Optional'
                             ' arguments start and end are\ninterpreted as in'
                             ' slice notation.')
unicode_encode     = SMM('encode', 3, defaults=(None, None),
                         argnames=['encoding', 'errors'],
                         doc='S.encode([encoding[,errors]]) -> string or'
                             ' unicode\n\nEncodes S using the codec registered'
                             ' for encoding. encoding defaults\nto the default'
                             ' encoding. errors may be given to set a'
                             ' different error\nhandling scheme. Default is'
                             " 'strict' meaning that encoding errors raise\na"
                             ' UnicodeEncodeError. Other possible values are'
                             " 'ignore', 'replace' and\n'xmlcharrefreplace' as"
                             ' well as any other name registered'
                             ' with\ncodecs.register_error that can handle'
                             ' UnicodeEncodeErrors.')
unicode_expandtabs = SMM('expandtabs', 2, defaults=(8,),
                         doc='S.expandtabs([tabsize]) -> unicode\n\nReturn a'
                             ' copy of S where all tab characters are expanded'
                             ' using spaces.\nIf tabsize is not given, a tab'
                             ' size of 8 characters is assumed.')
unicode_format     = SMM('format', 1, general__args__=True,
                         doc='S.format() -> new style formating')
unicode_isalnum    = SMM('isalnum', 1,
                         doc='S.isalnum() -> bool\n\nReturn True if all'
                             ' characters in S are alphanumeric\nand there is'
                             ' at least one character in S, False otherwise.')
unicode_isalpha    = SMM('isalpha', 1,
                         doc='S.isalpha() -> bool\n\nReturn True if all'
                             ' characters in S are alphabetic\nand there is at'
                             ' least one character in S, False otherwise.')
unicode_isdecimal  = SMM('isdecimal', 1,
                         doc='S.isdecimal() -> bool\n\nReturn True if there'
                             ' are only decimal characters in S,\nFalse'
                             ' otherwise.')
unicode_isdigit    = SMM('isdigit', 1,
                         doc='S.isdigit() -> bool\n\nReturn True if all'
                             ' characters in S are digits\nand there is at'
                             ' least one character in S, False otherwise.')
unicode_islower    = SMM('islower', 1,
                         doc='S.islower() -> bool\n\nReturn True if all cased'
                             ' characters in S are lowercase and there is\nat'
                             ' least one cased character in S, False'
                             ' otherwise.')
unicode_isnumeric  = SMM('isnumeric', 1,
                         doc='S.isnumeric() -> bool\n\nReturn True if there'
                             ' are only numeric characters in S,\nFalse'
                             ' otherwise.')
unicode_isspace    = SMM('isspace', 1,
                         doc='S.isspace() -> bool\n\nReturn True if all'
                             ' characters in S are whitespace\nand there is at'
                             ' least one character in S, False otherwise.')
unicode_istitle    = SMM('istitle', 1,
                         doc='S.istitle() -> bool\n\nReturn True if S is a'
                             ' titlecased string and there is at least'
                             ' one\ncharacter in S, i.e. upper- and titlecase'
                             ' characters may only\nfollow uncased characters'
                             ' and lowercase characters only cased'
                             ' ones.\nReturn False otherwise.')
unicode_isupper    = SMM('isupper', 1,
                         doc='S.isupper() -> bool\n\nReturn True if all cased'
                             ' characters in S are uppercase and there is\nat'
                             ' least one cased character in S, False'
                             ' otherwise.')
unicode_join       = SMM('join', 2,
                         doc='S.join(sequence) -> unicode\n\nReturn a string'
                             ' which is the concatenation of the strings in'
                             ' the\nsequence.  The separator between elements'
                             ' is S.')
unicode_ljust      = SMM('ljust', 3, defaults=(' ',),
                         doc='S.ljust(width[, fillchar]) -> int\n\nReturn S'
                             ' left justified in a Unicode string of length'
                             ' width. Padding is\ndone using the specified'
                             ' fill character (default is a space).')
unicode_lower      = SMM('lower', 1,
                         doc='S.lower() -> unicode\n\nReturn a copy of the'
                             ' string S converted to lowercase.')
unicode_rjust      = SMM('rjust', 3, defaults=(' ',),
                         doc='S.rjust(width[, fillchar]) -> unicode\n\nReturn'
                             ' S right justified in a Unicode string of length'
                             ' width. Padding is\ndone using the specified'
                             ' fill character (default is a space).')
unicode_swapcase   = SMM('swapcase', 1,
                         doc='S.swapcase() -> unicode\n\nReturn a copy of S'
                             ' with uppercase characters converted to'
                             ' lowercase\nand vice versa.')
unicode_title      = SMM('title', 1,
                         doc='S.title() -> unicode\n\nReturn a titlecased'
                             ' version of S, i.e. words start with title'
                             ' case\ncharacters, all remaining cased'
                             ' characters have lower case.')
unicode_translate  = SMM('translate', 2,
                         doc='S.translate(table) -> unicode\n\nReturn a copy'
                             ' of the string S, where all characters have been'
                             ' mapped\nthrough the given translation table,'
                             ' which must be a mapping of\nUnicode ordinals to'
                             ' Unicode ordinals, Unicode strings or'
                             ' None.\nUnmapped characters are left untouched.'
                             ' Characters mapped to None\nare deleted.')
unicode_upper      = SMM('upper', 1,
                         doc='S.upper() -> unicode\n\nReturn a copy of S'
                             ' converted to uppercase.')
unicode_zfill      = SMM('zfill', 2,
                         doc='S.zfill(width) -> unicode\n\nPad a numeric'
                             ' string x with zeros on the left, to fill a'
                             ' field\nof the specified width. The string x is'
                             ' never truncated.')

unicode_formatter_parser           = SMM('_formatter_parser', 1)
unicode_formatter_field_name_split = SMM('_formatter_field_name_split', 1)

def unicode_formatter_parser__ANY(space, w_unicode):
    from pypy.objspace.std.newformat import unicode_template_formatter
    tformat = unicode_template_formatter(space, space.unicode_w(w_unicode))
    return tformat.formatter_parser()

def unicode_formatter_field_name_split__ANY(space, w_unicode):
    from pypy.objspace.std.newformat import unicode_template_formatter
    tformat = unicode_template_formatter(space, space.unicode_w(w_unicode))
    return tformat.formatter_field_name_split()

# stuff imported from bytesobject for interoperability

from pypy.objspace.std.bytesobject import str_endswith as unicode_endswith
from pypy.objspace.std.bytesobject import str_startswith as unicode_startswith
from pypy.objspace.std.bytesobject import str_find as unicode_find
from pypy.objspace.std.bytesobject import str_index as unicode_index
from pypy.objspace.std.bytesobject import str_replace as unicode_replace
from pypy.objspace.std.bytesobject import str_rfind as unicode_rfind
from pypy.objspace.std.bytesobject import str_rindex as unicode_rindex
from pypy.objspace.std.bytesobject import str_split as unicode_split
from pypy.objspace.std.bytesobject import str_rsplit as unicode_rsplit
from pypy.objspace.std.bytesobject import str_partition as unicode_partition
from pypy.objspace.std.bytesobject import str_rpartition as unicode_rpartition
from pypy.objspace.std.bytesobject import str_splitlines as unicode_splitlines
from pypy.objspace.std.bytesobject import str_strip as unicode_strip
from pypy.objspace.std.bytesobject import str_rstrip as unicode_rstrip
from pypy.objspace.std.bytesobject import str_lstrip as unicode_lstrip
from pypy.objspace.std.bytesobject import str_decode as unicode_decode

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
errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.'''
    )

unicode_typedef.registermethods(globals())

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
    w_uni = unicode_from_string(space, w_str)
    assert isinstance(w_uni, W_UnicodeObject) # help the annotator!
    return w_uni

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

def str__Unicode(space, w_uni):
    return encode_object(space, w_uni, None, None)

def eq__Unicode_Unicode(space, w_left, w_right):
    return space.newbool(w_left._value == w_right._value)

def eq__Unicode_String(space, w_uni, w_str):
    return _unicode_string_comparison(space, w_uni, w_str,
                    False, unicode_from_string)

def ne__Unicode_String(space, w_uni, w_str):
    return _unicode_string_comparison(space, w_uni, w_str,
                    True, unicode_from_string)

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
    # XXX fragile implementation detail: for "string + unicode subclass",
    # if the unicode subclass overrides __radd__(), then it will be
    # called (see test_str_unicode_concat_overrides).  This occurs as a
    # result of the following call to space.add() in which the first
    # argument is a unicode and the second argument a subclass of unicode
    # (and thus the usual logic about calling __radd__() first applies).
    return space.add(unicode_from_string(space, w_left) , w_right)

def add__Unicode_String(space, w_left, w_right):
    # this function is needed to make 'abc'.__radd__(u'def') return
    # u'defabc', although it's completely unclear if that's necessary
    # given that CPython doesn't even have a method str.__radd__().
    return space.add(w_left, unicode_from_string(space, w_right))
    # Note about "unicode + string subclass": look for
    # "cpython bug compatibility" in descroperation.py

def contains__String_Unicode(space, w_container, w_item):
    return space.contains(unicode_from_string(space, w_container), w_item )


def contains__Unicode_Unicode(space, w_container, w_item):
    item = w_item._value
    container = w_container._value
    return space.newbool(container.find(item) != -1)

def unicode_join__Unicode_ANY(space, w_self, w_list):
    l = space.listview_unicode(w_list)
    if l is not None:
        if len(l) == 1:
            return space.wrap(l[0])
        return space.wrap(w_self._value.join(l))
    list_w = space.listview(w_list)
    size = len(list_w)

    if size == 0:
        return W_UnicodeObject.EMPTY

    if size == 1:
        w_s = list_w[0]
        if space.is_w(space.type(w_s), space.w_unicode):
            return w_s

    return _unicode_join_many_items(space, w_self, list_w, size)

@jit.look_inside_iff(lambda space, w_self, list_w, size:
                     jit.loop_unrolling_heuristic(list_w, size))
def _unicode_join_many_items(space, w_self, list_w, size):
    self = w_self._value
    prealloc_size = len(self) * (size - 1)
    for i in range(size):
        try:
            prealloc_size += len(space.unicode_w(list_w[i]))
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            raise operationerrfmt(space.w_TypeError,
                        "sequence item %d: expected string or Unicode", i)
    sb = UnicodeBuilder(prealloc_size)
    for i in range(size):
        if self and i != 0:
            sb.append(self)
        w_s = list_w[i]
        sb.append(space.unicode_w(w_s))
    return space.wrap(sb.build())

def hash__Unicode(space, w_uni):
    x = compute_hash(w_uni._value)
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
    return space.call_method(w_self, 'strip',
                             unicode_from_string(space, w_chars))

def unicode_lstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 0)
def unicode_lstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 0)
def unicode_lstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'lstrip',
                             unicode_from_string(space, w_chars))


def unicode_rstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 0, 1)
def unicode_rstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 0, 1)
def unicode_rstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'rstrip',
                             unicode_from_string(space, w_chars))


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

@specialize.arg(4)
def _convert_idx_params(space, w_self, w_start, w_end, upper_bound=False):
    self = w_self._value
    start, end = slicetype.unwrap_start_stop(
            space, len(self), w_start, w_end, upper_bound)
    return (self, start, end)

def unicode_endswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self,
                                                   w_start, w_end, True)
    return space.newbool(stringendswith(self, w_substr._value, start, end))

def unicode_startswith__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end, True)
    # XXX this stuff can be waaay better for ootypebased backends if
    #     we re-use more of our rpython machinery (ie implement startswith
    #     with additional parameters as rpython)
    return space.newbool(stringstartswith(self, w_substr._value, start, end))

def unicode_startswith__Unicode_ANY_ANY_ANY(space, w_unistr, w_prefixes,
                                              w_start, w_end):
    if not space.isinstance_w(w_prefixes, space.w_tuple):
        raise FailedToImplement
    unistr, start, end = _convert_idx_params(space, w_unistr,
                                             w_start, w_end, True)
    for w_prefix in space.fixedview(w_prefixes):
        prefix = space.unicode_w(w_prefix)
        if stringstartswith(unistr, prefix, start, end):
            return space.w_True
    return space.w_False

def unicode_endswith__Unicode_ANY_ANY_ANY(space, w_unistr, w_suffixes,
                                            w_start, w_end):
    if not space.isinstance_w(w_suffixes, space.w_tuple):
        raise FailedToImplement
    unistr, start, end = _convert_idx_params(space, w_unistr,
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
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    return space.wrap(self.find(w_substr._value, start, end))

def unicode_rfind__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    return space.wrap(self.rfind(w_substr._value, start, end))

def unicode_index__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    index = self.find(w_substr._value, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_rindex__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    index = self.rfind(w_substr._value, start, end)
    if index < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('substring not found'))
    return space.wrap(index)

def unicode_count__Unicode_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    return space.wrap(self.count(w_substr._value, start, end))

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

_repr_function, _ = make_unicode_escape_function(
    pass_printable=False, unicode_output=False, quotes=True, prefix='u')

def repr__Unicode(space, w_unicode):
    chars = w_unicode._value
    size = len(chars)
    s = _repr_function(chars, size, "strict")
    return space.wrap(s)

def mod__Unicode_ANY(space, w_format, w_values):
    return mod_format(space, w_format, w_values, do_unicode=True)

def unicode_format__Unicode(space, w_unicode, __args__):
    return newformat.format_method(space, w_unicode, __args__, True)

def format__Unicode_ANY(space, w_unicode, w_format_spec):
    if not space.isinstance_w(w_format_spec, space.w_unicode):
        w_format_spec = space.call_function(space.w_unicode, w_format_spec)
    w_unicode = unicode_from_object(space, w_unicode)
    spec = space.unicode_w(w_format_spec)
    formatter = newformat.unicode_formatter(space, spec)
    return formatter.format_string(space.unicode_w(w_unicode))


register_all(vars(), globals())

# str.strip(unicode) needs to convert self to unicode and call unicode.strip we
# use the following magic to register strip_string_unicode as a String
# multimethod.

# XXX couldn't string and unicode _share_ the multimethods that make up their
# methods?

class str_methods:
    from pypy.objspace.std import bytesobject
    W_UnicodeObject = W_UnicodeObject
    from pypy.objspace.std.bytesobject import W_BytesObject as W_StringObject
    def str_strip__String_Unicode(space, w_self, w_chars):
        return space.call_method(unicode_from_string(space, w_self),
                                 'strip', w_chars)
    def str_lstrip__String_Unicode(space, w_self, w_chars):
        return space.call_method(unicode_from_string(space, w_self),
                                 'lstrip', w_chars)
    def str_rstrip__String_Unicode(space, w_self, w_chars):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rstrip', w_chars)
    def str_count__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'count', w_substr, w_start, w_end)
    def str_find__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'find', w_substr, w_start, w_end)
    def str_rfind__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rfind', w_substr, w_start, w_end)
    def str_index__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'index', w_substr, w_start, w_end)
    def str_rindex__String_Unicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rindex', w_substr, w_start, w_end)
    def str_replace__String_Unicode_Unicode_ANY(space, w_self, w_old, w_new, w_maxsplit):
        return space.call_method(unicode_from_string(space, w_self),
                                 'replace', w_old, w_new, w_maxsplit)
    def str_split__String_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
        return space.call_method(unicode_from_string(space, w_self),
                                 'split', w_delim, w_maxsplit)
    def str_rsplit__String_Unicode_ANY(space, w_self, w_delim, w_maxsplit):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rsplit', w_delim, w_maxsplit)
    register_all(vars(), bytesobject)
