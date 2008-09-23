
""" String builder interface
"""

from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation.model import SomeObject, SomeString, s_None,\
     SomeChar, SomeInteger, SomeUnicodeCodePoint, SomeUnicodeString

# -------------- public API ---------------------------------

INIT_SIZE = 100 # XXX tweak

class AbstractStringBuilder(object):
    def __init__(self, init_size=INIT_SIZE):
        self.l = []

    def append(self, s):
        self.l.append(s)

    def append_slice(self, s, start, end):
        self.l.append(s[start:end])

    def append_multiple_char(self, c, times):
        self.l.append(c * times)

class StringBuilder(AbstractStringBuilder):
    def build(self):
        return "".join(self.l)

class UnicodeBuilder(AbstractStringBuilder):
    def build(self):
        return u''.join(self.l)

# ------------------------------------------------------------
# ----------------- implementation details -------------------
# ------------------------------------------------------------

class SomeStringBuilder(SomeObject):
    def method_append(self, s_str):
        assert isinstance(s_str, (SomeString, SomeChar))
        return s_None

    def method_append_slice(self, s_str, s_start, s_end):
        assert isinstance(s_str, SomeString)
        assert isinstance(s_start, SomeInteger)
        assert isinstance(s_end, SomeInteger)
        assert s_start.nonneg
        assert s_end.nonneg
        return s_None

    def method_append_multiple_char(self, s_char, s_times):
        assert isinstance(s_char, SomeChar)
        assert isinstance(s_times, SomeInteger)
        assert s_times.nonneg
        return s_None

    def method_build(self):
        return SomeString()
    
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rbuilder.stringbuilder_repr

class SomeUnicodeBuilder(SomeObject):
    def method_append(self, s_str):
        assert isinstance(s_str, (SomeUnicodeCodePoint, SomeUnicodeString))
        return s_None

    def method_append_slice(self, s_str, s_start, s_end):
        assert isinstance(s_str, SomeUnicodeString)
        assert isinstance(s_start, SomeInteger)
        assert isinstance(s_end, SomeInteger)
        assert s_start.nonneg
        assert s_end.nonneg
        return s_None

    def method_append_multiple_char(self, s_char, s_times):
        assert isinstance(s_char, SomeUnicodeCodePoint)
        assert isinstance(s_times, SomeInteger)
        assert s_times.nonneg
        return s_None

    def method_build(self):
        return SomeUnicodeString()
    
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rbuilder.unicodebuilder_repr

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
