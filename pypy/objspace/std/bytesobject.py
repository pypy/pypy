"""The builtin str implementation"""

from sys import maxint
from pypy.interpreter.buffer import StringBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.objspace.std import newformat, slicetype
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.stringmethods import StringMethods
from rpython.rlib import jit
from rpython.rlib.jit import we_are_jitted
from rpython.rlib.objectmodel import (compute_hash, compute_unique_id,
        specialize)
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.rstring import StringBuilder, split


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

    def unicode_w(w_self, space):
        # Use the default encoding.
        from pypy.objspace.std.unicodetype import (unicode_from_string,
            decode_object, _get_encoding_and_errors)
        w_defaultencoding = space.call_function(space.sys.get(
                                                'getdefaultencoding'))
        encoding, errors = _get_encoding_and_errors(space, w_defaultencoding,
                                                    space.w_None)
        if encoding is None and errors is None:
            return space.unicode_w(unicode_from_string(space, w_self))
        return space.unicode_w(decode_object(space, w_self, encoding, errors))


class W_BytesObject(W_AbstractBytesObject, StringMethods):
    _immutable_fields_ = ['_value']

    def __init__(w_self, str):
        w_self._value = str

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self, space):
        return w_self._value

    def str_w(w_self, space):
        return w_self._value

    def listview_str(w_self):
        return _create_list_from_string(w_self._value)

    def _new(self, value):
        return W_BytesObject(value)

    def _len(self):
        return len(self._value)

    def _val(self):
        return self._value


W_StringObject = W_BytesObject

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

def sliced(space, s, start, stop, orig_obj):
    assert start >= 0
    assert stop >= 0
    if start == 0 and stop == len(s) and space.is_w(space.type(orig_obj), space.w_str):
        return orig_obj
    return wrapstr(space, s[start:stop])

def joined2(space, str1, str2):
    if space.config.objspace.std.withstrbuf:
        from pypy.objspace.std.strbufobject import joined2
        return joined2(str1, str2)
    else:
        return wrapstr(space, str1 + str2)

str_join    = SMM('join', 2,
                  doc='S.join(sequence) -> string\n\nReturn a string which is'
                      ' the concatenation of the strings in the\nsequence. '
                      ' The separator between elements is S.')
str_split   = SMM('split', 3, defaults=(None,-1),
                  doc='S.split([sep [,maxsplit]]) -> list of strings\n\nReturn'
                      ' a list of the words in the string S, using sep as'
                      ' the\ndelimiter string.  If maxsplit is given, at most'
                      ' maxsplit\nsplits are done. If sep is not specified or'
                      ' is None, any\nwhitespace string is a separator.')
str_rsplit  = SMM('rsplit', 3, defaults=(None,-1),
                  doc='S.rsplit([sep [,maxsplit]]) -> list of'
                      ' strings\n\nReturn a list of the words in the string S,'
                      ' using sep as the\ndelimiter string, starting at the'
                      ' end of the string and working\nto the front.  If'
                      ' maxsplit is given, at most maxsplit splits are\ndone.'
                      ' If sep is not specified or is None, any whitespace'
                      ' string\nis a separator.')
str_format     = SMM('format', 1, general__args__=True)
str_isdigit    = SMM('isdigit', 1,
                     doc='S.isdigit() -> bool\n\nReturn True if all characters'
                         ' in S are digits\nand there is at least one'
                         ' character in S, False otherwise.')
str_isalpha    = SMM('isalpha', 1,
                     doc='S.isalpha() -> bool\n\nReturn True if all characters'
                         ' in S are alphabetic\nand there is at least one'
                         ' character in S, False otherwise.')
str_isspace    = SMM('isspace', 1,
                     doc='S.isspace() -> bool\n\nReturn True if all characters'
                         ' in S are whitespace\nand there is at least one'
                         ' character in S, False otherwise.')
str_isupper    = SMM('isupper', 1,
                     doc='S.isupper() -> bool\n\nReturn True if all cased'
                         ' characters in S are uppercase and there is\nat'
                         ' least one cased character in S, False otherwise.')
str_islower    = SMM('islower', 1,
                     doc='S.islower() -> bool\n\nReturn True if all cased'
                         ' characters in S are lowercase and there is\nat'
                         ' least one cased character in S, False otherwise.')
str_istitle    = SMM('istitle', 1,
                     doc='S.istitle() -> bool\n\nReturn True if S is a'
                         ' titlecased string and there is at least'
                         ' one\ncharacter in S, i.e. uppercase characters may'
                         ' only follow uncased\ncharacters and lowercase'
                         ' characters only cased ones. Return'
                         ' False\notherwise.')
str_isalnum    = SMM('isalnum', 1,
                     doc='S.isalnum() -> bool\n\nReturn True if all characters'
                         ' in S are alphanumeric\nand there is at least one'
                         ' character in S, False otherwise.')
str_ljust      = SMM('ljust', 3, defaults=(' ',),
                     doc='S.ljust(width[, fillchar]) -> string\n\nReturn S'
                         ' left justified in a string of length width. Padding'
                         ' is\ndone using the specified fill character'
                         ' (default is a space).')
str_rjust      = SMM('rjust', 3, defaults=(' ',),
                     doc='S.rjust(width[, fillchar]) -> string\n\nReturn S'
                         ' right justified in a string of length width.'
                         ' Padding is\ndone using the specified fill character'
                         ' (default is a space)')
str_upper      = SMM('upper', 1,
                     doc='S.upper() -> string\n\nReturn a copy of the string S'
                         ' converted to uppercase.')
str_lower      = SMM('lower', 1,
                     doc='S.lower() -> string\n\nReturn a copy of the string S'
                         ' converted to lowercase.')
str_swapcase   = SMM('swapcase', 1,
                     doc='S.swapcase() -> string\n\nReturn a copy of the'
                         ' string S with uppercase characters\nconverted to'
                         ' lowercase and vice versa.')
str_capitalize = SMM('capitalize', 1,
                     doc='S.capitalize() -> string\n\nReturn a copy of the'
                         ' string S with only its first'
                         ' character\ncapitalized.')
str_title      = SMM('title', 1,
                     doc='S.title() -> string\n\nReturn a titlecased version'
                         ' of S, i.e. words start with uppercase\ncharacters,'
                         ' all remaining cased characters have lowercase.')
str_find       = SMM('find', 4, defaults=(0, maxint),
                     doc='S.find(sub [,start [,end]]) -> int\n\nReturn the'
                         ' lowest index in S where substring sub is'
                         ' found,\nsuch that sub is contained within'
                         ' s[start,end].  Optional\narguments start and end'
                         ' are interpreted as in slice notation.\n\nReturn -1'
                         ' on failure.')
str_rfind      = SMM('rfind', 4, defaults=(0, maxint),
                     doc='S.rfind(sub [,start [,end]]) -> int\n\nReturn the'
                         ' highest index in S where substring sub is'
                         ' found,\nsuch that sub is contained within'
                         ' s[start,end].  Optional\narguments start and end'
                         ' are interpreted as in slice notation.\n\nReturn -1'
                         ' on failure.')
str_partition  = SMM('partition', 2,
                     doc='S.partition(sep) -> (head, sep, tail)\n\nSearches'
                         ' for the separator sep in S, and returns the part before'
                         ' it,\nthe separator itself, and the part after it.  If'
                         ' the separator is not\nfound, returns S and two empty'
                         ' strings.')
str_rpartition = SMM('rpartition', 2,
                     doc='S.rpartition(sep) -> (tail, sep, head)\n\nSearches'
                         ' for the separator sep in S, starting at the end of S,'
                         ' and returns\nthe part before it, the separator itself,'
                         ' and the part after it.  If the\nseparator is not found,'
                         ' returns two empty strings and S.')
str_index      = SMM('index', 4, defaults=(0, maxint),
                     doc='S.index(sub [,start [,end]]) -> int\n\nLike S.find()'
                         ' but raise ValueError when the substring is not'
                         ' found.')
str_rindex     = SMM('rindex', 4, defaults=(0, maxint),
                     doc='S.rindex(sub [,start [,end]]) -> int\n\nLike'
                         ' S.rfind() but raise ValueError when the substring'
                         ' is not found.')
str_replace    = SMM('replace', 4, defaults=(-1,),
                     doc='S.replace (old, new[, count]) -> string\n\nReturn a'
                         ' copy of string S with all occurrences of'
                         ' substring\nold replaced by new.  If the optional'
                         ' argument count is\ngiven, only the first count'
                         ' occurrences are replaced.')
str_zfill      = SMM('zfill', 2,
                     doc='S.zfill(width) -> string\n\nPad a numeric string S'
                         ' with zeros on the left, to fill a field\nof the'
                         ' specified width.  The string S is never truncated.')
str_strip      = SMM('strip',  2, defaults=(None,),
                     doc='S.strip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with leading and'
                         ' trailing\nwhitespace removed.\nIf chars is given'
                         ' and not None, remove characters in chars'
                         ' instead.\nIf chars is unicode, S will be converted'
                         ' to unicode before stripping')
str_rstrip     = SMM('rstrip', 2, defaults=(None,),
                     doc='S.rstrip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with trailing whitespace'
                         ' removed.\nIf chars is given and not None, remove'
                         ' characters in chars instead.\nIf chars is unicode,'
                         ' S will be converted to unicode before stripping')
str_lstrip     = SMM('lstrip', 2, defaults=(None,),
                     doc='S.lstrip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with leading whitespace'
                         ' removed.\nIf chars is given and not None, remove'
                         ' characters in chars instead.\nIf chars is unicode,'
                         ' S will be converted to unicode before stripping')
str_center     = SMM('center', 3, defaults=(' ',),
                     doc='S.center(width[, fillchar]) -> string\n\nReturn S'
                         ' centered in a string of length width. Padding'
                         ' is\ndone using the specified fill character'
                         ' (default is a space)')
str_count      = SMM('count', 4, defaults=(0, maxint),
                     doc='S.count(sub[, start[, end]]) -> int\n\nReturn the'
                         ' number of occurrences of substring sub in'
                         ' string\nS[start:end].  Optional arguments start and'
                         ' end are\ninterpreted as in slice notation.')
str_endswith   = SMM('endswith', 4, defaults=(0, maxint),
                     doc='S.endswith(suffix[, start[, end]]) -> bool\n\nReturn'
                         ' True if S ends with the specified suffix, False'
                         ' otherwise.\nWith optional start, test S beginning'
                         ' at that position.\nWith optional end, stop'
                         ' comparing S at that position.')
str_expandtabs = SMM('expandtabs', 2, defaults=(8,),
                     doc='S.expandtabs([tabsize]) -> string\n\nReturn a copy'
                         ' of S where all tab characters are expanded using'
                         ' spaces.\nIf tabsize is not given, a tab size of 8'
                         ' characters is assumed.')
str_splitlines = SMM('splitlines', 2, defaults=(0,),
                     doc='S.splitlines([keepends]) -> list of'
                         ' strings\n\nReturn a list of the lines in S,'
                         ' breaking at line boundaries.\nLine breaks are not'
                         ' included in the resulting list unless keepends\nis'
                         ' given and true.')
str_startswith = SMM('startswith', 4, defaults=(0, maxint),
                     doc='S.startswith(prefix[, start[, end]]) ->'
                         ' bool\n\nReturn True if S starts with the specified'
                         ' prefix, False otherwise.\nWith optional start, test'
                         ' S beginning at that position.\nWith optional end,'
                         ' stop comparing S at that position.')
str_translate  = SMM('translate', 3, defaults=('',), #unicode mimic not supported now
                     doc='S.translate(table [,deletechars]) -> string\n\n'
                         'Return a copy of the string S, where all characters'
                         ' occurring\nin the optional argument deletechars are'
                         ' removed, and the\nremaining characters have been'
                         ' mapped through the given\ntranslation table, which'
                         ' must be a string of length 256.')
str_decode     = SMM('decode', 3, defaults=(None, None),
                     argnames=['encoding', 'errors'],
                     doc='S.decode([encoding[,errors]]) -> object\n\nDecodes S'
                         ' using the codec registered for encoding. encoding'
                         ' defaults\nto the default encoding. errors may be'
                         ' given to set a different error\nhandling scheme.'
                         " Default is 'strict' meaning that encoding errors"
                         ' raise\na UnicodeDecodeError. Other possible values'
                         " are 'ignore' and 'replace'\nas well as any other"
                         ' name registerd with codecs.register_error that'
                         ' is\nable to handle UnicodeDecodeErrors.')
str_encode     = SMM('encode', 3, defaults=(None, None),
                     argnames=['encoding', 'errors'],
                     doc='S.encode([encoding[,errors]]) -> object\n\nEncodes S'
                         ' using the codec registered for encoding. encoding'
                         ' defaults\nto the default encoding. errors may be'
                         ' given to set a different error\nhandling scheme.'
                         " Default is 'strict' meaning that encoding errors"
                         ' raise\na UnicodeEncodeError. Other possible values'
                         " are 'ignore', 'replace' and\n'xmlcharrefreplace' as"
                         ' well as any other name registered'
                         ' with\ncodecs.register_error that is able to handle'
                         ' UnicodeEncodeErrors.')

str_formatter_parser           = SMM('_formatter_parser', 1)
str_formatter_field_name_split = SMM('_formatter_field_name_split', 1)

def str_formatter_parser__ANY(space, w_str):
    from pypy.objspace.std.newformat import str_template_formatter
    tformat = str_template_formatter(space, space.str_w(w_str))
    return tformat.formatter_parser()

def str_formatter_field_name_split__ANY(space, w_str):
    from pypy.objspace.std.newformat import str_template_formatter
    tformat = str_template_formatter(space, space.str_w(w_str))
    return tformat.formatter_field_name_split()

# ____________________________________________________________

@unwrap_spec(w_object = WrappedDefault(""))
def descr__new__(space, w_stringtype, w_object):
    # NB. the default value of w_object is really a *wrapped* empty string:
    #     there is gateway magic at work
    w_obj = space.str(w_object)
    if space.is_w(w_stringtype, space.w_str):
        return w_obj  # XXX might be reworked when space.str() typechecks
    value = space.str_w(w_obj)
    w_obj = space.allocate_instance(W_BytesObject, w_stringtype)
    W_BytesObject.__init__(w_obj, value)
    return w_obj

# ____________________________________________________________

str_typedef = W_BytesObject.typedef = StdTypeDef(
    "str", basestring_typedef,
    __new__ = interp2app(descr__new__),
    __doc__ = '''str(object) -> string

Return a nice string representation of the object.
If the argument is a string, the return value is the same object.''',

#    __repr__ = interp2app(W_BytesObject.descr_repr),
#    __str__ = interp2app(W_BytesObject.descr_str),

#    __eq__ = interp2app(W_BytesObject.descr_eq),
#    __ne__ = interp2app(W_BytesObject.descr_ne),
#    __lt__ = interp2app(W_BytesObject.descr_lt),
#    __le__ = interp2app(W_BytesObject.descr_le),
#    __gt__ = interp2app(W_BytesObject.descr_gt),
#    __ge__ = interp2app(W_BytesObject.descr_ge),

#    __len__ = interp2app(W_BytesObject.descr_len),
#    __iter__ = interp2app(W_BytesObject.descr_iter),
#    __contains__ = interp2app(W_BytesObject.descr_contains),

#    __add__ = interp2app(W_BytesObject.descr_add),
    __mul__ = interp2app(W_BytesObject.descr_mul),
    __rmul__ = interp2app(W_BytesObject.descr_mul),

#    __getitem__ = interp2app(W_BytesObject.descr_getitem),

#    capitalize = interp2app(W_BytesObject.descr_capitalize),
#    center = interp2app(W_BytesObject.descr_center),
#    count = interp2app(W_BytesObject.descr_count),
#    decode = interp2app(W_BytesObject.descr_decode),
#    expandtabs = interp2app(W_BytesObject.descr_expandtabs),
#    find = interp2app(W_BytesObject.descr_find),
#    rfind = interp2app(W_BytesObject.descr_rfind),
#    index = interp2app(W_BytesObject.descr_index),
#    rindex = interp2app(W_BytesObject.descr_rindex),
#    isalnum = interp2app(W_BytesObject.descr_isalnum),
#    isalpha = interp2app(W_BytesObject.descr_isalpha),
#    isdigit = interp2app(W_BytesObject.descr_isdigit),
#    islower = interp2app(W_BytesObject.descr_islower),
#    isspace = interp2app(W_BytesObject.descr_isspace),
#    istitle = interp2app(W_BytesObject.descr_istitle),
#    isupper = interp2app(W_BytesObject.descr_isupper),
#    join = interp2app(W_BytesObject.descr_join),
#    ljust = interp2app(W_BytesObject.descr_ljust),
#    rjust = interp2app(W_BytesObject.descr_rjust),
#    lower = interp2app(W_BytesObject.descr_lower),
#    partition = interp2app(W_BytesObject.descr_partition),
#    rpartition = interp2app(W_BytesObject.descr_rpartition),
#    replace = interp2app(W_BytesObject.descr_replace),
#    split = interp2app(W_BytesObject.descr_split),
#    rsplit = interp2app(W_BytesObject.descr_rsplit),
#    splitlines = interp2app(W_BytesObject.descr_splitlines),
#    startswith = interp2app(W_BytesObject.descr_startswith),
#    endswith = interp2app(W_BytesObject.descr_endswith),
#    strip = interp2app(W_BytesObject.descr_strip),
#    lstrip = interp2app(W_BytesObject.descr_lstrip),
#    rstrip = interp2app(W_BytesObject.descr_rstrip),
#    swapcase = interp2app(W_BytesObject.descr_swapcase),
#    title = interp2app(W_BytesObject.descr_title),
#    translate = interp2app(W_BytesObject.descr_translate),
#    upper = interp2app(W_BytesObject.descr_upper),
#    zfill = interp2app(W_BytesObject.descr_zfill),
)

str_typedef.registermethods(globals())

# ____________________________________________________________

# Helpers for several string implementations

@specialize.argtype(0)
def stringendswith(u_self, suffix, start, end):
    begin = end - len(suffix)
    if begin < start:
        return False
    for i in range(len(suffix)):
        if u_self[begin+i] != suffix[i]:
            return False
    return True

@specialize.argtype(0)
def stringstartswith(u_self, prefix, start, end):
    stop = start + len(prefix)
    if stop > end:
        return False
    for i in range(len(prefix)):
        if u_self[start+i] != prefix[i]:
            return False
    return True


@specialize.arg(2)
def _is_generic(space, w_self, fun):
    v = w_self._value
    if len(v) == 0:
        return space.w_False
    if len(v) == 1:
        c = v[0]
        return space.newbool(fun(c))
    else:
        return _is_generic_loop(space, v, fun)

@specialize.arg(2)
def _is_generic_loop(space, v, fun):
    for idx in range(len(v)):
        if not fun(v[idx]):
            return space.w_False
    return space.w_True

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
    return space.wrap(self.upper())

def str_lower__String(space, w_self):
    self = w_self._value
    return space.wrap(self.lower())

def str_swapcase__String(space, w_self):
    self = w_self._value
    builder = StringBuilder(len(self))
    for i in range(len(self)):
        ch = self[i]
        if ch.isupper():
            o = ord(ch) + 32
            builder.append(chr(o))
        elif ch.islower():
            o = ord(ch) - 32
            builder.append(chr(o))
        else:
            builder.append(ch)

    return space.wrap(builder.build())


def str_capitalize__String(space, w_self):
    input = w_self._value
    builder = StringBuilder(len(input))
    if len(input) > 0:
        ch = input[0]
        if ch.islower():
            o = ord(ch) - 32
            builder.append(chr(o))
        else:
            builder.append(ch)

        for i in range(1, len(input)):
            ch = input[i]
            if ch.isupper():
                o = ord(ch) + 32
                builder.append(chr(o))
            else:
                builder.append(ch)

    return space.wrap(builder.build())

def str_title__String(space, w_self):
    input = w_self._value
    builder = StringBuilder(len(input))
    prev_letter = ' '

    for pos in range(len(input)):
        ch = input[pos]
        if not prev_letter.isalpha():
            ch = _upper(ch)
            builder.append(ch)
        else:
            ch = _lower(ch)
            builder.append(ch)

        prev_letter = ch

    return space.wrap(builder.build())

def str_split__String_None_ANY(space, w_self, w_none, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    res = []
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
        res.append(value[i:j])

        # continue to look from the character following the space after the word
        i = j + 1

    return space.newlist_str(res)

def str_split__String_String_ANY(space, w_self, w_by, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    value = w_self._value
    by = w_by._value
    bylen = len(by)
    if bylen == 0:
        raise OperationError(space.w_ValueError, space.wrap("empty separator"))

    if bylen == 1 and maxsplit < 0:
        res = []
        start = 0
        # fast path: uses str.rfind(character) and str.count(character)
        by = by[0]    # annotator hack: string -> char
        count = value.count(by)
        res = [None] * (count + 1)
        end = len(value)
        while count >= 0:
            assert end >= 0
            prev = value.rfind(by, 0, end)
            start = prev + 1
            assert start >= 0
            res[count] = value[start:end]
            count -= 1
            end = prev
    else:
        res = split(value, by, maxsplit)

    return space.newlist_str(res)

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
        res_w.append(sliced(space, value, j1, i+1, w_self))

        # continue to look from the character before the space before the word
        i = j - 1

    res_w.reverse()
    return space.newlist(res_w)

def make_rsplit_with_delim(funcname, sliced):
    from rpython.tool.sourcetools import func_with_new_name

    def fn(space, w_self, w_by, w_maxsplit=-1):
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
            res_w.append(sliced(space, value, next+bylen, end, w_self))
            end = next
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        res_w.append(sliced(space, value, 0, end, w_self))
        res_w.reverse()
        return space.newlist(res_w)

    return func_with_new_name(fn, funcname)

str_rsplit__String_String_ANY = make_rsplit_with_delim('str_rsplit__String_String_ANY',
                                                       sliced)

def str_join__String_ANY(space, w_self, w_list):
    l = space.listview_str(w_list)
    if l is not None:
        if len(l) == 1:
            return space.wrap(l[0])
        return space.wrap(w_self._value.join(l))
    list_w = space.listview(w_list)
    size = len(list_w)

    if size == 0:
        return W_BytesObject.EMPTY

    if size == 1:
        w_s = list_w[0]
        # only one item,  return it if it's not a subclass of str
        if (space.is_w(space.type(w_s), space.w_str) or
            space.is_w(space.type(w_s), space.w_unicode)):
            return w_s

    return _str_join_many_items(space, w_self, list_w, size)

@jit.look_inside_iff(lambda space, w_self, list_w, size:
                     jit.loop_unrolling_heuristic(list_w, size))
def _str_join_many_items(space, w_self, list_w, size):
    self = w_self._value
    reslen = len(self) * (size - 1)
    for i in range(size):
        w_s = list_w[i]
        if not space.isinstance_w(w_s, space.w_str):
            if space.isinstance_w(w_s, space.w_unicode):
                # we need to rebuild w_list here, because the original
                # w_list might be an iterable which we already consumed
                w_list = space.newlist(list_w)
                w_u = space.call_function(space.w_unicode, w_self)
                return space.call_method(w_u, "join", w_list)
            raise operationerrfmt(
                space.w_TypeError,
                "sequence item %d: expected string, %s "
                "found", i, space.type(w_s).getname(space))
        reslen += len(space.str_w(w_s))

    sb = StringBuilder(reslen)
    for i in range(size):
        if self and i != 0:
            sb.append(self)
        sb.append(space.str_w(list_w[i]))
    return space.wrap(sb.build())

def str_rjust__String_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_arg = space.int_w(w_arg)
    u_self = w_self._value
    fillchar = space.str_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("rjust() argument 2 must be a single character"))

    d = u_arg - len(u_self)
    if d > 0:
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
    if d > 0:
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_self += d * fillchar

    return space.wrap(u_self)

@specialize.arg(4)
def _convert_idx_params(space, w_self, w_start, w_end, upper_bound=False):
    self = w_self._value
    lenself = len(self)

    start, end = slicetype.unwrap_start_stop(
            space, lenself, w_start, w_end, upper_bound=upper_bound)
    return (self, start, end)

def contains__String_String(space, w_self, w_sub):
    self = w_self._value
    sub = w_sub._value
    return space.newbool(self.find(sub) >= 0)

def str_find__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.find(w_sub._value, start, end)
    return space.wrap(res)

def str_rfind__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.rfind(w_sub._value, start, end)
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
        return space.newtuple([sliced(space, self, 0, pos, w_self),
                               w_sub,
                               sliced(space, self, pos+len(sub), len(self),
                                      w_self)])

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
        return space.newtuple([sliced(space, self, 0, pos, w_self),
                               w_sub,
                               sliced(space, self, pos+len(sub), len(self), w_self)])


def str_index__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.find(w_sub._value, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))

    return space.wrap(res)


def str_rindex__String_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, start, end) = _convert_idx_params(space, w_self, w_start, w_end)
    res = self.rfind(w_sub._value, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return space.wrap(res)

def _string_replace(space, input, sub, by, maxsplit):
    if maxsplit == 0:
        return space.wrap(input)

    if not sub:
        upper = len(input)
        if maxsplit > 0 and maxsplit < upper + 2:
            upper = maxsplit - 1
            assert upper >= 0

        try:
            result_size = ovfcheck(upper * len(by))
            result_size = ovfcheck(result_size + upper)
            result_size = ovfcheck(result_size + len(by))
            remaining_size = len(input) - upper
            result_size = ovfcheck(result_size + remaining_size)
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("replace string is too long")
            )
        builder = StringBuilder(result_size)
        for i in range(upper):
            builder.append(by)
            builder.append(input[i])
        builder.append(by)
        builder.append_slice(input, upper, len(input))
    else:
        # First compute the exact result size
        count = input.count(sub)
        if count > maxsplit and maxsplit > 0:
            count = maxsplit
        diff_len = len(by) - len(sub)
        try:
            result_size = ovfcheck(diff_len * count)
            result_size = ovfcheck(result_size + len(input))
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("replace string is too long")
            )

        builder = StringBuilder(result_size)
        start = 0
        sublen = len(sub)

        while maxsplit != 0:
            next = input.find(sub, start)
            if next < 0:
                break
            builder.append_slice(input, start, next)
            builder.append(by)
            start = next + sublen
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        builder.append_slice(input, start, len(input))

    return space.wrap(builder.build())


def str_replace__String_ANY_ANY_ANY(space, w_self, w_sub, w_by, w_maxsplit):
    return _string_replace(space, w_self._value, space.buffer_w(w_sub).as_str(),
                           space.buffer_w(w_by).as_str(),
                           space.int_w(w_maxsplit))

def str_replace__String_String_String_ANY(space, w_self, w_sub, w_by, w_maxsplit=-1):
    input = w_self._value
    sub = w_sub._value
    by = w_by._value
    maxsplit = space.int_w(w_maxsplit)
    return _string_replace(space, input, sub, by, maxsplit)

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
    return sliced(space, u_self, lpos, rpos, w_self)

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
    return sliced(space, u_self, lpos, rpos, w_self)

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
        offset = d//2 + (d & u_arg & 1)
        fillchar = fillchar[0]    # annotator hint: it's a single character
        u_centered = offset * fillchar + u_self + (d - offset) * fillchar
    else:
        u_centered = u_self

    return wrapstr(space, u_centered)

def str_count__String_String_ANY_ANY(space, w_self, w_arg, w_start, w_end):
    u_self, u_start, u_end = _convert_idx_params(space, w_self, w_start, w_end)
    return wrapint(space, u_self.count(w_arg._value, u_start, u_end))

def str_endswith__String_String_ANY_ANY(space, w_self, w_suffix, w_start, w_end):
    (u_self, start, end) = _convert_idx_params(space, w_self, w_start,
                                               w_end, True)
    return space.newbool(stringendswith(u_self, w_suffix._value, start, end))

def str_endswith__String_ANY_ANY_ANY(space, w_self, w_suffixes, w_start, w_end):
    if not space.isinstance_w(w_suffixes, space.w_tuple):
        raise FailedToImplement
    (u_self, start, end) = _convert_idx_params(space, w_self, w_start,
                                               w_end, True)
    for w_suffix in space.fixedview(w_suffixes):
        if space.isinstance_w(w_suffix, space.w_unicode):
            w_u = space.call_function(space.w_unicode, w_self)
            return space.call_method(w_u, "endswith", w_suffixes, w_start,
                                     w_end)
        suffix = space.str_w(w_suffix)
        if stringendswith(u_self, suffix, start, end):
            return space.w_True
    return space.w_False

def str_startswith__String_String_ANY_ANY(space, w_self, w_prefix, w_start, w_end):
    (u_self, start, end) = _convert_idx_params(space, w_self, w_start,
                                               w_end, True)
    return space.newbool(stringstartswith(u_self, w_prefix._value, start, end))

def str_startswith__String_ANY_ANY_ANY(space, w_self, w_prefixes, w_start, w_end):
    if not space.isinstance_w(w_prefixes, space.w_tuple):
        raise FailedToImplement
    (u_self, start, end) = _convert_idx_params(space, w_self,
                                               w_start, w_end, True)
    for w_prefix in space.fixedview(w_prefixes):
        if space.isinstance_w(w_prefix, space.w_unicode):
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
                break
            distance += 1
            offset -= 1
            if offset == 0:
                break

        #the same like distance = len(u_token) - (offset + 1)
        #print '<offset:%d distance:%d tabsize:%d token:%s>' % (offset, distance, u_tabsize, u_token)
        distance = (u_tabsize-distance) % u_tabsize
        if distance == 0:
            distance = u_tabsize

    return distance


def str_expandtabs__String_ANY(space, w_self, w_tabsize):
    u_self = w_self._value
    u_tabsize = space.int_w(w_tabsize)

    u_expanded = ""
    if u_self:
        split = u_self.split("\t")
        try:
            ovfcheck(len(split) * u_tabsize)
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("new string is too long")
            )
        u_expanded = oldtoken = split.pop(0)

        for token in split:
            #print  "%d#%d -%s-" % (_tabindent(oldtoken,u_tabsize), u_tabsize, token)
            u_expanded += " " * _tabindent(oldtoken, u_tabsize) + token
            oldtoken = token

    return wrapstr(space, u_expanded)


def str_splitlines__String_ANY(space, w_self, w_keepends):
    u_keepends = space.int_w(w_keepends)  # truth value, but type checked
    data = w_self._value
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
        strs_w.append(sliced(space, data, j, eol, w_self))
        j = i

    if j < selflen:
        strs_w.append(sliced(space, data, j, len(data), w_self))
    return space.newlist(strs_w)

def str_zfill__String_ANY(space, w_self, w_width):
    input = w_self._value
    width = space.int_w(w_width)

    num_zeros = width - len(input)
    if num_zeros <= 0:
        # cannot return w_self, in case it is a subclass of str
        return space.wrap(input)

    builder = StringBuilder(width)
    if len(input) > 0 and (input[0] == '+' or input[0] == '-'):
        builder.append(input[0])
        start = 1
    else:
        start = 0

    builder.append_multiple_char('0', num_zeros)
    builder.append_slice(input, start, len(input))
    return space.wrap(builder.build())


def hash__String(space, w_str):
    s = w_str._value
    x = compute_hash(s)
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
        raise OperationError(space.w_IndexError,
                             space.wrap("string index out of range"))
    return wrapchar(space, str[ival])

def getitem__String_Slice(space, w_str, w_slice):
    s = w_str._value
    length = len(s)
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        return W_BytesObject.EMPTY
    elif step == 1:
        assert start >= 0 and stop >= 0
        return sliced(space, s, start, stop, w_str)
    else:
        str = "".join([s[start + i*step] for i in range(sl)])
    return wrapstr(space, str)

def getslice__String_ANY_ANY(space, w_str, w_start, w_stop):
    s = w_str._value
    start, stop = normalize_simple_slice(space, len(s), w_start, w_stop)
    if start == stop:
        return W_BytesObject.EMPTY
    else:
        return sliced(space, s, start, stop, w_str)

def add__String_String(space, w_left, w_right):
    right = w_right._value
    left = w_left._value
    return joined2(space, left, right)

def len__String(space, w_str):
    return space.wrap(len(w_str._value))

def str__String(space, w_str):
    if type(w_str) is W_BytesObject:
        return w_str
    return wrapstr(space, w_str._value)

def ord__String(space, w_str):
    u_str = w_str._value
    if len(u_str) != 1:
        raise operationerrfmt(
            space.w_TypeError,
            "ord() expected a character, but string "
            "of length %d found", len(u_str))
    return space.wrap(ord(u_str[0]))

def getnewargs__String(space, w_str):
    return space.newtuple([wrapstr(space, w_str._value)])

def repr__String(space, w_str):
    s = w_str._value

    quote = "'"
    if quote in s and '"' not in s:
        quote = '"'

    return space.wrap(string_escape_encode(s, quote))

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


DEFAULT_NOOP_TABLE = ''.join([chr(i) for i in range(256)])

def str_translate__String_ANY_ANY(space, w_string, w_table, w_deletechars=''):
    """charfilter - unicode handling is not implemented

    Return a copy of the string where all characters occurring
    in the optional argument deletechars are removed, and the
    remaining characters have been mapped through the given translation table,
    which must be a string of length 256"""

    if space.is_w(w_table, space.w_None):
        table = DEFAULT_NOOP_TABLE
    else:
        table = space.bufferstr_w(w_table)
        if len(table) != 256:
            raise OperationError(
                space.w_ValueError,
                space.wrap("translation table must be 256 characters long"))

    string = w_string._value
    deletechars = space.str_w(w_deletechars)
    if len(deletechars) == 0:
        buf = StringBuilder(len(string))
        for char in string:
            buf.append(table[ord(char)])
    else:
        buf = StringBuilder()
        deletion_table = [False] * 256
        for c in deletechars:
            deletion_table[ord(c)] = True
        for char in string:
            if not deletion_table[ord(char)]:
                buf.append(table[ord(char)])
    return W_BytesObject(buf.build())

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

def str_format__String(space, w_string, __args__):
    return newformat.format_method(space, w_string, __args__, False)

def format__String_ANY(space, w_string, w_format_spec):
    if not space.isinstance_w(w_format_spec, space.w_str):
        w_format_spec = space.str(w_format_spec)
    spec = space.str_w(w_format_spec)
    formatter = newformat.str_formatter(space, spec)
    return formatter.format_string(w_string._value)

def buffer__String(space, w_string):
    return space.wrap(StringBuffer(w_string._value))

# register all methods
register_all(vars(), globals())
