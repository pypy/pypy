""" String builder interface and string functions
"""
import sys

from rpython.annotator.model import (SomeObject, SomeString, s_None, SomeChar,
    SomeInteger, SomeUnicodeCodePoint, SomeUnicodeString, SomePtr, SomePBC)
from rpython.rlib.objectmodel import newlist_hint, specialize
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.tool.pairtype import pairtype
from rpython.rlib import jit


# -------------- public API for string functions -----------------------

@specialize.argtype(0)
def split(value, by=None, maxsplit=-1):
    if by is None:
        length = len(value)
        i = 0
        res = []
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
        return res

    if isinstance(value, str):
        assert isinstance(by, str)
    else:
        assert isinstance(by, unicode)
    bylen = len(by)
    if bylen == 0:
        raise ValueError("empty separator")

    start = 0
    if bylen == 1:
        # fast path: uses str.rfind(character) and str.count(character)
        by = by[0]    # annotator hack: string -> char
        count = value.count(by)
        if 0 <= maxsplit < count:
            count = maxsplit
        res = newlist_hint(count + 1)
        while count > 0:
            next = value.find(by, start)
            assert next >= 0 # cannot fail due to the value.count above
            res.append(value[start:next])
            start = next + bylen
            count -= 1
        res.append(value[start:len(value)])
        return res

    if maxsplit > 0:
        res = newlist_hint(min(maxsplit + 1, len(value)))
    else:
        res = []

    while maxsplit != 0:
        next = value.find(by, start)
        if next < 0:
            break
        res.append(value[start:next])
        start = next + bylen
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res.append(value[start:len(value)])
    return res


@specialize.argtype(0)
def rsplit(value, by=None, maxsplit=-1):
    if by is None:
        res = []

        i = len(value) - 1
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
            res.append(value[j1:i+1])

            # continue to look from the character before the space before the word
            i = j - 1

        res.reverse()
        return res

    if isinstance(value, str):
        assert isinstance(by, str)
    else:
        assert isinstance(by, unicode)
    if maxsplit > 0:
        res = newlist_hint(min(maxsplit + 1, len(value)))
    else:
        res = []
    end = len(value)
    bylen = len(by)
    if bylen == 0:
        raise ValueError("empty separator")

    while maxsplit != 0:
        next = value.rfind(by, 0, end)
        if next < 0:
            break
        res.append(value[next + bylen:end])
        end = next
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res.append(value[:end])
    res.reverse()
    return res


@specialize.argtype(0)
@jit.elidable
def replace(input, sub, by, maxsplit=-1):
    if isinstance(input, str):
        assert isinstance(sub, str)
        assert isinstance(by, str)
        Builder = StringBuilder
    else:
        assert isinstance(sub, unicode)
        assert isinstance(by, unicode)
        Builder = UnicodeBuilder
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
        count = input.count(sub)
        if count > maxsplit and maxsplit > 0:
            count = maxsplit
        diff_len = len(by) - len(sub)
        try:
            result_size = ovfcheck(diff_len * count)
            result_size = ovfcheck(result_size + len(input))
        except OverflowError:
            raise

        builder = Builder(result_size)
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

@specialize.argtype(0)
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

@specialize.argtype(0)
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

class ParseStringOverflowError(Exception):
    def __init__(self, parser):
        self.parser = parser

# iterator-like class
class NumberStringParser:

    def error(self):
        raise ParseStringError("invalid literal for %s() with base %d: '%s'" %
                               (self.fname, self.original_base, self.literal))

    def __init__(self, s, literal, base, fname):
        self.literal = literal
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
            raise ParseStringError, "%s() base must be >= 2 and <= 36" % (fname,)
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

# -------------- public API ---------------------------------

INIT_SIZE = 100 # XXX tweak


class AbstractStringBuilder(object):
    def __init__(self, init_size=INIT_SIZE):
        self.l = []
        self.size = 0

    def _grow(self, size):
        try:
            self.size = ovfcheck(self.size + size)
        except OverflowError:
            raise MemoryError

    def append(self, s):
        assert isinstance(s, self.tp)
        self.l.append(s)
        self._grow(len(s))

    def append_slice(self, s, start, end):
        assert isinstance(s, self.tp)
        assert 0 <= start <= end <= len(s)
        s = s[start:end]
        self.l.append(s)
        self._grow(len(s))

    def append_multiple_char(self, c, times):
        assert isinstance(c, self.tp)
        self.l.append(c * times)
        self._grow(times)

    def append_charpsize(self, s, size):
        assert size >= 0
        l = []
        for i in xrange(size):
            l.append(s[i])
        self.l.append(self.tp("").join(l))
        self._grow(size)

    def build(self):
        return self.tp("").join(self.l)

    def getlength(self):
        return len(self.build())


class StringBuilder(AbstractStringBuilder):
    tp = str


class UnicodeBuilder(AbstractStringBuilder):
    tp = unicode


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
        return SomeString()

    def rtyper_makerepr(self, rtyper):
        from rpython.rtyper.lltypesystem.rbuilder import stringbuilder_repr
        return stringbuilder_repr

    def rtyper_makekey(self):
        return self.__class__,


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
        return SomeUnicodeString()

    def rtyper_makerepr(self, rtyper):
        from rpython.rtyper.lltypesystem.rbuilder import unicodebuilder_repr
        return unicodebuilder_repr

    def rtyper_makekey(self):
        return self.__class__,


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


class __extend__(pairtype(SomeStringBuilder, SomePBC)):
    def union((sb, p)):
        assert p.const is None
        return SomeStringBuilder()


class __extend__(pairtype(SomePBC, SomeStringBuilder)):
    def union((p, sb)):
        assert p.const is None
        return SomeStringBuilder()


class __extend__(pairtype(SomeUnicodeBuilder, SomePBC)):
    def union((sb, p)):
        assert p.const is None
        return SomeUnicodeBuilder()


class __extend__(pairtype(SomePBC, SomeUnicodeBuilder)):
    def union((p, sb)):
        assert p.const is None
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


