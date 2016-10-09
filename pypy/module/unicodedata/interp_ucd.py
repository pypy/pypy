"""
Implementation of the interpreter-level functions in the module unicodedata.
"""

from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from rpython.rlib.rarithmetic import r_longlong
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.runicode import MAXUNICODE
from rpython.rlib.unicodedata import unicodedb_5_2_0, unicodedb_3_2_0
from rpython.rlib.runicode import code_to_unichr, ord_accepts_surrogate
import sys


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


if MAXUNICODE > 0xFFFF:
    # Target is wide build
    def unichr_to_code_w(space, w_unichr):
        if not space.isinstance_w(w_unichr, space.w_unicode):
            raise oefmt(
                space.w_TypeError, 'argument 1 must be unicode, not %T',
                w_unichr)

        if not we_are_translated() and sys.maxunicode == 0xFFFF:
            # Host CPython is narrow build, accept surrogates
            try:
                return ord_accepts_surrogate(space.unicode_w(w_unichr))
            except TypeError:
                raise oefmt(space.w_TypeError,
                            "need a single Unicode character as parameter")
        else:
            if not space.len_w(w_unichr) == 1:
                raise oefmt(space.w_TypeError,
                            "need a single Unicode character as parameter")
            return space.int_w(space.ord(w_unichr))

else:
    # Target is narrow build
    def unichr_to_code_w(space, w_unichr):
        if not space.isinstance_w(w_unichr, space.w_unicode):
            raise oefmt(
                space.w_TypeError, 'argument 1 must be unicode, not %T',
                w_unichr)

        if not we_are_translated() and sys.maxunicode > 0xFFFF:
            # Host CPython is wide build, forbid surrogates
            if not space.len_w(w_unichr) == 1:
                raise oefmt(space.w_TypeError,
                            "need a single Unicode character as parameter")
            return space.int_w(space.ord(w_unichr))

        else:
            # Accept surrogates
            try:
                return ord_accepts_surrogate(space.unicode_w(w_unichr))
            except TypeError:
                raise oefmt(space.w_TypeError,
                            "need a single Unicode character as parameter")


class UCD(W_Root):
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

    def name(self, space, w_unichr, w_default=None):
        code = unichr_to_code_w(space, w_unichr)
        try:
            name = self._name(code)
        except KeyError:
            if w_default is not None:
                return w_default
            raise oefmt(space.w_ValueError, "no such name")
        return space.wrap(name)

    def decimal(self, space, w_unichr, w_default=None):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._decimal(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise oefmt(space.w_ValueError, "not a decimal")

    def digit(self, space, w_unichr, w_default=None):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._digit(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise oefmt(space.w_ValueError, "not a digit")

    def numeric(self, space, w_unichr, w_default=None):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._numeric(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise oefmt(space.w_ValueError, "not a numeric character")

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
        if not space.isinstance_w(w_unistr, space.w_unicode):
            raise oefmt(
                space.w_TypeError, 'argument 2 must be unicode, not %T',
                w_unistr)
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
            raise oefmt(space.w_ValueError, "invalid normalization form")

        strlen = space.len_w(w_unistr)
        result = [0] * (strlen + strlen / 10 + 10)
        j = 0
        resultlen = len(result)
        # Expand the character
        for i in range(strlen):
            ch = space.int_w(space.ord(space.getitem(w_unistr, space.wrap(i))))
            # Do Hangul decomposition
            if SBase <= ch < SBase + SCount:
                SIndex = ch - SBase
                L = LBase + SIndex / NCount
                V = VBase + (SIndex % NCount) / TCount
                T = TBase + SIndex % TCount
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
