from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.rlib.runicode import str_decode_utf_8, str_decode_ascii,\
     unicode_encode_utf_8, unicode_encode_ascii

from sys import maxint

def wrapunicode(space, uni):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    from pypy.objspace.std.ropeunicodeobject import wrapunicode
    if space.config.objspace.std.withropeunicode:
        return wrapunicode(space, uni)
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

# stuff imported from stringtype for interoperability

from pypy.objspace.std.stringtype import str_endswith as unicode_endswith
from pypy.objspace.std.stringtype import str_startswith as unicode_startswith
from pypy.objspace.std.stringtype import str_find as unicode_find
from pypy.objspace.std.stringtype import str_index as unicode_index
from pypy.objspace.std.stringtype import str_replace as unicode_replace
from pypy.objspace.std.stringtype import str_rfind as unicode_rfind
from pypy.objspace.std.stringtype import str_rindex as unicode_rindex
from pypy.objspace.std.stringtype import str_split as unicode_split
from pypy.objspace.std.stringtype import str_rsplit as unicode_rsplit
from pypy.objspace.std.stringtype import str_partition as unicode_partition
from pypy.objspace.std.stringtype import str_rpartition as unicode_rpartition
from pypy.objspace.std.stringtype import str_splitlines as unicode_splitlines
from pypy.objspace.std.stringtype import str_strip as unicode_strip
from pypy.objspace.std.stringtype import str_rstrip as unicode_rstrip
from pypy.objspace.std.stringtype import str_lstrip as unicode_lstrip
from pypy.objspace.std.stringtype import str_decode as unicode_decode

# ____________________________________________________________

def decode_error_handler(space):
    def raise_unicode_exception_decode(errors, encoding, msg, s,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeDecodeError,
                             space.newtuple([space.wrap(encoding),
                                             space.wrap(s),
                                             space.wrap(startingpos),
                                             space.wrap(endingpos),
                                             space.wrap(msg)]))
    return raise_unicode_exception_decode
decode_error_handler._annspecialcase_ = 'specialize:memo'

def encode_error_handler(space):
    def raise_unicode_exception_encode(errors, encoding, msg, u,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeEncodeError,
                             space.newtuple([space.wrap(encoding),
                                             space.wrap(u),
                                             space.wrap(startingpos),
                                             space.wrap(endingpos),
                                             space.wrap(msg)]))
    return raise_unicode_exception_encode
encode_error_handler._annspecialcase_ = 'specialize:memo'

# ____________________________________________________________

def getdefaultencoding(space):
    return space.sys.defaultencoding

def _get_encoding_and_errors(space, w_encoding, w_errors):
    if space.is_w(w_encoding, space.w_None):
        encoding = None
    else:
        encoding = space.str_w(w_encoding)
    if space.is_w(w_errors, space.w_None):
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
                eh = encode_error_handler(space)
                return space.wrap(unicode_encode_ascii(u, len(u), None,
                                                       errorhandler=eh))
            if encoding == 'utf-8':
                u = space.unicode_w(w_object)
                eh = encode_error_handler(space)
                return space.wrap(unicode_encode_utf_8(u, len(u), None,
                                                       errorhandler=eh))
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
            eh = decode_error_handler(space)
            return space.wrap(str_decode_ascii(s, len(s), None,
                                               final=True,
                                               errorhandler=eh)[0])
        if encoding == 'utf-8':
            s = space.bufferstr_w(w_obj)
            eh = decode_error_handler(space)
            return space.wrap(str_decode_utf_8(s, len(s), None,
                                               final=True,
                                               errorhandler=eh)[0])
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
    if space.config.objspace.std.withropeunicode:
        from pypy.objspace.std.ropeunicodeobject import unicode_from_string
        return unicode_from_string(space, w_str)
    encoding = getdefaultencoding(space)
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
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


def descr_new_(space, w_unicodetype, w_string='', w_encoding=None, w_errors=None):
    # NB. the default value of w_obj is really a *wrapped* empty string:
    #     there is gateway magic at work
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    from pypy.objspace.std.ropeunicodeobject import W_RopeUnicodeObject
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

    if space.config.objspace.std.withropeunicode:
        assert isinstance(w_value, W_RopeUnicodeObject)
        w_newobj = space.allocate_instance(W_RopeUnicodeObject, w_unicodetype)
        W_RopeUnicodeObject.__init__(w_newobj, w_value._node)
        return w_newobj

    assert isinstance(w_value, W_UnicodeObject)
    w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
    W_UnicodeObject.__init__(w_newobj, w_value._value)
    return w_newobj

# ____________________________________________________________

unicode_typedef = StdTypeDef("unicode", basestring_typedef,
    __new__ = gateway.interp2app(descr_new_),
    __doc__ = '''unicode(string [, encoding[, errors]]) -> object

Create a new Unicode object from the given encoded string.
encoding defaults to the current default string encoding.
errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.'''
    )

unicode_typedef.registermethods(globals())

unitypedef = unicode_typedef
register_all(vars(), globals())
