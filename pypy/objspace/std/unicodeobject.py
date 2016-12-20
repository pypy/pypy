"""The builtin str implementation"""

from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin)
from rpython.rlib.buffer import StringBuffer
from rpython.rlib.rstring import StringBuilder, UnicodeBuilder
from rpython.rlib.runicode import (
    make_unicode_escape_function, str_decode_ascii, str_decode_utf_8,
    unicode_encode_ascii, unicode_encode_utf_8, fast_str_decode_ascii,
    unicode_encode_utf8sp, unicode_encode_utf8_forbid_surrogates,
    SurrogateError)
from rpython.rlib import jit

from pypy.interpreter import unicodehelper
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module.unicodedata import unicodedb
from pypy.objspace.std import newformat
from pypy.objspace.std.formatting import mod_format, FORMAT_UNICODE
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.util import IDTAG_SPECIAL, IDTAG_SHIFT

__all__ = ['W_UnicodeObject', 'encode_object', 'decode_object',
           'unicode_from_object', 'unicode_to_decimal_w']


class W_UnicodeObject(W_Root):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_value']

    def __init__(self, unistr):
        assert isinstance(unistr, unicode)
        self._value = unistr
        self._utf8 = None

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def unwrap(self, space):
        # for testing
        return self._value

    def create_if_subclassed(self):
        if type(self) is W_UnicodeObject:
            return self
        return W_UnicodeObject(self._value)

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_UnicodeObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        s1 = space.unicode_w(self)
        s2 = space.unicode_w(w_other)
        if len(s2) > 1:
            return s1 is s2
        else:            # strings of len <= 1 are unique-ified
            return s1 == s2

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        s = space.unicode_w(self)
        if len(s) > 1:
            uid = compute_unique_id(s)
        else:            # strings of len <= 1 are unique-ified
            if len(s) == 1:
                base = ~ord(s[0])      # negative base values
            else:
                base = 257       # empty unicode string: base value 257
            uid = (base << IDTAG_SHIFT) | IDTAG_SPECIAL
        return space.newint(uid)

    def unicode_w(self, space):
        return self._value

    def _identifier_or_text_w(self, space, ignore_sg):
        try:
            identifier = jit.conditional_call_elidable(
                                self._utf8, g_encode_utf8, self._value)
            if not jit.isconstant(self):
                self._utf8 = identifier
        except SurrogateError:
            # If 'ignore_sg' is False, this logic is here only
            # to get an official app-level UnicodeEncodeError.
            # If 'ignore_sg' is True, we encode instead using
            # unicode_encode_utf8sp().
            u = self._value
            if ignore_sg:
                identifier = unicode_encode_utf8sp(u, len(u))
            else:
                eh = unicodehelper.rpy_encode_error_handler()
                try:
                    identifier = unicode_encode_utf_8(u, len(u), None,
                                                      errorhandler=eh)
                except unicodehelper.RUnicodeEncodeError as ue:
                    raise wrap_encode_error(space, ue)
        return identifier

    def text_w(self, space):
        return self._identifier_or_text_w(space, ignore_sg=True)

    def identifier_w(self, space):
        return self._identifier_or_text_w(space, ignore_sg=False)

    def listview_unicode(self):
        return _create_list_from_unicode(self._value)

    def ord(self, space):
        if len(self._value) != 1:
            raise oefmt(space.w_TypeError,
                         "ord() expected a character, but string of length %d "
                         "found", len(self._value))
        return space.newint(ord(self._value[0]))

    def _new(self, value):
        return W_UnicodeObject(value)

    def _new_from_list(self, value):
        return W_UnicodeObject(u''.join(value))

    def _empty(self):
        return W_UnicodeObject.EMPTY

    def _len(self):
        return len(self._value)

    _val = unicode_w

    @staticmethod
    def _use_rstr_ops(space, w_other):
        # Always return true because we always need to copy the other
        # operand(s) before we can do comparisons
        return True

    @staticmethod
    def _op_val(space, w_other, allow_char=False):
        if isinstance(w_other, W_UnicodeObject):
            return w_other._value
        raise oefmt(space.w_TypeError,
                    "Can't convert '%T' object to str implicitly", w_other)

    def _chr(self, char):
        assert len(char) == 1
        return unicode(char)[0]

    _builder = UnicodeBuilder

    def _generic_name(self):
        return "str"

    def _isupper(self, ch):
        return unicodedb.isupper(ord(ch))

    def _islower(self, ch):
        return unicodedb.islower(ord(ch))

    def _isnumeric(self, ch):
        return unicodedb.isnumeric(ord(ch))

    def _istitle(self, ch):
        return unicodedb.isupper(ord(ch)) or unicodedb.istitle(ord(ch))

    def _isspace(self, ch):
        return unicodedb.isspace(ord(ch))

    def _isalpha(self, ch):
        return unicodedb.isalpha(ord(ch))

    def _isalnum(self, ch):
        return unicodedb.isalnum(ord(ch))

    def _isdigit(self, ch):
        return unicodedb.isdigit(ord(ch))

    def _isdecimal(self, ch):
        return unicodedb.isdecimal(ord(ch))

    def _iscased(self, ch):
        return unicodedb.iscased(ord(ch))

    def _islinebreak(self, ch):
        return unicodedb.islinebreak(ord(ch))

    def _upper(self, ch):
        return u''.join([unichr(x) for x in
                         unicodedb.toupper_full(ord(ch))])

    def _lower_in_str(self, value, i):
        ch = value[i]
        if ord(ch) == 0x3A3:
            # Obscure special case.
            return self._handle_capital_sigma(value, i)
        return u''.join([unichr(x) for x in
                         unicodedb.tolower_full(ord(ch))])

    def _title(self, ch):
        return u''.join([unichr(x) for x in
                         unicodedb.totitle_full(ord(ch))])

    def _handle_capital_sigma(self, value, i):
        # U+03A3 is in the Final_Sigma context when, it is found like this:
        #\p{cased} \p{case-ignorable}* U+03A3 not(\p{case-ignorable}* \p{cased})
        # where \p{xxx} is a character with property xxx.
        j = i - 1
        final_sigma = False
        while j >= 0:
            ch = value[j]
            if unicodedb.iscaseignorable(ord(ch)):
                j -= 1
                continue
            final_sigma = unicodedb.iscased(ord(ch))
            break
        if final_sigma:
            j = i + 1
            length = len(value)
            while j < length:
                ch = value[j]
                if unicodedb.iscaseignorable(ord(ch)):
                    j += 1
                    continue
                final_sigma = not unicodedb.iscased(ord(ch))
                break
        if final_sigma:
            return unichr(0x3C2)
        else:
            return unichr(0x3C3)

    def _newlist_unwrapped(self, space, lst):
        return space.newlist_unicode(lst)

    @staticmethod
    def descr_new(space, w_unicodetype, w_object=None, w_encoding=None,
                  w_errors=None):
        if w_object is None:
            w_value = W_UnicodeObject.EMPTY
        else:
            encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                        w_errors)
            if encoding is None and errors is None:
                w_value = unicode_from_object(space, w_object)
            else:
                w_value = unicode_from_encoded_object(space, w_object,
                                                      encoding, errors)
        if space.is_w(w_unicodetype, space.w_unicode):
            return w_value

        assert isinstance(w_value, W_UnicodeObject)
        w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
        W_UnicodeObject.__init__(w_newobj, w_value._value)
        return w_newobj

    @staticmethod
    def descr_maketrans(space, w_type, w_x, w_y=None, w_z=None):
        y = None if space.is_none(w_y) else space.unicode_w(w_y)
        z = None if space.is_none(w_z) else space.unicode_w(w_z)
        w_new = space.newdict()

        if y is not None:
            # x must be a string too, of equal length
            ylen = len(y)
            try:
                x = space.unicode_w(w_x)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise oefmt(space.w_TypeError,
                            "first maketrans argument must be a string if "
                            "there is a second argument")
            if len(x) != ylen:
                raise oefmt(space.w_ValueError,
                            "the first two maketrans arguments must have "
                            "equal length")
            # create entries for translating chars in x to those in y
            for i in range(len(x)):
                w_key = space.newint(ord(x[i]))
                w_value = space.newint(ord(y[i]))
                space.setitem(w_new, w_key, w_value)
            # create entries for deleting chars in z
            if z is not None:
                for i in range(len(z)):
                    w_key = space.newint(ord(z[i]))
                    space.setitem(w_new, w_key, space.w_None)
        else:
            # x must be a dict
            if not space.is_w(space.type(w_x), space.w_dict):
                raise oefmt(space.w_TypeError,
                            "if you give only one argument to maketrans it "
                            "must be a dict")
            # copy entries into the new dict, converting string keys to int keys
            w_iter = space.iter(space.call_method(w_x, "items"))
            while True:
                try:
                    w_item = space.next(w_iter)
                except OperationError as e:
                    if not e.match(space, space.w_StopIteration):
                        raise
                    break
                w_key, w_value = space.unpackiterable(w_item, 2)
                if space.isinstance_w(w_key, space.w_unicode):
                    # convert string keys to integer keys
                    key = space.unicode_w(w_key)
                    if len(key) != 1:
                        raise oefmt(space.w_ValueError,
                                    "string keys in translate table must be "
                                    "of length 1")
                    w_key = space.newint(ord(key[0]))
                else:
                    # just keep integer keys
                    try:
                        space.int_w(w_key)
                    except OperationError as e:
                        if not e.match(space, space.w_TypeError):
                            raise
                        raise oefmt(space.w_TypeError,
                                    "keys in translate table must be strings "
                                    "or integers")
                space.setitem(w_new, w_key, w_value)
        return w_new

    def descr_repr(self, space):
        chars = self._value
        size = len(chars)
        s = _repr_function(chars, size, "strict")
        return space.newtext(s)

    def descr_str(self, space):
        if space.is_w(space.type(self), space.w_unicode):
            return self
        # Subtype -- return genuine unicode string with the same value.
        return space.newunicode(space.unicode_w(self))

    def descr_hash(self, space):
        x = compute_hash(self._value)
        return space.newint(x)

    def descr_eq(self, space, w_other):
        try:
            res = self._val(space) == self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_ne(self, space, w_other):
        try:
            res = self._val(space) != self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_lt(self, space, w_other):
        try:
            res = self._val(space) < self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_le(self, space, w_other):
        try:
            res = self._val(space) <= self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_gt(self, space, w_other):
        try:
            res = self._val(space) > self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_ge(self, space, w_other):
        try:
            res = self._val(space) >= self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def _parse_format_arg(self, space, w_kwds, __args__):
        for i in range(len(__args__.keywords)):
            try:     # pff
                arg = __args__.keywords[i].decode('utf-8')
            except UnicodeDecodeError:
                continue   # uh, just skip that
            space.setitem(w_kwds, space.newunicode(arg),
                          __args__.keywords_w[i])

    def descr_format(self, space, __args__):
        w_kwds = space.newdict()
        if __args__.keywords:
            self._parse_format_arg(space, w_kwds, __args__)
        return newformat.format_method(space, self, __args__.arguments_w,
                                       w_kwds, True)

    def descr_format_map(self, space, w_mapping):
        return newformat.format_method(space, self, None, w_mapping, True)

    def descr__format__(self, space, w_format_spec):
        return newformat.run_formatter(space, w_format_spec, "format_string",
                                       self)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, fmt_type=FORMAT_UNICODE)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, fmt_type=FORMAT_UNICODE)

    def descr_translate(self, space, w_table):
        selfvalue = self._value
        w_sys = space.getbuiltinmodule('sys')
        maxunicode = space.int_w(space.getattr(w_sys,
                                               space.newtext("maxunicode")))
        result = []
        for unichar in selfvalue:
            try:
                w_newval = space.getitem(w_table, space.newint(ord(unichar)))
            except OperationError as e:
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
                        raise oefmt(space.w_TypeError,
                                    "character mapping must be in range(%s)",
                                    hex(maxunicode + 1))
                    result.append(unichr(newval))
                elif space.isinstance_w(w_newval, space.w_unicode):
                    result.append(space.unicode_w(w_newval))
                else:
                    raise oefmt(space.w_TypeError,
                                "character mapping must return integer, None "
                                "or str")
        return W_UnicodeObject(u''.join(result))

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        return encode_object(space, self, encoding, errors)

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_unicode(w_list)
        if l is not None:
            if len(l) == 1:
                return space.newunicode(l[0])
            return space.newunicode(self._val(space).join(l))
        return self._StringMethods_descr_join(space, w_list)

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def descr_casefold(self, space):
        value = self._val(space)
        builder = self._builder(len(value))
        for c in value:
            c_ord = ord(c)
            folded = unicodedb.casefold_lookup(c_ord)
            if folded is None:
                builder.append(unichr(unicodedb.tolower(c_ord)))
            else:
                for r in folded:
                    builder.append(unichr(r))
        return self._new(builder.build())

    def descr_isdecimal(self, space):
        return self._is_generic(space, '_isdecimal')

    def descr_isnumeric(self, space):
        return self._is_generic(space, '_isnumeric')

    def descr_islower(self, space):
        cased = False
        for uchar in self._value:
            if (unicodedb.isupper(ord(uchar)) or
                unicodedb.istitle(ord(uchar))):
                return space.w_False
            if not cased and unicodedb.islower(ord(uchar)):
                cased = True
        return space.newbool(cased)

    def descr_isupper(self, space):
        cased = False
        for uchar in self._value:
            if (unicodedb.islower(ord(uchar)) or
                unicodedb.istitle(ord(uchar))):
                return space.w_False
            if not cased and unicodedb.isupper(ord(uchar)):
                cased = True
        return space.newbool(cased)

    def descr_isidentifier(self, space):
        return space.newbool(_isidentifier(self._value))

    def descr_isprintable(self, space):
        for uchar in self._value:
            if not unicodedb.isprintable(ord(uchar)):
                return space.w_False
        return space.w_True

    def _fix_fillchar(func):
        # XXX: hack
        from rpython.tool.sourcetools import func_with_new_name
        func = func_with_new_name(func, func.__name__)
        func.unwrap_spec = func.unwrap_spec.copy()
        func.unwrap_spec['w_fillchar'] = WrappedDefault(u' ')
        return func

    descr_center = _fix_fillchar(StringMethods.descr_center)
    descr_ljust = _fix_fillchar(StringMethods.descr_ljust)
    descr_rjust = _fix_fillchar(StringMethods.descr_rjust)

    @staticmethod
    def _iter_getitem_result(self, space, index):
        assert isinstance(self, W_UnicodeObject)
        return self._getitem_result(space, index)


def _isidentifier(u):
    if not u:
        return False

    # PEP 3131 says that the first character must be in XID_Start and
    # subsequent characters in XID_Continue, and for the ASCII range,
    # the 2.x rules apply (i.e start with letters and underscore,
    # continue with letters, digits, underscore). However, given the
    # current definition of XID_Start and XID_Continue, it is sufficient
    # to check just for these, except that _ must be allowed as starting
    # an identifier.
    first = u[0]
    if not (unicodedb.isxidstart(ord(first)) or first == u'_'):
        return False

    for i in range(1, len(u)):
        if not unicodedb.isxidcontinue(ord(u[i])):
            return False
    return True

# stuff imported from bytesobject for interoperability


# ____________________________________________________________

def getdefaultencoding(space):
    return space.sys.defaultencoding


def _get_encoding_and_errors(space, w_encoding, w_errors):
    encoding = None if w_encoding is None else space.str_w(w_encoding)
    errors = None if w_errors is None else space.str_w(w_errors)
    return encoding, errors


def encode_object(space, w_object, encoding, errors):
    if errors is None or errors == 'strict':
        try:
            if encoding is None or encoding == 'utf-8':
                u = space.unicode_w(w_object)
                eh = unicodehelper.encode_error_handler(space)
                return space.newbytes(unicode_encode_utf_8(
                        u, len(u), errors, errorhandler=eh))
            elif encoding == 'ascii':
                u = space.unicode_w(w_object)
                eh = unicodehelper.encode_error_handler(space)
                return space.newbytes(unicode_encode_ascii(
                        u, len(u), errors, errorhandler=eh))
        except unicodehelper.RUnicodeEncodeError as ue:
            raise wrap_encode_error(space, ue)

    from pypy.module._codecs.interp_codecs import encode_text
    w_retval = encode_text(space, w_object, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_bytes):
        raise oefmt(space.w_TypeError,
                    "encoder did not return a bytes object (type '%T')",
                    w_retval)
    return w_retval


def wrap_encode_error(space, ue):
    raise OperationError(space.w_UnicodeEncodeError,
                         space.newtuple([
        space.newtext(ue.encoding),
        space.newbytes(ue.object),
        space.newint(ue.start),
        space.newint(ue.end),
        space.newtext(ue.reason)]))


def decode_object(space, w_obj, encoding, errors):
    if encoding is None:
        encoding = getdefaultencoding(space)
    if errors is None or errors == 'strict':
        if encoding == 'ascii':
            # XXX error handling
            s = space.charbuf_w(w_obj)
            try:
                u = fast_str_decode_ascii(s)
            except ValueError:
                eh = unicodehelper.decode_error_handler(space)
                u = str_decode_ascii(     # try again, to get the error right
                    s, len(s), None, final=True, errorhandler=eh)[0]
            return space.newunicode(u)
        if encoding == 'utf-8':
            s = space.charbuf_w(w_obj)
            eh = unicodehelper.decode_error_handler(space)
            return space.newunicode(str_decode_utf_8(
                    s, len(s), None, final=True, errorhandler=eh)[0])

    from pypy.module._codecs.interp_codecs import decode_text
    w_retval = decode_text(space, w_obj, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_unicode):
        raise oefmt(space.w_TypeError,
                    "decoder did not return a bytes object (type '%T')",
                    w_retval)
    return w_retval


def unicode_from_encoded_object(space, w_obj, encoding, errors):
    w_retval = decode_object(space, w_obj, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_unicode):
        raise oefmt(space.w_TypeError,
                    "decoder did not return a str object (type '%T')",
                    w_retval)
    assert isinstance(w_retval, W_UnicodeObject)
    return w_retval


def unicode_from_object(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    if space.lookup(w_obj, "__str__") is not None:
        return space.str(w_obj)
    return space.repr(w_obj)

def ascii_from_object(space, w_obj):
    """Implements builtins.ascii()"""
    # repr is guaranteed to be unicode
    w_repr = space.repr(w_obj)
    w_encoded = encode_object(space, w_repr, 'ascii', 'backslashreplace')
    return decode_object(space, w_encoded, 'ascii', None)


class UnicodeDocstrings:
    """str(object='') -> str
    str(bytes_or_buffer[, encoding[, errors]]) -> str

    Create a new string object from the given object. If encoding or
    errors is specified, then the object must expose a data buffer
    that will be decoded using the given encoding and error handler.
    Otherwise, returns the result of object.__str__() (if defined)
    or repr(object).
    encoding defaults to sys.getdefaultencoding().
    errors defaults to 'strict'.

    """

    def __add__():
        """x.__add__(y) <==> x+y"""

    def __contains__():
        """x.__contains__(y) <==> y in x"""

    def __eq__():
        """x.__eq__(y) <==> x==y"""

    def __format__():
        """S.__format__(format_spec) -> unicode

        Return a formatted version of S as described by format_spec.
        """

    def __ge__():
        """x.__ge__(y) <==> x>=y"""

    def __getattribute__():
        """x.__getattribute__('name') <==> x.name"""

    def __getitem__():
        """x.__getitem__(y) <==> x[y]"""

    def __getnewargs__():
        ""

    def __gt__():
        """x.__gt__(y) <==> x>y"""

    def __hash__():
        """x.__hash__() <==> hash(x)"""

    def __iter__():
        """x.__iter__() <==> iter(x)"""

    def __le__():
        """x.__le__(y) <==> x<=y"""

    def __len__():
        """x.__len__() <==> len(x)"""

    def __lt__():
        """x.__lt__(y) <==> x<y"""

    def __mod__():
        """x.__mod__(y) <==> x%y"""

    def __rmod__():
        """x.__rmod__(y) <==> y%x"""

    def __mul__():
        """x.__mul__(n) <==> x*n"""

    def __ne__():
        """x.__ne__(y) <==> x!=y"""

    def __repr__():
        """x.__repr__() <==> repr(x)"""

    def __rmod__():
        """x.__rmod__(y) <==> y%x"""

    def __rmul__():
        """x.__rmul__(n) <==> n*x"""

    def __sizeof__():
        """S.__sizeof__() -> size of S in memory, in bytes"""

    def __str__():
        """x.__str__() <==> str(x)"""

    def capitalize():
        """S.capitalize() -> unicode

        Return a capitalized version of S, i.e. make the first character
        have upper case and the rest lower case.
        """

    def center():
        """S.center(width[, fillchar]) -> unicode

        Return S centered in a Unicode string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def count():
        """S.count(sub[, start[, end]]) -> int

        Return the number of non-overlapping occurrences of substring sub in
        Unicode string S[start:end].  Optional arguments start and end are
        interpreted as in slice notation.
        """

    def decode():
        """S.decode(encoding=None, errors='strict') -> string or unicode

        Decode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeDecodeError. Other possible values are 'ignore' and 'replace'
        as well as any other name registered with codecs.register_error that is
        able to handle UnicodeDecodeErrors.
        """

    def encode():
        """S.encode(encoding=None, errors='strict') -> string or unicode

        Encode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeEncodeError. Other possible values are 'ignore', 'replace' and
        'xmlcharrefreplace' as well as any other name registered with
        codecs.register_error that can handle UnicodeEncodeErrors.
        """

    def endswith():
        """S.endswith(suffix[, start[, end]]) -> bool

        Return True if S ends with the specified suffix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        suffix can also be a tuple of strings to try.
        """

    def expandtabs():
        """S.expandtabs([tabsize]) -> unicode

        Return a copy of S where all tab characters are expanded using spaces.
        If tabsize is not given, a tab size of 8 characters is assumed.
        """

    def find():
        """S.find(sub[, start[, end]]) -> int

        Return the lowest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def format():
        """S.format(*args, **kwargs) -> unicode

        Return a formatted version of S, using substitutions from args and
        kwargs.  The substitutions are identified by braces ('{' and '}').
        """

    def format_map():
        """S.format_map(mapping) -> str

        Return a formatted version of S, using substitutions from
        mapping.  The substitutions are identified by braces ('{' and
        '}').
        """

    def index():
        """S.index(sub[, start[, end]]) -> int

        Like S.find() but raise ValueError when the substring is not found.
        """

    def isalnum():
        """S.isalnum() -> bool

        Return True if all characters in S are alphanumeric
        and there is at least one character in S, False otherwise.
        """

    def isalpha():
        """S.isalpha() -> bool

        Return True if all characters in S are alphabetic
        and there is at least one character in S, False otherwise.
        """

    def casefold():
        """S.casefold() -> str

        Return a version of S suitable for caseless comparisons.
        """

    def isdecimal():
        """S.isdecimal() -> bool

        Return True if there are only decimal characters in S,
        False otherwise.
        """

    def isdigit():
        """S.isdigit() -> bool

        Return True if all characters in S are digits
        and there is at least one character in S, False otherwise.
        """

    def isidentifier():
        """S.isidentifier() -> bool

        Return True if S is a valid identifier according to the language
        definition.
        """

    def islower():
        """S.islower() -> bool

        Return True if all cased characters in S are lowercase and there is
        at least one cased character in S, False otherwise.
        """

    def isnumeric():
        """S.isnumeric() -> bool

        Return True if there are only numeric characters in S,
        False otherwise.
        """

    def isprintable():
        """S.isprintable() -> bool

        Return True if all characters in S are considered printable in
        repr() or S is empty, False otherwise.
        """

    def isspace():
        """S.isspace() -> bool

        Return True if all characters in S are whitespace
        and there is at least one character in S, False otherwise.
        """

    def istitle():
        """S.istitle() -> bool

        Return True if S is a titlecased string and there is at least one
        character in S, i.e. upper- and titlecase characters may only
        follow uncased characters and lowercase characters only cased ones.
        Return False otherwise.
        """

    def isupper():
        """S.isupper() -> bool

        Return True if all cased characters in S are uppercase and there is
        at least one cased character in S, False otherwise.
        """

    def join():
        """S.join(iterable) -> unicode

        Return a string which is the concatenation of the strings in the
        iterable.  The separator between elements is S.
        """

    def ljust():
        """S.ljust(width[, fillchar]) -> int

        Return S left-justified in a Unicode string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def lower():
        """S.lower() -> unicode

        Return a copy of the string S converted to lowercase.
        """

    def lstrip():
        """S.lstrip([chars]) -> unicode

        Return a copy of the string S with leading whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """

    def maketrans():
        """str.maketrans(x[, y[, z]]) -> dict (static method)

        Return a translation table usable for str.translate().  If there
        is only one argument, it must be a dictionary mapping Unicode
        ordinals (integers) or characters to Unicode ordinals, strings
        or None.  Character keys will be then converted to ordinals.  If
        there are two arguments, they must be strings of equal length,
        and in the resulting dictionary, each character in x will be
        mapped to the character at the same position in y. If there is a
        third argument, it must be a string, whose characters will be
        mapped to None in the result.
        """

    def partition():
        """S.partition(sep) -> (head, sep, tail)

        Search for the separator sep in S, and return the part before it,
        the separator itself, and the part after it.  If the separator is not
        found, return S and two empty strings.
        """

    def replace():
        """S.replace(old, new[, count]) -> unicode

        Return a copy of S with all occurrences of substring
        old replaced by new.  If the optional argument count is
        given, only the first count occurrences are replaced.
        """

    def rfind():
        """S.rfind(sub[, start[, end]]) -> int

        Return the highest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def rindex():
        """S.rindex(sub[, start[, end]]) -> int

        Like S.rfind() but raise ValueError when the substring is not found.
        """

    def rjust():
        """S.rjust(width[, fillchar]) -> unicode

        Return S right-justified in a Unicode string of length width. Padding
        is done using the specified fill character (default is a space).
        """

    def rpartition():
        """S.rpartition(sep) -> (head, sep, tail)

        Search for the separator sep in S, starting at the end of S, and return
        the part before it, the separator itself, and the part after it.  If
        the separator is not found, return two empty strings and S.
        """

    def rsplit():
        """S.rsplit(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in S, using sep as the
        delimiter string, starting at the end of the string and
        working to the front.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified, any whitespace string
        is a separator.
        """

    def rstrip():
        """S.rstrip([chars]) -> unicode

        Return a copy of the string S with trailing whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """

    def split():
        """S.split(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in S, using sep as the
        delimiter string.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified or is None, any
        whitespace string is a separator and empty strings are
        removed from the result.
        """

    def splitlines():
        """S.splitlines(keepends=False) -> list of strings

        Return a list of the lines in S, breaking at line boundaries.
        Line breaks are not included in the resulting list unless keepends
        is given and true.
        """

    def startswith():
        """S.startswith(prefix[, start[, end]]) -> bool

        Return True if S starts with the specified prefix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        prefix can also be a tuple of strings to try.
        """

    def strip():
        """S.strip([chars]) -> unicode

        Return a copy of the string S with leading and trailing
        whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """

    def swapcase():
        """S.swapcase() -> unicode

        Return a copy of S with uppercase characters converted to lowercase
        and vice versa.
        """

    def title():
        """S.title() -> unicode

        Return a titlecased version of S, i.e. words start with title case
        characters, all remaining cased characters have lower case.
        """

    def translate():
        """S.translate(table) -> unicode

        Return a copy of the string S, where all characters have been mapped
        through the given translation table, which must be a mapping of
        Unicode ordinals to Unicode ordinals, Unicode strings or None.
        Unmapped characters are left untouched. Characters mapped to None
        are deleted.
        """

    def upper():
        """S.upper() -> unicode

        Return a copy of S converted to uppercase.
        """

    def zfill():
        """S.zfill(width) -> unicode

        Pad a numeric string S with zeros on the left, to fill a field
        of the specified width. The string S is never truncated.
        """


W_UnicodeObject.typedef = TypeDef(
    "str",
    __new__ = interp2app(W_UnicodeObject.descr_new),
    __doc__ = UnicodeDocstrings.__doc__,

    __repr__ = interp2app(W_UnicodeObject.descr_repr,
                          doc=UnicodeDocstrings.__repr__.__doc__),
    __str__ = interp2app(W_UnicodeObject.descr_str,
                         doc=UnicodeDocstrings.__str__.__doc__),
    __hash__ = interp2app(W_UnicodeObject.descr_hash,
                          doc=UnicodeDocstrings.__hash__.__doc__),

    __eq__ = interp2app(W_UnicodeObject.descr_eq,
                        doc=UnicodeDocstrings.__eq__.__doc__),
    __ne__ = interp2app(W_UnicodeObject.descr_ne,
                        doc=UnicodeDocstrings.__ne__.__doc__),
    __lt__ = interp2app(W_UnicodeObject.descr_lt,
                        doc=UnicodeDocstrings.__lt__.__doc__),
    __le__ = interp2app(W_UnicodeObject.descr_le,
                        doc=UnicodeDocstrings.__le__.__doc__),
    __gt__ = interp2app(W_UnicodeObject.descr_gt,
                        doc=UnicodeDocstrings.__gt__.__doc__),
    __ge__ = interp2app(W_UnicodeObject.descr_ge,
                        doc=UnicodeDocstrings.__ge__.__doc__),

    __iter__ = interp2app(W_UnicodeObject.descr_iter,
                         doc=UnicodeDocstrings.__iter__.__doc__),
    __len__ = interp2app(W_UnicodeObject.descr_len,
                         doc=UnicodeDocstrings.__len__.__doc__),
    __contains__ = interp2app(W_UnicodeObject.descr_contains,
                              doc=UnicodeDocstrings.__contains__.__doc__),

    __add__ = interp2app(W_UnicodeObject.descr_add,
                         doc=UnicodeDocstrings.__add__.__doc__),
    __mul__ = interp2app(W_UnicodeObject.descr_mul,
                         doc=UnicodeDocstrings.__mul__.__doc__),
    __rmul__ = interp2app(W_UnicodeObject.descr_mul,
                          doc=UnicodeDocstrings.__rmul__.__doc__),

    __getitem__ = interp2app(W_UnicodeObject.descr_getitem,
                             doc=UnicodeDocstrings.__getitem__.__doc__),

    capitalize = interp2app(W_UnicodeObject.descr_capitalize,
                            doc=UnicodeDocstrings.capitalize.__doc__),
    casefold = interp2app(W_UnicodeObject.descr_casefold,
                            doc=UnicodeDocstrings.casefold.__doc__),
    center = interp2app(W_UnicodeObject.descr_center,
                        doc=UnicodeDocstrings.center.__doc__),
    count = interp2app(W_UnicodeObject.descr_count,
                       doc=UnicodeDocstrings.count.__doc__),
    encode = interp2app(W_UnicodeObject.descr_encode,
                        doc=UnicodeDocstrings.encode.__doc__),
    expandtabs = interp2app(W_UnicodeObject.descr_expandtabs,
                            doc=UnicodeDocstrings.expandtabs.__doc__),
    find = interp2app(W_UnicodeObject.descr_find,
                      doc=UnicodeDocstrings.find.__doc__),
    rfind = interp2app(W_UnicodeObject.descr_rfind,
                       doc=UnicodeDocstrings.rfind.__doc__),
    index = interp2app(W_UnicodeObject.descr_index,
                       doc=UnicodeDocstrings.index.__doc__),
    rindex = interp2app(W_UnicodeObject.descr_rindex,
                        doc=UnicodeDocstrings.rindex.__doc__),
    isalnum = interp2app(W_UnicodeObject.descr_isalnum,
                         doc=UnicodeDocstrings.isalnum.__doc__),
    isalpha = interp2app(W_UnicodeObject.descr_isalpha,
                         doc=UnicodeDocstrings.isalpha.__doc__),
    isdecimal = interp2app(W_UnicodeObject.descr_isdecimal,
                           doc=UnicodeDocstrings.isdecimal.__doc__),
    isdigit = interp2app(W_UnicodeObject.descr_isdigit,
                         doc=UnicodeDocstrings.isdigit.__doc__),
    isidentifier = interp2app(W_UnicodeObject.descr_isidentifier,
                         doc=UnicodeDocstrings.isidentifier.__doc__),
    islower = interp2app(W_UnicodeObject.descr_islower,
                         doc=UnicodeDocstrings.islower.__doc__),
    isnumeric = interp2app(W_UnicodeObject.descr_isnumeric,
                           doc=UnicodeDocstrings.isnumeric.__doc__),
    isprintable = interp2app(W_UnicodeObject.descr_isprintable,
                         doc=UnicodeDocstrings.isprintable.__doc__),
    isspace = interp2app(W_UnicodeObject.descr_isspace,
                         doc=UnicodeDocstrings.isspace.__doc__),
    istitle = interp2app(W_UnicodeObject.descr_istitle,
                         doc=UnicodeDocstrings.istitle.__doc__),
    isupper = interp2app(W_UnicodeObject.descr_isupper,
                         doc=UnicodeDocstrings.isupper.__doc__),
    join = interp2app(W_UnicodeObject.descr_join,
                      doc=UnicodeDocstrings.join.__doc__),
    ljust = interp2app(W_UnicodeObject.descr_ljust,
                       doc=UnicodeDocstrings.ljust.__doc__),
    rjust = interp2app(W_UnicodeObject.descr_rjust,
                       doc=UnicodeDocstrings.rjust.__doc__),
    lower = interp2app(W_UnicodeObject.descr_lower,
                       doc=UnicodeDocstrings.lower.__doc__),
    partition = interp2app(W_UnicodeObject.descr_partition,
                           doc=UnicodeDocstrings.partition.__doc__),
    rpartition = interp2app(W_UnicodeObject.descr_rpartition,
                            doc=UnicodeDocstrings.rpartition.__doc__),
    replace = interp2app(W_UnicodeObject.descr_replace,
                         doc=UnicodeDocstrings.replace.__doc__),
    split = interp2app(W_UnicodeObject.descr_split,
                       doc=UnicodeDocstrings.split.__doc__),
    rsplit = interp2app(W_UnicodeObject.descr_rsplit,
                        doc=UnicodeDocstrings.rsplit.__doc__),
    splitlines = interp2app(W_UnicodeObject.descr_splitlines,
                            doc=UnicodeDocstrings.splitlines.__doc__),
    startswith = interp2app(W_UnicodeObject.descr_startswith,
                            doc=UnicodeDocstrings.startswith.__doc__),
    endswith = interp2app(W_UnicodeObject.descr_endswith,
                          doc=UnicodeDocstrings.endswith.__doc__),
    strip = interp2app(W_UnicodeObject.descr_strip,
                       doc=UnicodeDocstrings.strip.__doc__),
    lstrip = interp2app(W_UnicodeObject.descr_lstrip,
                        doc=UnicodeDocstrings.lstrip.__doc__),
    rstrip = interp2app(W_UnicodeObject.descr_rstrip,
                        doc=UnicodeDocstrings.rstrip.__doc__),
    swapcase = interp2app(W_UnicodeObject.descr_swapcase,
                          doc=UnicodeDocstrings.swapcase.__doc__),
    title = interp2app(W_UnicodeObject.descr_title,
                       doc=UnicodeDocstrings.title.__doc__),
    translate = interp2app(W_UnicodeObject.descr_translate,
                           doc=UnicodeDocstrings.translate.__doc__),
    upper = interp2app(W_UnicodeObject.descr_upper,
                       doc=UnicodeDocstrings.upper.__doc__),
    zfill = interp2app(W_UnicodeObject.descr_zfill,
                       doc=UnicodeDocstrings.zfill.__doc__),

    format = interp2app(W_UnicodeObject.descr_format,
                        doc=UnicodeDocstrings.format.__doc__),
    format_map = interp2app(W_UnicodeObject.descr_format_map,
                        doc=UnicodeDocstrings.format_map.__doc__),
    __format__ = interp2app(W_UnicodeObject.descr__format__,
                            doc=UnicodeDocstrings.__format__.__doc__),
    __mod__ = interp2app(W_UnicodeObject.descr_mod,
                         doc=UnicodeDocstrings.__mod__.__doc__),
    __rmod__ = interp2app(W_UnicodeObject.descr_rmod,
                         doc=UnicodeDocstrings.__rmod__.__doc__),
    __getnewargs__ = interp2app(W_UnicodeObject.descr_getnewargs,
                                doc=UnicodeDocstrings.__getnewargs__.__doc__),
    maketrans = interp2app(W_UnicodeObject.descr_maketrans,
                           as_classmethod=True,
                           doc=UnicodeDocstrings.maketrans.__doc__),
)
W_UnicodeObject.typedef.flag_sequence_bug_compat = True


def _create_list_from_unicode(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_unicode
    return [s for s in value]


W_UnicodeObject.EMPTY = W_UnicodeObject(u'')

# Helper for converting int/long this is called only from
# {int,long,float}type.descr__new__: in the default branch this is implemented
# using the same logic as PyUnicode_EncodeDecimal, as CPython 2.7 does.
#
# In CPython3 the call to PyUnicode_EncodeDecimal has been replaced to a call
# to _PyUnicode_TransformDecimalAndSpaceToASCII, which is much simpler.
# We do that here plus the final step of encoding the result to utf-8.
# This final step corresponds to encode_utf8. In float.__new__() and
# complex.__new__(), a lone surrogate will throw an app-level
# UnicodeEncodeError.

def unicode_to_decimal_w(space, w_unistr, allow_surrogates=False):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise oefmt(space.w_TypeError, "expected unicode, got '%T'", w_unistr)
    value = _rpy_unicode_to_decimal_w(space, w_unistr._value)
    return unicodehelper.encode_utf8(space, value,
                                     allow_surrogates=allow_surrogates)

def _rpy_unicode_to_decimal_w(space, unistr):
    result = [u'\0'] * len(unistr)
    for i in xrange(len(unistr)):
        uchr = ord(unistr[i])
        if uchr > 127:
            if unicodedb.isspace(uchr):
                result[i] = ' '
                continue
            try:
                uchr = ord(u'0') + unicodedb.decimal(uchr)
            except KeyError:
                pass
        result[i] = unichr(uchr)
    return u''.join(result)

@jit.elidable
def g_encode_utf8(value):
    """This is a global function because of jit.conditional_call_value"""
    return unicode_encode_utf8_forbid_surrogates(value, len(value))

_repr_function, _ = make_unicode_escape_function(
    pass_printable=True, unicode_output=True, quotes=True, prefix='')
