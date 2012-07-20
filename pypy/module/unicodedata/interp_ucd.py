"""
Implementation of the interpreter-level functions in the module unicodedata.
"""
from pypy.interpreter.gateway import  interp2app, unwrap_spec, NoneNotWrapped
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.rlib.rarithmetic import r_longlong
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.runicode import MAXUNICODE
import sys

from pypy.module.unicodedata import unicodedb_5_2_0, unicodedb_3_2_0

# Contants for Hangul characters
SBase = 0xAC00
LBase = 0x1100
VBase = 0x1161
TBase = 0x11A7
LCount = 19
VCount = 21
TCount = 28
NCount = (VCount*TCount)
SCount = (LCount*NCount)

# Since Python2.7, the unicodedata module gives a preview of Python3 character
# handling: on narrow unicode builds, a surrogate pair is considered as one
# unicode code point.

# The functions below are subtly different from the ones in runicode.py.
# When PyPy implements Python 3 they should be merged.

def UNICHR(c):
    if c <= sys.maxunicode and c <= MAXUNICODE:
        return unichr(c)
    else:
        c -= 0x10000
        return (unichr(0xD800 + (c >> 10)) +
                unichr(0xDC00 + (c & 0x03FF)))

def ORD(u):
    assert isinstance(u, unicode)
    if len(u) == 1:
        return ord(u[0])
    elif len(u) == 2:
        ch1 = ord(u[0])
        ch2 = ord(u[1])
        if 0xD800 <= ch1 <= 0xDBFF and 0xDC00 <= ch2 <= 0xDFFF:
            return (((ch1 - 0xD800) << 10) | (ch2 - 0xDC00)) + 0x10000
    raise ValueError

if MAXUNICODE > 0xFFFF:
    # Target is wide build
    def unichr_to_code_w(space, w_unichr):
        if not space.is_true(space.isinstance(w_unichr, space.w_unicode)):
            raise OperationError(space.w_TypeError, space.wrap(
                'argument 1 must be unicode'))

        if not we_are_translated() and sys.maxunicode == 0xFFFF:
            # Host CPython is narrow build, accept surrogates
            try:
                return ORD(space.unicode_w(w_unichr))
            except ValueError:
                raise OperationError(space.w_TypeError, space.wrap(
                    'need a single Unicode character as parameter'))
        else:
            if not space.len_w(w_unichr) == 1:
                raise OperationError(space.w_TypeError, space.wrap(
                    'need a single Unicode character as parameter'))
            return space.int_w(space.ord(w_unichr))

    def code_to_unichr(code):
        if not we_are_translated() and sys.maxunicode == 0xFFFF:
            # Host CPython is narrow build, generate surrogates
            return UNICHR(code)
        else:
            return unichr(code)
else:
    # Target is narrow build
    def unichr_to_code_w(space, w_unichr):
        if not space.is_true(space.isinstance(w_unichr, space.w_unicode)):
            raise OperationError(space.w_TypeError, space.wrap(
                'argument 1 must be unicode'))

        if not we_are_translated() and sys.maxunicode > 0xFFFF:
            # Host CPython is wide build, forbid surrogates
            if not space.len_w(w_unichr) == 1:
                raise OperationError(space.w_TypeError, space.wrap(
                    'need a single Unicode character as parameter'))
            return space.int_w(space.ord(w_unichr))

        else:
            # Accept surrogates
            try:
                return ORD(space.unicode_w(w_unichr))
            except ValueError:
                raise OperationError(space.w_TypeError, space.wrap(
                    'need a single Unicode character as parameter'))

    def code_to_unichr(code):
        # generate surrogates for large codes
        return UNICHR(code)


class UCD(Wrappable):
    def __init__(self, unicodedb):
        self._lookup = unicodedb.lookup
        self._name = unicodedb.name
        self._decimal = unicodedb.decimal
        self._digit = unicodedb.digit
        self._numeric = unicodedb.numeric
        self._category = unicodedb.category
        self._east_asian_width = unicodedb.east_asian_width
        self._bidirectional = unicodedb.bidirectional
        self._combining = unicodedb.combining
        self._mirrored = unicodedb.mirrored
        self._decomposition = unicodedb.decomposition
        self._canon_decomposition = unicodedb.canon_decomposition
        self._compat_decomposition = unicodedb.compat_decomposition
        self._composition = unicodedb._composition

        self.version = unicodedb.version

    @unwrap_spec(name=str)
    def _get_code(self, space, name):
        try:
            code = self._lookup(name.upper())
        except KeyError:
            msg = space.mod(space.wrap("undefined character name '%s'"), space.wrap(name))
            raise OperationError(space.w_KeyError, msg)
        return space.wrap(code)

    @unwrap_spec(name=str)
    def lookup(self, space, name):
        try:
            code = self._lookup(name.upper())
        except KeyError:
            msg = space.mod(space.wrap("undefined character name '%s'"), space.wrap(name))
            raise OperationError(space.w_KeyError, msg)
        return space.wrap(code_to_unichr(code))

    def name(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            name = self._name(code)
        except KeyError:
            if w_default is not None:
                return w_default
            raise OperationError(space.w_ValueError, space.wrap('no such name'))
        return space.wrap(name)


    def decimal(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._decimal(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError, space.wrap('not a decimal'))

    def digit(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._digit(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError, space.wrap('not a digit'))

    def numeric(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._numeric(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError,
                             space.wrap('not a numeric character'))

    def category(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._category(code))

    def east_asian_width(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._east_asian_width(code))

    def bidirectional(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._bidirectional(code))

    def combining(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._combining(code))

    def mirrored(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        # For no reason, unicodedata.mirrored() returns an int, not a bool
        return space.wrap(int(self._mirrored(code)))

    def decomposition(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._decomposition(code))

    @unwrap_spec(form=str)
    def normalize(self, space, form, w_unistr):
        if not space.is_true(space.isinstance(w_unistr, space.w_unicode)):
            raise OperationError(space.w_TypeError, space.wrap('argument 2 must be unicode'))
        if form == 'NFC':
            composed = True
            decomposition = self._canon_decomposition
        elif form == 'NFD':
            composed = False
            decomposition = self._canon_decomposition
        elif form == 'NFKC':
            composed = True
            decomposition = self._compat_decomposition
        elif form == 'NFKD':
            composed = False
            decomposition = self._compat_decomposition
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap('invalid normalization form'))

        strlen = space.len_w(w_unistr)
        result = [0] * (strlen + strlen / 10 + 10)
        j = 0
        resultlen = len(result)
        # Expand the character
        for i in range(strlen):
            ch = space.int_w(space.ord(space.getitem(w_unistr, space.wrap(i))))
            # Do Hangul decomposition
            if SBase <= ch < SBase + SCount:
                SIndex = ch - SBase;
                L = LBase + SIndex / NCount;
                V = VBase + (SIndex % NCount) / TCount;
                T = TBase + SIndex % TCount;
                if T == TBase:
                    if j + 2 > resultlen:
                        result.extend([0] * (j + 2 - resultlen + 10))
                        resultlen = len(result)
                    result[j] = L
                    result[j + 1] = V
                    j += 2
                else:
                    if j + 3 > resultlen:
                        result.extend([0] * (j + 3 - resultlen + 10))
                        resultlen = len(result)
                    result[j] = L
                    result[j + 1] = V
                    result[j + 2] = T
                    j += 3
                continue
            decomp = decomposition(ch)
            if decomp:
                decomplen = len(decomp)
                if j + decomplen > resultlen:
                    result.extend([0] * (j + decomplen - resultlen + 10))
                    resultlen = len(result)
                for ch in decomp:
                    result[j] = ch
                    j += 1
            else:
                if j + 1 > resultlen:
                    result.extend([0] * (j + 1 - resultlen + 10))
                    resultlen = len(result)
                result[j] = ch
                j += 1

        # Sort all combining marks
        for i in range(j):
            ch = result[i]
            comb = self._combining(ch)
            if comb == 0:
                continue
            for k in range(i, 0, -1):
                if self._combining(result[k - 1]) <= comb:
                    result[k] = ch
                    break

                result[k] = result[k - 1]
            else:
                result[0] = ch

        if not composed: # If decomposed normalization we are done
            return space.wrap(u''.join([unichr(i) for i in result[:j]]))

        if j <= 1:
            return space.wrap(u''.join([unichr(i) for i in result[:j]]))

        current = result[0]
        starter_pos = 0
        next_insert = 1
        prev_combining = 0
        if self._combining(current):
            prev_combining = 256
        for k in range(1, j):
            next = result[k]
            next_combining = self._combining(next)
            if next_insert == starter_pos + 1 or prev_combining < next_combining:
                # Combine if not blocked
                if (LBase <= current < LBase + LCount and
                    VBase <= next < VBase + VCount):
                    # If L, V -> LV
                    current = SBase + ((current - LBase)*VCount + (next - VBase)) * TCount
                    continue
                if (SBase <= current < SBase + SCount and
                    TBase <= next < TBase + TCount and
                    (current - SBase) % TCount == 0):
                    # If LV, T -> LVT
                    current = current + (next - TBase)
                    continue
                key = r_longlong(current) << 32 | next
                try:
                    current = self._composition[key]
                    continue
                except KeyError:
                    pass

            if next_combining == 0:
                # New starter symbol
                result[starter_pos] = current
                starter_pos = next_insert
                next_insert += 1
                prev_combining = 0
                current = next
                continue


            result[next_insert] = next
            next_insert += 1
            if next_combining > prev_combining:
                prev_combining = next_combining

        result[starter_pos] = current

        return space.wrap(u''.join([unichr(i) for i in result[:next_insert]]))


methods = {}
for methodname in """
        _get_code lookup name decimal digit numeric category east_asian_width
        bidirectional combining mirrored decomposition normalize
        """.split():
    methods[methodname] = interp2app(getattr(UCD, methodname))


UCD.typedef = TypeDef("unicodedata.UCD",
                      __doc__ = "",
                      unidata_version = interp_attrproperty('version', UCD),
                      **methods)

ucd_3_2_0 = UCD(unicodedb_3_2_0)
ucd_5_2_0 = UCD(unicodedb_5_2_0)
ucd = ucd_5_2_0
