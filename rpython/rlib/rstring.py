""" String builder interface and string functions
"""
import sys

from rpython.annotator.model import (SomeObject, SomeString, s_None, SomeChar,
    SomeInteger, SomeUnicodeCodePoint, SomeUnicodeString, SomePBC)
from rpython.rtyper.llannotation import SomePtr
from rpython.rlib import jit
from rpython.rlib.objectmodel import newlist_hint, resizelist_hint, specialize, not_rpython
from rpython.rlib.rarithmetic import ovfcheck, LONG_BIT as BLOOM_WIDTH
from rpython.rlib.unicodedata import unicodedb_5_2_0 as unicodedb
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.tool.pairtype import pairtype


# -------------- public API for string functions -----------------------

@specialize.argtype(0)
def _isspace(char):
    if isinstance(char, str):
        return char.isspace()
    else:
        assert isinstance(char, unicode)
        return unicodedb.isspace(ord(char))


@specialize.argtype(0, 1)
def split(value, by=None, maxsplit=-1):
    if by is None:
        length = len(value)
        i = 0
        res = []
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
            res.append(value[i:j])

            # continue to look from the character following the space after the word
            i = j + 1
        return res

    if isinstance(value, unicode):
        assert isinstance(by, unicode)
    if isinstance(value, str):
        assert isinstance(by, str)
    if isinstance(value, list):
        assert isinstance(by, str)

    bylen = len(by)
    if bylen == 0:
        raise ValueError("empty separator")

    start = 0
    if bylen == 1:
        # fast path: uses str.rfind(character) and str.count(character)
        by = by[0]    # annotator hack: string -> char
        cnt = count(value, by, 0, len(value))
        if 0 <= maxsplit < cnt:
            cnt = maxsplit
        res = newlist_hint(cnt + 1)
        while cnt > 0:
            next = find(value, by, start, len(value))
            assert next >= 0 # cannot fail due to the value.count above
            res.append(value[start:next])
            start = next + bylen
            cnt -= 1
        res.append(value[start:len(value)])
        return res

    if maxsplit > 0:
        res = newlist_hint(min(maxsplit + 1, len(value)))
    else:
        res = []

    while maxsplit != 0:
        next = find(value, by, start, len(value))
        if next < 0:
            break
        assert start >= 0
        res.append(value[start:next])
        start = next + bylen
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res.append(value[start:len(value)])
    return res


@specialize.argtype(0, 1)
def rsplit(value, by=None, maxsplit=-1):
    if by is None:
        res = []

        i = len(value) - 1
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
            res.append(value[j1:i+1])

            # continue to look from the character before the space before the word
            i = j - 1

        res.reverse()
        return res

    if isinstance(value, unicode):
        assert isinstance(by, unicode)
    if isinstance(value, str):
        assert isinstance(by, str)
    if isinstance(value, list):
        assert isinstance(by, str)

    if maxsplit > 0:
        res = newlist_hint(min(maxsplit + 1, len(value)))
    else:
        res = []
    end = len(value)
    bylen = len(by)
    if bylen == 0:
        raise ValueError("empty separator")

    while maxsplit != 0:
        next = rfind(value, by, 0, end)
        if next < 0:
            break
        res.append(value[next + bylen:end])
        end = next
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res.append(value[:end])
    res.reverse()
    return res


@specialize.argtype(0, 1)
@jit.elidable
def replace(input, sub, by, maxsplit=-1):
    if isinstance(input, str):
        Builder = StringBuilder
    elif isinstance(input, unicode):
        Builder = UnicodeBuilder
    else:
        assert isinstance(input, list)
        Builder = ByteListBuilder
    if maxsplit == 0:
        return input


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
            raise
        builder = Builder(result_size)
        for i in range(upper):
            builder.append(by)
            builder.append(input[i])
        builder.append(by)
        builder.append_slice(input, upper, len(input))
    else:
        # First compute the exact result size
        cnt = count(input, sub, 0, len(input))
        if cnt > maxsplit and maxsplit > 0:
            cnt = maxsplit
        diff_len = len(by) - len(sub)
        try:
            result_size = ovfcheck(diff_len * cnt)
            result_size = ovfcheck(result_size + len(input))
        except OverflowError:
            raise

        builder = Builder(result_size)
        start = 0
        sublen = len(sub)

        while maxsplit != 0:
            next = find(input, sub, start, len(input))
            if next < 0:
                break
            builder.append_slice(input, start, next)
            builder.append(by)
            start = next + sublen
            maxsplit -= 1   # NB. if it's already < 0, it stays < 0

        builder.append_slice(input, start, len(input))

    return builder.build()

def _normalize_start_end(length, start, end):
    if start < 0:
        start += length
        if start < 0:
            start = 0
    if end < 0:
        end += length
        if end < 0:
            end = 0
    elif end > length:
        end = length
    return start, end

@specialize.argtype(0, 1)
@jit.elidable
def startswith(u_self, prefix, start=0, end=sys.maxint):
    length = len(u_self)
    start, end = _normalize_start_end(length, start, end)
    stop = start + len(prefix)
    if stop > end:
        return False
    for i in range(len(prefix)):
        if u_self[start+i] != prefix[i]:
            return False
    return True

@specialize.argtype(0, 1)
@jit.elidable
def endswith(u_self, suffix, start=0, end=sys.maxint):
    length = len(u_self)
    start, end = _normalize_start_end(length, start, end)
    begin = end - len(suffix)
    if begin < start:
        return False
    for i in range(len(suffix)):
        if u_self[begin+i] != suffix[i]:
            return False
    return True

@specialize.argtype(0, 1)
def find(value, other, start, end):
    if ((isinstance(value, str) and isinstance(other, str)) or
        (isinstance(value, unicode) and isinstance(other, unicode))):
        return value.find(other, start, end)
    return _search(value, other, start, end, SEARCH_FIND)

@specialize.argtype(0, 1)
def rfind(value, other, start, end):
    if ((isinstance(value, str) and isinstance(other, str)) or
        (isinstance(value, unicode) and isinstance(other, unicode))):
        return value.rfind(other, start, end)
    return _search(value, other, start, end, SEARCH_RFIND)

@specialize.argtype(0, 1)
def count(value, other, start, end):
    if ((isinstance(value, str) and isinstance(other, str)) or
        (isinstance(value, unicode) and isinstance(other, unicode))):
        return value.count(other, start, end)
    return _search(value, other, start, end, SEARCH_COUNT)

# -------------- substring searching helper ----------------
# XXX a lot of code duplication with lltypesystem.rstr :-(

SEARCH_COUNT = 0
SEARCH_FIND = 1
SEARCH_RFIND = 2

def bloom_add(mask, c):
    return mask | (1 << (ord(c) & (BLOOM_WIDTH - 1)))

def bloom(mask, c):
    return mask & (1 << (ord(c) & (BLOOM_WIDTH - 1)))

@specialize.argtype(0, 1)
def _search(value, other, start, end, mode):
    if start < 0:
        start = 0
    if end > len(value):
        end = len(value)
    if start > end:
        if mode == SEARCH_COUNT:
            return 0
        return -1

    count = 0
    n = end - start
    m = len(other)

    if m == 0:
        if mode == SEARCH_COUNT:
            return end - start + 1
        elif mode == SEARCH_RFIND:
            return end
        else:
            return start

    w = n - m

    if w < 0:
        if mode == SEARCH_COUNT:
            return 0
        return -1

    mlast = m - 1
    skip = mlast - 1
    mask = 0

    if mode != SEARCH_RFIND:
        for i in range(mlast):
            mask = bloom_add(mask, other[i])
            if other[i] == other[mlast]:
                skip = mlast - i - 1
        mask = bloom_add(mask, other[mlast])

        i = start - 1
        while i + 1 <= start + w:
            i += 1
            if value[i + m - 1] == other[m - 1]:
                for j in range(mlast):
                    if value[i + j] != other[j]:
                        break
                else:
                    if mode != SEARCH_COUNT:
                        return i
                    count += 1
                    i += mlast
                    continue

                if i + m < len(value):
                    c = value[i + m]
                else:
                    c = '\0'
                if not bloom(mask, c):
                    i += m
                else:
                    i += skip
            else:
                if i + m < len(value):
                    c = value[i + m]
                else:
                    c = '\0'
                if not bloom(mask, c):
                    i += m
    else:
        mask = bloom_add(mask, other[0])
        for i in range(mlast, 0, -1):
            mask = bloom_add(mask, other[i])
            if other[i] == other[0]:
                skip = i - 1

        i = start + w + 1
        while i - 1 >= start:
            i -= 1
            if value[i] == other[0]:
                for j in xrange(mlast, 0, -1):
                    if value[i + j] != other[j]:
                        break
                else:
                    return i
                if i - 1 >= 0 and not bloom(mask, value[i - 1]):
                    i -= m
                else:
                    i -= skip
            else:
                if i - 1 >= 0 and not bloom(mask, value[i - 1]):
                    i -= m

    if mode != SEARCH_COUNT:
        return -1
    return count

# -------------- numeric parsing support --------------------

def strip_spaces(s):
    # XXX this is not locale-dependent
    p = 0
    q = len(s)
    while p < q and s[p] in ' \f\n\r\t\v':
        p += 1
    while p < q and s[q-1] in ' \f\n\r\t\v':
        q -= 1
    assert q >= p     # annotator hint, don't remove
    return s[p:q]

class ParseStringError(Exception):
    def __init__(self, msg):
        self.msg = msg

class InvalidBaseError(ParseStringError):
    """Signals an invalid base argument"""

class ParseStringOverflowError(Exception):
    def __init__(self, parser):
        self.parser = parser

# iterator-like class
class NumberStringParser:

    def error(self):
        raise ParseStringError("invalid literal for %s() with base %d" %
                               (self.fname, self.original_base))

    def __init__(self, s, literal, base, fname):
        self.fname = fname
        sign = 1
        if s.startswith('-'):
            sign = -1
            s = strip_spaces(s[1:])
        elif s.startswith('+'):
            s = strip_spaces(s[1:])
        self.sign = sign
        self.original_base = base

        if base == 0:
            if s.startswith('0x') or s.startswith('0X'):
                base = 16
            elif s.startswith('0b') or s.startswith('0B'):
                base = 2
            elif s.startswith('0'): # also covers the '0o' case
                base = 8
            else:
                base = 10
        elif base < 2 or base > 36:
            raise InvalidBaseError("%s() base must be >= 2 and <= 36" % fname)
        self.base = base

        if base == 16 and (s.startswith('0x') or s.startswith('0X')):
            s = s[2:]
        if base == 8 and (s.startswith('0o') or s.startswith('0O')):
            s = s[2:]
        if base == 2 and (s.startswith('0b') or s.startswith('0B')):
            s = s[2:]
        if not s:
            self.error()
        self.s = s
        self.n = len(s)
        self.i = 0

    def rewind(self):
        self.i = 0

    def next_digit(self): # -1 => exhausted
        if self.i < self.n:
            c = self.s[self.i]
            digit = ord(c)
            if '0' <= c <= '9':
                digit -= ord('0')
            elif 'A' <= c <= 'Z':
                digit = (digit - ord('A')) + 10
            elif 'a' <= c <= 'z':
                digit = (digit - ord('a')) + 10
            else:
                self.error()
            if digit >= self.base:
                self.error()
            self.i += 1
            return digit
        else:
            return -1

    def prev_digit(self):
        # After exhausting all n digits in next_digit(), you can walk them
        # again in reverse order by calling prev_digit() exactly n times
        i = self.i - 1
        assert i >= 0
        self.i = i
        c = self.s[i]
        digit = ord(c)
        if '0' <= c <= '9':
            digit -= ord('0')
        elif 'A' <= c <= 'Z':
            digit = (digit - ord('A')) + 10
        elif 'a' <= c <= 'z':
            digit = (digit - ord('a')) + 10
        else:
            raise AssertionError
        return digit

# -------------- public API ---------------------------------

INIT_SIZE = 100 # XXX tweak


class AbstractStringBuilder(object):
    # This is not the real implementation!

    @not_rpython
    def __init__(self, init_size=INIT_SIZE):
        self._l = []
        self._size = 0

    @not_rpython
    def _grow(self, size):
        self._size += size

    @not_rpython
    def append(self, s):
        assert isinstance(s, self._tp)
        self._l.append(s)
        self._grow(len(s))

    @not_rpython
    def append_slice(self, s, start, end):
        assert isinstance(s, self._tp)
        assert 0 <= start <= end <= len(s)
        s = s[start:end]
        self._l.append(s)
        self._grow(len(s))

    @not_rpython
    def append_multiple_char(self, c, times):
        assert isinstance(c, self._tp)
        self._l.append(c * times)
        self._grow(times)

    @not_rpython
    def append_charpsize(self, s, size):
        assert size >= 0
        l = []
        for i in xrange(size):
            l.append(s[i])
        self._l.append(self._tp("").join(l))
        self._grow(size)

    @not_rpython
    def build(self):
        result = self._tp("").join(self._l)
        assert len(result) == self._size
        self._l = [result]
        return result

    @not_rpython
    def getlength(self):
        return self._size


class StringBuilder(AbstractStringBuilder):
    _tp = str


class UnicodeBuilder(AbstractStringBuilder):
    _tp = unicode

class ByteListBuilder(object):
    def __init__(self, init_size=INIT_SIZE):
        assert init_size >= 0
        self.l = newlist_hint(init_size)

    @specialize.argtype(1)
    def append(self, s):
        l = self.l
        for c in s:
            l.append(c)

    @specialize.argtype(1)
    def append_slice(self, s, start, end):
        l = self.l
        for i in xrange(start, end):
            l.append(s[i])

    def append_multiple_char(self, c, times):
        assert isinstance(c, str)
        self.l.extend([c[0]] * times)

    def append_charpsize(self, s, size):
        assert size >= 0
        l = self.l
        for i in xrange(size):
            l.append(s[i])

    def build(self):
        return self.l

    def getlength(self):
        return len(self.l)

# ------------------------------------------------------------
# ----------------- implementation details -------------------
# ------------------------------------------------------------

class SomeStringBuilder(SomeObject):
    def method_append(self, s_str):
        if s_str != s_None:
            assert isinstance(s_str, (SomeString, SomeChar))
        return s_None

    def method_append_slice(self, s_str, s_start, s_end):
        if s_str != s_None:
            assert isinstance(s_str, SomeString)
        assert isinstance(s_start, SomeInteger)
        assert isinstance(s_end, SomeInteger)
        return s_None

    def method_append_multiple_char(self, s_char, s_times):
        assert isinstance(s_char, SomeChar)
        assert isinstance(s_times, SomeInteger)
        return s_None

    def method_append_charpsize(self, s_ptr, s_size):
        assert isinstance(s_ptr, SomePtr)
        assert isinstance(s_size, SomeInteger)
        return s_None

    def method_getlength(self):
        return SomeInteger(nonneg=True)

    def method_build(self):
        return SomeString(can_be_None=False)

    def rtyper_makerepr(self, rtyper):
        from rpython.rtyper.lltypesystem.rbuilder import stringbuilder_repr
        return stringbuilder_repr

    def rtyper_makekey(self):
        return self.__class__,

    def noneify(self):
        return self


class SomeUnicodeBuilder(SomeObject):
    def method_append(self, s_str):
        if s_str != s_None:
            assert isinstance(s_str, (SomeUnicodeCodePoint, SomeUnicodeString))
        return s_None

    def method_append_slice(self, s_str, s_start, s_end):
        if s_str != s_None:
            assert isinstance(s_str, SomeUnicodeString)
        assert isinstance(s_start, SomeInteger)
        assert isinstance(s_end, SomeInteger)
        return s_None

    def method_append_multiple_char(self, s_char, s_times):
        assert isinstance(s_char, SomeUnicodeCodePoint)
        assert isinstance(s_times, SomeInteger)
        return s_None

    def method_append_charpsize(self, s_ptr, s_size):
        assert isinstance(s_ptr, SomePtr)
        assert isinstance(s_size, SomeInteger)
        return s_None

    def method_getlength(self):
        return SomeInteger(nonneg=True)

    def method_build(self):
        return SomeUnicodeString(can_be_None=False)

    def rtyper_makerepr(self, rtyper):
        from rpython.rtyper.lltypesystem.rbuilder import unicodebuilder_repr
        return unicodebuilder_repr

    def rtyper_makekey(self):
        return self.__class__,

    def noneify(self):
        return self


class BaseEntry(object):
    def compute_result_annotation(self, s_init_size=None):
        if s_init_size is not None:
            assert isinstance(s_init_size, SomeInteger)
        if self.use_unicode:
            return SomeUnicodeBuilder()
        return SomeStringBuilder()

    def specialize_call(self, hop):
        return hop.r_result.rtyper_new(hop)


class StringBuilderEntry(BaseEntry, ExtRegistryEntry):
    _about_ = StringBuilder
    use_unicode = False

class UnicodeBuilderEntry(BaseEntry, ExtRegistryEntry):
    _about_ = UnicodeBuilder
    use_unicode = True

class __extend__(pairtype(SomeStringBuilder, SomeStringBuilder)):

    def union((obj1, obj2)):
        return obj1

class __extend__(pairtype(SomeUnicodeBuilder, SomeUnicodeBuilder)):

    def union((obj1, obj2)):
        return obj1

class PrebuiltStringBuilderEntry(ExtRegistryEntry):
    _type_ = StringBuilder

    def compute_annotation(self):
        return SomeStringBuilder()

class PrebuiltUnicodeBuilderEntry(ExtRegistryEntry):
    _type_ = UnicodeBuilder

    def compute_annotation(self):
        return SomeUnicodeBuilder()


#___________________________________________________________________
# Support functions for SomeString.no_nul

def assert_str0(fname):
    assert '\x00' not in fname, "NUL byte in string"
    return fname

class Entry(ExtRegistryEntry):
    _about_ = assert_str0

    def compute_result_annotation(self, s_obj):
        if s_None.contains(s_obj):
            return s_obj
        assert isinstance(s_obj, (SomeString, SomeUnicodeString))
        if s_obj.no_nul:
            return s_obj
        new_s_obj = SomeObject.__new__(s_obj.__class__)
        new_s_obj.__dict__ = s_obj.__dict__.copy()
        new_s_obj.no_nul = True
        return new_s_obj

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputarg(hop.args_r[0], arg=0)

def check_str0(fname):
    """A 'probe' to trigger a failure at translation time, if the
    string was not proved to not contain NUL characters."""
    assert '\x00' not in fname, "NUL byte in string"

class Entry(ExtRegistryEntry):
    _about_ = check_str0

    def compute_result_annotation(self, s_obj):
        if not isinstance(s_obj, (SomeString, SomeUnicodeString)):
            return s_obj
        if not s_obj.no_nul:
            raise ValueError("Value is not no_nul")

    def specialize_call(self, hop):
        hop.exception_cannot_occur()


